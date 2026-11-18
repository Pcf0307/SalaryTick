from __future__ import annotations

import threading
from collections.abc import Callable


class TrayIcon:
    """Windows system-tray controller. pystray and Pillow are loaded lazily."""

    def __init__(
        self,
        schedule_on_ui: Callable[[Callable[[], None]], None],
        open_main: Callable[[], None],
        toggle_amount: Callable[[], None],
        shift_expected: Callable[[int], None],
        open_settings: Callable[[], None],
        open_overtime_details: Callable[[], None],
        open_overtime_editor: Callable[[], None],
        exit_app: Callable[[], None],
        amount_hidden_getter: Callable[[], bool],
        i18n=None,
    ):
        self.schedule_on_ui = schedule_on_ui
        self.open_main = open_main
        self.toggle_amount = toggle_amount
        self.shift_expected = shift_expected
        self.open_settings = open_settings
        self.open_overtime_details = open_overtime_details
        self.open_overtime_editor = open_overtime_editor
        self.exit_app = exit_app
        self.amount_hidden_getter = amount_hidden_getter
        self.i18n = i18n
        self._ = i18n.t if i18n else (lambda text: text)
        self.icon = None
        self.thread: threading.Thread | None = None
        self.error: Exception | None = None

    def _run_ui(self, action: Callable[[], None]) -> None:
        self.schedule_on_ui(action)

    @staticmethod
    def _create_image():
        from PIL import Image, ImageDraw

        size = 64
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((5, 5, 59, 59), radius=14, fill="#27313D")
        draw.ellipse((16, 14, 48, 46), outline="#F4F6F8", width=4)
        draw.line((32, 30, 32, 20), fill="#F4F6F8", width=4)
        draw.line((32, 30, 41, 35), fill="#F4F6F8", width=4)
        draw.rounded_rectangle((19, 47, 45, 53), radius=3, fill="#506B88")
        return image

    def start(self) -> bool:
        if self.thread and self.thread.is_alive():
            return True
        try:
            import pystray
        except ImportError as error:
            self.error = error
            return False

        def amount_label(_item):
            return self._("显示金额") if self.amount_hidden_getter() else self._("隐藏金额")

        menu = pystray.Menu(
            pystray.MenuItem(self._("打开主界面"), lambda *_: self._run_ui(self.open_main), default=True),
            pystray.MenuItem(amount_label, lambda *_: self._run_ui(self.toggle_amount)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self._("预计下班 -30分钟"), lambda *_: self._run_ui(lambda: self.shift_expected(-30))),
            pystray.MenuItem(self._("预计下班 +30分钟"), lambda *_: self._run_ui(lambda: self.shift_expected(30))),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self._("设置"), lambda *_: self._run_ui(self.open_settings)),
            pystray.MenuItem(self._("本月加班明细"), lambda *_: self._run_ui(self.open_overtime_details)),
            pystray.MenuItem(self._("补录加班"), lambda *_: self._run_ui(self.open_overtime_editor)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self._("退出程序"), lambda *_: self._run_ui(self.exit_app)),
        )
        self.icon = pystray.Icon("SalaryTick", self._create_image(), "SalaryTick", menu)
        self.thread = threading.Thread(target=self.icon.run, name="SalaryTickTray", daemon=True)
        self.thread.start()
        return True

    def refresh_menu(self) -> None:
        if self.icon is not None:
            try:
                self.icon.update_menu()
            except Exception:
                pass

    def stop(self) -> None:
        icon = self.icon
        self.icon = None
        if icon is not None:
            try:
                icon.stop()
            except Exception:
                pass
