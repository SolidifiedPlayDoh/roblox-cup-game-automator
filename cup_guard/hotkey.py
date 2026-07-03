"""Global 0-key listener.

On macOS we use a Quartz event tap that reads raw keycodes only. pynput's
listener calls Text Input Source APIs from a background thread, which crashes
on recent macOS when the app is launched as a GUI .app bundle.
"""

from __future__ import annotations

import sys
import threading
from typing import Callable, Protocol


class ZeroHotkeyListener(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...


def create_zero_listener(on_zero: Callable[[], None]) -> ZeroHotkeyListener:
    if sys.platform == "darwin":
        return _DarwinZeroListener(on_zero)
    return _PynputZeroListener(on_zero)


class _PynputZeroListener:
    def __init__(self, on_zero: Callable[[], None]) -> None:
        from pynput import keyboard

        self._on_zero = on_zero
        self._keyboard = keyboard

        def on_press(key: keyboard.Key | keyboard.KeyCode) -> None:
            from cup_guard.core import is_zero_key

            if is_zero_key(key):
                self._on_zero()
            return None

        self._listener = keyboard.Listener(on_press=on_press)

    def start(self) -> None:
        self._listener.start()

    def stop(self) -> None:
        self._listener.stop()


class _DarwinZeroListener:
    # kVK_ANSI_0 and kVK_Keypad0
    _ZERO_KEYCODES = frozenset({29, 82})

    def __init__(self, on_zero: Callable[[], None]) -> None:
        self._on_zero = on_zero
        self._running = False
        self._thread: threading.Thread | None = None
        self._loop = None
        self._handler_ref = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, name="zero-hotkey", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._loop is not None:
            try:
                from Quartz import CFRunLoopStop

                CFRunLoopStop(self._loop)
            except Exception:
                pass
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _handler(self, _proxy, event_type, event, _refcon):
        from Quartz import (
            CGEventGetIntegerValueField,
            kCGEventKeyDown,
            kCGKeyboardEventKeycode,
        )

        if event_type == kCGEventKeyDown:
            vk = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
            if vk in self._ZERO_KEYCODES:
                self._on_zero()
        return event

    def _run(self) -> None:
        from Quartz import (
            CFMachPortCreateRunLoopSource,
            CFRunLoopAddSource,
            CFRunLoopGetCurrent,
            CFRunLoopRunInMode,
            CGEventMaskBit,
            CGEventTapCreate,
            CGEventTapEnable,
            kCFRunLoopDefaultMode,
            kCFRunLoopRunTimedOut,
            kCGEventKeyDown,
            kCGEventTapOptionListenOnly,
            kCGHeadInsertEventTap,
            kCGSessionEventTap,
        )

        self._handler_ref = self._handler
        mask = CGEventMaskBit(kCGEventKeyDown)
        tap = CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionListenOnly,
            mask,
            self._handler_ref,
            None,
        )
        if tap is None:
            return

        loop_source = CFMachPortCreateRunLoopSource(None, tap, 0)
        self._loop = CFRunLoopGetCurrent()
        CFRunLoopAddSource(self._loop, loop_source, kCFRunLoopDefaultMode)
        CGEventTapEnable(tap, True)

        while self._running:
            result = CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.25, False)
            if result != kCFRunLoopRunTimedOut:
                break

        self._loop = None
        self._handler_ref = None
