"""
Windows automation actions: mouse, keyboard, app launch.
Uses pywin32 / ctypes for low-level control.
"""

import logging
import subprocess
import time
from typing import Optional

import win32api
import win32con
import win32gui
import win32com.client
from ctypes import *
from ctypes.wintypes import *

log = logging.getLogger("hulker.actions")

# --- Types ---

PUL = POINTER(c_ulong)


class MOUSEINPUT(Structure):
    _fields_ = [
        ("dx", c_long),
        ("dy", c_long),
        ("mouseData", c_ulong),
        ("dwFlags", c_ulong),
        ("time", c_ulong),
        ("dwExtraInfo", PUL),
    ]


class KEYBDINPUT(Structure):
    _fields_ = [
        ("wVk", c_ushort),
        ("wScan", c_ushort),
        ("dwFlags", c_ulong),
        ("time", c_ulong),
        ("dwExtraInfo", PUL),
    ]


class INPUT(Structure):
    _fields_ = [
        ("type", c_ulong),
        ("mi", MOUSEINPUT),
    ]


class INPUT_KB(Structure):
    _fields_ = [
        ("type", c_ulong),
        ("ki", KEYBDINPUT),
    ]


INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_ABSOLUTE = 0x8000
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004


# --- Mouse ---

def _send_mouse_input(flags: int, x: int = 0, y: int = 0, data: int = 0):
    """Send a single mouse input event."""
    extra = c_ulong(0)
    mi = MOUSEINPUT(x, y, data, flags, 0, pointer(extra))
    inp = INPUT(INPUT_MOUSE, mi)
    windll.user32.SendInput(1, pointer(inp), sizeof(INPUT))


def click(x: int, y: int, button: str = "left", delay: float = 0.05):
    """Click at screen coordinates (x, y). button: left, right, middle."""
    _send_mouse_input(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, x, y)
    time.sleep(0.02)

    down_flag = {
        "left": MOUSEEVENTF_LEFTDOWN,
        "right": MOUSEEVENTF_RIGHTDOWN,
        "middle": MOUSEEVENTF_MIDDLEDOWN,
    }[button]
    up_flag = {
        "left": MOUSEEVENTF_LEFTUP,
        "right": MOUSEEVENTF_RIGHTUP,
        "middle": MOUSEEVENTF_MIDDLEUP,
    }[button]

    _send_mouse_input(down_flag)
    time.sleep(delay)
    _send_mouse_input(up_flag)
    log.info("Clicked %s at (%d, %d)", button, x, y)


def right_click(x: int, y: int):
    click(x, y, button="right")


def middle_click(x: int, y: int):
    click(x, y, button="middle")


def double_click(x: int, y: int, delay: float = 0.1):
    click(x, y, button="left")
    time.sleep(delay)
    click(x, y, button="left")


def mouse_move(x: int, y: int):
    """Move mouse to (x, y) without clicking."""
    _send_mouse_input(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, x, y)
    log.info("Mouse moved to (%d, %d)", x, y)


def mouse_scroll(lines: int = 3):
    """Scroll mouse wheel."""
    _send_mouse_input(MOUSEEVENTF_WHEEL, data=lines * 120)
    log.info("Scrolled %d lines", lines)


# --- Keyboard ---

def _send_keyboard_input(wVk: int, wScan: int, dwFlags: int):
    """Send a single keyboard input event."""
    extra = c_ulong(0)
    ki = KEYBDINPUT(wVk, wScan, dwFlags, 0, pointer(extra))
    inp = INPUT_KB(INPUT_KEYBOARD, ki)
    windll.user32.SendInput(1, pointer(inp), sizeof(INPUT_KB))


def type_text(text: str, delay: float = 0.02):
    """Type text character by character using SendInput with Unicode."""
    for char in text:
        code = ord(char)
        _send_keyboard_input(0, code, KEYEVENTF_UNICODE)
        _send_keyboard_input(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)
        time.sleep(delay)
    log.info("Typed: %s", text[:50])


def key_press(vk_code: int):
    """Press a single key by virtual key code."""
    _send_keyboard_input(vk_code, 0, 0)
    _send_keyboard_input(vk_code, 0, KEYEVENTF_KEYUP)


# --- App Launch ---

def launch_app(path: str) -> bool:
    """Launch an application by path or name."""
    try:
        subprocess.Popen(path, shell=True)
        log.info("Launched: %s", path)
        return True
    except Exception as e:
        log.error("Failed to launch %s: %s", path, e)
        return False


def find_window(title_contains: str) -> Optional[int]:
    """Find a window by title substring. Returns HWND or None."""
    def enum_callback(hwnd, result):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title_contains.lower() in title.lower():
                result.append(hwnd)
        return True

    results = []
    win32gui.EnumWindows(enum_callback, results)
    return results[0] if results else None


def activate_window(title_contains: str) -> bool:
    """Find and bring a window to foreground by title."""
    hwnd = find_window(title_contains)
    if hwnd:
        win32gui.SetForegroundWindow(hwnd)
        log.info("Activated window: %s", title_contains)
        return True
    log.warning("Window not found: %s", title_contains)
    return False


# --- Wrapper classes ---

class Mouse:
    def click(self, x: int, y: int, button: str = "left"):
        click(x, y, button)

    def right_click(self, x: int, y: int):
        right_click(x, y)

    def double_click(self, x: int, y: int):
        double_click(x, y)

    def move(self, x: int, y: int):
        mouse_move(x, y)

    def scroll(self, lines: int = 3):
        mouse_scroll(lines)


class Keyboard:
    def type(self, text: str, delay: float = 0.02):
        type_text(text, delay)

    def press(self, vk_code: int):
        key_press(vk_code)


class AppLauncher:
    def open(self, name_or_path: str) -> bool:
        return launch_app(name_or_path)

    def find(self, title: str) -> Optional[int]:
        return find_window(title)

    def activate(self, title: str) -> bool:
        return activate_window(title)
