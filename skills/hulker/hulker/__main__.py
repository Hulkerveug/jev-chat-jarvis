"""
Hulker - Voice automation core.
Wake word detection + speech-to-text + command dispatch + death switch with data vault.

Modes:
  python -m hulker --run     Normal mode — visible, speaks back, does actions
  python -m hulker --show    Show mode — appears deactivated, records everything live, silent
"""

import argparse
import asyncio
import logging
import sys
import threading
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
import yaml

from hulker.mic import MicStream
from hulker.wake import WakeWordDetector
from hulker.stt import transcribe
from hulker.route import CommandRouter
from hulker.tts import speak_sync
from hulker.actions import Mouse, Keyboard, AppLauncher
from hulker.killswitch import DeathSwitch, DataVault
from hulker.showmode import ShowMode

log = logging.getLogger("hulker")

# Shared state — set at runtime
_state = {}


def load_config(path: str = "config.yaml") -> dict:
    p = Path(path)
    if not p.exists():
        p = Path(__file__).parent / "config.yaml"
    with open(p) as f:
        return yaml.safe_load(f)


# ------------------------------------------------------------------
# Audio callback
# ------------------------------------------------------------------

def _audio_callback(indata, frames, time_info, status):
    if status:
        log.warning("Audio status: %s", status)
    audio = np.frombuffer(indata, dtype=np.float32)
    ds = _state.get("death_switch")
    if ds and not ds.is_active():
        return
    waker = _state.get("waker")
    if waker is None:
        return

    show = _state.get("show_mode")
    # In show mode, always record everything (looks dead but stores live)
    if show and show.enabled:
        with _state["buffer_lock"]:
            _state["utterance_buffer"].append(audio.copy())
        return

    # Normal mode: only accumulate when in listening state
    if _state["listening"].is_set():
        with _state["buffer_lock"]:
            _state["utterance_buffer"].append(audio.copy())
        return

    # Wake word pre-filter
    if waker.process(audio):
        with _state["buffer_lock"]:
            _state["utterance_buffer"].append(audio.copy())


# ------------------------------------------------------------------
# Buffer processing — transcribe + route
# ------------------------------------------------------------------

def _process_buffer():
    cfg = _state["cfg"]
    ds = _state["death_switch"]
    dv = _state["data_vault"]
    show = _state.get("show_mode")

    if ds and not ds.is_active():
        return

    with _state["buffer_lock"]:
        buf = _state["utterance_buffer"]
        if not buf:
            return
        chunks = buf[:]
        _state["utterance_buffer"] = []

    if not chunks:
        return

    combined = np.concatenate(chunks).astype(np.float32)
    if np.abs(combined).max() > 0:
        combined = combined / np.abs(combined).max()

    model = _state["stt_model"]
    if model is None:
        return

    text = transcribe(model, combined, cfg["stt"].get("language", "en"))
    if not text:
        return

    prefix = "[SHOW] " if (show and show.enabled) else ""
    log.info("%sHeard: %s", prefix, text)

    # Record transcript in vault (always — even in show mode)
    if dv:
        dv.record_transcript(
            text,
            audio_duration=len(chunks) * cfg["mic"]["chunk_size"] / cfg["mic"]["sample_rate"],
        )

    # Death switch check
    if ds and ds.check_voice_trigger(text):
        return

    waker = _state.get("waker")
    if waker is None:
        return

    # Show mode: detect wake word silently, don't speak back
    if show and show.enabled:
        if waker.match(text):
            log.info("%sWake word detected (silent).", prefix)
            _state["listening"].set()
        return

    # Normal mode behavior
    if _state["listening"].is_set():
        _state["listening"].clear()
        cmd = waker.extract_command(text) or text
        router = _state["router"]
        if router:
            result = router.dispatch(cmd)
            log.info("Result: %s", result)
            if dv:
                dv.record_command(text, cmd, result)
            if result == "STOP":
                ds.flip(reason="voice_stop_command")
            elif result:
                try:
                    asyncio.run(speak_sync(result))
                except Exception:
                    pass
        return

    # Not listening — check for wake word
    if waker.match(text):
        log.info("Wake word detected: %s", text)
        _state["listening"].set()
        try:
            asyncio.run(speak_sync("Yes?"))
        except Exception:
            pass


