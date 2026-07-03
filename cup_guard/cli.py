"""CLI entry points (legacy terminal mode)."""

from __future__ import annotations

import argparse
import sys
import threading
import time

from PIL import Image
from pynput import keyboard, mouse
from pynput.keyboard import Key

import mss

from cup_guard.core import (
    Config,
    calibrate_from_cursor,
    capture_is_blocked,
    capture_patch,
    config_path,
    debug_image_path,
    detect_capture_scale,
    is_zero_key,
    open_screen_recording_settings,
    to_capture_coords,
)
from cup_guard.crash_report import check_mac_compatibility, notify, report_exception
from cup_guard.engine import MonitorEngine


def calibrate(args: argparse.Namespace) -> int:
    print("Calibration — hover cup rim, waiting 3s…")
    for remaining in range(3, 0, -1):
        print(f"  {remaining}…", flush=True)
        time.sleep(1)
    if calibrate_from_cursor(args.sensitivity) is None:
        print(f"Failed. See {debug_image_path()}")
        return 1
    print(f"Saved to {config_path()}")
    return 0


def test_capture(_args: argparse.Namespace) -> int:
    pos = mouse.Controller().position
    scale = detect_capture_scale(pos[0], pos[1])
    cap_x, cap_y = to_capture_coords(pos[0], pos[1], scale)
    region = {"left": cap_x - 250, "top": cap_y - 150, "width": 500, "height": 300}
    with mss.MSS() as sct:
        patch = capture_patch(sct, region)
    out = config_path().parent / "screen_test.png"
    Image.fromarray(patch).save(out)
    if capture_is_blocked(patch):
        print(f"BLOCKED — saved {out}")
        open_screen_recording_settings()
        return 1
    print(f"OK — saved {out}")
    return 0


def preview(args: argparse.Namespace) -> int:
    config = Config.load()
    if config is None or config.baseline is None:
        print("No calibration. Launch the overlay or run: cup-guard calibrate")
        return 1

    engine = MonitorEngine(
        on_state=lambda s: print(
            f"\r{'ON' if s.cup_on_table else 'GONE'} rf={s.red_frac:.2f}   ",
            end="",
            flush=True,
        )
    )
    engine._config = config
    engine._state.armed = True
    engine._state.auto_e = not args.no_press
    engine.set_monitoring(True)
    try:
        while True:
            time.sleep(0.2)
    except KeyboardInterrupt:
        engine.shutdown()
        print()
    return 0


def wait_for_arm_key_or_esc() -> str | None:
    result = {"value": None}

    def on_press(key: keyboard.Key | keyboard.KeyCode) -> bool | None:
        if is_zero_key(key):
            result["value"] = "arm"
            return False
        if key == Key.esc:
            result["value"] = "esc"
            return False
        return None

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()
    return result["value"]


def start_cli(args: argparse.Namespace) -> int:
    print("Cup Guard CLI — press 0 on cup rim to arm, ESC to quit")
    engine = MonitorEngine(
        on_state=lambda s: print(
            f"\r{'ON' if s.cup_on_table else 'GONE'} E={s.e_presses}   ",
            end="",
            flush=True,
        )
    )
    engine._state.sensitivity = args.sensitivity

    while True:
        action = wait_for_arm_key_or_esc()
        if action != "arm":
            engine.shutdown()
            return 0
        if not engine.calibrate_now():
            print("No red — try again")
            continue

        stop = threading.Event()

        def on_press(key: keyboard.Key | keyboard.KeyCode) -> bool | None:
            if key == Key.esc:
                stop.set()
                return False
            return None

        listener = keyboard.Listener(on_press=on_press)
        listener.start()
        while not stop.is_set():
            time.sleep(0.05)
        engine.set_monitoring(False)
        listener.stop()
        print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cup Guard — Roblox cup detector")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("gui", help="Launch overlay app (default)")
    p = sub.add_parser("start", help="CLI: press 0 to arm")
    p.add_argument("--sensitivity", type=float, default=0.52)
    c = sub.add_parser("calibrate")
    c.add_argument("--sensitivity", type=float, default=0.52)
    prev = sub.add_parser("preview")
    prev.add_argument("--no-press", action="store_true")
    sub.add_parser("test-capture")
    return parser


def main() -> None:
    from cup_guard.crash_report import install_handlers

    install_handlers()
    compat = check_mac_compatibility()
    if compat is not None:
        notify("Cup Guard cannot run", compat)
        raise SystemExit(1)

    parser = build_parser()
    parser.set_defaults(command="gui")
    args = parser.parse_args()
    try:
        if args.command == "gui":
            from cup_guard.overlay import run_overlay

            run_overlay()
            return
        if args.command == "start":
            raise SystemExit(start_cli(args))
        if args.command == "calibrate":
            raise SystemExit(calibrate(args))
        if args.command == "preview":
            raise SystemExit(preview(args))
        if args.command == "test-capture":
            raise SystemExit(test_capture(args))
        parser.print_help()
    except Exception:
        report_exception(*sys.exc_info())
        raise SystemExit(1)


if __name__ == "__main__":
    main()
