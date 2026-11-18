from __future__ import annotations

import tkinter as tk
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from tkinter import messagebox, ttk

from .calendar_service import month_workdays
from .window_utils import center_window
from .ui_styles import COLORS, configure_styles
from .i18n import I18n, LANGUAGE_LABELS


class SetupWizard:
    def __init__(self, parent, config, on_complete, i18n=None):
        self.parent, self.config, self.on_complete = parent, deepcopy(config), on_complete
        self.i18n = i18n or I18n(config.get("display", {}).get("language", "zh_CN"))
        self._ = self.i18n.t
        self.window = tk.Toplevel(parent); self.window.title(self._("欢迎使用 SalaryTick")); self.window.resizable(False, False); self.window.configure(bg=COLORS["app_bg"]); configure_styles(self.window, self.i18n.font_name); self.window.protocol("WM_DELETE_WINDOW", self.request_close)
        center_window(self.window, None, 500, 390)
        p=self.config["profile"]
        self.vars={key:tk.StringVar(value=str(p[key])) for key in ("monthly_salary","workdays","overtime_multiplier","work_start","lunch_start","lunch_end","work_end","overtime_start")}
        self.year=tk.IntVar(value=p["year"]); self.month=tk.IntVar(value=p["month"]); self.page=0
        self.language=tk.StringVar(value=self.i18n.language)
        self.manual_workdays=tk.BooleanVar(value=bool(p.get("manual_workdays",False)))
        self.salary_visible = False
        self.body=ttk.Frame(self.window,padding=22); self.body.pack(fill="both",expand=True)
        self.auto_days()
        self.render(); self.window.grab_set()

    def request_close(self):
        try:
            self.window.grab_release()
        except tk.TclError:
            pass
        self.parent.request_exit(parent=self.window)

    def render(self):
        self.window.title(self._("欢迎使用 SalaryTick"))
        configure_styles(self.window, self.i18n.font_name)
        for child in self.body.winfo_children(): child.destroy()
        if self.page==0: self.language_page()
        elif self.page==1: self.salary_page()
        else: self.schedule_page()
    def select_language(self, language):
        self.language.set(language)
        self.config["display"]["language"] = language
        self.i18n = I18n(language)
        self._ = self.i18n.t
        self.render()
    def language_page(self):
        title = "选择界面语言" if self.language.get()=="zh_CN" else "Choose Your Language"
        note = "请选择首次设置和应用界面使用的语言。" if self.language.get()=="zh_CN" else "Choose the language for setup and the application interface."
        ttk.Label(self.body,text=title,style="DialogTitle.TLabel").pack(anchor="w",pady=(0,10))
        ttk.Label(self.body,text=note,foreground="#667085").pack(anchor="w",pady=(0,18))
        ttk.Button(self.body,text=LANGUAGE_LABELS["zh_CN"],style="Primary.TButton" if self.language.get()=="zh_CN" else "Secondary.TButton",command=lambda:self.select_language("zh_CN")).pack(fill="x",pady=5)
        ttk.Button(self.body,text=LANGUAGE_LABELS["en_US"],style="Primary.TButton" if self.language.get()=="en_US" else "Secondary.TButton",command=lambda:self.select_language("en_US")).pack(fill="x",pady=5)
        ttk.Button(self.body,text=self._("下一步"),style="Primary.TButton",command=lambda:(setattr(self,"page",1),self.render())).pack(anchor="e",pady=(24,0))

    def field(self,row,label,var,mask=False):
        ttk.Label(self.body,text=self._(label)).grid(row=row,column=0,sticky="w",pady=10)
        if mask:
            box=ttk.Frame(self.body)
            box.grid(row=row,column=1,sticky="w",padx=18)
            entry=ttk.Entry(box,textvariable=var,width=17,show="●")
            entry.pack(side="left")
            self.salary_entry=entry
            self.salary_eye_button=ttk.Button(box,text=self._("显示"),style="Text.TButton",width=5,command=self.toggle_salary_visibility)
            self.salary_eye_button.pack(side="left",padx=(6,0))
        else:
            entry=ttk.Entry(self.body,textvariable=var,width=20)
            entry.grid(row=row,column=1,sticky="w",padx=18)
        return entry

    def toggle_salary_visibility(self):
        self.salary_visible=not self.salary_visible
        self.salary_entry.configure(show="" if self.salary_visible else "●")
        self.salary_eye_button.configure(text=self._("隐藏") if self.salary_visible else "显示")

    def salary_page(self):
        ttk.Label(self.body,text=self._("先设置工资信息"),style="DialogTitle.TLabel").grid(row=0,column=0,columnspan=2,sticky="w",pady=(0,12))
        ttk.Label(self.body,text=self._("这些信息只需设置一次，以后可以在设置中修改。"),foreground="#667085").grid(row=1,column=0,columnspan=2,sticky="w",pady=(0,15))
        box=ttk.Frame(self.body); box.grid(row=2,column=1,sticky="w",padx=18); ttk.Spinbox(box,from_=2020,to=2100,textvariable=self.year,width=7,command=self.auto_days).pack(side="left"); ttk.Label(box,text=self._("年")).pack(side="left",padx=4); ttk.Spinbox(box,from_=1,to=12,textvariable=self.month,width=5,command=self.auto_days).pack(side="left"); ttk.Label(box,text=self._("月")).pack(side="left",padx=4); ttk.Label(self.body,text=self._("工资所属年月")).grid(row=2,column=0,sticky="w")
        self.field(3,"月基本工资",self.vars["monthly_salary"],True)
        self.workdays_entry=self.field(4,"月工作日",self.vars["workdays"])
        ttk.Checkbutton(self.body,text=self._("手动修改工作日数"),variable=self.manual_workdays,command=self.auto_days).grid(row=5,column=1,sticky="w",padx=18)
        self.field(6,"加班倍率",self.vars["overtime_multiplier"])
        self.auto_days()
        ttk.Button(self.body,text=self._("上一步"),style="Text.TButton",command=lambda:(setattr(self,"page",0),self.render())).grid(row=8,column=0,sticky="w",pady=20)
        ttk.Button(self.body,text=self._("下一步"),style="Primary.TButton",command=self.next).grid(row=8,column=1,sticky="e",pady=20)

    def auto_days(self):
        manual=self.manual_workdays.get()
        if not manual:
            try:self.vars["workdays"].set(str(month_workdays(self.year.get(),self.month.get())))
            except Exception:pass
        if hasattr(self,"workdays_entry") and self.workdays_entry.winfo_exists():
            self.workdays_entry.configure(state="normal" if manual else "readonly")

    def schedule_page(self):
        ttk.Label(self.body,text=self._("设置标准作息"),style="DialogTitle.TLabel").grid(row=0,column=0,columnspan=2,sticky="w",pady=(0,14))
        for i,(label,key) in enumerate((("上班时间","work_start"),("午休开始","lunch_start"),("午休结束","lunch_end"),("正常下班","work_end"),("加班起算","overtime_start")),1): self.field(i,label,self.vars[key])
        ttk.Label(self.body,text=self._("正常下班至加班起算之间不计薪。"),foreground="#667085").grid(row=6,column=0,columnspan=2,sticky="w",pady=12)
        ttk.Button(self.body,text=self._("上一步"),style="Text.TButton",command=lambda:(setattr(self,"page",1),self.render())).grid(row=7,column=0,sticky="w"); ttk.Button(self.body,text=self._("完成设置"),style="Primary.TButton",command=self.finish).grid(row=7,column=1,sticky="e")

    def next(self):
        try:
            self.auto_days()
            if Decimal(self.vars["monthly_salary"].get())<0 or Decimal(self.vars["workdays"].get())<=0 or Decimal(self.vars["overtime_multiplier"].get())<0: raise ValueError("工资、工作日和倍率输入不正确")
            self.page=2; self.render()
        except Exception as e:messagebox.showerror(self._("输入有误"),self.i18n.error(str(e)),parent=self.window)

    def finish(self):
        try:
            times=[datetime.strptime(self.vars[k].get(),"%H:%M").time() for k in ("work_start","lunch_start","lunch_end","work_end","overtime_start")]
            if not(times[0]<times[1]<times[2]<times[3]<=times[4]):raise ValueError("作息时间顺序不正确")
            p=self.config["profile"]; p.update({k:v.get() for k,v in self.vars.items()}); p["year"],p["month"],p["manual_workdays"]=self.year.get(),self.month.get(),bool(self.manual_workdays.get())
            self.config["display"]["language"] = self.language.get()
            self.config["today"]={"date":datetime.now().date().isoformat(),"expected_end":p["work_end"]}; self.config["setup_completed"]=True
            self.window.grab_release()
            self.window.destroy()
            self.on_complete(self.config)
        except Exception as e:messagebox.showerror(self._("输入有误"),self.i18n.error(str(e)),parent=self.window)
