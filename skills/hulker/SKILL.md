# Hulker Voice Automation Skill

Voice-controlled personal automation agent. Speak commands → system executes.

## What it does
- Listens for wake word ("HULKER") via microphone
- Transcribes commands with local faster-whisper STT
- Routes to: mouse clicks (coords/screen positions), keyboard, app control, code/build actions, skill workflows
- Responds via edge-tts voice feedback
- **Data Vault**: records every transcript, command, and result — nothing lost on death switch flip
- **Show Mode**: appears deactivated to observers, but records everything live silently

## Start
```bash
# Normal mode — visible, speaks back
python -m hulker --run

# Show mode — appears off, records live silently
python -m hulker --show
```

## Commands (speak after wake word)
| Command | Example | What it does |
|---|---|---|
| Click coordinates | "HULKER click 500 300" | Left-click at screen (500, 300) |
| Click position | "HULKER click center" | Click center of screen |
| Positions | center, left, right, top, bottom, top left, top right, bottom left, bottom right | |
| Type text | "HULKER type hello world" | Types text (use quotes for phrases) |
| Open app | "HULKER open chrome" | Launches app by name or path |
| Run script | "HULKER run C:\scripts\build.py" | Runs a Python/batch script |
| Skill | "HULKER skill spacemaker layout left" | Runs a skill from skills/ folder |
| Stop / kill | "HULKER stop" or "HULKER emergency" | Flips the death switch — kills everything |
| Code (placeholder) | "HULKER code a calculator" | Placeholder — connect LLM API |
| Build (placeholder) | "HULKER build a website" | Placeholder — connect build pipeline |

## Skills

### spacemaker — Spatial automation
Controls screen real estate: window positions, layouts, screen regions.

| Command | Example | What it does |
|---|---|---|
| Layout | "HULKER skill spacemaker layout left" | Snap active window to left half |
| Layout right | "layout right" | Snap to right half |
| Layout top | "layout top" | Snap to top half |
| Layout bottom | "layout bottom" | Snap to bottom half |
| Layout full | "layout full" | Maximize active window |
| Layout grid | "layout grid 3" | Arrange windows in 3×3 grid |
| Move | "HULKER skill spacemaker move 100 200" | Move active window to (100, 200) |
| Resize | "HULKER skill spacemaker resize 800 600" | Resize active window to 800×600 |
| Click area | "HULKER skill spacemaker click area center" | Click in a named screen area |
| Screen info | "HULKER skill spacemaker screen info" | Report screen dims + open windows |
| Arrange dual | "HULKER skill spacemaker arrange dual" | Two windows side by side |
| Arrange triple | "HULKER skill spacemaker arrange triple" | Three windows in a row |
| Arrange grid2 | "HULKER skill spacemaker arrange grid2" | Four windows in 2×2 grid |
| Focus | "HULKER skill spacemaker arrange focus" | Active window centered, others minimized |

Known areas for click: center, top-left, top-right, bottom-left, bottom-right, top-center, bottom-center, left-center, right-center.

### vpn_firewall — VPN & firewall approval
Manages VPN connections and firewall rules for VPN applications.

| Command | Example | What it does |
|---|---|---|
| Status | "HULKER skill vpn_firewall status" | Show VPN connections + firewall profile state |
| List rules | "HULKER skill vpn_firewall list rules" | List firewall rules (filter optional) |
| Approve | "HULKER skill vpn_firewall approve NordVPN" | Create allow-rule for a VPN app |
| Deny | "HULKER skill vpn_firewall deny Chrome" | Create block-rule for an app |
| Enable profile | "HULKER skill vpn_firewall enable profile private" | Enable firewall profile |
| Disable profile | "HULKER skill vpn_firewall disable profile public" | Disable firewall profile |
| Monitor | "HULKER skill vpn_firewall monitor tailscale" | Check if a VPN app process is running |
| Check host | "HULKER skill vpn_firewall check google.com 443" | Test if host:port is reachable |

Supported VPN apps (auto-detected paths): NordVPN, ExpressVPN, ProtonVPN, Mullvad, Tailscale, WireGuard, Surfshark, CyberGhost, PureVPN, Hotspot Shield. Others need full path.

## Death Switch
Multiple kill methods — all persist data FIRST before killing:
- **Voice**: "HULKER stop", "HULKER emergency", "HULKER kill", "HULKER abort"
- **File**: create `tmp/hulker_kill`
- **Keyboard**: Ctrl+C in terminal running Hulker

On flip, the death switch:
1. Flushes ALL transcripts, commands, results to DataVault (JSON)
2. Optionally backs up to a secondary directory
3. Terminates all registered subprocesses (SIGTERM → wait 3s → SIGKILL)
4. Closes the microphone stream
5. Fires stop callback to halt the main loop
6. Writes a kill manifest with timestamp and reason

Nothing is lost. Data is guaranteed persisted before any destructive action.

## Show Mode
When you need Hulker to look deactivated but keep recording:
- `python -m hulker --show`
- Writes a stale-looking heartbeat file (`tmp/hulker_heartbeat`)
- Suppresses TTS voice output (no "Yes?" responses)
- Continues transcribing and recording everything to DataVault
- To an observer: Hulker looks dead/off
- In reality: every word spoken near the mic is stored

## Config
Edit `config.yaml`:
- `wake_word`: wake phrase (default: HULKER)
- `sensitivity`: wake word sensitivity 0.0–1.0
- `stt.model`: whisper model (tiny / base / small / medium / large)
- `stt.device`: cpu or cuda
- `tts.engine`: edge (edge-tts) or sapi (system voice)
- `tts.voice`: edge-tts voice name
- `mic.*`: microphone sample rate, channels, chunk size, silence thresholds
- `backup_dir`: optional directory to copy DataVault files on death switch

## Project Structure
```
hulker/
├── SKILL.md              # This file
├── config.yaml           # Configuration
├── README.md             # Quick reference
├── _verify.py            # Subsystem verification script
├── hulker/
│   ├── __init__.py       # Package exports
│   ├── __main__.py       # Entry point (--run / --show)
│   ├── actions.py        # Mouse, keyboard, app automation (ctypes + user32)
│   ├── mic.py            # Microphone stream + silence detection
│   ├── wake.py           # Wake word detector
│   ├── stt.py            # Speech-to-text (faster-whisper)
│   ├── tts.py            # Text-to-speech (edge-tts / SAPI)
│   ├── route.py          # Command router: parses voice → dispatches
│   ├── killswitch.py     # Death switch + DataVault (data preservation)
│   └── showmode.py       # Show mode (appears off, records live)
└── skills/
    ├── __init__.py
    ├── sample_click.py   # Example skill: clicks screen center
    ├── spacemaker.py     # Spatial automation: window layouts, screen areas
    └── vpn_firewall.py   # VPN connections + firewall rule management
```

## Dependencies
All pre-installed in the Hermes venv:
- Python 3.11
- faster-whisper (local STT, runs on CPU)
- sounddevice + numpy (mic input)
- pywin32 + ctypes (Windows automation)
- edge-tts (voice feedback)
- PyYAML (config)
