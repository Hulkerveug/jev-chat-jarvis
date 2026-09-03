"""
spacemaker - Spatial automation skill for Hulker.

Controls screen space: window positions, layouts, screen regions, clicks by area.
Invoke via voice: "HULKER skill spacemaker [command]"

Commands (pass as arguments to the skill, or speak directly to Hulker):
  layout grid [n]          — Arrange open windows in an n×n grid
  layout left              — Snap active window to left half
  layout right             — Snap active window to right half
  layout top               — Snap active window to top half
  layout bottom            — Snap active window to bottom half
  layout full              — Maximize active window
  move [x] [y]            — Move active window to (x, y) offset
  resize [w] [h]          — Resize active window to w×h
  click area [name]       — Click in a named screen area
  screen info             — Report screen dimensions and open windows
  arrange [preset]        — Apply a window arrangement preset

Presets:
  - dual          : two windows side by side
  - triple        : three windows in a row
  - grid2         : 2×2 grid
  - focus         : active window centered, all others minimized
"""

import sys
import ctypes
import time
from typing import List, Optional, Tuple

# Windows API for window management
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

SW_SHOWMINIMIZE = 2
SW_SHOWMAXIMIZE = 3
SW_SHOWNA = 8
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_SHOWWINDOW = 0x0040

INPUT_MODE = ctypes.c_ulong(3)  # SetWindowPos


def get_screen_size() -> Tuple[int, int]:
    """Get primary screen dimensions in pixels."""
    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)
    return w, h


def get_active_window() -> int:
    """Get handle of the foreground window."""
    return user32.GetForegroundWindow()


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def get_window_rect(hwnd: int) -> Optional[Tuple[int, int, int, int]]:
    """Get window rect (left, top, right, bottom). Returns tuple or None."""
    rect = RECT()
    if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return (rect.left, rect.top, rect.right, rect.bottom)
    return None


def set_window_pos(hwnd: int, x: int, y: int, w: int, h: int):
    """Set window position and size."""
    user32.SetWindowPos(
        hwnd, 0, x, y, w, h,
        SWP_NOZORDER | SWP_SHOWWINDOW
    )


def move_window(hwnd: int, x: int, y: int):
    """Move window to (x, y) without resizing."""
    user32.SetWindowPos(hwnd, 0, x, y, 0, 0, SWP_NOSIZE | SWP_NOZORDER)


def resize_window(hwnd: int, w: int, h: int):
    """Resize window to w×h without moving."""
    rect = get_window_rect(hwnd)
    if rect:
        x, y = rect[0], rect[1]
        user32.SetWindowPos(hwnd, 0, x, y, w, h, SWP_NOZORDER)


def minimize_window(hwnd: int):
    """Minimize a window."""
    user32.ShowWindow(hwnd, SW_SHOWMINIMIZE)


def maximize_window(hwnd: int):
    """Maximize a window."""
    user32.ShowWindow(hwnd, SW_SHOWMAXIMIZE)


def restore_window(hwnd: int):
    """Restore a window from minimized state."""
    user32.ShowWindow(hwnd, SW_SHOWNA)


def enumerate_windows() -> List[Tuple[int, str]]:
    """Enumerate all visible top-level windows. Returns list of (hwnd, title)."""
    results = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
    def enum_proc(hwnd, lParam):
        if user32.IsWindowVisible(hwnd):
            title = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, title, 256)
            title_str = title.value
            if title_str.strip():
                results.append((hwnd, title_str))
        return True

    user32.EnumWindows(enum_proc, 0)
    return results


