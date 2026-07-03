"""Always-on-top overlay for Cup Guard."""

from __future__ import annotations

import sys
from pathlib import Path

import customtkinter as ctk
from PIL import Image

from cup_guard.engine import LiveState, MonitorEngine
from cup_guard.paths import asset_path

OVERLAY_WIDTH = 300
OVERLAY_MARGIN = 16
PREVIEW_W = 268
PREVIEW_H = 140
IDLE_PREVIEW_TEXT = "Hover over the bottom rim\nof the cup and press 0"
HELP_IMAGE_WIDTH = 260


class HelpWindow(ctk.CTkToplevel):
    def __init__(self, master: ctk.CTk) -> None:
        super().__init__(master)
        self.title("How to calibrate")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self._images: list[ctk.CTkImage] = []

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=14)

        ctk.CTkLabel(
            body,
            text="How to calibrate",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(anchor="w", pady=(0, 8))

        ctk.CTkLabel(
            body,
            text=(
                "Put your mouse on the bottom rim of the red cup — exactly where "
                "the cursor is in the screenshot below. Press 0 and the green "
                "rectangle will appear in the live preview when you're locked on."
            ),
            wraplength=HELP_IMAGE_WIDTH,
            justify="left",
            font=ctk.CTkFont(size=13),
        ).pack(anchor="w", pady=(0, 12))

        ctk.CTkLabel(
            body,
            text="1. Hover here, then press 0",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#aaaaaa",
        ).pack(anchor="w", pady=(0, 4))
        self._add_image(body, asset_path("help_cursor.png"))

        ctk.CTkLabel(
            body,
            text="2. Success — green box in the preview, status shows CUP ON",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#aaaaaa",
        ).pack(anchor="w", pady=(12, 4))
        self._add_image(body, asset_path("help_success.png"))

        ctk.CTkButton(body, text="Got it", command=self.destroy, height=34).pack(
            fill="x", pady=(16, 4)
        )

        self.update_idletasks()
        self.geometry(f"{HELP_IMAGE_WIDTH + 56}x{self.winfo_reqheight() + 28}")
        self.transient(master)
        self.focus_force()

    def _add_image(self, parent: ctk.CTkFrame, path: Path) -> None:
        image = Image.open(path)
        scale = HELP_IMAGE_WIDTH / image.width
        height = max(1, int(image.height * scale))
        scaled = image.resize((HELP_IMAGE_WIDTH, height), Image.Resampling.LANCZOS)
        ctk_image = ctk.CTkImage(
            light_image=scaled,
            dark_image=scaled,
            size=(HELP_IMAGE_WIDTH, height),
        )
        self._images.append(ctk_image)
        ctk.CTkLabel(parent, text="", image=ctk_image).pack(anchor="w")


class OverlayApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Cup Guard")
        self.geometry(f"{OVERLAY_WIDTH}x548")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self._place_top_right()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        self.engine = MonitorEngine()
        self._preview_image: ctk.CTkImage | None = None
        self._updating = False
        self._help_window: HelpWindow | None = None

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(250, self.engine.start_hotkeys)
        self.after(33, self._tick)

    def _place_top_right(self) -> None:
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        x = max(0, sw - OVERLAY_WIDTH - OVERLAY_MARGIN)
        self.geometry(f"{OVERLAY_WIDTH}x548+{x}+{OVERLAY_MARGIN}")

    def _build_ui(self) -> None:
        pad = {"padx": 14, "pady": (6, 4)}

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", **pad)
        ctk.CTkLabel(
            header,
            text="Cup Guard",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(side="left")
        self.status_pill = ctk.CTkLabel(
            header,
            text="WAITING",
            width=90,
            fg_color="#444444",
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.status_pill.pack(side="right")

        self.preview_section = ctk.CTkFrame(self, fg_color="transparent")
        self.preview_section.pack(fill="x", **pad)

        self.preview_label = ctk.CTkLabel(
            self.preview_section,
            text=IDLE_PREVIEW_TEXT,
            width=PREVIEW_W,
            height=PREVIEW_H,
            wraplength=PREVIEW_W - 24,
            font=ctk.CTkFont(size=13),
            text_color="#cccccc",
            fg_color="#1a1a1a",
            corner_radius=8,
        )
        self.preview_label.pack()

        self.help_btn = ctk.CTkButton(
            self.preview_section,
            text="Need help?",
            height=28,
            fg_color="transparent",
            border_width=1,
            border_color="#555555",
            hover_color="#2a2a2a",
            text_color="#aaaaaa",
            font=ctk.CTkFont(size=12),
            command=self._show_help,
        )
        self.help_btn.pack(pady=(6, 0))

        stats = ctk.CTkFrame(self)
        stats.pack(fill="x", padx=14, pady=4)
        self.red_label = ctk.CTkLabel(stats, text="red: —", anchor="w")
        self.red_label.pack(fill="x", padx=10, pady=2)
        self.excess_label = ctk.CTkLabel(stats, text="excess: —", anchor="w")
        self.excess_label.pack(fill="x", padx=10, pady=2)
        self.mean_label = ctk.CTkLabel(stats, text="mean R: —", anchor="w")
        self.mean_label.pack(fill="x", padx=10, pady=2)
        self.count_label = ctk.CTkLabel(stats, text="E: 0   Q: 0", anchor="w")
        self.count_label.pack(fill="x", padx=10, pady=(2, 8))

        toggles = ctk.CTkFrame(self, fg_color="transparent")
        toggles.pack(fill="x", padx=14, pady=4)
        self.monitor_var = ctk.BooleanVar(value=False)
        self.auto_e_var = ctk.BooleanVar(value=True)
        self.auto_q_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(
            toggles,
            text="Monitoring",
            variable=self.monitor_var,
            command=self._on_monitor_toggle,
        ).pack(fill="x", pady=3)
        ctk.CTkSwitch(
            toggles,
            text="Auto-press E",
            variable=self.auto_e_var,
            command=lambda: self.engine.set_auto_e(self.auto_e_var.get()),
        ).pack(fill="x", pady=3)
        ctk.CTkSwitch(
            toggles,
            text="Auto-press Q after E",
            variable=self.auto_q_var,
            command=lambda: self.engine.set_auto_q(self.auto_q_var.get()),
        ).pack(fill="x", pady=3)

        sens_row = ctk.CTkFrame(self, fg_color="transparent")
        sens_row.pack(fill="x", padx=14, pady=6)
        ctk.CTkLabel(sens_row, text="Sensitivity").pack(anchor="w")
        self.sens_slider = ctk.CTkSlider(
            sens_row,
            from_=0.35,
            to=0.75,
            number_of_steps=40,
            command=self._on_sensitivity,
        )
        self.sens_slider.set(0.52)
        self.sens_slider.pack(fill="x", pady=(4, 0))
        self.sens_value = ctk.CTkLabel(sens_row, text="0.52")
        self.sens_value.pack(anchor="e")

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=8)
        ctk.CTkButton(
            btn_row,
            text="Arm (0)",
            command=self._arm,
            height=36,
        ).pack(fill="x", pady=2)
        manual = ctk.CTkFrame(btn_row, fg_color="transparent")
        manual.pack(fill="x", pady=2)
        ctk.CTkButton(
            manual,
            text="E",
            width=80,
            command=self.engine.manual_press_e,
        ).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(
            manual,
            text="Q",
            width=80,
            command=self.engine.manual_press_q,
        ).pack(side="left", expand=True, fill="x", padx=(4, 0))

        self.message_label = ctk.CTkLabel(
            self,
            text="",
            wraplength=OVERLAY_WIDTH - 28,
            text_color="#aaaaaa",
            font=ctk.CTkFont(size=11),
        )
        self.message_label.pack(padx=14, pady=(4, 12))

    def _show_help(self) -> None:
        if self._help_window is not None and self._help_window.winfo_exists():
            self._help_window.focus_force()
            self._help_window.lift()
            return
        self._help_window = HelpWindow(self)
        self._help_window.protocol("WM_DELETE_WINDOW", self._close_help)

    def _close_help(self) -> None:
        if self._help_window is not None:
            self._help_window.destroy()
            self._help_window = None

    def _on_monitor_toggle(self) -> None:
        if self._updating:
            return
        self.engine.set_monitoring(self.monitor_var.get())

    def _on_sensitivity(self, value: float) -> None:
        self.sens_value.configure(text=f"{value:.2f}")
        self.engine.set_sensitivity(value)

    def _arm(self) -> None:
        if self.engine.calibrate_now():
            self.monitor_var.set(True)

    def _set_idle_preview(self) -> None:
        self._preview_image = None
        self.preview_label.configure(
            image=None,
            text=IDLE_PREVIEW_TEXT,
            fg_color="#1a1a1a",
        )
        if not self.help_btn.winfo_ismapped():
            self.help_btn.pack(pady=(6, 0))

    def _set_live_preview(self, state: LiveState) -> None:
        self.help_btn.pack_forget()
        self.preview_label.configure(text="", fg_color="transparent")
        if state.preview is not None:
            scaled = state.preview.resize(
                (PREVIEW_W, PREVIEW_H), Image.Resampling.NEAREST
            )
            self._preview_image = ctk.CTkImage(
                light_image=scaled,
                dark_image=scaled,
                size=(PREVIEW_W, PREVIEW_H),
            )
            self.preview_label.configure(image=self._preview_image)

    def _apply_state(self, state: LiveState) -> None:
        if state.blocked:
            self.status_pill.configure(text="BLOCKED", fg_color="#884400")
        elif not state.armed:
            self.status_pill.configure(text="WAITING", fg_color="#444444")
        elif state.cup_on_table:
            self.status_pill.configure(text="CUP ON", fg_color="#1a7f37")
        else:
            self.status_pill.configure(text="CUP GONE", fg_color="#b62324")

        self.red_label.configure(text=f"red_frac: {state.red_frac:.2f}")
        self.excess_label.configure(text=f"red_excess: {state.red_excess:.1f}")
        self.mean_label.configure(text=f"mean R: {state.mean_r:.0f}")
        self.count_label.configure(text=f"E: {state.e_presses}   Q: {state.q_presses}")
        self.message_label.configure(text=state.message)

        if not state.armed:
            self._set_idle_preview()
        else:
            self._set_live_preview(state)

        self.auto_e_var.set(state.auto_e)
        self.auto_q_var.set(state.auto_q)
        self._updating = True
        self.monitor_var.set(state.monitoring)
        self._updating = False
        if abs(self.sens_slider.get() - state.sensitivity) > 0.01:
            self.sens_slider.set(state.sensitivity)
            self.sens_value.configure(text=f"{state.sensitivity:.2f}")

    def _tick(self) -> None:
        state = self.engine.poll_state()
        if state is None:
            state = self.engine.state
        self._apply_state(state)
        self.after(33, self._tick)

    def _on_close(self) -> None:
        self._close_help()
        self.engine.shutdown()
        self.destroy()


def run_overlay() -> None:
    if sys.platform == "darwin":
        try:
            from ctypes import cdll

            cdll.LoadLibrary("/System/Library/Frameworks/Cocoa.framework/Cocoa")
        except Exception:
            pass
    app = OverlayApp()
    app.mainloop()


if __name__ == "__main__":
    run_overlay()
