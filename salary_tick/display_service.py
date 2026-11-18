from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class DisplayArea:
    left: int
    top: int
    right: int
    bottom: int
    primary: bool = False

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


def _intersection_size(
    x: int, y: int, width: int, height: int, area: DisplayArea
) -> tuple[int, int]:
    overlap_width = max(0, min(x + width, area.right) - max(x, area.left))
    overlap_height = max(0, min(y + height, area.bottom) - max(y, area.top))
    return overlap_width, overlap_height


def window_is_visible(
    x: int,
    y: int,
    width: int,
    height: int,
    displays: list[DisplayArea],
    minimum_visible: int = 40,
) -> bool:
    required_width = min(max(1, minimum_visible), width)
    required_height = min(max(1, minimum_visible), height)
    return any(
        overlap_width >= required_width and overlap_height >= required_height
        for area in displays
        for overlap_width, overlap_height in [_intersection_size(x, y, width, height, area)]
    )


def area_for_point(x: int, y: int, displays: list[DisplayArea]) -> DisplayArea:
    for area in displays:
        if area.left <= x < area.right and area.top <= y < area.bottom:
            return area
    if not displays:
        return DisplayArea(0, 0, 1920, 1080, True)

    def distance_squared(area: DisplayArea) -> int:
        nearest_x = min(max(x, area.left), area.right - 1)
        nearest_y = min(max(y, area.top), area.bottom - 1)
        return (nearest_x - x) ** 2 + (nearest_y - y) ** 2

    return min(displays, key=distance_squared)


def area_for_window(
    x: int, y: int, width: int, height: int, displays: list[DisplayArea]
) -> DisplayArea:
    if not displays:
        return DisplayArea(0, 0, 1920, 1080, True)
    center_x = x + width // 2
    center_y = y + height // 2
    return area_for_point(center_x, center_y, displays)


def restore_visible_position(
    x: int,
    y: int,
    width: int,
    height: int,
    displays: list[DisplayArea],
    margin: int = 20,
) -> tuple[int, int]:
    """Keep a valid saved position. Recover invalid positions to the primary display."""
    if window_is_visible(x, y, width, height, displays):
        return x, y
    if not displays:
        return 30, 30
    target = next((area for area in displays if area.primary), displays[0])
    safe_x = min(max(target.left + margin, target.left), max(target.left, target.right - width - margin))
    safe_y = max(target.top + margin, target.bottom - height - margin)
    return safe_x, safe_y


def get_display_areas() -> list[DisplayArea]:
    """Return Windows monitor work areas in virtual-desktop coordinates."""
    if os.name != "nt":
        return []

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", wintypes.LONG),
            ("top", wintypes.LONG),
            ("right", wintypes.LONG),
            ("bottom", wintypes.LONG),
        ]

    class MONITORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("rcMonitor", RECT),
            ("rcWork", RECT),
            ("dwFlags", wintypes.DWORD),
        ]

    monitor_enum_proc = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HMONITOR,
        wintypes.HDC,
        ctypes.POINTER(RECT),
        wintypes.LPARAM,
    )
    result: list[DisplayArea] = []

    def callback(monitor, _hdc, _rect, _data):
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            work = info.rcWork
            result.append(
                DisplayArea(
                    int(work.left),
                    int(work.top),
                    int(work.right),
                    int(work.bottom),
                    bool(info.dwFlags & 1),
                )
            )
        return True

    callback_ref = monitor_enum_proc(callback)
    user32.EnumDisplayMonitors(0, 0, callback_ref, 0)
    return result
