#!/usr/bin/env python3
"""XTOBE Ai System Tray Launcher — quick access to all agents"""
import os
import sys
import subprocess
import threading
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "pillow"], capture_output=True)
    from PIL import Image, ImageDraw

try:
    import pystray
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "pystray"], capture_output=True)
    import pystray

BASE = Path(__file__).parent
OPERA = r"C:\Users\Nishan\AppData\Local\Programs\Opera GX\opera.exe"
OLLAMA = r"C:\Users\Nishan\AppData\Local\Programs\Ollama\ollama.exe"

def make_icon():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=(255, 61, 0, 255))
    d.ellipse([12, 12, 52, 52], fill=(10, 10, 15, 255))
    d.ellipse([20, 20, 44, 44], fill=(255, 145, 0, 255))
    return img

def run(cmd, cwd=str(BASE)):
    subprocess.Popen(cmd, cwd=cwd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def start_ollama():
    subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def start_voice():
    run([sys.executable, str(BASE / "voice_agent_server.py")])

def start_bridge():
    run([sys.executable, str(BASE / "agent_bridge.py")])

def open_opera(url):
    subprocess.Popen([OPERA, url])

def stop_ollama():
    os.system("taskkill /F /IM ollama.exe 2>nul")

def stop_python():
    os.system("taskkill /F /IM python.exe 2>nul")

def create_menu():
    return pystray.Menu(
        pystray.MenuItem("XTOBE Voice (8765)", lambda: open_opera("http://127.0.0.1:8765")),
        pystray.MenuItem("Agent Bridge (8767)", lambda: open_opera("http://127.0.0.1:8767")),
        pystray.MenuItem("Dashboard (8000)", lambda: open_opera("http://127.0.0.1:8000")),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Start All", lambda: (start_ollama(), start_voice(), start_bridge())),
        pystray.MenuItem("Start Voice Agent", start_voice),
        pystray.MenuItem("Start Bridge", start_bridge),
        pystray.MenuItem("Restart Ollama", lambda: (stop_ollama(), start_ollama())),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Stop All", lambda: (stop_python(), stop_ollama())),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", lambda: icon.stop()),
    )

icon = pystray.Icon("xtobe_ai", make_icon(), "XTOBE Ai Sentinel", create_menu())
icon.run()
