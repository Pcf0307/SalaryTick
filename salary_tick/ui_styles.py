from __future__ import annotations

from tkinter import ttk

COLORS = {
    "app_bg": "#F4F6F8",
    "card_bg": "#FFFFFF",
    "text": "#27313D",
    "muted": "#667085",
    "weak": "#98A2B3",
    "border": "#DDE2E8",
    "accent": "#506B88",
    "accent_hover": "#425B74",
    "soft": "#EEF2F6",
    "soft_hover": "#E4E9EE",
    "normal": "#506B88",
    "pause": "#7A8491",
    "wait": "#756A8F",
    "overtime": "#A66B35",
    "done": "#537A68",
    "error": "#B54747",
}

def configure_styles(widget, font_name: str = "Microsoft YaHei UI") -> ttk.Style:
    style = ttk.Style(widget)
    style.theme_use("clam")

    style.configure("TFrame", background=COLORS["app_bg"])
    style.configure("Card.TFrame", background=COLORS["card_bg"])
    style.configure("TLabel", background=COLORS["app_bg"], foreground=COLORS["text"], font=(font_name, 9))
    style.configure("Card.TLabel", background=COLORS["card_bg"], foreground=COLORS["text"], font=(font_name, 9))
    style.configure("Title.TLabel", background=COLORS["app_bg"], foreground=COLORS["text"], font=(font_name, 18, "bold"))
    style.configure("Muted.TLabel", background=COLORS["app_bg"], foreground=COLORS["muted"], font=(font_name, 9))
    style.configure("CardLabel.TLabel", background=COLORS["card_bg"], foreground=COLORS["muted"], font=(font_name, 9))
    style.configure("Money.TLabel", background=COLORS["card_bg"], foreground=COLORS["text"], font=(font_name, 15, "bold"))
    style.configure("Total.TLabel", background=COLORS["card_bg"], foreground=COLORS["text"], font=(font_name, 16, "bold"))

    for name, color in (
        ("StatusWork", COLORS["normal"]),
        ("StatusPause", COLORS["pause"]),
        ("StatusWait", COLORS["wait"]),
        ("StatusOvertime", COLORS["overtime"]),
        ("StatusDone", COLORS["done"]),
        ("StatusError", COLORS["error"]),
    ):
        style.configure(f"{name}.TLabel", background=COLORS["card_bg"], foreground=color, font=(font_name, 9, "bold"))

    style.configure("Primary.TButton", padding=(12, 5), foreground="#FFFFFF", background=COLORS["accent"], borderwidth=0, font=(font_name, 9, "bold"))
    style.map("Primary.TButton", background=[("active", COLORS["accent_hover"]), ("disabled", COLORS["weak"])])
    style.configure("Secondary.TButton", padding=(10, 4), foreground=COLORS["text"], background=COLORS["soft"], borderwidth=0, relief="flat", font=(font_name, 9))
    style.map("Secondary.TButton", background=[("active", COLORS["soft_hover"])])
    style.configure("Small.TButton", padding=(8, 3), foreground=COLORS["text"], background=COLORS["soft"], borderwidth=0, relief="flat", font=(font_name, 9))
    style.map("Small.TButton", background=[("active", COLORS["soft_hover"])])
    style.configure("Text.TButton", padding=(7, 3), foreground=COLORS["accent"], background=COLORS["app_bg"], borderwidth=0, font=(font_name, 9))
    style.map("Text.TButton", foreground=[("active", COLORS["accent_hover"])])

    style.configure("TEntry", padding=(7, 4), fieldbackground="#FFFFFF", foreground=COLORS["text"], bordercolor=COLORS["border"], lightcolor=COLORS["border"], darkcolor=COLORS["border"], font=(font_name, 9))
    style.configure("TSpinbox", padding=(6, 3), fieldbackground="#FFFFFF", foreground=COLORS["text"], bordercolor=COLORS["border"], arrowsize=12, font=(font_name, 9))
    style.configure("TCheckbutton", background=COLORS["app_bg"], foreground=COLORS["text"], font=(font_name, 9), padding=(2, 3))
    style.configure("TRadiobutton", background=COLORS["app_bg"], foreground=COLORS["text"], font=(font_name, 9), padding=(2, 3))

    style.configure("Nav.TButton", anchor="w", padding=(10, 6), foreground=COLORS["text"], background=COLORS["app_bg"], borderwidth=0, relief="flat", font=(font_name, 9))
    style.map("Nav.TButton", background=[("active", COLORS["soft"])])
    style.configure("NavActive.TButton", anchor="w", padding=(10, 6), foreground=COLORS["accent"], background=COLORS["soft"], borderwidth=0, relief="flat", font=(font_name, 9, "bold"))
    style.configure("DialogTitle.TLabel", background=COLORS["app_bg"], foreground=COLORS["text"], font=(font_name, 14, "bold"))
    style.configure("Treeview", background="#FFFFFF", fieldbackground="#FFFFFF", foreground=COLORS["text"], rowheight=32, borderwidth=0, font=(font_name, 9))
    style.configure("Treeview.Heading", background=COLORS["soft"], foreground=COLORS["text"], relief="flat", borderwidth=0, padding=(8, 6), font=(font_name, 9, "bold"))
    style.map("Treeview", background=[("selected", "#E8EEF4")], foreground=[("selected", COLORS["text"])])
    style.map("Treeview.Heading", background=[("active", COLORS["soft_hover"])])
    style.configure("TSeparator", background=COLORS["border"])
    return style
