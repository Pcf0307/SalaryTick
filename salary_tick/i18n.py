from __future__ import annotations

import re

SUPPORTED_LANGUAGES = {"zh_CN", "en_US"}
LANGUAGE_LABELS = {"zh_CN": "简体中文", "en_US": "English"}

EN = {
    "实时工资计算器": "SalaryTick",
    "设置": "Settings", "显示金额": "Show Amount", "隐藏金额": "Hide Amount",
    "正常工时自动累计；加班只累计到今日预计下班时间。": "Regular hours accrue automatically; overtime stops at today's expected end time.",
    "今日安排": "Today", "今日预计下班时间": "Expected End", "工作时长": "Work Time", "今日合计": "Today's Total",
    "本月概览": "This Month", "+ 补录加班": "+ Add Overtime", "查看明细": "View Details",
    "本月基本工资": "Base Pay", "本月加班": "Overtime", "设置有误": "Invalid Settings",
    "准备就绪": "Ready", "输入有误": "Invalid input", "预计下班时间格式应为 HH:MM": "Expected end time must use HH:MM.",
    "金额已隐藏": "Amount Hidden", "当前设置为“始终隐藏”。": "Amount visibility is set to Always Hidden.",
    "本月加班明细": "Overtime Details", "选择": "Select", "日期": "Date", "计薪加班": "Paid Overtime", "估算金额": "Estimated Pay", "来源": "Source",
    "删除": "Delete", "编辑": "Edit", "请选择记录": "Select a Record", "请先勾选一条记录。": "Select one record first.",
    "删除加班记录": "Delete Overtime Record", "确定删除所选记录吗？": "Delete the selected record?",
    "修改加班记录": "Edit Overtime Record", "补录加班": "Add Overtime", "加班小时": "Overtime Hours", "加班分钟": "Overtime Minutes",
    "保存": "Save", "无法保存": "Unable to Save", "记录已存在": "Record Already Exists", "是否覆盖？": "Overwrite it?",
    "日期不在可补录范围内": "The date is outside the allowed range.", "小时必须为0～23，分钟必须为0～59": "Hours must be 0-23 and minutes must be 0-59.",
    "加班时长必须大于0": "Overtime duration must be greater than zero.", "今天仍在实时计算，请通过‘今日预计下班时间’调整": "Today is still being calculated. Adjust the expected end time instead.",
    "退出确认": "Exit SalaryTick", "确定退出实时工资计算器吗？": "Exit SalaryTick?", "以后退出时不再提示": "Do not ask again", "取消": "Cancel", "退出": "Exit",
    "打开主界面": "Open Dashboard", "预计下班": "Expected End", "预计下班 -30分钟": "End Time -30 min", "预计下班 +30分钟": "End Time +30 min",
    "显示／隐藏金额": "Show / Hide Amount", "退出程序": "Exit SalaryTick",
    "用户基本信息": "User Profile", "工资信息": "Salary", "标准作息": "Work Schedule", "工具设置": "App Settings",
    "显示设置": "Display", "悬浮窗设置": "Floating Window", "程序行为": "Behavior", "数据管理": "Data",
    "保存并应用": "Save and Apply", "工资所属年月": "Salary Month", "月基本工资": "Monthly Salary", "月工作日": "Workdays",
    "手动修改工作日数": "Set workdays manually", "加班倍率": "Overtime Multiplier", "上班时间": "Work Start",
    "午休开始": "Lunch Start", "午休结束": "Lunch End", "正常下班": "Work End", "加班起算": "Overtime Start",
    "正常下班至加班起算之间不计入工作时长和加班工资。": "Time between work end and overtime start is unpaid.",
    "刷新方式": "Refresh Mode", "秒表（金额平滑上涨）": "Stopwatch (smooth amount updates)", "每秒刷新": "Once per second",
    "金额显示方式": "Amount Visibility", "只影响界面显示，不影响工资计算和本地保存。": "Affects display only, not calculations or local storage.",
    "直接显示": "Always Show", "默认隐藏，手动切换": "Hidden by Default", "始终隐藏": "Always Hidden", "手动切换": "Hidden by Default",
    "SalaryTick启动后始终显示悬浮窗。": "The floating window is always shown when SalaryTick starts.",
    "悬浮窗默认显示金额": "Show amount in floating window by default", "默认隐藏或始终隐藏时，此选项不可用。": "Unavailable when amounts are hidden by default or always hidden.",
    "退出程序时显示确认": "Confirm before exit", "新的一天恢复正常下班时间": "Reset expected end time each day",
    "数据保存在当前Windows用户的 LocalAppData 目录。": "Data is stored in the current Windows user's LocalAppData folder.",
    "打开数据保存位置": "Open Data Folder", "无法打开": "Unable to Open", "界面语言": "Language",
    "更改语言后重新启动 SalaryTick 生效。": "Restart SalaryTick to apply the language change.",
    "语言设置": "Language Changed", "语言设置将在下次启动时生效。": "The new language will be applied the next time SalaryTick starts.",
    "工资仅保存到当前Windows用户的本地数据目录。": "Salary data is stored only in the current Windows user's local data folder.",
    "隐藏": "Hide", "显示": "Show", "年": "Year", "月": "Month",
    "欢迎使用 SalaryTick": "Welcome to SalaryTick", "先设置工资信息": "Set Up Salary Information",
    "这些信息只需设置一次，以后可以在设置中修改。": "Set this up once. You can change it later in Settings.",
    "下一步": "Next", "设置标准作息": "Set Work Schedule", "正常下班至加班起算之间不计薪。": "Time between work end and overtime start is unpaid.",
    "上一步": "Back", "完成设置": "Finish Setup", "输入有误": "Invalid Input",
    "程序记录": "Automatic", "手动补录": "Manual", "手动修正": "Adjusted",
    "所选月份不是当前月份": "Selected month is not current", "今天不是法定工作日": "Non-working day", "尚未上班": "Not started",
    "午休中，收入暂停累计": "Lunch break", "正常工作时间": "Working", "加班中": "Overtime", "今日计算已停止": "Finished for today",
    "月基本工资不能为负数": "Monthly salary cannot be negative.", "月工作日必须大于0": "Monthly workdays must be greater than zero.",
    "加班倍率不能为负数": "Overtime multiplier cannot be negative.", "时间顺序应为：上班 < 午休开始 < 午休结束 < 下班": "Time order must be: work start < lunch start < lunch end < work end.",
    "加班起算时间不能早于正常下班时间": "Overtime start cannot be earlier than work end.", "今日预计下班时间不能早于正常下班时间": "Expected end cannot be earlier than work end.",
    "作息时间顺序不正确": "Work schedule times are not in the correct order.", "工资、工作日和倍率输入不正确": "Salary, workdays, or overtime multiplier is invalid.",
}


