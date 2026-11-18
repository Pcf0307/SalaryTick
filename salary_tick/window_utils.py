from __future__ import annotations

import tkinter as tk


def center_window(window: tk.Toplevel, parent: tk.Misc | None, width: int, height: int) -> None:
    """Center a popup over a visible parent, otherwise center it on screen."""
    window.update_idletasks()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    use_parent = False
    if parent is not None:
        try:
            use_parent = bool(parent.winfo_viewable())
        except tk.TclError:
            use_parent = False
    if use_parent:
        x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
    else:
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
    x = max(0, min(x, screen_width - width))
    y = max(0, min(y, screen_height - height))
    window.geometry(f"{width}x{height}+{x}+{y}")
