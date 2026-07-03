"""Background monitor thread with live state for the overlay."""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from typing import Callable

import mss
from PIL import Image

from cup_guard.core import (
    Baseline,
    Config,
    analyze_patch,
    calibrate_from_cursor,
    cancel_pending_grab,
    capture_is_blocked,
    capture_patch,
    cup_is_gone,
    cup_is_present,
    draw_preview_frame,
    handle_cup_transition,
    logical_monitor_rect,
    monitor_region,
    preview_region,
    press_e,
    press_q,
    schedule_random_grab,
)
from cup_guard.hotkey import ZeroHotkeyListener, create_zero_listener


@dataclass
class LiveState:
    armed: bool = False
    monitoring: bool = False
    blocked: bool = False
    cup_on_table: bool = False
    cup_gone: bool = False
    red_frac: float = 0.0
    red_excess: float = 0.0
    mean_r: float = 0.0
    e_presses: int = 0
    q_presses: int = 0
    message: str = "Hover over the bottom rim of the cup and press 0"
    preview: Image.Image | None = None
    monitor_rect: tuple[int, int, int, int] | None = None
    auto_e: bool = True
    auto_q: bool = True
    sensitivity: float = 0.52


class MonitorEngine:
    def __init__(self, on_state: Callable[[LiveState], None] | None = None) -> None:
        self._on_state = on_state
        self._state = LiveState()
        self._config: Config | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._monitor_thread: threading.Thread | None = None
        self._hotkey_listener: ZeroHotkeyListener | None = None
        self._state_queue: queue.Queue[LiveState] = queue.Queue(maxsize=1)

    @property
    def state(self) -> LiveState:
        with self._lock:
            return LiveState(**self._state.__dict__)

    def _emit(self, **updates: object) -> None:
        with self._lock:
            for key, value in updates.items():
                setattr(self._state, key, value)
            snapshot = LiveState(**self._state.__dict__)
        if self._on_state:
            try:
                self._on_state(snapshot)
            except Exception:
                pass
        try:
            while True:
                self._state_queue.get_nowait()
        except queue.Empty:
            pass
        try:
            self._state_queue.put_nowait(snapshot)
        except queue.Full:
            pass

    def poll_state(self) -> LiveState | None:
        try:
            return self._state_queue.get_nowait()
        except queue.Empty:
            return None

    def set_auto_e(self, enabled: bool) -> None:
        self._emit(auto_e=enabled)

    def set_auto_q(self, enabled: bool) -> None:
        self._emit(auto_q=enabled)

    def set_sensitivity(self, value: float) -> None:
        with self._lock:
            self._state.sensitivity = value
            if self._config is not None:
                self._config.sensitivity = value
                self._config.save()
        self._emit(sensitivity=value)

    def set_monitoring(self, enabled: bool) -> None:
        if enabled:
            if self._config is None or self._config.baseline is None:
                self._emit(
                    message="Hover over the bottom rim of the cup and press 0"
                )
                return
            self._start_monitor_loop()
        else:
            self._stop_monitor_loop()
            rect = None
            with self._lock:
                if self._config is not None and self._state.armed:
                    rect = logical_monitor_rect(self._config)
            self._emit(
                monitoring=False,
                monitor_rect=rect,
                message="Monitoring paused — press 0 to reposition",
            )

    def calibrate_now(self) -> bool:
        with self._lock:
            sensitivity = self._state.sensitivity
        self._stop_monitor_loop(wait=True)
        cancel_pending_grab()
        config = calibrate_from_cursor(sensitivity, save_debug=True)
        if config is None:
            self._emit(
                armed=False,
                monitoring=False,
                monitor_rect=None,
                message="No red detected — hover cup rim and press 0",
            )
            return False
        self._config = config
        rect = logical_monitor_rect(config)
        self._emit(
            armed=True,
            monitoring=True,
            blocked=False,
            cup_on_table=False,
            cup_gone=False,
            monitor_rect=rect,
            message="Calibrated — press 0 anytime to reposition",
            sensitivity=config.sensitivity,
        )
        self._restart_monitor_loop()
        return True

    def manual_press_e(self) -> None:
        press_e()
        with self._lock:
            count = self._state.e_presses + 1
        self._emit(e_presses=count, message=f"Manual E (#{count})")

    def manual_press_q(self) -> None:
        press_q()
        with self._lock:
            count = self._state.q_presses + 1
        self._emit(q_presses=count, message=f"Manual Q (#{count})")

    def start_hotkeys(self) -> None:
        if self._hotkey_listener is not None:
            return

        def on_zero() -> None:
            threading.Thread(target=self.calibrate_now, daemon=True).start()

        self._hotkey_listener = create_zero_listener(on_zero)
        self._hotkey_listener.start()
        self._emit(message="Hover over the bottom rim of the cup and press 0")

    def shutdown(self) -> None:
        self._stop.set()
        self._stop_monitor_loop()
        cancel_pending_grab()
        if self._hotkey_listener is not None:
            self._hotkey_listener.stop()
            self._hotkey_listener = None

    def _start_monitor_loop(self) -> None:
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._stop.clear()
            self._emit(monitoring=True)
            return
        self._stop.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def _stop_monitor_loop(self, *, wait: bool = False) -> None:
        self._stop.set()
        cancel_pending_grab()
        if wait and self._monitor_thread is not None and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.5)

    def _restart_monitor_loop(self) -> None:
        self._stop_monitor_loop(wait=True)
        self._monitor_thread = None
        self._stop.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def _monitor_loop(self) -> None:
        if self._config is None or self._config.baseline is None:
            return
        config = self._config
        baseline: Baseline = config.baseline
        cup_present = True
        missing_frames = 0
        last_press = 0.0
        presses = 0

        self._emit(
            monitoring=True,
            monitor_rect=logical_monitor_rect(config),
            message="Watching cup — press 0 to reposition",
        )

        with mss.MSS() as sct:
            while not self._stop.is_set():
                with self._lock:
                    auto_e = self._state.auto_e
                    auto_q = self._state.auto_q
                    config.sensitivity = self._state.sensitivity
                    if self._config is not config:
                        config = self._config
                        baseline = config.baseline  # type: ignore[assignment]
                        cup_present = True
                        missing_frames = 0

                region = monitor_region(config)
                preview_reg = preview_region(config)
                monitor_patch = capture_patch(sct, region)
                preview_patch = capture_patch(sct, preview_reg)
                blocked = capture_is_blocked(monitor_patch)

                if blocked:
                    self._emit(
                        blocked=True,
                        cup_on_table=False,
                        cup_gone=False,
                        message="Screen capture blocked — check permissions",
                        monitor_rect=logical_monitor_rect(config),
                        preview=draw_preview_frame(preview_patch, config),
                    )
                    time.sleep(0.05)
                    continue

                red_frac, red_excess, mean_r = analyze_patch(monitor_patch)
                present = cup_is_present(red_frac, baseline, config.sensitivity)
                gone = cup_is_gone(
                    red_frac, baseline, config.sensitivity, config.gone_boost
                )

                def on_e(count: int) -> None:
                    self._emit(
                        e_presses=count,
                        message=f"E pressed (#{count})",
                    )

                def on_q(delay: float) -> None:
                    with self._lock:
                        q_count = self._state.q_presses + 1
                    self._emit(
                        q_presses=q_count,
                        message=f"Q in {delay:.1f}s → pressed (#{q_count})",
                    )

                cup_present, missing_frames, last_press, presses = handle_cup_transition(
                    red_frac,
                    baseline,
                    cup_present,
                    missing_frames,
                    config,
                    last_press,
                    presses,
                    auto_e=auto_e,
                    auto_q=auto_q,
                    on_e_press=on_e,
                    on_q_scheduled=on_q,
                )

                self._emit(
                    blocked=False,
                    cup_on_table=present and not gone,
                    cup_gone=gone,
                    red_frac=red_frac,
                    red_excess=red_excess,
                    mean_r=mean_r,
                    e_presses=presses,
                    monitor_rect=logical_monitor_rect(config),
                    preview=draw_preview_frame(preview_patch, config),
                )

        cancel_pending_grab()
        rect = None
        with self._lock:
            if self._config is not None and self._state.armed:
                rect = logical_monitor_rect(self._config)
        self._emit(monitoring=False, monitor_rect=rect)
