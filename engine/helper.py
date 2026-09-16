import os
import re
import shutil
import subprocess
import time
import markdown2
from bs4 import BeautifulSoup

# --- ADB E2E helpers (fixed 2026-09-16) ---
# All adb automation funnels through _adb() so we get:
#  single device selection via ANDROID_SERIAL/DEVICE_SERIAL, clear errors
#  instead of silent os.system failures, and safe text escaping.

ADB_HOST_SERIAL = os.environ.get("ANDROID_SERIAL") or os.environ.get("DEVICE_SERIAL") or ""


def _adb_base():
    exe = shutil.which("adb") or "adb"
    if ADB_HOST_SERIAL:
        return [exe, "-s", ADB_HOST_SERIAL]
    return [exe]


def _run_adb(*args, timeout=15):
    cmd = _adb_base() + list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except FileNotFoundError:
        return 127, "adb not found in PATH (winget install Google.PlatformTools)"
    except subprocess.TimeoutExpired:
        return 124, "adb timed out: " + " ".join(cmd)


def ensure_device(timeout=10):
    """True if at least one authorized device is visible to adb."""
    code, out = _run_adb("devices", timeout=timeout)
    if code != 0:
        return False
    for line in out.splitlines()[1:]:
        line = line.strip()
        if not line or line.startswith("*") or line.startswith("List"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            return True
    return False


def _escape_adb_text(s):
    # adb 'input text' needs %s for spaces and backslash-escaping for shell specials.
    # Order matters: backslash first, spaces last (else we double-escape).
    s = str(s).replace("\\", "\\\\")
    for ch in ["'", '"', "(", ")", "&", "|", "<", ">", ";", "$", "`", "!", "#", "*", "?", "~"]:
        s = s.replace(ch, "\\" + ch)
    return s.replace(" ", "%s")

def extract_yt_term(command):
    # Define a regular expression pattern to capture the song name
    pattern = r'play\s+(.*?)\s+on\s+youtube'
    # Use re.search to find the match in the command
    match = re.search(pattern, command, re.IGNORECASE)
    # If a match is found, return the extracted song name; otherwise, return None
    return match.group(1) if match else None


def remove_words(input_string, words_to_remove):
    # Split the input string into words
    words = input_string.split()

    # Remove unwanted words
    filtered_words = [word for word in words if word.lower() not in words_to_remove]

    # Join the remaining words back into a string
    result_string = ' '.join(filtered_words)

    return result_string



# key events like receive call, stop call, go back
def keyEvent(key_code):
    if not ensure_device():
        print("[adb] No authorized device detected. Phone path removed; skipping keyevent.")
        return False
    code, out = _run_adb("shell", "input", "keyevent", str(int(key_code)))
    time.sleep(1)
    if code != 0:
        print(f"[adb] keyevent failed: {out.strip()}")
        return False
    return True

# Tap event used to tap anywhere on screen
def tapEvents(x, y):
    if not ensure_device():
        print("[adb] No authorized device detected. Phone path removed; skipping tap.")
        return False
    code, out = _run_adb("shell", "input", "tap", str(int(x)), str(int(y)))
    time.sleep(1)
    if code != 0:
        print(f"[adb] tap failed: {out.strip()}")
        return False
    return True

# Input Event is used to insert text in mobile
def adbInput(message):
    if not ensure_device():
        print("[adb] No authorized device detected. Phone path removed; skipping input.")
        return False
    safe = _escape_adb_text(message)
    code, out = _run_adb("shell", "input", "text", safe)
    time.sleep(1)
    if code != 0:
        print(f"[adb] input failed: {out.strip()}")
        return False
    return True

# to go complete back
def goback(key_code):
    for i in range(6):
        keyEvent(key_code)

# To replace space in string with %s for complete message send
def replace_spaces_with_percent_s(input_string):
    return input_string.replace(' ', '%s')

def markdown_to_text(md):
    html = markdown2.markdown(md)
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text().strip()