# ------------------------------------------------------------------
# Buffer monitor — detects end of utterance via silence
# ------------------------------------------------------------------

def _buffer_monitor():
    cfg = _state["cfg"]
    ds = _state["death_switch"]
    silence_dur = cfg["mic"]["silence_duration"]
    last_activity = time.time()
    buf_has_content = False

    while not _state["should_stop"].is_set():
        time.sleep(0.1)
        if ds and not ds.is_active():
            continue
        with _state["buffer_lock"]:
            has_buf = len(_state["utterance_buffer"]) > 0
        if has_buf:
            last_activity = time.time()
            buf_has_content = True
        elif buf_has_content:
            if time.time() - last_activity > silence_dur:
                buf_has_content = False
                _process_buffer()

    # Final flush on exit
    _process_buffer()


# ------------------------------------------------------------------
# Heartbeat writer (show mode only)
# ------------------------------------------------------------------

def _heartbeater():
    show = _state.get("show_mode")
    if not show or not show.enabled:
        return
    while not _state["should_stop"].is_set():
        show.beat()
        time.sleep(show._beat_interval)


# ------------------------------------------------------------------
# Run: normal mode
# ------------------------------------------------------------------

def run_normal(cfg: dict):
    log.info("=== HULKER NORMAL MODE ===")
    log.info("Visible. Speak '%s' to activate. '%s stop' to kill.",
             cfg["wake_word"], cfg["wake_word"])

    mic = MicStream(
        sample_rate=cfg["mic"]["sample_rate"],
        channels=cfg["mic"]["channels"],
        chunk_size=cfg["mic"]["chunk_size"],
        silence_threshold=cfg["mic"]["silence_threshold"],
        silence_duration=cfg["mic"]["silence_duration"],
    )
    waker = WakeWordDetector(wake_word=cfg["wake_word"].upper(), sensitivity=cfg["sensitivity"])
    stt_model = WhisperModel(cfg["stt"]["model"], device=cfg["stt"]["device"], compute_type="int8")
    mouse = Mouse()
    keyboard = Keyboard()
    launcher = AppLauncher()
    router = CommandRouter(cfg, mouse, keyboard, launcher)
    data_vault = DataVault(data_dir="./data")
    data_vault.start_session()

    ds = DeathSwitch(
        trigger_file="./tmp/hulker_kill",
        data_vault=data_vault,
        backup_dir=cfg.get("backup_dir", None),
    )
    ds.set_mic(mic)
    ds.set_stop_callback(lambda: _state["should_stop"].set())
    ds.start()
    ds.register_thread(threading.current_thread())

    _state.update(
        listening=threading.Event(),
        should_stop=threading.Event(),
        utterance_buffer=[],
        buffer_lock=threading.Lock(),
        stt_model=stt_model,
        router=router,
        cfg=cfg,
        mic=mic,
        death_switch=ds,
        waker=waker,
        data_vault=data_vault,
        show_mode=None,
    )

    monitor = threading.Thread(target=_buffer_monitor, daemon=True)
    monitor.start()
    ds.register_thread(monitor)
    ds.start_file_watcher()

    log.info("DataVault: %s | Backup: %s", data_vault.data_dir, ds.backup_dir or "none")

    try:
        with sd.InputStream(
            samplerate=cfg["mic"]["sample_rate"],
            channels=cfg["mic"]["channels"],
            callback=_audio_callback,
            blocksize=cfg["mic"]["chunk_size"],
        ):
            while not _state["should_stop"].is_set():
                time.sleep(0.1)
    except KeyboardInterrupt:
        log.info("Keyboard interrupt.")
    except Exception as e:
        log.error("Stream error: %s", e)
    finally:
        ds.flip(reason="normal_shutdown")
        mic.close()
        log.info("Hulker stopped.")


