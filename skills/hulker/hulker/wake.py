"""
Wake word detection using audio energy + keyword spotting.
"""

import logging
import re
from typing import Optional

import numpy as np

log = logging.getLogger("hulker.wake")


class WakeWordDetector:
    """
    Detects wake word from audio stream.
    Uses energy-based speech detection as a pre-filter;
    actual wake word matching is done at the utterance level
    via keyword spotting on transcribed text.
    """

    def __init__(self, wake_word: str = "HULKER", sensitivity: float = 0.5):
        self.wake_word = wake_word.upper()
        self.sensitivity = sensitivity
        self._energy_threshold = 0.02 * (1.0 - sensitivity * 0.5)
        self._pattern = re.compile(
            r"\b" + re.escape(wake_word.lower()) + r"\b",
            re.IGNORECASE,
        )

    def process(self, audio: np.ndarray) -> bool:
        """
        Process an audio chunk. Returns True if audio energy suggests
        speech may be present (pre-filter for wake word detection).
        """
        energy = np.sqrt(np.mean(audio ** 2))
        return energy > self._energy_threshold

    def match(self, text: str) -> bool:
        """Check if transcribed text contains the wake word."""
        return bool(self._pattern.search(text.lower()))

    def extract_command(self, text: str) -> Optional[str]:
        """
        If wake word present, return the text after it (the actual command).
        Otherwise return None.
        """
        if self.match(text):
            cleaned = re.sub(
                r"\b" + re.escape(self.wake_word.lower()) + r"\b\s*",
                "",
                text.lower(),
                flags=re.IGNORECASE,
            ).strip()
            return cleaned if cleaned else None
        return None
