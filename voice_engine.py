#!/usr/bin/env python3
"""
XTOBE Ai Voice Engine - STT + TTS for Xtobe Agent
Uses faster-whisper for speech recognition, edge-tts for Tamil/English synthesis
"""

import asyncio
import io
import os
import tempfile
import wave
from pathlib import Path

import edge_tts
import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel

# === CONFIG ===
WHISPER_MODEL = "base"  # tiny/base/small - base is good balance
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_DURATION = 0.5  # seconds per chunk
SILENCE_THRESHOLD = 0.01
SILENCE_DURATION = 1.5  # seconds of silence to stop recording

# Tamil/English voices available in edge-tts
VOICES = {
    "tamil": "ta-IN-ValluvarNeural",      # Male Tamil voice
    "english": "en-IN-NeerjaNeural",       # Female Indian English
    "english_male": "en-US-ChristopherNeural",
    "tamil_female": "ta-IN-PallaviNeural",
}


class VoiceEngine:
    def __init__(self, model_size=WHISPER_MODEL):
        print(f"[VOICE] Loading Whisper model: {model_size}...")
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        print("[VOICE] Whisper model loaded ✓")
        self.is_speaking = False

    def record_audio(self, duration=None):
        """Record audio from microphone. If duration is None, record until silence."""
        print("[VOICE] Recording...")
        recorded_frames = []
        silence_counter = 0
        is_speaking = False
        max_duration = 30  # max 30 seconds

        def callback(indata, frames, time_info, status):
            nonlocal silence_counter, is_speaking
            volume = np.linalg.norm(indata) / np.sqrt(len(indata))

            if volume > SILENCE_THRESHOLD:
                is_speaking = True
                silence_counter = 0
            elif is_speaking:
                silence_counter += frames / SAMPLE_RATE

            recorded_frames.append(indata.copy())

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=np.float32,
            blocksize=int(SAMPLE_RATE * CHUNK_DURATION),
            callback=callback
        ):
            if duration:
                sd.sleep(int(duration * 1000))
            else:
                # Record until silence or max duration
                total_silence = 0
                while True:
                    sd.sleep(100)
                    if is_speaking and silence_counter >= SILENCE_DURATION:
                        break
                    if len(recorded_frames) * CHUNK_DURATION >= max_duration:
                        break

        if not recorded_frames:
            return None

        audio = np.concatenate(recorded_frames, axis=0)
        return audio.flatten()

    def transcribe(self, audio_np):
        """Transcribe audio numpy array to text using Whisper."""
        if audio_np is None or len(audio_np) == 0:
            return ""

        # Convert to int16 for whisper
        audio_int16 = (audio_np * 32767).astype(np.int16)

        # Save to temp wav file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            with wave.open(f, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(audio_int16.tobytes())

        try:
            segments, info = self.model.transcribe(
                temp_path,
                language=None,  # auto-detect
                vad_filter=True,
                beam_size=5
            )

            text = " ".join([seg.text for seg in segments]).strip()
            print(f"[VOICE] Transcribed: '{text}' (lang: {info.language}, prob: {info.language_probability:.2f})")
            return text
        finally:
            os.unlink(temp_path)

    def listen(self):
        """Record and transcribe in one step."""
        audio = self.record_audio()
        return self.transcribe(audio)

    async def _speak_async(self, text, voice="english", rate="+10%"):
        """Async TTS using edge-tts."""
        if not text or self.is_speaking:
            return

        self.is_speaking = True
        communicate = edge_tts.Communicate(text, voice, rate=rate)

        # Collect audio data
        audio_chunks = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])

        if not audio_chunks:
            self.is_speaking = False
            return

        # Combine and play
        audio_data = b"".join(audio_chunks)

        # Convert MP3 to raw audio using pydub-like approach
        # edge-ts outputs MP3, we need to decode it
        try:
            import subprocess
            # Use ffmpeg or similar to convert mp3 to wav
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as mp3_f:
                mp3_f.write(audio_data)
                mp3_path = mp3_f.name

            wav_path = mp3_path.replace(".mp3", ".wav")
            subprocess.run(
                ["ffmpeg", "-y", "-i", mp3_path, "-ar", str(SAMPLE_RATE),
                 "-ac", str(CHANNELS), "-f", "wav", wav_path],
                capture_output=True, timeout=10
            )

            # Read wav and play
            with wave.open(wav_path, 'rb') as wf:
                audio_frames = wf.readframes(wf.getnframes())
                audio_np = np.frombuffer(audio_frames, dtype=np.int16).astype(np.float32) / 32768.0

                sd.play(audio_np, wf.getframerate())
                sd.wait()

            os.unlink(mp3_path)
            os.unlink(wav_path)
        except Exception as e:
            print(f"[VOICE] TTS playback error: {e}")
            # Fallback: try direct playback
            try:
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    f.write(audio_data)
                    f.flush()
                    os.system(f'start "" "{f.name}"')
            except:
                pass

        self.is_speaking = False

    def speak(self, text, voice="english", rate="+10%"):
        """Synchronous wrapper for TTS."""
        asyncio.run(self._speak_async(text, voice, rate))

    def speak_tamil(self, text, rate="+10%"):
        """Speak in Tamil."""
        self.speak(text, voice=VOICES["tamil"], rate=rate)

    def speak_english(self, text, rate="+10%"):
        """Speak in English."""
        self.speak(text, voice=VOICES["english"], rate=rate)


if __name__ == "__main__":
    engine = VoiceEngine()
    print("[VOICE] Say something... (5 seconds)")
    text = engine.listen()
    print(f"You said: {text}")
    engine.speak("Hello, I am Xtobe Ai. How can I help you?")
