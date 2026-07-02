"""Screen capture, calibration, and cup detection."""

from __future__ import annotations

import json
import os
import random
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import mss
import numpy as np
from PIL import Image, ImageDraw
from pynput import keyboard, mouse
from pynput.keyboard import Controller as KeyboardController, Key

from cup_guard.paths import config_path, debug_image_path

DEFAULT_REGION_WIDTH = 90
DEFAULT_REGION_HEIGHT = 16
DEBUG_CONTEXT_WIDTH = 200
DEBUG_CONTEXT_HEIGHT = 120
PREVIEW_CONTEXT_WIDTH = 160
PREVIEW_CONTEXT_HEIGHT = 96
CURSOR_OFFSET_Y = -12
GRAB_Q_MIN_DELAY_S = 2.5
GRAB_Q_MAX_DELAY_S = 4.0

_grab_timer: threading.Timer | None = None
_grab_timer_lock = threading.Lock()


@dataclass
class Baseline:
    red_frac: float
    red_excess: float
    mean_r: float


@dataclass
class Config:
    x: float
    y: float
    width: int = DEFAULT_REGION_WIDTH
    height: int = DEFAULT_REGION_HEIGHT
    scale: float = 1.0
    baseline: Baseline | None = None
    sensitivity: float = 0.52
    gone_boost: float = 0.07
    confirm_frames: int = 1
    cooldown_s: float = 0.12

    @classmethod
    def load(cls, path: Path | None = None) -> Config | None:
        path = path or config_path()
        if not path.exists():
            legacy = Path.cwd() / "config.json"
            if legacy.exists():
                import shutil

                shutil.copy(legacy, path)
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        baseline = data.get("baseline")
        if baseline is not None:
            baseline = Baseline(**baseline)
        return cls(
            x=data["x"],
            y=data["y"],
            width=data.get("width", DEFAULT_REGION_WIDTH),
            height=data.get("height", DEFAULT_REGION_HEIGHT),
            scale=data.get("scale", 1.0),
            baseline=baseline,
            sensitivity=data.get("sensitivity", 0.52),
            gone_boost=data.get("gone_boost", 0.07),
            confirm_frames=data.get("confirm_frames", 1),
            cooldown_s=data.get("cooldown_s", 0.12),
        )

    def save(self, path: Path | None = None) -> None:
        path = path or config_path()
        path.write_text(json.dumps(asdict(self), indent=2))


def sample_point(cursor_x: float, cursor_y: float) -> tuple[float, float]:
    return cursor_x, cursor_y + CURSOR_OFFSET_Y


def screen_scale() -> float:
    if sys.platform != "darwin":
        return 1.0
    try:
        from AppKit import NSScreen

        return float(NSScreen.mainScreen().backingScaleFactor())
    except Exception:
        return 1.0


def to_capture_coords(x: float, y: float, scale: float) -> tuple[int, int]:
    return int(round(x * scale)), int(round(y * scale))


def monitor_region(config: Config) -> dict[str, int]:
    x, y = to_capture_coords(config.x, config.y, config.scale)
    half_w = config.width // 2
    half_h = config.height // 2
    return {
        "left": x - half_w,
        "top": y - half_h,
        "width": config.width,
        "height": config.height,
    }


def logical_monitor_rect(config: Config) -> tuple[int, int, int, int]:
    """Monitor box as left, top, width, height in logical screen pixels."""
    width = max(1, int(round(config.width / config.scale)))
    height = max(1, int(round(config.height / config.scale)))
    left = int(round(config.x - width / 2))
    top = int(round(config.y - height / 2))
    return left, top, width, height


def preview_region(config: Config) -> dict[str, int]:
    x, y = to_capture_coords(config.x, config.y, config.scale)
    return {
        "left": x - PREVIEW_CONTEXT_WIDTH // 2,
        "top": y - PREVIEW_CONTEXT_HEIGHT // 2,
        "width": PREVIEW_CONTEXT_WIDTH,
        "height": PREVIEW_CONTEXT_HEIGHT,
    }


def analyze_patch(patch: np.ndarray) -> tuple[float, float, float]:
    r = patch[:, :, 0].astype(np.float32)
    g = patch[:, :, 1].astype(np.float32)
    b = patch[:, :, 2].astype(np.float32)
    bright_red = (r > 110) & (r > g + 12) & (r > b + 12)
    dark_red = (r > 80) & (r > g + 8) & (r > b + 8) & (r >= g) & (r >= b)
    red_mask = bright_red | dark_red
    return float(red_mask.mean()), float((r - np.maximum(g, b)).mean()), float(r.mean())


