#!/usr/bin/env python3
"""XTOBE Ai Voice Agent — WebSocket + REST, real-time STT/TTS, Ollama AI"""
import asyncio
import json
import os
import tempfile
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd
from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from faster_whisper import WhisperModel
import edge_tts

app = Flask(__name__, static_folder=str(Path(__file__).parent / "static"), static_url_path="/static")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

WHISPER_MODEL = "base"
SAMPLE_RATE = 16000
CHANNELS = 1
SILENCE_THRESHOLD = 0.01
SILENCE_DURATION = 1.5
MAX_DURATION = 30
VOICE_PORT = 8765
# XTOBE Host=0.0.0.0 lets the xtobe-ai phone app reach the voice agent over LAN.
VOICE_HOST = os.environ.get("XTOBE_HOST", "127.0.0.1")

VOICES = {
    "tamil_male": "ta-IN-ValluvarNeural",
    "tamil_female": "ta-IN-PallaviNeural",
    "english_female": "en-IN-NeerjaNeural",
    "english_male": "en-US-ChristopherNeural",
}

print("[XTOBE] Loading Whisper model...")
whisper = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
print("[XTOBE] Whisper loaded OK")


def record_audio():
    frames = []
    silence_counter = 0
    is_speaking = False

    def callback(indata, frames_list, time_info, status):
        nonlocal silence_counter, is_speaking
        volume = np.linalg.norm(indata) / np.sqrt(len(indata))
        if volume > SILENCE_THRESHOLD:
            is_speaking = True
            silence_counter = 0
        elif is_speaking:
            silence_counter += len(indata) / SAMPLE_RATE
        frames.append(indata.copy())

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=np.float32, callback=callback):
        total = 0
        while True:
            sd.sleep(100)
            total += 0.1
            if is_speaking and silence_counter >= SILENCE_DURATION:
                break
            if total >= MAX_DURATION:
                break

    if not frames:
        return None
    return np.concatenate(frames, axis=0).flatten()


def transcribe(audio_np):
    if audio_np is None or len(audio_np) == 0:
        return ""
    audio_int16 = (audio_np * 32767).astype(np.int16)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        temp_path = f.name
        with wave.open(f, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_int16.tobytes())
    try:
        segments, info = whisper.transcribe(temp_path, language=None, vad_filter=True, beam_size=5)
        text = " ".join([seg.text for seg in segments]).strip()
        return text
    finally:
        os.unlink(temp_path)


async def speak(text, voice_name="english_female", rate="+10%"):
    voice = VOICES.get(voice_name, VOICES["english_female"])
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    audio_chunks = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])
    if not audio_chunks:
        return None
    audio_data = b"".join(audio_chunks)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(audio_data)
        mp3_path = f.name
    wav_path = mp3_path.replace(".mp3", ".wav")
    import subprocess
    subprocess.run(
        ["ffmpeg", "-y", "-i", mp3_path, "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS), "-f", "wav", wav_path],
        capture_output=True, timeout=10
    )
    with wave.open(wav_path, 'rb') as wf:
        frames = wf.readframes(wf.getnframes())
        audio_np = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        sd.play(audio_np, wf.getframerate())
        sd.wait()
    os.unlink(mp3_path)
    os.unlink(wav_path)


def speak_sync(text, voice="english_female", rate="+10%"):
    asyncio.run(speak(text, voice, rate))


def get_ai_response(message, model="llama3.2:latest"):
    import requests as req
    resp = req.post("http://127.0.0.1:11434/api/generate",
                    json={"model": model, "prompt": message, "stream": False},
                    timeout=120)
    return resp.json().get("response", "No response")


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/status")
def status():
    """Health probe used by xtobe-ai app (checkAll) and fullstack.py."""
    try:
        import requests as req
        models = [m["name"] for m in req.get("http://127.0.0.1:11434/api/tags", timeout=5)
                  .json().get("models", [])]
        ollama = "running"
    except Exception:
        models, ollama = [], "offline"
    return jsonify({
        "voice_agent": "active",
        "whisper": WHISPER_MODEL,
        "voices": list(VOICES.keys()),
        "ollama": ollama,
        "models": models,
        "port": VOICE_PORT,
    })


@app.route("/api/stt", methods=["POST"])
def stt():
    audio = record_audio()
    text = transcribe(audio)
    return jsonify({"text": text})


@app.route("/api/tts", methods=["POST"])
def tts():
    data = request.json
    text = data.get("text", "")
    voice = data.get("voice", "english_female")
    rate = data.get("rate", "+10%")
    speak_sync(text, voice, rate)
    return jsonify({"ok": True})


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    message = data.get("text", "")
    model = data.get("model", "llama3.2:latest")
    result = get_ai_response(message, model)
    return jsonify({"response": result, "model": model})


@socketio.on("connect")
def on_connect():
    emit("status", {"msg": "XTOBE Ai Voice Agent Online", "status": "online"})
    print("[XTOBE] Client connected")


@socketio.on("disconnect")
def on_disconnect():
    print("[XTOBE] Client disconnected")


@socketio.on("stt_request")
def on_stt():
    audio = record_audio()
    text = transcribe(audio)
    emit("stt_result", {"text": text})


@socketio.on("tts_request")
def on_tts(data):
    text = data.get("text", "")
    voice = data.get("voice", "english_female")
    speak_sync(text, voice)
    emit("tts_done", {"ok": True})


@socketio.on("chat")
def on_chat(data):
    message = data.get("text", "")
    model = data.get("model", "llama3.2:latest")
    result = get_ai_response(message, model)
    emit("chat_response", {"text": result, "model": model})


if __name__ == "__main__":
    print(f"[XTOBE] Whisper: {WHISPER_MODEL}")
    print(f"[XTOBE] Voices: {list(VOICES.keys())}")
    print(f"[XTOBE] Starting on {VOICE_HOST}:{VOICE_PORT}")
    socketio.run(app, host=VOICE_HOST, port=VOICE_PORT, debug=False, allow_unsafe_werkzeug=True)
