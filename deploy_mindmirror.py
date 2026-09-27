#!/usr/bin/env python3
"""Publish MindMirror to Netlify via their CLI"""
import subprocess, os, sys
from pathlib import Path

MINDMIRROR = Path.home() / "XTOBE/projects/mindmirror"
DEST = Path.home() / "XTOBE/netlify_deploy"
DEST.mkdir(exist_ok=True)

# Copy mindmirror to deploy folder
import shutil
if (DEST / "index.html").exists():
    (DEST / "index.html").unlink()
shutil.copy2(MINDMIRROR / "index.html", DEST / "index.html")

print(f"[NETLIFY] Deploy folder: {DEST}")
print("To get your live global URL:")
print("1. Open Opera GX → https://app.netlify.com/drop")
print("2. Drag this folder:", str(DEST))
print("3. Done — you get mindmirror-xtobe.netlify.app LIVE GLOBAL")

# Alternative: use Netlify CLI if available
try:
    subprocess.run(["netlify", "deploy", "--dir", str(DEST), "--prod"], 
                   check=True, capture_output=True)
    print("[NETLIFY] Deployed via CLI!")
except Exception as e:
    print(f"[NETLIFY] CLI deploy failed: {e}")
    print("Use the browser method above.")
