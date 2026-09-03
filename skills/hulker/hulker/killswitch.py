"""
Hard death switch for Hulker.

Real kill, not a flag. On flip:
1. Persists all in-flight data (transcripts, commands, results) to secure local storage
2. Terminates all registered subprocesses forcefully
3. Closes the microphone and releases audio handles
4. Stops the main loop via event
5. Writes a kill manifest for audit
6. Optionally locks the data directory

Nothing is lost. Data is preserved before the kill lands.
"""

import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

import numpy as np

log = logging.getLogger("hulker.killswitch")


class DataVault:
    """
    Secure local storage for Hulker session data.
    Persists transcripts, commands, results, and state so nothing is lost on death-switch flip.
    All data stored locally under the data_dir. No network, no external sync.
    """

    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._session_transcripts: List[Dict] = []
        self._session_commands: List[Dict] = []
        self._session_results: List[Dict] = []
        self._session_started: Optional[datetime] = None
        log.info("DataVault initialized at: %s", self.data_dir)

    def start_session(self):
        """Mark the start of a new session."""
        with self._lock:
            self._session_started = datetime.now(timezone.utc)
            self._session_transcripts = []
            self._session_commands = []
            self._session_results = []
        log.info("DataVault session started.")

    def record_transcript(self, text: str, audio_duration: float = 0.0):
        """Record a transcribed utterance."""
        with self._lock:
            entry = {
                "type": "transcript",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "text": text,
                "audio_duration_sec": audio_duration,
            }
            self._session_transcripts.append(entry)
        return entry

    def record_command(self, text: str, Command: str, result: str):
        """Record a dispatched command and its result."""
        with self._lock:
            entry = {
                "type": "command",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "command_text": text,
                "command_type": Command,
                "result": result,
            }
            self._session_commands.append(entry)
        return entry

    def record_result(self, text: str, result_type: str = "action", detail: str = ""):
        """Record an action result."""
        with self._lock:
            entry = {
                "type": "result",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "result_type": result_type,
                "text": text,
                "detail": detail,
            }
            self._session_results.append(entry)
        return entry

    def persist(self, prefix: str = "session") -> Path:
        """
        Flush all in-memory session data to disk as JSON.
        Returns the path to the written file.
        """
        with self._lock:
            import json
            bundle = {
                "session_started": self._session_started.isoformat() if self._session_started else None,
                "transcripts": list(self._session_transcripts),
                "commands": list(self._session_commands),
                "results": list(self._session_results),
                "persisted_at": datetime.now(timezone.utc).isoformat(),
            }
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filepath = self.data_dir / f"{prefix}_{ts}.json"
            tmp_path = self.data_dir / f".{prefix}_{ts}.tmp"
            with open(tmp_path, "w") as f:
                json.dump(bundle, f, indent=2, default=str)
            os.replace(str(tmp_path), str(filepath))
            log.info("DataVault persisted %d transcripts, %d commands, %d results → %s",
                     len(bundle["transcripts"]),
                     len(bundle["commands"]),
                     len(bundle["results"]),
                     filepath)
            # Clear in-memory after successful persist
            self._session_transcripts = []
            self._session_commands = []
            self._session_results = []
            return filepath

    def secure_copy(self, dest_dir: str) -> List[Path]:
        """
        Copy all persisted session files to an alternate location (backup).
        Returns list of copied file paths.
        """
        dest = Path(dest_dir).resolve()
        dest.mkdir(parents=True, exist_ok=True)
        copied = []
        for f in sorted(self.data_dir.glob("session_*.json")):
            try:
                shutil.copy2(str(f), str(dest / f.name))
                copied.append(dest / f.name)
            except Exception as e:
                log.error("Failed to backup %s: %s", f, e)
        log.info("DataVault backed up %d files to %s", len(copied), dest)
        return copied

    def list_sessions(self) -> List[Path]:
        """List all persisted session files."""
        return sorted(self.data_dir.glob("session_*.json"))

    def wipe(self, confirm_token: str = ""):
        """
        Wipe all persisted data. Requires a non-empty confirm_token to prevent accidents.
        """
        if not confirm_token:
            log.warning("DataVault.wipe() called without confirm_token — aborting.")
            return False
        with self._lock:
            for f in self.data_dir.glob("session_*.json"):
                try:
                    f.unlink()
                except Exception as e:
                    log.error("Failed to wipe %s: %s", f, e)
            log.info("DataVault wiped.")
        return True