def normalize_language(value: str | None) -> str:
    return value if value in SUPPORTED_LANGUAGES else "zh_CN"


class I18n:
    def __init__(self, language: str = "zh_CN"):
        self.language = normalize_language(language)

    @property
    def font_name(self) -> str:
        return "Segoe UI" if self.language == "en_US" else "Microsoft YaHei UI"

    def t(self, text: str) -> str:
        if self.language != "en_US":
            return text
        return EN.get(text, text)

    def status(self, text: str) -> str:
        if self.language != "en_US":
            return text
        if text in EN:
            return EN[text]
        match = re.fullmatch(r"加班休息时间，(\d{2}:\d{2})开始计薪", text)
        if match:
            return f"Overtime break; paid overtime starts at {match.group(1)}"
        match = re.fullmatch(r"加班中，预计(\d{2}:\d{2})结束", text)
        if match:
            return f"Overtime; expected end {match.group(1)}"
        match = re.fullmatch(r"今日计算已于(\d{2}:\d{2})停止", text)
        if match:
            return f"Finished at {match.group(1)}"
        if text.startswith("输入有误："):
            return "Invalid input: " + self.error(text.removeprefix("输入有误："))
        return text

    def error(self, text: str) -> str:
        return self.t(text)

    def record_source(self, source: str) -> str:
        labels = {
            "automatic": self.t("程序记录"),
            "manual": self.t("手动补录"),
            "manual_override": self.t("手动修正"),
        }
        return labels.get(source, source)

    def weekday(self, weekday: int) -> str:
        if self.language == "en_US":
            return ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[weekday]
        return "一二三四五六日"[weekday]
