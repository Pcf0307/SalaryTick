from __future__ import annotations

from .display_service import DisplayArea


def popup_size(screen_width: int, screen_height: int) -> tuple[int, int]:
    width = max(540, min(680, screen_width - 80))
    height = max(400, min(500, screen_height - 100))
    return width, height


def floating_menu_position(
    float_x: int,
    float_y: int,
    float_width: int,
    float_height: int,
    menu_width: int,
    menu_height: int,
    work_area: DisplayArea,
    gap: int = 8,
) -> tuple[int, int]:
    """Place the menu beside the float inside the float's current monitor."""
    if float_x + float_width + gap + menu_width <= work_area.right:
        x = float_x + float_width + gap
    else:
        x = max(work_area.left, float_x - menu_width - gap)
    centered_y = float_y + (float_height - menu_height) // 2
    max_y = max(work_area.top + gap, work_area.bottom - menu_height - gap)
    y = min(max(work_area.top + gap, centered_y), max_y)
    return x, y


def float_window_is_mandatory() -> bool:
    return True
