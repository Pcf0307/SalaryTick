from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from .display_service import (
    DisplayArea,
    area_for_window,
    get_display_areas,
    restore_visible_position,
)
from .window_state_rules import floating_menu_position


class FloatingWindow:
    def __init__(
        self,
        parent: tk.Misc,
        amount_getter: Callable[[], str],
        duration_getter: Callable[[], str],
        hidden_getter: Callable[[], bool],
        toggle_amount: Callable[[], None],
        refresh_interval_getter: Callable[[], int],
        open_main: Callable[[], None] | None = None,
        exit_app: Callable[[], None] | None = None,
        shift_expected: Callable[[int], None] | None = None,
        open_settings: Callable[[], None] | None = None,
        open_overtime_details: Callable[[], None] | None = None,
        open_overtime_editor: Callable[[], None] | None = None,
        expected_end_getter: Callable[[], str] | None = None,
        i18n=None,
    ):
        self.parent = parent
        self.amount_getter = amount_getter
        self.duration_getter = duration_getter
        self.hidden_getter = hidden_getter
        self.toggle_amount = toggle_amount
        self.refresh_interval_getter = refresh_interval_getter
        self.open_main = open_main
        self.exit_app = exit_app
        self.shift_expected = shift_expected
        self.open_settings = open_settings
        self.open_overtime_details = open_overtime_details
        self.open_overtime_editor = open_overtime_editor
        self.expected_end_getter = expected_end_getter
        self.i18n = i18n
        self._ = i18n.t if i18n else (lambda text: text)
        self.font_name = i18n.font_name if i18n else "Microsoft YaHei UI"
        self.window: tk.Toplevel | None = None
        self.timer_id: str | None = None
        self._drag_x = 0
        self._drag_y = 0
        self.last_x = 30
        self.last_y = 30
        self.menu_window: tk.Toplevel | None = None
        self.menu_action_in_progress = False

    @property
    def is_open(self) -> bool:
        try:
            return self.window is not None and bool(self.window.winfo_exists())
        except tk.TclError:
            return False

    def open(self, x: int = 30, y: int = 30) -> None:
        if self.is_open:
            self.window.lift()
            return
        displays = self._display_areas()
        x, y = restore_visible_position(int(x), int(y), 300, 102, displays)
        self.last_x, self.last_y = x, y
        window = tk.Toplevel(self.parent)
        self.window = window
        window.overrideredirect(True)
        window.attributes("-topmost", True)
        window.wm_attributes("-transparentcolor", "#ff00ff")
        window.configure(bg="#ff00ff")
        window.geometry(f"300x102+{x}+{y}")

        canvas = tk.Canvas(window, width=300, height=102, bg="#ff00ff", highlightthickness=0)
        canvas.pack()
        self._round_rect(canvas, 3, 3, 297, 99, 20, fill="#111827", outline="#273449")
        amount = canvas.create_text(126, 34, fill="#f8fafc", font=(self.font_name, 16, "bold"))
        duration = canvas.create_text(126, 70, fill="#cbd5e1", font=(self.font_name, 11))
        eye_hit = canvas.create_rectangle(252, 18, 294, 60, fill="#111827", outline="")
        eye_bg = canvas.create_oval(258, 25, 286, 53, fill="#1f2937", outline="#475569")
        eye = canvas.create_oval(265, 33, 279, 45, outline="#cbd5e1", width=2)
        pupil = canvas.create_oval(270, 37, 274, 41, fill="#cbd5e1", outline="")

        def update() -> None:
            self.timer_id = None
            if self.window is not window or not self.is_open:
                return
            canvas.itemconfigure(amount, text=self.amount_getter())
            canvas.itemconfigure(duration, text=self.duration_getter())
            color = "#64748b" if self.hidden_getter() else "#f8fafc"
            canvas.itemconfigure(eye, outline=color)
            canvas.itemconfigure(pupil, fill=color)
            self.timer_id = window.after(self.refresh_interval_getter(), update)

        def toggle_eye(_event=None):
            self.toggle_amount()
            return "break"

        for item in (eye_hit, eye_bg, eye, pupil):
            canvas.tag_bind(item, "<Button-1>", toggle_eye)
        def close_menu() -> None:
            popup = self.menu_window
            self.menu_action_in_progress = False
            self.menu_window = None
            if popup is not None:
                try:
                    if popup.winfo_exists():
                        popup.destroy()
                except tk.TclError:
                    pass

        def run_modal_action(action: Callable[[], None] | None) -> None:
            # Destroy only this popup. Do not unbind application-wide mouse events.
            self.menu_action_in_progress = True
            popup = self.menu_window
            self.menu_window = None
            if popup is not None:
                try:
                    if popup.winfo_exists():
                        popup.destroy()
                except tk.TclError:
                    pass
            if action is not None:
                self.parent.after(40, action)
            self.parent.after(80, lambda: setattr(self, "menu_action_in_progress", False))

        def show_menu(event) -> None:
            if self.menu_window is not None:
                close_menu()
                return

            popup = tk.Toplevel(window)
            self.menu_window = popup
            popup.overrideredirect(True)
            popup.attributes("-topmost", True)
            popup.configure(bg="#ffffff", highlightbackground="#d0d5dd", highlightthickness=1)

            body = tk.Frame(popup, bg="#ffffff", padx=3, pady=3)
            body.pack(fill="both", expand=True)
            expected_var = tk.StringVar(
                value=f"预计下班  {self.expected_end_getter()}" if self.expected_end_getter else self._("预计下班")
            )

            def add_button(text: str, command, *, muted: bool = False) -> None:
                button = tk.Button(
                    body,
                    text=text,
                    command=command,
                    anchor="w",
                    relief="flat",
                    bd=0,
                    padx=9,
                    pady=3,
                    bg="#ffffff",
                    activebackground="#eef4ff",
                    fg="#667085" if muted else "#101828",
                    activeforeground="#175cd3",
                    font=(self.font_name, 9),
                    cursor="hand2",
                )
                button.pack(fill="x")

            def add_separator() -> None:
                tk.Frame(body, height=1, bg="#e4e7ec").pack(fill="x", pady=2)

            def shift(minutes: int) -> None:
                # Keep this custom menu open as requested.
                if self.shift_expected:
                    self.shift_expected(minutes)
                if self.expected_end_getter:
                    expected_var.set(f"{self._('预计下班')}  {self.expected_end_getter()}")

            if self.open_main:
                add_button(self._("打开主界面"), lambda: run_modal_action(self.open_main))

            label = tk.Label(
                body,
                textvariable=expected_var,
                anchor="w",
                padx=9,
                pady=3,
                bg="#f9fafb",
                fg="#667085",
                font=(self.font_name, 9),
            )
            label.pack(fill="x")

            if self.shift_expected:
                add_button(self._("预计下班 -30分钟"), lambda: shift(-30))
                add_button(self._("预计下班 +30分钟"), lambda: shift(30))

            add_separator()
            add_button(self._("显示／隐藏金额"), lambda: run_modal_action(self.toggle_amount))
            if self.open_settings:
                add_button(self._("设置"), lambda: run_modal_action(self.open_settings))
            if self.open_overtime_details:
                add_button(self._("本月加班明细"), lambda: run_modal_action(self.open_overtime_details))
            if self.open_overtime_editor:
                add_button(self._("补录加班"), lambda: run_modal_action(self.open_overtime_editor))

            if self.exit_app:
                add_separator()
                add_button(self._("退出程序"), lambda: run_modal_action(self.exit_app))

            popup.update_idletasks()
            width = max(178, min(196, popup.winfo_reqwidth()))
            height = popup.winfo_reqheight()
            float_x = window.winfo_rootx()
            float_y = window.winfo_rooty()
            float_width = window.winfo_width()
            float_height = window.winfo_height()
            displays = self._display_areas()
            work_area = area_for_window(float_x, float_y, float_width, float_height, displays)
            x, y = floating_menu_position(
                float_x, float_y, float_width, float_height,
                width, height, work_area,
            )
            # The menu is placed beside the floating window and never covers it.
            popup.geometry(f"{width}x{height}+{x}+{y}")
            popup.bind("<Escape>", lambda _event: close_menu())

            def close_on_focus_out(_event=None):
                if self.menu_action_in_progress or self.menu_window is not popup:
                    return
                # Let Tk finish assigning focus. If focus did not move to a child
                # of this popup, the user clicked the desktop or another window.
                def check_focus():
                    if self.menu_action_in_progress or self.menu_window is not popup:
                        return
                    try:
                        focused = popup.focus_get()
                        widget = focused
                        while widget is not None:
                            if widget == popup:
                                return
                            widget = getattr(widget, "master", None)
                    except tk.TclError:
                        pass
                    close_menu()
                self.parent.after(20, check_focus)

            popup.bind("<FocusOut>", close_on_focus_out, add="+")
            popup.lift()
            popup.focus_force()

        canvas.bind("<Button-3>", show_menu)
        canvas.bind("<ButtonPress-1>", self._drag_start)
        canvas.bind("<B1-Motion>", self._drag)
        update()

    def close(self) -> None:
        if self.menu_window is not None:
            try:
                if self.menu_window.winfo_exists():
                    self.menu_window.destroy()
            except tk.TclError:
                pass
            self.menu_window = None
        window = self.window
        if self.is_open:
            self.last_x, self.last_y = window.winfo_x(), window.winfo_y()
        self.window = None
        self.cancel_timer()
        if window is None:
            return
        try:
            if window.winfo_exists():
                window.withdraw()
                self.parent.after_idle(lambda: self._safe_destroy(window))
        except tk.TclError:
            pass

    def cancel_timer(self) -> None:
        if self.timer_id is not None:
            try:
                self.parent.after_cancel(self.timer_id)
            except tk.TclError:
                pass
            self.timer_id = None

    def position(self) -> tuple[int, int]:
        if not self.is_open:
            return self.last_x, self.last_y
        self.last_x, self.last_y = self.window.winfo_x(), self.window.winfo_y()
        return self.last_x, self.last_y

    def _drag_start(self, event) -> None:
        self._drag_x, self._drag_y = event.x, event.y

    def _drag(self, event) -> None:
        if self.is_open:
            x = self.window.winfo_x() + event.x - self._drag_x
            y = self.window.winfo_y() + event.y - self._drag_y
            self.last_x, self.last_y = x, y
            self.window.geometry(f"+{x}+{y}")

    def _display_areas(self) -> list[DisplayArea]:
        displays = get_display_areas()
        if displays:
            return displays
        width = max(300, self.parent.winfo_screenwidth())
        height = max(102, self.parent.winfo_screenheight())
        return [DisplayArea(0, 0, width, height, True)]

    @staticmethod
    def _safe_destroy(window: tk.Toplevel) -> None:
        try:
            if window.winfo_exists():
                window.destroy()
        except tk.TclError:
            pass

    @staticmethod
    def _round_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        return canvas.create_polygon(points, smooth=True, splinesteps=36, **kwargs)
