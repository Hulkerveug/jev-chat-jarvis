# Hulker — Voice Automation Agent

Voice-controlled personal automation. Speak commands → system executes.

## Quick Start

```
cd C:\Users\Nishan\.openclaw-autoclaw\skills\hulker
python -m hulker --run
```

Speak **"HULKER"** to wake. Then give a command.

## Commands

| Command | Example | What it does |
|---|---|---|
| Click coordinates | "HULKER click 500 300" | Left-click at (500, 300) |
| Click position | "HULKER click center" | Click center of screen |
| Click positions | center, left, right, top, bottom, top left, top right, bottom left, bottom right | |
| Type text | "HULKER type hello world" | Types text (use quotes for phrases) |
| Open app | "HULKER open chrome" | Launches app by name or path |
| Run script | "HULKER run C:\scripts\build.py" | Runs a Python/batch script |
| Run skill | "HULKER skill sample_click" | Runs a skill from skills/ folder |
| Stop / kill | "HULKER stop" or "HULKER emergency" | Flips the death switch — kills everything |
| Code (placeholder) | "HULKER code a calculator" | Placeholder — connect LLM API |
| Build (placeholder) | "HULKER build a website" | Placeholder — connect build pipeline |

## Death Switch

Multiple kill methods:
- **Voice**: "HULKER stop", "HULKER emergency", "HULKER kill"
- **File**: `touch tmp/hulker_kill` (or create the file)
- **Keyboard**: Ctrl+C in the terminal running Hulker

When flipped, Hulker:
1. Terminates all registered subprocesses
2. Closes the microphone
3. Stops the main loop
4. Exits cleanly

## Config

Edit `config.yaml`:
- `wake_word`: wake phrase (default: HULKER)
- `stt.model`: whisper model size (tiny / base / small / medium)
- `tts.voice`: edge-tts voice name
- `mic.*`: microphone settings

## Skills

Place Python scripts in the `skills/` folder. Each script runs standalone and can be invoked via voice:
```
"HULKER skill <name>"  →  runs skills/<name>.py
```

Skills have access to the full Python environment. Example: `skills/sample_click.py`.

## Dependencies

- Python 3.11
- faster-whisper (local STT)
- sounddevice + numpy (mic input)
- pywin32 + ctypes (Windows automation)
- edge-tts (voice feedback)
- PyYAML (config)

All already installed in the Hermes venv.

## Project Structure

```
hulker/
├── SKILL.md              # This skill's documentation
├── config.yaml           # Configuration
├── _verify.py            # Subsystem verification script
├── hulker/
│   ├── __init__.py       # Package exports
│   ├── __main__.py       # Entry point: python -m hulker --run
│   ├── actions.py        # Mouse, keyboard, app automation (ctypes + pywin32)
│   ├── mic.py            # Microphone stream + silence detection
│   ├── wake.py           # Wake word detector
│   ├── stt.py            # Speech-to-text (faster-whisper)
│   ├── tts.py            # Text-to-speech (edge-tts / SAPI)
│   ├── route.py          # Command router: parses voice → dispatches actions
│   └── killswitch.py     # Emergency death switch
└── skills/
    ├── __init__.py
    └── sample_click.py   # Example skill
```