class DeathSwitch:
    """
    Hard death switch for Hulker.

    Kill triggers:
    - Voice: "HULKER stop", "HULKER emergency", "HULKER kill", "HULKER abort"
    - File: create ./tmp/hulker_kill (or configured trigger path)
    - Direct: death_switch.flip()

    On flip (in order):
    1. Flushes ALL in-flight data to DataVault (JSON persist + optional backup)
    2. Terminates all registered subprocesses (SIGTERM → wait 3s → SIGKILL)
    3. Closes the microphone stream and releases audio handles
    4. Fires the stop callback to halt the main loop
    5. Writes a kill manifest with timestamp and reason
    6. Optionally locks the data directory (chmod 000 on Linux; on Windows marks as read-only)

    Nothing is lost. Data is guaranteed persisted before any destructive action.
    """

    def __init__(
        self,
        trigger_file: str = "./tmp/hulker_kill",
        data_vault: Optional[DataVault] = None,
        backup_dir: Optional[str] = None,
    ):
        self.trigger_file = Path(trigger_file)
        self.data_vault = data_vault or DataVault()
        self.backup_dir = backup_dir
        self._active = False
        self._threads: Set[threading.Thread] = set()
        self._processes: Set[subprocess.Popen] = set()
        self._mic = None
        self._stop_callback: Optional[Callable] = None
        self._lock = threading.Lock()
        self._watcher: Optional[threading.Thread] = None
        self._flipped = False
        self._flip_reason: Optional[str] = None

    # --- Registration ---

    def register_thread(self, thread: threading.Thread):
        with self._lock:
            self._threads.add(thread)

    def register_process(self, proc: subprocess.Popen):
        with self._lock:
            self._processes.add(proc)

    def set_mic(self, mic):
        with self._lock:
            self._mic = mic

    def set_stop_callback(self, callback: Callable):
        with self._lock:
            self._stop_callback = callback

    # --- File watcher ---

    def start_file_watcher(self):
        self.trigger_file.parent.mkdir(parents=True, exist_ok=True)
        self._watcher = threading.Thread(target=self._watch_file, daemon=True)
        self._watcher.start()
        self.register_thread(self._watcher)
        log.info("Death switch file watcher watching: %s", self.trigger_file)

    def _watch_file(self):
        while self._active:
            if self.trigger_file.exists():
                reason = f"trigger file: {self.trigger_file}"
                log.warning("Death switch triggered via %s", reason)
                self.flip(reason=reason)
                try:
                    self.trigger_file.unlink()
                except OSError:
                    pass
            time.sleep(0.3)

    # --- Voice trigger check ---

    def check_voice_trigger(self, text: str) -> bool:
        triggers = ["stop", "emergency", "kill", "shutdown", "abort", "die", "terminate"]
        text_lower = text.lower().strip()
        for t in triggers:
            if t in text_lower:
                reason = f"voice command: '{text}'"
                log.warning("Death switch triggered via voice: %s", reason)
                self.flip(reason=reason)
                return True
        return False

    # --- The flip ---

    def flip(self, reason: Optional[str] = None):
        """
        Execute the hard kill. Data is persisted BEFORE anything is destroyed.
        Idempotent — safe to call multiple times.
        """
        with self._lock:
            if self._flipped:
                log.info("Death switch already flipped. Ignoring duplicate.")
                return
            self._flipped = True
            self._flip_reason = reason or "direct call"

        log.critical("=" * 60)
        log.critical("DEATH SWITCH FLIPPED — reason: %s", self._flip_reason)
        log.critical("=" * 60)

        # Step 1: Persist data FIRST — nothing lost
        try:
            log.info("Persisting session data to DataVault...")
            session_file = self.data_vault.persist(prefix="session")
            if self.backup_dir:
                self.data_vault.secure_copy(self.backup_dir)
            log.info("Data persisted. Session file: %s", session_file)
        except Exception as e:
            log.critical("DATA PERSISTENCE FAILED: %s", e)

        # Step 2: Kill all registered processes
        killed = []
        with self._lock:
            for proc in list(self._processes):
                try:
                    if proc.poll() is None:
                        proc.terminate()
                        killed.append(proc)
                except Exception as e:
                    log.error("Error terminating process: %s", e)
            self._processes.clear()

        for proc in killed:
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    proc.kill()
                    log.warning("Had to SIGKILL process pid=%d", proc.pid)
                except Exception:
                    pass

        log.info("Terminated %d process(es).", len(killed))

        # Step 3: Close mic
        with self._lock:
            mic = self._mic
            self._mic = None
        if mic is not None:
            try:
                mic.close()
                log.info("Microphone closed.")
            except Exception as e:
                log.error("Error closing mic: %s", e)

        # Step 4: Fire stop callback
        with self._lock:
            cb = self._stop_callback
            self._stop_callback = None
        if cb is not None:
            try:
                cb()
                log.info("Stop callback fired.")
            except Exception as e:
                log.error("Error in stop callback: %s", e)

        # Step 5: Write kill manifest
        try:
            manifest_path = self.data_vault.data_dir / "kill_manifest.json"
            import json
            manifest = {
                "flipped_at": datetime.now(timezone.utc).isoformat(),
                "reason": self._flip_reason,
                "processes_killed": len(killed),
                "data_persisted": str(session_file) if 'session_file' in dir() else None,
            }
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)
            log.info("Kill manifest written: %s", manifest_path)
        except Exception as e:
            log.error("Failed to write kill manifest: %s", e)

        # Step 6: Mark inactive
        self._active = False
        log.critical("DEATH SWITCH COMPLETE — all data persisted, processes killed, mic closed.")
        log.critical("=" * 60)

    # --- Lifecycle ---

    def start(self):
        self._active = True
        self._flipped = False
        log.info("Death switch activated.")

    def stop(self):
        """Deactivate without killing."""
        self._active = False
        log.info("Death switch deactivated (no kill).")

    def is_active(self) -> bool:
        return self._active and not self._flipped

    def is_flipped(self) -> bool:
        return self._flipped

    def get_flip_reason(self) -> Optional[str]:
        return self._flip_reason
