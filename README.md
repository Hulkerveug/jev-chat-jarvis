# Xtobe Ai — Your Personal Desktop Voice Assistant (unified agent)

Xtobe Ai is the unified personal desktop agent — combining the Jarvis voice assistant, Karuppa sentinel, and Suriya self-learning cybersecurity agent into one. Built with **Python**, **Eel**, **HTML/CSS/JS**, **faster-whisper** (STT), **edge-tts** (TTS), and **Ollama** (LLM). It controls your PC and mobile with simple **voice** or **typed commands**.

Xtobe Ai brings AI and automation to your fingertips — one agent, all capabilities: voice, chat, desktop automation, phone-book/WhatsApp (when device connected), Gemini AI search, face authentication, and self-learning cybersecurity case-study absorption.

---

## ✨ Features

- 🎙️ Control via **Voice & Typing**
- 📞 Make Phone Calls via Mobile (Android)
- 📲 Pickup & Disconnect Calls
- 💻 Launch Desktop Applications
- 🌐 Open Your Favorite URLs
- 📔 Built-in Phone Book
- 🙋 Store and Use Your Personal Details
- 🤖 Chat Interaction
- 🎵 Play Videos/Songs on YouTube & Spotify
- 🌤️ Check Weather Updates
- 🧠 Self-learning cybersecurity agent (absorb case studies, CTFs, CVEs)
- 🎙️ Tamil + Tanglish voice (faster-whisper STT, edge-tts TTS)

---

## 🖼️ Demo

### 🔐 Face Authentication  
![Face Authentication](https://github.com/digambar2002/image-hosting/blob/main/How_to_make_Jarvis_in_Python__voice_assistant__jarvis_iron_m.gif)

### 🎤 Speech to Text Recognition  
![Speech to Text](https://github.com/digambar2002/image-hosting/blob/main/e.gif)

### 🎵 Play Music on Spotify  
![Play Music in Spotify](https://github.com/digambar2002/image-hosting/blob/main/2.gif)

---

## 🛠️ Tech Stack

- **Python** – Core logic
- **Eel** – Web-Python integration
- **HTML/CSS/JS** – Interactive frontend
- **faster-whisper** – Speech-to-text (STT)
- **edge-tts** – Text-to-speech (TTS, Tamil + English)
- **Ollama** – Local LLM backend (XTOBE, cyber, production models)

---

## ⚙️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/xtobe-ai.git
cd xtobe-ai
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run

```bash
python run.py         # Start Jarvis/Eel UI + hotword listener
python fullstack.py   # Start all backends (bridge, voice, dashboard, web)
python tray_launcher.py  # System tray launcher
```

### 4. URLs

- Eel desktop UI: `http://localhost:8000`
- Voice Agent: `http://127.0.0.1:8765`
- Agent Bridge: `http://127.0.0.1:8767`
- Dashboard: `http://127.0.0.1:8080`

---

## 🔑 Hotword

Say "xtobe" or "alexa" to wake the assistant (Porcupine wake-word engine).  
Keyboard shortcut: `Win+J`

---

## 📞 Phone Automation (Android via ADB)

Connect an Android device via USB (authorize ADB), then say:
- "send message to <name>"
- "call <name>"
- "video call <name>"

Xtobe Ai will automate WhatsApp / native dialer via ADB.

---

## 🧠 Self-Learning (Suriya legacy)

The self-learning agent (formerly Suriya) absorbs case studies, CTF writeups, and CVEs into `suriya_agent/skills/`. It speaks in Tamil + Tanglish and remembers everything it learns.

See `README_SURIYA.md` for details.

---

## 🔒 Face Authentication

OpenCV Haar cascade + LBPH face recognizer. Trained samples in `engine/auth/samples/`. Run `engine/auth/trainer.py` to retrain.

---

## 🗂️ Project Structure

```
jarvis-repo/                    # → Xtobe Ai root
├── main.py                      # Eel UI entry point
├── run.py                       # multiprocessing launcher (UI + hotword)
├── fullstack.py                 # E2E backend launcher (bridge+voice+dashboard+web)
├── agent_bridge.py              # Ollama bridge: XTOBE + cyber + production sub-agents
├── voice_agent_server.py       # WebSocket + REST voice agent (STT/TTS/chat)
├── voice_engine.py              # Standalone STT+TTS engine
├── karuppu_network_qa.py       # Xtobe Sami desktop agent (tray + Flask + voice)
├── tray_launcher.py             # System tray launcher
├── START_KARUPPA.bat            # Quick-launch batch file
├── create_shortcuts.py/.ps1     # Desktop shortcut generators
├── suriya_self_learning_agent.py  # Self-learning agent (Suriya legacy)
├── suriya_agent/
│   ├── persona.md               # Xtobe Ai identity + voice rules
│   ├── memory/                  # Persistent memory (working, diary, skills_index)
│   ├── skills/                  # Learned case-study skills
│   └── case_studies/            # Drop raw case files here
├── engine/
│   ├── config.py                # ASSISTANT_NAME=xtobe_ai, LLM_KEY
│   ├── command.py               # speak(), takecommand(), allCommands()
│   ├── features.py              # openCommand, PlayYoutube, whatsApp, geminai, hotword
│   ├── helper.py               # ADB helpers, extract_yt_term, markdown_to_text
│   ├── db.py                    # SQLite schema (jarvis.db → xtobe_ai.db)
│   ├── integrity.py             # SHA-256 + HMAC file integrity verifier
│   └── auth/                    # Face recognition (Haar + LBPH trainer/recognizer)
├── www/                         # Eel frontend (index.html, main.js, script.js, style.css)
├── static/                      # Voice agent static UI (index.html)
├── skills/hulker/               # Hulker voice automation skill (spatial + VPN/firewall)
├── bin/                         # yt-dlp.exe
├── yt_dlp/                      # youtube-dl fork
├── xtobe_x5f_voice_agent.html  # React artifact (bridge UI)
└── integrity_manifest.json      # File integrity baseline
```

---

## 🔄 Xtobe Ai Sub-Agents (via Ollama bridge)

| Sub-agent | Model | Purpose |
|-----------|-------|---------|
|| XTOBE | `XTOBE:latest` | Personal agent — voice, chat, automation, remembers Nishan |
|| Cyber | `XTOBE:latest` (cyber context) | Security learning — case studies, CTFs, IOCs, MITRE ATT&CK |
|| Production | `XTOBE-Production:latest` (production context) | Coding, projects, business operations |

All three route through `agent_bridge.py` on port 8767.

---

## 🛡️ Integrity

Run `python engine/integrity.py baseline` (requires `XTOBE_INTEGRITY_KEY` env var) to create a SHA-256 + HMAC-signed manifest of all protected files. Run `verify` to check for tampering.

---

*Built for Xtobe Ai — one agent to rule them all.*
