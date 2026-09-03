"""
Text-to-speech using edge-tts.
"""

import asyncio
import logging
import subprocess
from typing import Optional

import edge_tts

log = logging.getLogger("hulker.tts")


class TTSEngine:
    """Voice synthesis engine."""

    def __init__(self, engine: str = "edge", voice: str = "en-US-JennyNeural",
                 rate: str = "+0%", volume: str = "+0%"):
        self.engine = engine
        self.voice = voice
        self.rate = rate
        self.volume = volume

    async def _edge_speak(self, text: str) -> bool:
        """Speak using edge-tts (async, saves to file then plays)."""
        try:
            communicate = edge_tts.Communicate(
                text,
                self.voice,
                rate=self.rate,
                volume=self.volume,
            )
            await communicate.save("./tmp/hulker_response.mp3")
            # Play via PowerShell
            subprocess.run(
                [
                    "powershell", "-c",
                    "$a = New-Object Media.SoundPlayer './tmp/hulker_response.mp3'; $a.PlaySync()",
                ],
                capture_output=True,
                timeout=30,
            )
            return True
        except Exception as e:
            log.error("edge-tts speak failed: %s", e)
            return False

    async def _sapi_speak(self, text: str) -> bool:
        """Speak using Windows SAPI (system voice)."""
        try:
            import win32com.client
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            speaker.Speak(text)
            return True
        except Exception as e:
            log.error("SAPI TTS failed: %s", e)
            return False

    async def speak(self, text: str) -> bool:
        """Speak text using the configured engine."""
        if self.engine == "edge":
            return await self._edge_speak(text)
        elif self.engine == "sapi":
            return await self._sapi_speak(text)
        else:
            log.error("Unknown TTS engine: %s", self.engine)
            return False


# Module-level singleton
_engine: Optional[TTSEngine] = None


def init_tts(cfg: dict) -> TTSEngine:
    """Initialize TTS engine from config dict."""
    global _engine
    tts_cfg = cfg.get("tts", {})
    _engine = TTSEngine(
        engine=tts_cfg.get("engine", "edge"),
        voice=tts_cfg.get("voice", "en-US-JennyNeural"),
        rate=tts_cfg.get("rate", "+0%"),
        volume=tts_cfg.get("volume", "+0%"),
    )
    return _engine


async def speak(text: str) -> bool:
    """Speak text using the initialized TTS engine (async)."""
    global _engine
    if _engine is None:
        log.warning("TTS not initialized; cannot speak: %s", text)
        return False
    return await _engine.speak(text)


def speak_sync(text: str) -> bool:
    """Synchronous wrapper — use from non-async contexts."""
    try:
        return asyncio.run(speak(text))
    except RuntimeError:
        # Event loop already running — use create_task
        loop = asyncio.get_event_loop()
        task = loop.create_task(speak(text))
        return True  # Fire and forget
