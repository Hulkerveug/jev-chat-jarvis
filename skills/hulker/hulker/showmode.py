"""
Show mode for Hulker.

When enabled:
- Hulker appears deactivated / offline to any observer
- Heartbeat file shows a stale timestamp
- Log output can be suppressed
- BUT: data vault keeps recording every transcript, command, and result live
- Voice commands can still be processed silently (no TTS response)

This is for when you need Hulker to look off but keep storing.
"""

import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("hulker.showmode")


class ShowMode:
    """
    Makes Hulker appear deactivated while it continues recording live.

    - Writes a stale-looking heartbeat file
    - Suppresses TTS voice output (looks dead)
    - Data vault records everything regardless
    """

    def __init__(self, enabled: bool = False, heartbeat_file: str = "./tmp/hulker_heartbeat"):
        self.enabled = enabled
        self.heartbeat_file = Path(heartbeat_file)
        self._last_beat: datetime = None
        self._beat_interval = 300  # 5 min — looks stale to an observer
        self._silent_mode = False  # no voice output
        self._suppress_logs = False

    def activate(self):
        self.enabled = True
        self._last_beat = datetime.now(timezone.utc)
        self._write_heartbeat()
        log.info("Show mode ON — Hulker appears deactivated, recording live.")

    def deactivate(self):
        self.enabled = False
        self._clear_heartbeat()
        log.info("Show mode OFF — Hulker visible again.")

    def _write_heartbeat(self):
        self.heartbeat_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.heartbeat_file, "w") as f:
            # Write a timestamp that looks stale (slightly old)
            stale = self._last_beat - __import__("datetime").timedelta(seconds=30)
            f.write(stale.isoformat())

    def _clear_heartbeat(self):
        try:
            self.heartbeat_file.unlink()
        except OSError:
            pass

    def beat(self):
        """Update heartbeat with a stale-looking timestamp."""
        if not self.enabled:
            return
        self._last_beat = datetime.now(timezone.utc)
        self._write_heartbeat()

    def is_visible(self) -> bool:
        return not self.enabled

    def should_suppress_output(self) -> bool:
        return self.enabled and (self._silent_mode or self._suppress_logs)

    def set_silent(self, silent: bool):
        self._silent_mode = silent

    def set_suppress_logs(self, suppress: bool):
        self._suppress_logs = suppress