def calibration_is_valid(metrics: tuple[float, float, float]) -> bool:
    red_frac, red_excess, mean_r = metrics
    if red_frac >= 0.08:
        return True
    return mean_r >= 120 and red_excess >= 25


def cup_is_present(
    red_frac: float,
    baseline: Baseline,
    sensitivity: float,
) -> bool:
    return red_frac >= baseline.red_frac * sensitivity


def cup_is_gone(
    red_frac: float,
    baseline: Baseline,
    sensitivity: float,
    gone_boost: float,
) -> bool:
    return red_frac < baseline.red_frac * (sensitivity + gone_boost)


def capture_patch(sct: mss.MSS, region: dict[str, int]) -> np.ndarray:
    shot = sct.grab(region)
    bgra = np.array(shot)
    return bgra[:, :, [2, 1, 0]]


def capture_is_blocked(patch: np.ndarray) -> bool:
    if patch.size == 0:
        return True
    pixels = patch.reshape(-1, 3).astype(np.float32)
    if ((pixels > 250).all(axis=1)).mean() > 0.85:
        return True
    return float(pixels.std()) < 2.0


def app_name() -> str:
    if getattr(sys, "frozen", False):
        return "Cup Guard"
    term = os.environ.get("TERM_PROGRAM", "")
    if term == "Apple_Terminal":
        return "Terminal"
    if term == "iTerm.app":
        return "iTerm"
    if term == "vscode":
        return "Cursor"
    return "Cup Guard"


def open_screen_recording_settings() -> None:
    if sys.platform == "darwin":
        subprocess.run(
            [
                "open",
                "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
            ],
            check=False,
        )
    elif sys.platform == "win32":
        subprocess.run(["start", "ms-settings:privacy"], shell=True, check=False)


def open_accessibility_settings() -> None:
    if sys.platform == "darwin":
        subprocess.run(
            [
                "open",
                "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
            ],
            check=False,
        )
    elif sys.platform == "win32":
        subprocess.run(["start", "ms-settings:privacy"], shell=True, check=False)


_MAC_VK = {"e": 14, "q": 12}


def press_key(char: str) -> None:
    if sys.platform == "darwin":
        try:
            from Quartz import CGEventCreateKeyboardEvent, CGEventPost, kCGHIDEventTap

            code = _MAC_VK.get(char.lower(), 0)
            down = CGEventCreateKeyboardEvent(None, code, True)
            up = CGEventCreateKeyboardEvent(None, code, False)
            CGEventPost(kCGHIDEventTap, down)
            CGEventPost(kCGHIDEventTap, up)
            return
        except Exception:
            pass
    kb = KeyboardController()
    kb.press(char)
    kb.release(char)


def press_e() -> None:
    press_key("e")


def press_q() -> None:
    press_key("q")


def cancel_pending_grab() -> None:
    global _grab_timer
    with _grab_timer_lock:
        if _grab_timer is not None:
            _grab_timer.cancel()
            _grab_timer = None


def schedule_random_grab(
    *,
    enabled: bool,
    min_delay: float = GRAB_Q_MIN_DELAY_S,
    max_delay: float = GRAB_Q_MAX_DELAY_S,
    on_grab: Callable[[float], None] | None = None,
) -> float | None:
    if not enabled:
        return None
    global _grab_timer
    delay = random.uniform(min_delay, max_delay)

    def grab_cup() -> None:
        press_q()
        if on_grab:
            on_grab(delay)

    with _grab_timer_lock:
        if _grab_timer is not None:
            _grab_timer.cancel()
        _grab_timer = threading.Timer(delay, grab_cup)
        _grab_timer.daemon = True
        _grab_timer.start()
    return delay


def save_calibration_debug(
    context_patch: np.ndarray,
    sample_center_x: int,
    sample_center_y: int,
    cursor_x: int | None = None,
    cursor_y: int | None = None,
) -> None:
    image = Image.fromarray(context_patch)
    draw = ImageDraw.Draw(image)
    half_w = DEFAULT_REGION_WIDTH // 2
    half_h = DEFAULT_REGION_HEIGHT // 2
    draw.rectangle(
        [
            sample_center_x - half_w,
            sample_center_y - half_h,
            sample_center_x + half_w,
            sample_center_y + half_h,
        ],
        outline=(0, 255, 0),
        width=2,
    )
    if cursor_x is not None and cursor_y is not None:
        draw.line(
            [cursor_x - 8, cursor_y, cursor_x + 8, cursor_y],
            fill=(255, 255, 0),
            width=2,
        )
        draw.line(
            [cursor_x, cursor_y - 8, cursor_x, cursor_y + 8],
            fill=(255, 255, 0),
            width=2,
        )
    image.save(debug_image_path())


