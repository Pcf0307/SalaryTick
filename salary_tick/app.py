from __future__ import annotations

import calendar
import tkinter as tk
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from tkinter import messagebox, ttk

from .calculator import calculate_month, calculate_today, pay_for_overtime_seconds
from .calendar_service import has_official_calendar, month_workdays
from .floating_window import FloatingWindow
from .models import OvertimeRecord, SalarySettings
from .overtime_store import OvertimeStore
from .settings_store import SettingsStore
from .state_rules import normalize_amount_visibility, normalize_expected_end
from .window_utils import center_window
from .ui_styles import COLORS, configure_styles
from .settings_dialog import SettingsDialog
from .setup_wizard import SetupWizard
from .tray_icon import TrayIcon
from .i18n import I18n


def parse_hhmm(text: str):
    return datetime.strptime(text.strip(), "%H:%M").time()


def format_duration(seconds: int, include_seconds: bool = True) -> str:
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, second = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{second:02d}" if include_seconds else f"{hours:02d}:{minutes:02d}"


class SalaryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("700x520")
        self.minsize(650, 420)
        self.configure(bg=COLORS["app_bg"])

        self.settings_store = SettingsStore()
        self.overtime_store = OvertimeStore()
        self.config = self.settings_store.load()
        self.i18n = I18n(self.config.get("display", {}).get("language", "zh_CN"))
        self._ = self.i18n.t
        self.title(self._("实时工资计算器"))
        saved = self.config
        profile, today_cfg, display_cfg, window_cfg = saved["profile"], saved["today"], saved["display"], saved["window"]

        self.year = tk.IntVar(value=int(profile["year"]))
        self.month = tk.IntVar(value=int(profile["month"]))
        self.salary = tk.StringVar(value=str(profile["monthly_salary"]))
        self.workdays = tk.StringVar(value=str(profile["workdays"]))
        self.manual_days = tk.BooleanVar(value=bool(profile["manual_workdays"]))
        self.multiplier = tk.StringVar(value=str(profile["overtime_multiplier"]))
        self.start = tk.StringVar(value=profile["work_start"])
        self.lunch_start = tk.StringVar(value=profile["lunch_start"])
        self.lunch_end = tk.StringVar(value=profile["lunch_end"])
        self.end = tk.StringVar(value=profile["work_end"])
        self.overtime_start = tk.StringVar(value=profile["overtime_start"])
        self.expected_end = tk.StringVar(value=today_cfg["expected_end"])
        self.refresh_mode = tk.StringVar(value=display_cfg["refresh_mode"])
        self.privacy_mode = tk.StringVar(value=display_cfg["privacy_mode"])
        self.settings_dialog = None
        self.amounts_revealed = self.privacy_mode.get() == "直接显示"
        self.float_amount_visible = (
            bool(display_cfg.get("float_amount_visible", False))
            if self.privacy_mode.get() == "直接显示"
            else False
        )

        self.today_base = tk.StringVar(value="¥ •••.•••")
        self.today_ot = tk.StringVar(value="¥ •••.•••")
        self.today_total = tk.StringVar(value="¥ •••.•••")
        self.today_duration = tk.StringVar(value="00:00:00")
        self.month_base = tk.StringVar(value="¥ •••.••")
        self.month_ot = tk.StringVar(value="¥ •••.••")
        self.month_total = tk.StringVar(value="¥ •••.••")
        self.month_ot_days = tk.StringVar(value="0 days" if self.i18n.language == "en_US" else "0天")
        self.month_ot_duration = tk.StringVar(value="00:00")
        self.month_ot_amount = tk.StringVar(value="¥ •••.•••")
        self.status = tk.StringVar(value=self._("准备就绪"))
        self.calendar_hint = tk.StringVar()
        self.float_amount = tk.StringVar(value=f"{self._('今日安排')}  ¥•••.•••")
        self.float_duration = tk.StringVar(value=f"{self._('工作时长')}  00:00:00")

        self.records = self.overtime_store.load()
        self.tick_timer_id = None
        self.details_window = None
        self.overtime_checked_key = None
        self._closing = False
        self._saved_float_open = bool(window_cfg.get("float_open", False))
        self._saved_float_x = int(window_cfg.get("float_x", 30))
        self._saved_float_y = int(window_cfg.get("float_y", 30))
        self._last_overtime_save_at = None
        self._last_overtime_saved_seconds = None
        self.runtime_date = date.today()
        self.last_calculation_result = None

        self.floating = FloatingWindow(
            self,
            self.float_amount.get,
            self.float_duration.get,
            lambda: self.privacy_mode.get() == "始终隐藏" or not self.float_amount_visible,
            self.toggle_float_amount,
            self.refresh_interval_ms,
            open_main=self.show_main_window,
            exit_app=self.request_exit,
            shift_expected=self.shift_expected,
            open_settings=self.open_settings,
            open_overtime_details=self.open_overtime_details,
            open_overtime_editor=self.open_overtime_editor,
            expected_end_getter=self.expected_end.get,
            i18n=self.i18n,
        )
        self.tray = TrayIcon(
            schedule_on_ui=lambda action: self.after(0, action),
            open_main=self.show_main_window,
            toggle_amount=self.toggle_float_amount,
            shift_expected=self.shift_expected,
            open_settings=self.open_settings,
            open_overtime_details=self.open_overtime_details,
            open_overtime_editor=self.open_overtime_editor,
            exit_app=self.request_exit,
            amount_hidden_getter=self.float_hidden,
            i18n=self.i18n,
        )

        self.build_ui()
        self.protocol("WM_DELETE_WINDOW", self.hide_main_window)
        self.fit_main_window()
        if not self.config.get("setup_completed", False):
            self.withdraw()
            SetupWizard(self, self.config, self.complete_first_setup, i18n=self.i18n)
        else:
            self.withdraw()
            self.floating.open(self._saved_float_x, self._saved_float_y)
            self._saved_float_open = True
        self.tray.start()
        self.refresh_now()

    def build_ui(self):
        style = configure_styles(self, self.i18n.font_name)

        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)
        header = ttk.Frame(root)
        header.pack(fill="x")
        ttk.Label(header, text=self._("实时工资计算器"), style="Title.TLabel").pack(side="left")
        ttk.Button(header, text=self._("设置"), style="Secondary.TButton", command=self.open_settings).pack(side="right")
        self.privacy_button = ttk.Button(header, style="Text.TButton", command=self.quick_privacy_action)
        self.privacy_button.pack(side="right")
        self.update_privacy_button()
        ttk.Label(root, text=self._("正常工时自动累计；加班只累计到今日预计下班时间。"), style="Muted.TLabel").pack(anchor="w", pady=(2, 10))

        today = ttk.Frame(root, style="Card.TFrame", padding=18)
        today.pack(fill="x")
        top = ttk.Frame(today, style="Card.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text=self._("今日安排"), style="CardLabel.TLabel").pack(side="left")
        self.status_label = ttk.Label(top, textvariable=self.status, style="StatusWork.TLabel")
        self.status_label.pack(side="right")
        adjust = ttk.Frame(today, style="Card.TFrame")
        adjust.pack(fill="x", pady=(9, 14))
        ttk.Label(adjust, text=self._("今日预计下班时间"), style="CardLabel.TLabel").pack(side="left")
        ttk.Button(adjust, text="+30 min" if self.i18n.language == "en_US" else "+30分", style="Small.TButton", command=lambda: self.shift_expected(30)).pack(side="right")
        ttk.Button(adjust, text="-30 min" if self.i18n.language == "en_US" else "-30分", style="Small.TButton", command=lambda: self.shift_expected(-30)).pack(side="right", padx=6)
        ttk.Entry(adjust, textvariable=self.expected_end, width=8).pack(side="right", padx=8)

        today_summary = ttk.Frame(today, style="Card.TFrame")
        today_summary.pack(fill="x", pady=(2, 0))
        today_summary.columnconfigure(0, weight=1)
        today_summary.columnconfigure(1, weight=1)
        ttk.Label(today_summary, text=self._("工作时长"), style="CardLabel.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(today_summary, text=self._("今日合计"), style="CardLabel.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(today_summary, textvariable=self.today_duration, style="Money.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Label(today_summary, textvariable=self.today_total, style="Total.TLabel").grid(row=1, column=1, sticky="w", pady=(4, 0))

        month = ttk.Frame(root, style="Card.TFrame", padding=14)
        month.pack(fill="x", pady=(10, 0))
        month_head = ttk.Frame(month, style="Card.TFrame")
        month_head.pack(fill="x", pady=(0, 10))
        ttk.Label(month_head, text=self._("本月概览"), style="CardLabel.TLabel").pack(side="left")
        ttk.Button(month_head, text=self._("+ 补录加班"), style="Secondary.TButton", command=self.open_overtime_editor).pack(side="right")
        ttk.Button(month_head, text=self._("查看明细"), style="Secondary.TButton", command=self.open_overtime_details).pack(side="right", padx=8)

        month_summary = ttk.Frame(month, style="Card.TFrame")
        month_summary.pack(fill="x")
        month_summary.columnconfigure(0, weight=1)
        month_summary.columnconfigure(1, weight=1)
        ttk.Label(month_summary, text=self._("本月基本工资"), style="CardLabel.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(month_summary, text=self._("本月加班"), style="CardLabel.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(month_summary, textvariable=self.month_base, style="Money.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))
        overtime_value = ttk.Frame(month_summary, style="Card.TFrame")
        overtime_value.grid(row=1, column=1, sticky="w", pady=(4, 0))
        ttk.Label(overtime_value, textvariable=self.month_ot_duration, style="Money.TLabel").pack(side="left")
        ttk.Label(overtime_value, text="  /  ", style="CardLabel.TLabel").pack(side="left")
        ttk.Label(overtime_value, textvariable=self.month_ot_amount, style="Money.TLabel").pack(side="left")


    def result_row(self, parent, items, compact=False):
        row = ttk.Frame(parent, style="Card.TFrame")
        row.pack(fill="x", pady=(8 if compact else 0, 0))
        count = len(items)
        for index in range(count):
            row.columnconfigure(index, weight=1)
        for index, (label, variable) in enumerate(items):
            ttk.Label(row, text=label, style="CardLabel.TLabel").grid(row=0, column=index, sticky="w")
            is_total = label in ("今日合计", "本月合计")
            style = "Total.TLabel" if is_total else "Money.TLabel"
            ttk.Label(row, textvariable=variable, style=style).grid(row=1, column=index, sticky="w", pady=(4, 0))


    def build_settings(self) -> SalarySettings:
        return SalarySettings(
            year=int(self.year.get()), month=int(self.month.get()),
            monthly_salary=Decimal(self.salary.get()), workdays=Decimal(self.workdays.get()),
            overtime_multiplier=Decimal(self.multiplier.get()),
            work_start=parse_hhmm(self.start.get()), lunch_start=parse_hhmm(self.lunch_start.get()),
            lunch_end=parse_hhmm(self.lunch_end.get()), work_end=parse_hhmm(self.end.get()),
            overtime_start=parse_hhmm(self.overtime_start.get()), expected_end=parse_hhmm(self.expected_end.get()),
        )

    def records_for_month(self):
        year, month = int(self.year.get()), int(self.month.get())
        return [record for record in self.records.values() if (record.record_date.year, record.record_date.month) == (year, month)]

    def check_date_boundary(self, now: datetime):
        new_date = now.date()
        if new_date == self.runtime_date:
            return
        previous_date = self.runtime_date
        self.finalize_previous_day(previous_date)
        month_changed = (previous_date.year, previous_date.month) != (new_date.year, new_date.month)
        self.runtime_date = new_date

        if month_changed:
            # 手动工作日只对原月份有效。新月份恢复自动日历计算。
            self.year.set(new_date.year)
            self.month.set(new_date.month)
            self.manual_days.set(False)
            self.workdays.set(str(month_workdays(new_date.year, new_date.month)))

        if self.config["behavior"].get("reset_expected_end_daily", True) or month_changed:
            self.expected_end.set(self.end.get())

        self.config["profile"].update({
            "year": int(self.year.get()),
            "month": int(self.month.get()),
            "workdays": self.workdays.get(),
            "manual_workdays": bool(self.manual_days.get()),
        })
        self.config["today"] = {"date": new_date.isoformat(), "expected_end": self.expected_end.get()}
        self._last_overtime_save_at = None
        self._last_overtime_saved_seconds = None
        self.settings_store.save(self.config)

    def finalize_previous_day(self, previous_date: date):
        key = previous_date.isoformat()
        existing = self.records.get(key)
        if existing and existing.source in ("manual", "manual_override"):
            return
        if self.last_calculation_result and self.last_calculation_result.overtime_work_seconds > 0:
            self.overtime_store.upsert(
                OvertimeRecord(previous_date, self.last_calculation_result.overtime_work_seconds, "automatic"),
                self.records,
            )
        elif existing and existing.source == "automatic":
            self.overtime_store.upsert(existing, self.records)

    def tick(self):
        self.tick_timer_id = None
        if self._closing: return
        now = datetime.now()
        self.check_date_boundary(now)
        if self.refresh_mode.get() == "每秒": now = now.replace(microsecond=0)
        try:
            settings = self.build_settings()
            today = calculate_today(now, settings)
            self.last_calculation_result = today
            self.save_live_overtime(now, today.overtime_work_seconds, today.reached_expected_end)
            month = calculate_month(now, settings, self.records.values())
            self.update_values(today, month)
            self.status.set(self.i18n.status(today.status))
            self.update_status_style(today.status)
        except (ValueError, InvalidOperation) as error:
            self.status.set(self.i18n.status(f"输入有误：{error}"))
            self.update_status_style("输入有误")
        self.schedule_next_tick()

    def update_values(self, today, month):
        self.today_base.set(self.money(today.today_base_pay, 3))
        self.today_ot.set(self.money(today.today_overtime_pay, 3))
        self.today_total.set(self.money(today.today_total_pay, 3))
        self.month_base.set(self.money(month.base_pay, 2))
        self.month_ot.set(self.money(month.overtime_pay, 2))
        self.month_total.set(self.money(month.total_pay, 2))
        self.month_ot_days.set(f"{month.overtime_days} days" if self.i18n.language == "en_US" else f"{month.overtime_days}天")
        self.month_ot_duration.set(format_duration(month.overtime_seconds, False))
        self.month_ot_amount.set(self.money(month.overtime_pay, 3))
        self.float_amount.set(f"{self._('今日安排')}  ¥•••.•••" if self.float_hidden() else f"{self._('今日安排')}  ¥{today.today_total_pay:,.3f}")
        duration_text = format_duration(today.total_work_seconds)
        self.today_duration.set(duration_text)
        self.float_duration.set(f"{self._('工作时长')}  {duration_text}")
        if self.details_window and self.details_window.winfo_exists(): self.populate_overtime_tree()

    def save_live_overtime(self, now, seconds, reached_expected_end=False, force=False):
        if (int(self.year.get()), int(self.month.get())) != (now.year, now.month):
            return
        key = now.date().isoformat()
        existing = self.records.get(key)
        if existing and existing.source in ("manual", "manual_override"):
            return
        if seconds <= 0:
            if existing and existing.source == "automatic":
                self.overtime_store.delete(now.date(), self.records)
            self._last_overtime_saved_seconds = None
            return
        should_save = force or reached_expected_end or self._last_overtime_save_at is None
        if not should_save:
            should_save = (now - self._last_overtime_save_at).total_seconds() >= 30
        if not should_save:
            return
        rounded_seconds = int(seconds)
        if self._last_overtime_saved_seconds == rounded_seconds and not force:
            return
        record = OvertimeRecord(now.date(), rounded_seconds, "automatic")
        self.overtime_store.upsert(record, self.records)
        self._last_overtime_save_at = now
        self._last_overtime_saved_seconds = rounded_seconds

    def money(self, value: Decimal, decimals: int) -> str:
        if self.privacy_mode.get() == "直接显示" or self.amounts_revealed:
            return f"¥ {value:,.{decimals}f}"
        return "¥ •••.•••" if decimals == 3 else "¥ •••.••"

    def float_hidden(self):
        return self.privacy_mode.get() == "始终隐藏" or not self.float_amount_visible

    def quick_privacy_action(self):
        if self.privacy_mode.get() == "始终隐藏":
            messagebox.showinfo(self._("金额已隐藏"), self._("当前设置为“始终隐藏”。"), parent=self); return
        if self.privacy_mode.get() == "直接显示": self.privacy_mode.set("手动切换")
        self.amounts_revealed = not self.amounts_revealed
        self.update_privacy_button(); self.save_settings(); self.refresh_now(); self.tray.refresh_menu()

    def apply_privacy_mode(self):
        visible = self.privacy_mode.get() == "直接显示"
        self.amounts_revealed = visible; self.float_amount_visible = visible
        self.update_privacy_button(); self.save_settings(); self.refresh_now(); self.tray.refresh_menu()

    def update_privacy_button(self):
        self.privacy_button.configure(text=self._("隐藏金额") if self.amounts_revealed else self._("显示金额"))

    def toggle_float_amount(self):
        if self.privacy_mode.get() == "始终隐藏": return
        self.float_amount_visible = not self.float_amount_visible
        self.save_settings()
        self.refresh_now()
        self.tray.refresh_menu()

    def refresh_interval_ms(self): return 50 if self.refresh_mode.get() == "秒表" else 1000

    def cancel_tick(self):
        if self.tick_timer_id is not None:
            try: self.after_cancel(self.tick_timer_id)
            except tk.TclError: pass
            self.tick_timer_id = None

    def schedule_next_tick(self):
        if not self._closing:
            self.cancel_tick(); self.tick_timer_id = self.after(self.refresh_interval_ms(), self.tick)

    def refresh_now(self):
        if not self._closing:
            self.cancel_tick(); self.tick()

    def update_status_style(self, status):
        if not hasattr(self, "status_label"):
            return
        if "输入有误" in status:
            style = "StatusError.TLabel"
        elif "午休" in status or "尚未上班" in status or "不是法定工作日" in status:
            style = "StatusPause.TLabel"
        elif "休息时间" in status:
            style = "StatusWait.TLabel"
        elif "加班中" in status:
            style = "StatusOvertime.TLabel"
        elif "停止" in status or "完成" in status:
            style = "StatusDone.TLabel"
        else:
            style = "StatusWork.TLabel"
        self.status_label.configure(style=style)


    def show_main_window(self):
        self.deiconify()
        self.fit_main_window()
        self.lift()
        self.focus_force()

    def hide_main_window(self):
        self.withdraw()
        if not self.floating.is_open:
            self.floating.open(self._saved_float_x, self._saved_float_y)

    def shift_expected(self, minutes):
        try:
            value = datetime.combine(date.today(), parse_hhmm(self.expected_end.get())) + timedelta(minutes=minutes)
            if value.time() < parse_hhmm(self.end.get()): value = datetime.combine(date.today(), parse_hhmm(self.end.get()))
            self.expected_end.set(value.strftime("%H:%M")); self.save_settings(); self.refresh_now()
        except ValueError: self.status.set(self._("预计下班时间格式应为 HH:MM"))

    def apply_config(self, config):
        self.config = config
        p, t, d, w = config["profile"], config["today"], config["display"], config["window"]
        mappings = ((self.year,p["year"]),(self.month,p["month"]),(self.salary,p["monthly_salary"]),(self.workdays,p["workdays"]),(self.manual_days,p["manual_workdays"]),(self.multiplier,p["overtime_multiplier"]),(self.start,p["work_start"]),(self.lunch_start,p["lunch_start"]),(self.lunch_end,p["lunch_end"]),(self.end,p["work_end"]),(self.overtime_start,p["overtime_start"]),(self.expected_end,t["expected_end"]),(self.refresh_mode,d["refresh_mode"]),(self.privacy_mode,d["privacy_mode"]))
        for variable, value in mappings: variable.set(value)
        normalized_expected_end = normalize_expected_end(self.end.get(), self.expected_end.get())
        self.expected_end.set(normalized_expected_end)
        self.config["today"]["expected_end"] = normalized_expected_end
        self.float_amount_visible = normalize_amount_visibility(
            self.privacy_mode.get(), d.get("float_amount_visible", False)
        )
        self.amounts_revealed = self.privacy_mode.get() == "直接显示"
        self.update_privacy_button()
        self._saved_float_x, self._saved_float_y = int(w.get("float_x",30)), int(w.get("float_y",30))
        self._saved_float_open = True
        self.config["window"]["float_open"] = True
        self.settings_store.save(self.config)
        if not self.floating.is_open:
            self.floating.open(self._saved_float_x,self._saved_float_y)
        self.refresh_now()

    def complete_first_setup(self, config):
        self.apply_config(config)
        self.withdraw()
        if not self.floating.is_open:
            self.floating.open(self._saved_float_x, self._saved_float_y)
        self._saved_float_open = True
        self.save_settings()

    def open_settings(self):
        if self.settings_dialog:
            try:
                if self.settings_dialog.window.winfo_exists():
                    self.settings_dialog.window.lift(); return
            except tk.TclError:
                self.settings_dialog = None
        self.settings_dialog = SettingsDialog(
            self, self.config, self.apply_config, self.settings_store,
            on_close=lambda: setattr(self, "settings_dialog", None),
            i18n=self.i18n,
        )

    def fit_main_window(self):
        self.update_idletasks(); width=max(720 if self.i18n.language == "en_US" else 650,min(960,self.winfo_reqwidth()+8)); height=min(self.winfo_reqheight()+8,max(420,self.winfo_screenheight()-120)); self.geometry(f"{width}x{height}")


    def open_overtime_details(self):
        if self.details_window:
            try:
                if self.details_window.winfo_exists():
                    self.details_window.lift(); return
            except tk.TclError:
                self.details_window = None
        window = tk.Toplevel(self); self.details_window = window; window.title(self._("本月加班明细")); center_window(window, self if self.winfo_viewable() else None, 640, 430)
        window.minsize(600, 390)
        window.protocol("WM_DELETE_WINDOW", self.close_overtime_details)
        window.lift()
        window.attributes("-topmost", True)
        window.after(120, lambda: window.attributes("-topmost", False) if window.winfo_exists() else None)
        configure_styles(window, self.i18n.font_name)
        details_head = ttk.Frame(window, padding=(12, 10))
        details_head.pack(fill="x")
        ttk.Label(details_head, text=self._("本月加班明细"), style="DialogTitle.TLabel").pack(side="left")
        ttk.Button(details_head, text=self._("+ 补录加班"), style="Secondary.TButton", command=self.open_overtime_editor).pack(side="right")
        columns = ("checked", "date", "duration", "amount", "source")
        self.overtime_tree = ttk.Treeview(window, columns=columns, show="headings", selectmode="none")
        for column, title, width in (("checked", "选择", 72), ("date", "日期", 150), ("duration", "计薪加班", 130), ("amount", "估算金额", 140), ("source", "来源", 130)):
            self.overtime_tree.heading(column, text=title); self.overtime_tree.column(column, width=width, anchor="center")
        footer = ttk.Frame(window, padding=(12, 6, 12, 10))
        footer.pack(side="bottom", fill="x")
        self.overtime_tree.bind("<Button-1>", self.on_tree_click)
        self.overtime_tree.pack(side="top", fill="both", expand=True, padx=12, pady=(0, 6))
        ttk.Button(footer, text=self._("删除"), style="Secondary.TButton", command=self.delete_selected).pack(side="right")
        ttk.Button(footer, text=self._("编辑"), style="Secondary.TButton", command=self.edit_selected).pack(side="right", padx=6)
        self.populate_overtime_tree()

    def close_overtime_details(self):
        window = self.details_window
        self.details_window = None
        if window is not None:
            try:
                window.destroy()
            except tk.TclError:
                pass

    def populate_overtime_tree(self):
        if not hasattr(self, "overtime_tree") or not self.overtime_tree.winfo_exists(): return
        for item in self.overtime_tree.get_children(): self.overtime_tree.delete(item)
        settings = self.build_settings()
        for record in sorted(self.records_for_month(), key=lambda item: item.record_date, reverse=True):
            key = record.record_date.isoformat(); checked = "■" if key == self.overtime_checked_key else "□"; pay = pay_for_overtime_seconds(record.overtime_seconds, settings)
            weekday = self.i18n.weekday(record.record_date.weekday())
            date_text = (record.record_date.strftime("%b %d, %Y") + f" ({weekday})") if self.i18n.language == "en_US" else f"{record.record_date.month}月{record.record_date.day}日 周{weekday}"
            self.overtime_tree.insert("", "end", iid=key, values=(checked, date_text, format_duration(record.overtime_seconds, False), self.money(pay, 3), self.i18n.record_source(record.source)))

    def on_tree_click(self, event):
        row = self.overtime_tree.identify_row(event.y)
        if row: self.overtime_checked_key = None if self.overtime_checked_key == row else row; self.populate_overtime_tree()
        return "break"

    def edit_selected(self):
        if not self.overtime_checked_key: messagebox.showinfo(self._("请选择记录"), self._("请先勾选一条记录。"), parent=self.details_window); return
        self.open_overtime_editor(self.overtime_checked_key)

    def delete_selected(self):
        if not self.overtime_checked_key: messagebox.showinfo(self._("请选择记录"), self._("请先勾选一条记录。"), parent=self.details_window); return
        if messagebox.askyesno(self._("删除加班记录"), self._("确定删除所选记录吗？"), parent=self.details_window):
            self.overtime_store.delete(date.fromisoformat(self.overtime_checked_key), self.records); self.overtime_checked_key = None; self.refresh_now()

    def open_overtime_editor(self, edit_key=None):
        settings = self.build_settings(); today = date.today(); max_day = calendar.monthrange(settings.year, settings.month)[1]
        if (settings.year, settings.month) == (today.year, today.month): max_day = min(max_day, today.day)
        existing = self.records.get(edit_key) if edit_key else None; total = existing.overtime_seconds if existing else 0
        window = tk.Toplevel(self)
        window.title(self._("修改加班记录") if edit_key else self._("补录加班"))
        visible_parent = self if self.winfo_viewable() else None
        center_window(window, visible_parent, 360, 270)
        if visible_parent is not None:
            window.transient(visible_parent)
        window.lift()
        window.attributes("-topmost", True)
        window.after(120, lambda: window.attributes("-topmost", False) if window.winfo_exists() else None)
        window.grab_set()
        configure_styles(window, self.i18n.font_name)
        frame = ttk.Frame(window, padding=16); frame.pack(fill="both", expand=True)
        day_var = tk.IntVar(value=existing.record_date.day if existing else max_day); hour_var = tk.IntVar(value=total // 3600); minute_var = tk.IntVar(value=(total % 3600) // 60)
        ttk.Label(frame, text=(f"{self._('日期')}: {settings.year}-{settings.month:02d}" if self.i18n.language == "en_US" else f"日期：{settings.year}年{settings.month}月")).grid(row=0, column=0, sticky="w", pady=8); ttk.Spinbox(frame, from_=1, to=max_day, textvariable=day_var, width=8, state="readonly" if edit_key else "normal").grid(row=0, column=1)
        ttk.Label(frame, text=self._("加班小时")).grid(row=1, column=0, sticky="w", pady=8); ttk.Spinbox(frame, from_=0, to=23, textvariable=hour_var, width=8).grid(row=1, column=1)
        ttk.Label(frame, text=self._("加班分钟")).grid(row=2, column=0, sticky="w", pady=8); ttk.Spinbox(frame, from_=0, to=59, textvariable=minute_var, width=8).grid(row=2, column=1)
        def save():
            try:
                day = int(day_var.get()); hours = int(hour_var.get()); minutes = int(minute_var.get())
                if not 1 <= day <= max_day:
                    raise ValueError("日期不在可补录范围内")
                if not 0 <= hours <= 23 or not 0 <= minutes <= 59:
                    raise ValueError("小时必须为0～23，分钟必须为0～59")
                seconds = (hours * 60 + minutes) * 60
                if seconds <= 0:
                    raise ValueError("加班时长必须大于0")
                record_date = date(settings.year, settings.month, day)
                key = record_date.isoformat()
                now = datetime.now()
                if record_date == now.date() and now.time() < settings.expected_end:
                    raise ValueError("今天仍在实时计算，请通过‘今日预计下班时间’调整")
                existing_record = self.records.get(key)
                if not edit_key and existing_record:
                    current = format_duration(existing_record.overtime_seconds, False)
                    if not messagebox.askyesno(self._("记录已存在"), (f"A record already exists for this date ({current}). Overwrite it?" if self.i18n.language == "en_US" else f"该日期已有记录（{current}）。是否覆盖？"), parent=window):
                        return
                source = "manual_override" if edit_key or existing_record else "manual"
                self.overtime_store.upsert(OvertimeRecord(record_date, seconds, source), self.records)
                window.destroy(); self.refresh_now()
            except (ValueError, tk.TclError) as error:
                messagebox.showerror(self._("无法保存"), self.i18n.error(str(error)), parent=window)
        ttk.Button(frame, text=self._("保存"), style="Primary.TButton", command=save).grid(row=4, column=1, sticky="e", pady=(14, 4))

    def save_settings(self):
        x, y = self.floating.position()
        self._saved_float_x, self._saved_float_y = x, y
        self._saved_float_open = True
        p=self.config["profile"]; p.update({"year":int(self.year.get()),"month":int(self.month.get()),"monthly_salary":self.salary.get(),"workdays":self.workdays.get(),"manual_workdays":bool(self.manual_days.get()),"overtime_multiplier":self.multiplier.get(),"work_start":self.start.get(),"lunch_start":self.lunch_start.get(),"lunch_end":self.lunch_end.get(),"work_end":self.end.get(),"overtime_start":self.overtime_start.get()})
        self.config["today"]={"date":date.today().isoformat(),"expected_end":self.expected_end.get()}
        self.config["display"].update({"refresh_mode":self.refresh_mode.get(),"privacy_mode":self.privacy_mode.get(),"float_amount_visible":bool(self.float_amount_visible)})
        self.config["window"].update({"float_x":x,"float_y":y,"float_open":self._saved_float_open})
        self.settings_store.save(self.config)

    def on_close(self):
        self.request_exit()

    def request_exit(self, parent=None):
        if self._closing: return
        if self.config["behavior"].get("skip_close_confirmation",False): self.perform_exit(); return
        dialog_parent = parent if parent is not None else self
        dialog = tk.Toplevel(dialog_parent)
        dialog.title(self._("退出确认"))
        visible_parent = dialog_parent if dialog_parent.winfo_viewable() else None
        center_window(dialog, visible_parent, 380, 210)
        if visible_parent is not None:
            dialog.transient(visible_parent)
        configure_styles(dialog)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=18); frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=self._("确定退出实时工资计算器吗？"), style="DialogTitle.TLabel").pack(anchor="w")
        no_prompt = tk.BooleanVar(value=False); ttk.Checkbutton(frame, text=self._("以后退出时不再提示"), variable=no_prompt).pack(anchor="w", pady=18)
        def confirm():
            if no_prompt.get(): self.config["behavior"]["skip_close_confirmation"]=True; self.settings_store.save(self.config)
            dialog.destroy(); self.perform_exit()
        ttk.Button(frame, text=self._("取消"), style="Text.TButton", command=dialog.destroy).pack(side="right"); ttk.Button(frame, text=self._("退出"), style="Primary.TButton", command=confirm).pack(side="right", padx=6)

    def perform_exit(self):
        if self._closing: return
        self._closing = True
        try:
            now = datetime.now(); current = calculate_today(now, self.build_settings())
            self.save_live_overtime(now, current.overtime_work_seconds, current.reached_expected_end, force=True)
        except (ValueError, InvalidOperation):
            pass
        self.save_settings(); self.cancel_tick(); self.floating.cancel_timer(); self.tray.stop()
        try: self.quit(); self.tk.call("destroy", ".")
        except tk.TclError: pass
