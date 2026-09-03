"""
Command router: parse natural language → dispatch to actions.
"""

import logging
import re
import subprocess
import ctypes
from pathlib import Path
from typing import Optional

from hulker.actions import Mouse, Keyboard, AppLauncher

log = logging.getLogger("hulker.route")


class CommandRouter:
    """
    Takes transcribed text and routes to the appropriate action.
    Supports: click, type, open, run, skill, code, build.
    """

    def __init__(self, cfg: dict, mouse: Mouse, keyboard: Keyboard, launcher: AppLauncher):
        self.cfg = cfg
        self.mouse = mouse
        self.keyboard = keyboard
        self.launcher = launcher
        self._skills_dir = Path(cfg.get("skills_dir", "skills"))

    @staticmethod
    def _get_screen_width() -> int:
        return ctypes.windll.user32.GetSystemMetrics(0)

    @staticmethod
    def _get_screen_height() -> int:
        return ctypes.windll.user32.GetSystemMetrics(1)

    def dispatch(self, text: str) -> str:
        """
        Parse text and execute the corresponding action.
        Returns a status string.
        """
        text = text.strip()

        # --- Click commands ---
        click_match = re.match(
            r"click\s+(?:at\s+)?(-?\d+)\s+(-?\d+)",
            text,
            re.IGNORECASE,
        )
        if click_match:
            x, y = int(click_match.group(1)), int(click_match.group(2))
            screen_w = self._get_screen_width()
            screen_h = self._get_screen_height()
            abs_x = int(x * 65535 / screen_w) if screen_w else 0
            abs_y = int(y * 65535 / screen_h) if screen_h else 0
            self.mouse.click(abs_x, abs_y)
            return f"Clicked at ({x}, {y})"

        # Click with screen position names
        pos_match = re.match(
            r"click\s+(left|right|center|top|bottom|top\s+left|top\s+right|bottom\s+left|bottom\s+right)",
            text,
            re.IGNORECASE,
        )
        if pos_match:
            pos = pos_match.group(1).lower()
            screen_w = self._get_screen_width()
            screen_h = self._get_screen_height()
            coords = {
                "left": (screen_w // 4, screen_h // 2),
                "right": (3 * screen_w // 4, screen_h // 2),
                "center": (screen_w // 2, screen_h // 2),
                "top": (screen_w // 2, screen_h // 4),
                "bottom": (screen_w // 2, 3 * screen_h // 4),
                "top left": (screen_w // 4, screen_h // 4),
                "top right": (3 * screen_w // 4, screen_h // 4),
                "bottom left": (screen_w // 4, 3 * screen_h // 4),
                "bottom right": (3 * screen_w // 4, 3 * screen_h // 4),
            }
            x, y = coords.get(pos, (screen_w // 2, screen_h // 2))
            abs_x = int(x * 65535 / screen_w) if screen_w else 0
            abs_y = int(y * 65535 / screen_h) if screen_h else 0
            self.mouse.click(abs_x, abs_y)
            return f"Clicked {pos} at ({x}, {y})"

        # --- Type command ---
        type_match = re.match(r"type\s+(.*)", text, re.IGNORECASE)
        if type_match:
            txt = type_match.group(1).strip()
            if txt.startswith('"') and txt.endswith('"'):
                txt = txt[1:-1]
            self.keyboard.type(txt)
            return f"Typed: {txt[:50]}"

        # --- Open / Launch command ---
        open_match = re.match(r"open\s+(.*)", text, re.IGNORECASE)
        if open_match:
            app = open_match.group(1).strip()
            if app.startswith('"') and app.endswith('"'):
                app = app[1:-1]
            if Path(app).exists():
                self.launcher.open(str(Path(app).resolve()))
                return f"Opened: {app}"
            else:
                result = self._try_launch_app(app)
                return f"Launched: {app}" if result else f"App not found: {app}"

        # --- Run command ---
        run_match = re.match(r"run\s+(.*)", text, re.IGNORECASE)
        if run_match:
            script = run_match.group(1).strip()
            if script.startswith('"') and script.endswith('"'):
                script = script[1:-1]
            path = Path(script)
            if path.exists():
                result = subprocess.run([str(path)], capture_output=True, text=True, timeout=30)
                out = result.stdout[:200] + result.stderr[:200]
                return f"Ran {script}: {out}"
            else:
                return f"Script not found: {script}"

        # --- Skill command ---
        skill_match = re.match(r"skill\s+(.*)", text, re.IGNORECASE)
        if skill_match:
            skill_name = skill_match.group(1).strip()
            return self._run_skill(skill_name)

        # --- Code command ---
        code_match = re.match(r"code\s+(.*)", text, re.IGNORECASE)
        if code_match:
            desc = code_match.group(1).strip()
            return self._generate_code(desc)

        # --- Build command ---
        build_match = re.match(r"build\s+(.*)", text, re.IGNORECASE)
        if build_match:
            desc = build_match.group(1).strip()
            return self._build_app(desc)

        # --- Stop / Exit ---
        if re.match(r"stop|exit|quit|shutdown", text, re.IGNORECASE):
            return "STOP"

        # --- Unknown ---
        return f"Unknown command: {text[:80]}"

    def _try_launch_app(self, name: str) -> bool:
        """Try to launch by common name."""
        app_map = {
            "chrome": "C:/Program Files/Google/Chrome/Application/chrome.exe",
            "edge": "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "terminal": "wt.exe",
            "powershell": "powershell.exe",
            "cmd": "cmd.exe",
            "visual studio code": "code.exe",
            "vscode": "code.exe",
        }
        path = app_map.get(name.lower())
        if path:
            return self.launcher.open(path)
        return self.launcher.open(name)

    def _run_skill(self, name: str) -> str:
        """Run a registered skill script."""
        skill_path = self._skills_dir / f"{name}.py"
        if skill_path.exists():
            result = subprocess.run(
                [str(skill_path)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            out = result.stdout[:300] + result.stderr[:200]
            return f"Skill '{name}': {out}"
        return f"Skill not found: {name}"

    def _generate_code(self, desc: str) -> str:
        """Placeholder for code generation. Connect an LLM API to enable this."""
        log.info("Code request: %s", desc)
        return f"Code generation for '{desc}' — connect an LLM API to enable this."

    def _build_app(self, desc: str) -> str:
        """Placeholder for app building. Connect a build pipeline to enable this."""
        log.info("Build request: %s", desc)
        return f"Build request for '{desc}' — connect a build pipeline to enable this."