def detect_capture_scale(logical_x: float, logical_y: float) -> float:
    retina = screen_scale()
    candidates = [1.0]
    if retina not in candidates:
        candidates.append(retina)
    best_scale = 1.0
    best_variance = -1.0
    with mss.MSS() as sct:
        for scale in candidates:
            cap_x, cap_y = to_capture_coords(logical_x, logical_y, scale)
            region = {
                "left": cap_x - 20,
                "top": cap_y - 20,
                "width": 40,
                "height": 40,
            }
            try:
                patch = capture_patch(sct, region)
            except Exception:
                continue
            if patch.size == 0 or capture_is_blocked(patch):
                continue
            variance = float(patch.astype(np.float32).std())
            if variance > best_variance:
                best_variance = variance
                best_scale = scale
    return best_scale


def calibrate_from_cursor(
    sensitivity: float = 0.52,
    *,
    save_debug: bool = True,
) -> Config | None:
    controller = mouse.Controller()
    mouse_x, mouse_y = controller.position
    sample_x, sample_y = sample_point(mouse_x, mouse_y)
    scale = detect_capture_scale(sample_x, sample_y)
    config = Config(x=sample_x, y=sample_y, scale=scale, sensitivity=sensitivity)
    region = monitor_region(config)
    cap_x, cap_y = to_capture_coords(sample_x, sample_y, scale)
    cursor_cap_x, cursor_cap_y = to_capture_coords(mouse_x, mouse_y, scale)
    context_region = {
        "left": cap_x - DEBUG_CONTEXT_WIDTH // 2,
        "top": cap_y - DEBUG_CONTEXT_HEIGHT // 2,
        "width": DEBUG_CONTEXT_WIDTH,
        "height": DEBUG_CONTEXT_HEIGHT,
    }
    with mss.MSS() as sct:
        monitor_patch = capture_patch(sct, region)
        context_patch = capture_patch(sct, context_region)
    if save_debug:
        save_calibration_debug(
            context_patch,
            cap_x - context_region["left"],
            cap_y - context_region["top"],
            cursor_cap_x - context_region["left"],
            cursor_cap_y - context_region["top"],
        )
    if capture_is_blocked(monitor_patch):
        return None
    metrics = analyze_patch(monitor_patch)
    if not calibration_is_valid(metrics):
        return None
    red_frac, red_excess, mean_r = metrics
    config.baseline = Baseline(red_frac=red_frac, red_excess=red_excess, mean_r=mean_r)
    config.save()
    return config


def handle_cup_transition(
    red_frac: float,
    baseline: Baseline,
    cup_present: bool,
    missing_frames: int,
    config: Config,
    last_press: float,
    presses: int,
    *,
    auto_e: bool,
    auto_q: bool,
    on_e_press: Callable[[int], None] | None = None,
    on_q_scheduled: Callable[[float], None] | None = None,
) -> tuple[bool, int, float, int]:
    present = cup_is_present(red_frac, baseline, config.sensitivity)
    gone = cup_is_gone(red_frac, baseline, config.sensitivity, config.gone_boost)
    if present and not gone:
        return True, 0, last_press, presses
    missing_frames += 1
    if auto_e and cup_present and gone and missing_frames >= config.confirm_frames:
        now = time.perf_counter()
        if now - last_press >= config.cooldown_s:
            press_e()
            schedule_random_grab(enabled=auto_q, on_grab=on_q_scheduled)
            last_press = now
            presses += 1
            if on_e_press:
                on_e_press(presses)
        return False, missing_frames, last_press, presses
    if gone and missing_frames >= config.confirm_frames:
        return False, missing_frames, last_press, presses
    return cup_present, missing_frames, last_press, presses


def is_zero_key(key: keyboard.Key | keyboard.KeyCode) -> bool:
    if getattr(key, "char", None) == "0":
        return True
    if isinstance(key, keyboard.KeyCode) and key.vk in (29, 82):
        return True
    return False


def draw_preview_frame(preview_patch: np.ndarray, config: Config) -> Image.Image:
    image = Image.fromarray(preview_patch.copy())
    draw = ImageDraw.Draw(image)
    region = preview_region(config)
    monitor = monitor_region(config)
    px = monitor["left"] - region["left"]
    py = monitor["top"] - region["top"]
    draw.rectangle(
        [px, py, px + monitor["width"], py + monitor["height"]],
        outline=(0, 255, 80),
        width=2,
    )
    return image
