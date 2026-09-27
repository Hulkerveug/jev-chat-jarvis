#!/usr/bin/env python3
"""Xtobe AI full-stack launcher + E2E (Windows, local-only install).
Starts on this PC (loopback): Agent Bridge :8767, Voice Agent :8765,
Xtobe Sami :8742, Local Dashboard :8080, Expo web export served :19008.
Then runs: bridge status/chat, dashboard stats, web bundle checks.
Usage:
  py fullstack.py --serve-only     (skip bridge chat model call)
  py fullstack.py --skip-web       (no expo export rebuild)
  py fullstack.py --web-port 19008 --bridge-port 8767 ...
"""
import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

XTOBE_ROOT = Path(r"C:\Users\Nishan\Documents\jarvis-repo")
EXPO = Path(r"C:\Users\Nishan\xtobe-ai")
DASH = Path(r"C:\Users\Nishan\projects\local-dashboard")
DIST = EXPO / "dist"

PROCS = []


def log(msg):
    print(f"[fullstack] {msg}", flush=True)


def port_in_use(port):
    """Windows-reliable probe: try to CONNECT to the port.
    Bind-probes fail here because http.server sets SO_REUSEADDR, which lets a
    second socket bind the same port even while one is LISTENING. A connect()
    succeeds against any live listener and is refused when the port is free."""
    s = socket.socket()
    s.settimeout(1.0)
    try:
        s.connect(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def wait_http(url, timeout=60, label=""):
    t0 = time.time()
    last = ""
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                body = r.read()
                log(f"{label or url} UP ({r.status}, {len(body)}B)")
                return body
        except Exception as e:
            last = str(e)
        time.sleep(2)
    log(f"{label or url} TIMEOUT: {last}")
    return None


def start_bg(cmd, cwd, label, port=None, env=None):
    if port and port_in_use(port):
        log(f"{label} :{port} already in use - reusing existing server.")
        return None
    log(f"start {label}: {' '.join(cmd)} (cwd={cwd})")
    run_env = dict(os.environ)
    if env:
        run_env.update(env)
    p = subprocess.Popen(cmd, cwd=str(cwd), env=run_env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    PROCS.append((label, p))
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve-only", action="store_true")
    ap.add_argument("--skip-web", action="store_true")
    ap.add_argument("--web-port", type=int, default=19008)
    ap.add_argument("--bridge-port", type=int, default=8767)
    ap.add_argument("--host", default="127.0.0.1",
                    help="Bind host for backends (default 127.0.0.1 - this PC only).")
    a = ap.parse_args()

    py = sys.executable or "py"
    fails = []

    def check(name, ok, detail=""):
        print(f"{'PASS' if ok else 'FAIL'} {name}{(' - ' + detail) if detail and not ok else ''}")
        if not ok:
            fails.append(name)

    # --- backends ---
    # XTOBE_HOST is read by agent_bridge.py / voice_agent_server.py.
    bind_env = {"XTOBE_HOST": a.host}
    start_bg([py, "agent_bridge.py"], XTOBE, "bridge", port=a.bridge_port, env=bind_env)
    start_bg([py, "samimode_server.py"], EXPO, "xtobe-sami", port=8742)
    start_bg([py, "-m", "uvicorn", "server:app", "--host", a.host, "--port", "8080"],
             DASH, "dashboard", port=8080)
    # Voice agent needs the PortAudio/whisper stack; start it, fall back to import-check.
    start_bg([py, "voice_agent_server.py"], XTOBE, "voice", port=8765, env=bind_env)

    bridge_ok = wait_http(f"http://127.0.0.1:{a.bridge_port}/api/status", 60, "bridge") is not None
    check("bridge-status", bridge_ok)
    sami_ok = wait_http("http://127.0.0.1:8742/api/status", 30, "xtobe-sami") is not None
    check("xtobe-sami-status", sami_ok)
    dash_ok = wait_http("http://127.0.0.1:8080/api/stats", 60, "dashboard") is not None
    check("dashboard-stats", dash_ok)

    voice_ok = wait_http("http://127.0.0.1:8765/api/status", 90, "voice") is not None
    check("voice-status", voice_ok)
    if not voice_ok:
        c = subprocess.run([py, "-c", "import voice_agent_server"],
                           cwd=str(XTOBE), capture_output=True, text=True, timeout=120)
        check("voice-import", c.returncode == 0, (c.stderr or "")[-300:])

    if bridge_ok and not a.serve_only:
        try:
            payload = json.dumps({"text": "say OK", "agent": "xtobe_ai"}).encode()
            req = urllib.request.Request(
                f"http://127.0.0.1:{a.bridge_port}/api/chat", data=payload,
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.loads(r.read().decode())
            # agent_bridge returns the literal "No response" (no model content) or
            # "Error: ..." on failure - treat those as FAIL, not a healthy reply.
            reply = str(data.get("response") or "")
            ok = bool(reply.strip()) and reply.strip() != "No response" \
                and not reply.strip().startswith("Error:")
            check("bridge-chat", ok, (str(data)[:200] if not ok else ""))
        except Exception as e:
            check("bridge-chat", False, str(e)[:300])
    else:
        print("SKIP bridge-chat (--serve-only or bridge down)")

    # --- expo web ---
    if not a.skip_web:
        log(f"expo export --platform web ...")
        npx = shutil.which("npx.cmd") or shutil.which("npx") or "npx"
        r = subprocess.run([npx, "expo", "export", "--platform", "web"],
                           cwd=str(EXPO), capture_output=True, text=True, timeout=600)
        tail = ((r.stdout or "") + (r.stderr or ""))[-800:]
        check("expo-export", r.returncode == 0 and (DIST / "index.html").exists(), tail)
    else:
        check("expo-export", (DIST / "index.html").exists(), "dist/index.html missing + --skip-web")

    # Serve from project root (cwd=EXPO): serving with cwd=dist locks the folder
    # on Windows and makes the next `expo export` fail with EBUSY: rmdir dist.
    # --bind 127.0.0.1: local-only install (http.server defaults to 0.0.0.0).
    start_bg([py, "-m", "http.server", str(a.web_port), "--bind", "127.0.0.1",
              "--directory", str(DIST)],
             EXPO, "web", port=a.web_port)
    idx = wait_http(f"http://127.0.0.1:{a.web_port}/", 30, "web-index")
    check("web-index", idx is not None and b"xtobe-ai" in idx)
    js = sorted(DIST.glob("_expo/static/js/web/*.js")) if DIST.exists() else []
    if js:
        name = js[0].name
        bundle = wait_http(f"http://127.0.0.1:{a.web_port}/_expo/static/js/web/{name}", 30, "web-bundle")
        check("web-bundle", bundle is not None and b"Xtobe" in bundle, name)
    else:
        check("web-bundle", False, "no bundle in dist/_expo/static/js/web/")

    print("XTOBE FULLSTACK %s" % ("PASS" if not fails else ("FAIL: " + ",".join(fails))))


if __name__ == "__main__":
    sys.exit(main())
