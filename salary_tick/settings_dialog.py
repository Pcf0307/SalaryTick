from __future__ import annotations

import os
import subprocess
import tkinter as tk
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from tkinter import messagebox, ttk

from .calendar_service import has_official_calendar, month_workdays
from .window_utils import center_window
from .window_state_rules import popup_size
from .ui_styles import COLORS, configure_styles
from .i18n import I18n, LANGUAGE_LABELS


class SettingsDialog:
    SECTIONS = (
        ("用户基本信息", None),
        ("工资信息", "salary"),
        ("标准作息", "schedule"),
        ("工具设置", None),
        ("显示设置", "display"),
        ("悬浮窗设置", "floating"),
        ("程序行为", "behavior"),
        ("数据管理", "data"),
    )

    def __init__(self, parent, config: dict, on_save, settings_store, on_close=None, i18n=None):
        self.parent = parent
        self.config = deepcopy(config)
        self.on_save = on_save
        self.settings_store = settings_store
        self.on_close = on_close
        self.i18n = i18n or I18n(config.get("display", {}).get("language", "zh_CN"))
        self._ = self.i18n.t
        self.original_language = self.i18n.language
        self.window = tk.Toplevel(parent)
        self.window.title(f"SalaryTick - {self._('设置')}")
        self.window.configure(bg=COLORS["app_bg"])
        configure_styles(self.window, self.i18n.font_name)
        if parent.winfo_viewable():
            self.window.transient(parent)
        self.window.protocol("WM_DELETE_WINDOW", self.cancel)
        self._fit_to_screen()
        self.vars = self._make_vars()
        self.salary_visible = False
        self.nav_buttons = {}
        self._build()
        self.show_section("salary")
        self.window.lift()
        self.window.attributes("-topmost", True)
        self.window.after(120, lambda: self.window.attributes("-topmost", False) if self.window.winfo_exists() else None)
        self.window.grab_set()

    def _fit_to_screen(self):
        width, height = popup_size(self.parent.winfo_screenwidth(), self.parent.winfo_screenheight())
        center_window(self.window, self.parent if self.parent.winfo_viewable() else None, width, height)
        self.window.minsize(min(680, width), min(480, height))

    def _make_vars(self):
        profile, display, window, behavior = (
            self.config["profile"], self.config["display"], self.config["window"], self.config["behavior"]
        )
        return {
            "year": tk.IntVar(value=profile["year"]), "month": tk.IntVar(value=profile["month"]),
            "monthly_salary": tk.StringVar(value=profile["monthly_salary"]), "workdays": tk.StringVar(value=profile["workdays"]),
            "manual_workdays": tk.BooleanVar(value=profile["manual_workdays"]), "overtime_multiplier": tk.StringVar(value=profile["overtime_multiplier"]),
            "work_start": tk.StringVar(value=profile["work_start"]), "lunch_start": tk.StringVar(value=profile["lunch_start"]),
            "lunch_end": tk.StringVar(value=profile["lunch_end"]), "work_end": tk.StringVar(value=profile["work_end"]),
            "overtime_start": tk.StringVar(value=profile["overtime_start"]), "refresh_mode": tk.StringVar(value=display["refresh_mode"]),
            "privacy_mode": tk.StringVar(value=display["privacy_mode"]),
            "language": tk.StringVar(value=display.get("language", "zh_CN")),
            "float_amount_visible": tk.BooleanVar(value=display.get("float_amount_visible", False)),
            "skip_close_confirmation": tk.BooleanVar(value=behavior["skip_close_confirmation"]),
            "reset_expected_end_daily": tk.BooleanVar(value=behavior["reset_expected_end_daily"]),
        }

    def _build(self):
        outer = ttk.Frame(self.window)
        outer.pack(fill="both", expand=True)
        nav = ttk.Frame(outer, padding=(12, 14), width=160)
        nav.pack(side="left", fill="y")
        ttk.Separator(outer, orient="vertical").pack(side="left", fill="y")
        right = ttk.Frame(outer)
        right.pack(side="left", fill="both", expand=True)
        self.title_var = tk.StringVar()
        ttk.Label(right, textvariable=self.title_var, style="DialogTitle.TLabel").pack(anchor="w", padx=16, pady=(14, 6))
        body_wrap = ttk.Frame(right)
        body_wrap.pack(fill="both", expand=True, padx=(16, 12), pady=(0, 6))
        self.content = ttk.Frame(body_wrap, padding=(0, 2, 10, 10))
        self.content.pack(fill="both", expand=True)
        footer = ttk.Frame(right, padding=10)
        footer.pack(fill="x")
        ttk.Button(footer, text=self._("取消"), style="Text.TButton", command=self.cancel).pack(side="right")
        ttk.Button(footer, text=self._("保存并应用"), style="Primary.TButton", command=self.save).pack(side="right", padx=8)
        for label, key in self.SECTIONS:
            if key is None:
                ttk.Label(nav, text=self._(label), font=(self.i18n.font_name, 10, "bold")).pack(anchor="w", pady=(12, 5))
            else:
                button = ttk.Button(nav, text=self._(label), style="Nav.TButton", command=lambda section=key: self.show_section(section))
                button.pack(fill="x", pady=2)
                self.nav_buttons[key] = button

    def clear(self):
        for child in self.content.winfo_children():
            child.destroy()

    def show_section(self, section):
        self.clear()
        for key, button in self.nav_buttons.items():
            button.configure(style="NavActive.TButton" if key == section else "Nav.TButton")
        builders = {
            "salary": ("工资信息", self._salary), "schedule": ("标准作息", self._schedule),
            "display": ("显示设置", self._display), "floating": ("悬浮窗设置", self._floating),
            "behavior": ("程序行为", self._behavior), "data": ("数据管理", self._data),
        }
        title, builder = builders[section]; self.title_var.set(self._(title)); builder()

    def field(self, row, label, variable, note=None, mask=False):
        ttk.Label(self.content, text=self._(label)).grid(row=row, column=0, sticky="w", pady=8)
        if mask:
            box = ttk.Frame(self.content)
            box.grid(row=row, column=1, sticky="w", padx=16, pady=8)
            entry = ttk.Entry(box, textvariable=variable, width=18, show="" if self.salary_visible else "●")
            entry.pack(side="left")
            self.salary_entry = entry
            self.salary_eye_button = ttk.Button(
                box,
                text=self._("隐藏") if self.salary_visible else self._("显示"),
                style="Text.TButton",
                width=5,
                command=self.toggle_salary_visibility,
            )
            self.salary_eye_button.pack(side="left", padx=(6, 0))
        else:
            entry = ttk.Entry(self.content, textvariable=variable, width=20)
            entry.grid(row=row, column=1, sticky="w", padx=16, pady=8)
        if note:
            ttk.Label(self.content, text=self._(note), foreground="#667085", wraplength=400).grid(
                row=row + 1, column=1, sticky="w"
            )
        return entry

    def toggle_salary_visibility(self):
        self.salary_visible = not self.salary_visible
        if hasattr(self, "salary_entry") and self.salary_entry.winfo_exists():
            self.salary_entry.configure(show="" if self.salary_visible else "●")
        if hasattr(self, "salary_eye_button") and self.salary_eye_button.winfo_exists():
            self.salary_eye_button.configure(text=self._("隐藏") if self.salary_visible else self._("显示"))

    def _salary(self):
        ttk.Label(self.content, text=self._("工资所属年月")).grid(row=0, column=0, sticky="w", pady=8)
        box = ttk.Frame(self.content); box.grid(row=0, column=1, sticky="w", padx=16)
        ttk.Spinbox(box, from_=2020, to=2100, textvariable=self.vars["year"], width=7, command=self._auto_days).pack(side="left")
        ttk.Label(box, text=self._("年")).pack(side="left", padx=(4, 8)); ttk.Spinbox(box, from_=1, to=12, textvariable=self.vars["month"], width=5, command=self._auto_days).pack(side="left"); ttk.Label(box, text=self._("月")).pack(side="left", padx=4)
        self.field(1, "月基本工资", self.vars["monthly_salary"], "工资仅保存到当前Windows用户的本地数据目录。", mask=True)
        self.workdays_entry = self.field(3, "月工作日", self.vars["workdays"])
        ttk.Checkbutton(self.content, text=self._("手动修改工作日数"), variable=self.vars["manual_workdays"], command=self._auto_days).grid(row=4, column=1, sticky="w", padx=16)
        self.field(5, "加班倍率", self.vars["overtime_multiplier"])
        self._auto_days()

    def _auto_days(self):
        manual = self.vars["manual_workdays"].get()
        if not manual:
            try:
                self.vars["workdays"].set(str(month_workdays(int(self.vars["year"].get()), int(self.vars["month"].get()))))
            except ValueError:
                pass
        if hasattr(self, "workdays_entry") and self.workdays_entry.winfo_exists():
            self.workdays_entry.configure(state="normal" if manual else "readonly")

    def _schedule(self):
        self.field(0, "上班时间", self.vars["work_start"]); self.field(1, "午休开始", self.vars["lunch_start"])
        self.field(2, "午休结束", self.vars["lunch_end"]); self.field(3, "正常下班", self.vars["work_end"])
        self.field(4, "加班起算", self.vars["overtime_start"])
        ttk.Label(self.content, text=self._("正常下班至加班起算之间不计入工作时长和加班工资。"), foreground="#667085").grid(row=5, column=0, columnspan=2, sticky="w", pady=14)

    def _sync_float_amount_option(self):
        direct=self.vars["privacy_mode"].get()=="直接显示"
        if not direct:
            self.vars["float_amount_visible"].set(False)
        if hasattr(self,"float_amount_checkbox") and self.float_amount_checkbox.winfo_exists():
            self.float_amount_checkbox.configure(state="normal" if direct else "disabled")

    def _display(self):
        ttk.Label(self.content, text=self._("刷新方式")).pack(anchor="w", pady=(4, 6))
        ttk.Radiobutton(self.content, text=self._("秒表（金额平滑上涨）"), variable=self.vars["refresh_mode"], value="秒表").pack(anchor="w", pady=3)
        ttk.Radiobutton(self.content, text=self._("每秒刷新"), variable=self.vars["refresh_mode"], value="每秒").pack(anchor="w", pady=3)
        ttk.Label(self.content, text=self._("金额显示方式")).pack(anchor="w", pady=(22, 6))
        ttk.Label(self.content, text=self._("只影响界面显示，不影响工资计算和本地保存。"), foreground="#667085").pack(anchor="w", pady=(0, 6))
        for text, value in ((self._("直接显示"), "直接显示"), (self._("默认隐藏，手动切换"), "手动切换"), (self._("始终隐藏"), "始终隐藏")):
            ttk.Radiobutton(self.content,text=text,variable=self.vars["privacy_mode"],value=value,command=self._sync_float_amount_option).pack(anchor="w",pady=3)
        ttk.Label(self.content, text=self._("界面语言")).pack(anchor="w", pady=(20, 6))
        language_box = ttk.Combobox(self.content, state="readonly", width=20)
        language_box["values"] = (LANGUAGE_LABELS["zh_CN"], LANGUAGE_LABELS["en_US"])
        language_box.set(LANGUAGE_LABELS.get(self.vars["language"].get(), LANGUAGE_LABELS["zh_CN"]))
        language_box.pack(anchor="w")
        language_box.bind("<<ComboboxSelected>>", lambda _event: self.vars["language"].set("en_US" if language_box.get() == "English" else "zh_CN"))
        ttk.Label(self.content, text=self._("更改语言后重新启动 SalaryTick 生效。"), foreground="#667085").pack(anchor="w", pady=(6, 0))

    def _floating(self):
        ttk.Label(self.content, text=self._("SalaryTick启动后始终显示悬浮窗。"), foreground="#667085").pack(anchor="w", pady=(4, 12))
        self.float_amount_checkbox=ttk.Checkbutton(self.content,text=self._("悬浮窗默认显示金额"),variable=self.vars["float_amount_visible"])
        self.float_amount_checkbox.pack(anchor="w",pady=8)
        self._sync_float_amount_option()
        ttk.Label(self.content, text=self._("默认隐藏或始终隐藏时，此选项不可用。"), foreground="#667085").pack(anchor="w", pady=(0, 8))
    def _behavior(self):
        ttk.Checkbutton(self.content, text=self._("退出程序时显示确认"), variable=self.vars["skip_close_confirmation"], onvalue=False, offvalue=True).pack(anchor="w", pady=8)
        ttk.Checkbutton(self.content, text=self._("新的一天恢复正常下班时间"), variable=self.vars["reset_expected_end_daily"]).pack(anchor="w", pady=8)

    def _data(self):
        ttk.Label(self.content, text=self._("数据保存在当前Windows用户的 LocalAppData 目录。"), wraplength=520).pack(anchor="w", pady=(4, 12))
        ttk.Button(self.content, text=self._("打开数据保存位置"), style="Secondary.TButton", command=self._open_data_dir).pack(anchor="w", pady=5)
        ttk.Label(self.content, text=str(self.settings_store.open_directory()), foreground="#667085", wraplength=520).pack(anchor="w", pady=8)

    def _open_data_dir(self):
        path = self.settings_store.open_directory()
        try:
            if os.name == "nt": os.startfile(path)
            else: subprocess.Popen(["xdg-open", str(path)])
        except OSError as error: messagebox.showerror(self._("无法打开"), str(error), parent=self.window)

    def validate(self):
        try:
            Decimal(self.vars["monthly_salary"].get()); Decimal(self.vars["workdays"].get()); Decimal(self.vars["overtime_multiplier"].get())
            times = [datetime.strptime(self.vars[key].get(), "%H:%M").time() for key in ("work_start", "lunch_start", "lunch_end", "work_end", "overtime_start")]
            if not (times[0] < times[1] < times[2] < times[3] <= times[4]): raise ValueError("作息时间顺序不正确")
            if Decimal(self.vars["workdays"].get()) <= 0: raise ValueError("月工作日必须大于0")
            return True
        except Exception as error:
            messagebox.showerror(self._("设置有误"), self.i18n.error(str(error)), parent=self.window); return False

    def save(self):
        self._auto_days()
        if not self.validate(): return
        p = self.config["profile"]
        for key in ("year", "month", "monthly_salary", "workdays", "manual_workdays", "overtime_multiplier", "work_start", "lunch_start", "lunch_end", "work_end", "overtime_start"):
            p[key] = self.vars[key].get()
        p["year"], p["month"], p["manual_workdays"] = int(self.vars["year"].get()), int(self.vars["month"].get()), bool(self.vars["manual_workdays"].get())
        self._sync_float_amount_option()
        for key in ("refresh_mode","privacy_mode","float_amount_visible","language"): self.config["display"][key]=self.vars[key].get()
        self.config["window"]["float_open"] = True
        for key in ("skip_close_confirmation", "reset_expected_end_daily"): self.config["behavior"][key] = bool(self.vars[key].get())
        self.config["setup_completed"] = True
        language_changed = self.vars["language"].get() != self.original_language
        self.on_save(self.config)
        if language_changed:
            messagebox.showinfo(self._("语言设置"), self._("语言设置将在下次启动时生效。"), parent=self.window)
        self.cancel()

    def cancel(self):
        try: self.window.grab_release()
        except tk.TclError: pass
        self.window.destroy()
        if self.on_close:
            self.on_close()