def snap_left(hwnd: int):
    """Snap window to left half of screen."""
    sw, sh = get_screen_size()
    resize_window(hwnd, sw // 2, sh)


def snap_right(hwnd: int):
    """Snap window to right half of screen."""
    sw, sh = get_screen_size()
    resize_window(hwnd, sw // 2, sh)
    move_window(hwnd, sw // 2, 0)


def snap_top(hwnd: int):
    """Snap window to top half of screen."""
    sw, sh = get_screen_size()
    resize_window(hwnd, sw, sh // 2)


def snap_bottom(hwnd: int):
    """Snap window to bottom half of screen."""
    sw, sh = get_screen_size()
    resize_window(hwnd, sw, sh // 2)
    move_window(hwnd, 0, sh // 2)


def snap_full(hwnd: int):
    """Maximize window."""
    maximize_window(hwnd)


def arrange_dual():
    """Arrange top two windows side by side."""
    windows = enumerate_windows()
    if len(windows) < 2:
        print("Need at least 2 windows for dual layout.")
        return
    sw, sh = get_screen_size()
    half_w = sw // 2
    hwnd1, _ = windows[0]
    hwnd2, _ = windows[1]
    set_window_pos(hwnd1, 0, 0, half_w, sh)
    set_window_pos(hwnd2, half_w, 0, half_w, sh)
    print(f"Dual layout applied: {windows[0][1]} | {windows[1][1]}")


def arrange_triple():
    """Arrange top three windows in a row."""
    windows = enumerate_windows()
    if len(windows) < 3:
        print("Need at least 3 windows for triple layout.")
        return
    sw, sh = get_screen_size()
    third_w = sw // 3
    for i, (hwnd, title) in enumerate(windows[:3]):
        set_window_pos(hwnd, i * third_w, 0, third_w, sh)
    print(f"Triple layout applied: {[w[1] for w in windows[:3]]}")


def arrange_grid2():
    """Arrange top four windows in a 2×2 grid."""
    windows = enumerate_windows()
    if len(windows) < 4:
        print("Need at least 4 windows for 2×2 grid.")
        return
    sw, sh = get_screen_size()
    half_w = sw // 2
    half_h = sh // 2
    positions = [
        (0, 0), (half_w, 0),
        (0, half_h), (half_w, half_h),
    ]
    for i, (hwnd, title) in enumerate(windows[:4]):
        x, y = positions[i]
        set_window_pos(hwnd, x, y, half_w, half_h)
    print(f"2×2 grid applied: {[w[1] for w in windows[:4]]}")


def focus_active():
    """Center active window, minimize all others."""
    hwnd = get_active_window()
    sw, sh = get_screen_size()
    w, h = sw // 2, sh // 2
    x = (sw - w) // 2
    y = (sh - h) // 2
    set_window_pos(hwnd, x, y, w, h)
    for other_hwnd, _ in enumerate_windows():
        if other_hwnd != hwnd:
            minimize_window(other_hwnd)
    print(f"Focus mode: {get_window_title(hwnd)} centered.")


def get_window_title(hwnd: int) -> str:
    """Get window title."""
    title = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, title, 256)
    return title.value


def click_area(name: str):
    """Click in a named screen area."""
    sw, sh = get_screen_size()
    areas = {
        "center": (sw // 2, sh // 2),
        "top-left": (sw // 4, sh // 4),
        "top-right": (3 * sw // 4, sh // 4),
        "bottom-left": (sw // 4, 3 * sh // 4),
        "bottom-right": (3 * sw // 4, 3 * sh // 4),
        "top-center": (sw // 2, sh // 4),
        "bottom-center": (sw // 2, 3 * sh // 4),
        "left-center": (sw // 4, sh // 2),
        "right-center": (3 * sw // 4, sh // 2),
    }
    if name.lower() not in areas:
        print(f"Unknown area: {name}. Known: {list(areas.keys())}")
        return
    x, y = areas[name.lower()]
    # Use Hulker's click via absolute coords
    abs_x = int(x * 65535 / sw)
    abs_y = int(y * 65535 / sh)
    from hulker.actions import click
    click(abs_x, abs_y)
    print(f"Clicked {name} area at ({x}, {y}).")


def screen_info():
    """Print screen info and open windows."""
    sw, sh = get_screen_size()
    print(f"Screen: {sw}×{sh}")
    windows = enumerate_windows()
    print(f"Open windows: {len(windows)}")
    for hwnd, title in windows[:10]:
        print(f"  [{hwnd}] {title}")
    if len(windows) > 10:
        print(f"  ... and {len(windows) - 10} more")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nUsage: python -m hulker.skills.spacemaker <command> [args]")
        print("\nCommands:")
        print("  layout [left|right|top|bottom|full]")
        print("  layout grid [n]")
        print("  move [x] [y]")
        print("  resize [w] [h]")
        print("  click area [name]")
        print("  screen info")
        print("  arrange [dual|triple|grid2|focus]")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "layout":
        if len(sys.argv) < 3:
            print("Usage: layout [left|right|top|bottom|full|grid]")
            sys.exit(1)
        sub = sys.argv[2].lower()
        hwnd = get_active_window()
        if sub == "left":
            snap_left(hwnd)
            print("Window snapped left.")
        elif sub == "right":
            snap_right(hwnd)
            print("Window snapped right.")
        elif sub == "top":
            snap_top(hwnd)
            print("Window snapped top.")
        elif sub == "bottom":
            snap_bottom(hwnd)
            print("Window snapped bottom.")
        elif sub == "full":
            snap_full(hwnd)
            print("Window maximized.")
        elif sub == "grid":
            n = int(sys.argv[3]) if len(sys.argv) > 3 else 2
            sw, sh = get_screen_size()
            cell_w = sw // n
            cell_h = sh // n
            windows = enumerate_windows()
            if len(windows) < n * n:
                print(f"Need {n*n} windows for {n}×{n} grid, have {len(windows)}.")
            else:
                for i, (wh, _) in enumerate(windows[:n*n]):
                    row, col = divmod(i, n)
                    set_window_pos(wh, col * cell_w, row * cell_h, cell_w, cell_h)
                print(f"{n}×{n} grid applied.")
        else:
            print(f"Unknown layout: {sub}")

    elif cmd == "move":
        if len(sys.argv) < 4:
            print("Usage: move [x] [y]")
            sys.exit(1)
        x, y = int(sys.argv[2]), int(sys.argv[3])
        hwnd = get_active_window()
        move_window(hwnd, x, y)
        print(f"Window moved to ({x}, {y}).")

    elif cmd == "resize":
        if len(sys.argv) < 4:
            print("Usage: resize [w] [h]")
            sys.exit(1)
        w, h = int(sys.argv[2]), int(sys.argv[3])
        hwnd = get_active_window()
        resize_window(hwnd, w, h)
        print(f"Window resized to {w}×{h}.")

    elif cmd == "click":
        if len(sys.argv) < 3:
            print("Usage: click area [name]")
            sys.exit(1)
        if sys.argv[2].lower() == "area":
            name = sys.argv[3] if len(sys.argv) > 3 else "center"
            click_area(name)
        else:
            print("Usage: click area [name]")

    elif cmd == "screen":
        if len(sys.argv) > 2 and sys.argv[2].lower() == "info":
            screen_info()
        else:
            screen_info()

    elif cmd == "arrange":
        if len(sys.argv) < 3:
            print("Usage: arrange [dual|triple|grid2|focus]")
            sys.exit(1)
        preset = sys.argv[2].lower()
        if preset == "dual":
            arrange_dual()
        elif preset == "triple":
            arrange_triple()
        elif preset == "grid2":
            arrange_grid2()
        elif preset == "focus":
            focus_active()
        else:
            print(f"Unknown preset: {preset}")
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