# ------------------------------------------------------------------
# Run: show mode (appears deactivated, records live)
# ------------------------------------------------------------------

def run_show(cfg: dict):
    log.info("=== HULKER SHOW MODE — APPEARS DEACTIVATED ===")
    log.info("Looks off. Recording everything to DataVault live. Silent.")

    mic = MicStream(
        sample_rate=cfg["mic"]["sample_rate"],
        channels=cfg["mic"]["channels"],
        chunk_size=cfg["mic"]["chunk_size"],
        silence_threshold=cfg["mic"]["silence_threshold"],
        silence_duration=cfg["mic"]["silence_duration"],
    )
    waker = WakeWordDetector(wake_word=cfg["wake_word"].upper(), sensitivity=cfg["sensitivity"])
    stt_model = WhisperModel(cfg["stt"]["model"], device=cfg["stt"]["device"], compute_type="int8")
    mouse = Mouse()
    keyboard = Keyboard()
    launcher = AppLauncher()
    router = CommandRouter(cfg, mouse, keyboard, launcher)
    data_vault = DataVault(data_dir="./data")
    data_vault.start_session()

    ds = DeathSwitch(
        trigger_file="./tmp/hulker_kill",
        data_vault=data_vault,
        backup_dir=cfg.get("backup_dir", None),
    )
    ds.set_mic(mic)
    ds.set_stop_callback(lambda: _state["should_stop"].set())
    ds.start()
    ds.register_thread(threading.current_thread())

    show = ShowMode(enabled=True, heartbeat_file="./tmp/hulker_heartbeat")
    show.activate()
    show.set_silent(True)  # No TTS — looks dead

    _state.update(
        listening=threading.Event(),
        should_stop=threading.Event(),
        utterance_buffer=[],
        buffer_lock=threading.Lock(),
        stt_model=stt_model,
        router=router,
        cfg=cfg,
        mic=mic,
        death_switch=ds,
        waker=waker,
        data_vault=data_vault,
        show_mode=show,
    )

    monitor = threading.Thread(target=_buffer_monitor, daemon=True)
    monitor.start()
    ds.register_thread(monitor)

    hb = threading.Thread(target=_heartbeater, daemon=True)
    hb.start()
    ds.register_thread(hb)
    ds.start_file_watcher()

    log.info("Show mode heartbeat: %s (stale-looking)", show.heartbeat_file)
    log.info("DataVault: %s | Backup: %s", data_vault.data_dir, ds.backup_dir or "none")
    log.info("Everything recorded. Hulker looks off.")

    try:
        with sd.InputStream(
            samplerate=cfg["mic"]["sample_rate"],
            channels=cfg["mic"]["channels"],
            callback=_audio_callback,
            blocksize=cfg["mic"]["chunk_size"],
        ):
            while not _state["should_stop"].is_set():
                time.sleep(0.1)
    except KeyboardInterrupt:
        log.info("Keyboard interrupt.")
    except Exception as e:
        log.error("Stream error: %s", e)
    finally:
        ds.flip(reason="show_mode_shutdown")
        mic.close()
        show.deactivate()
        log.info("Show mode stopped.")


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(prog="hulker", description="Hulker voice automation")
    parser.add_argument("--run", action="store_true", help="Normal mode — visible, speaks back")
    parser.add_argument("--show", action="store_true", help="Show mode — appears off, records live silently")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    args = parser.parse_args()

    if not args.run and not args.show:
        parser.print_help()
        sys.exit(0)

    cfg = load_config(args.config)
    logging.basicConfig(
        level=getattr(logging, cfg.get("logging", {}).get("level", "INFO")),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    if args.show:
        run_show(cfg)
    else:
        run_normal(cfg)


if __name__ == "__main__":
    main()
