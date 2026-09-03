"""
Sample Hulker skill: clicks a predefined position.
Place in skills/ directory. Invoke via: "skill sample_click"
"""


def main():
    import ctypes
    import time

    # Click at center of screen (example)
    screen_w = ctypes.windll.user32.GetSystemMetrics(0)
    screen_h = ctypes.windll.user32.GetSystemMetrics(1)
    x = int((screen_w // 2) * 65535 / screen_w)
    y = int((screen_h // 2) * 65535 / screen_h)

    # Send mouse input
    PUL = ctypes.POINTER(ctypes.c_ulong)

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", ctypes.c_long),
            ("dy", ctypes.c_long),
            ("mouseData", ctypes.c_ulong),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", PUL),
        ]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", ctypes.c_ulong), ("mi", MOUSEINPUT)]

    INPUT_MOUSE = 0
    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_ABSOLUTE = 0x8000

    def send_mouse(flags, x=0, y=0, data=0):
        extra = ctypes.c_ulong(0)
        mi = MOUSEINPUT(x, y, data, flags, 0, ctypes.pointer(extra))
        inp = INPUT(INPUT_MOUSE, mi)
        ctypes.windll.user32.SendInput(1, ctypes.pointer(inp), ctypes.sizeof(INPUT))

    send_mouse(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, x, y)
    time.sleep(0.02)
    send_mouse(MOUSEEVENTF_LEFTDOWN)
    time.sleep(0.05)
    send_mouse(MOUSEEVENTF_LEFTUP)

    print("Sample click executed at center of screen.")


if __name__ == "__main__":
    main()
