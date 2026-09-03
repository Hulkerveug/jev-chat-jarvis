"""
Speech-to-text using faster-whisper.
"""

import logging
from typing import Optional

import numpy as np
from faster_whisper import WhisperModel

log = logging.getLogger("hulker.stt")


def transcribe(
    model: WhisperModel,
    audio: np.ndarray,
    language: str = "en",
    beam_size: int = 5,
) -> Optional[str]:
    """
    Transcribe audio to text using the Whisper model.
    Returns the transcribed text, or None if no speech detected.
    """
    try:
        segments, info = model.transcribe(
            audio,
            language=language,
            beam_size=beam_size,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        log.debug("Transcription info: duration=%.2fs, language='%s', samples=%d",
                  info.duration, info.language, info.num_samples)
        return text if text else None
    except Exception as e:
        log.error("Transcription failed: %s", e)
        return None


def detect_language(model: WhisperModel, audio: np.ndarray) -> str:
    """Detect the language of the audio."""
    _, info = model.transcribe(audio, vad_filter=False)
    return info.language
