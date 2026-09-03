"""
Microphone stream with silence detection.
Yields audio chunks; detects when speech starts/stops.
"""

import logging
import threading
import time
from typing import List, Optional

import numpy as np
import sounddevice as sd

log = logging.getLogger("hulker.mic")


class MicStream:
    """
    Manages microphone input. Provides audio chunks and silence tracking.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
        silence_threshold: float = 0.01,
        silence_duration: float = 1.0,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration

        self._stream: Optional[sd.InputStream] = None
        self._audio_queue: List[np.ndarray] = []
        self._queue_lock = threading.Lock()
        self._speech_active = False
        self._silence_start: Optional[float] = None
        self._closed = False

    def is_speech(self, audio: np.ndarray) -> bool:
        """Check if audio chunk contains speech (above threshold)."""
        energy = np.sqrt(np.mean(audio ** 2))
        return energy > self.silence_threshold

    def process_chunk(self, audio: np.ndarray) -> bool:
        """
        Process an incoming audio chunk.
        Returns True if speech is currently active.
        """
        speech = self.is_speech(audio)
        now = time.time()

        if speech:
            self._silence_start = None
            self._speech_active = True
        elif self._speech_active:
            if self._silence_start is None:
                self._silence_start = now
            elif now - self._silence_start > self.silence_duration:
                self._speech_active = False
                self._silence_start = None

        # Store in queue if speech active
        if self._speech_active:
            with self._queue_lock:
                self._audio_queue.append(audio.copy())

        return self._speech_active

    def get_audio(self) -> List[np.ndarray]:
        """Get all accumulated audio chunks and clear queue."""
        with self._queue_lock:
            chunks = self._audio_queue[:]
            self._audio_queue.clear()
        return chunks

    def clear(self):
        """Clear the audio queue."""
        with self._queue_lock:
            self._audio_queue.clear()

    def start(self):
        """Open the microphone stream."""
        if self._closed:
            raise RuntimeError("MicStream already closed")
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            blocksize=self.chunk_size,
            dtype="float32",
        )
        self._stream.start()
        log.info("Microphone started: %d Hz, %d ch, %d buffer",
                 self.sample_rate, self.channels, self.chunk_size)

    def read(self) -> Optional[np.ndarray]:
        """Read a single chunk from the stream. Non-blocking via callback pattern."""
        # This is meant to be used with callback; direct read not implemented
        raise NotImplementedError("Use callback-based streaming instead")

    def close(self):
        """Close the microphone stream."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._closed = True
        log.info("Microphone closed.")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.close()
