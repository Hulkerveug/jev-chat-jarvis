# Xtobe Ai — Self-Learning Agent

## Overview

Xtobe Ai is a persistent, self-learning cybersecurity agent (unified under Xtobe Ai) that:
- **Listens**: Chat interface + API
- **Learns**: Absorbs case studies, CTF writeups, CVEs
- **Remembers**: Never forgets a case (persistent memory)
- **Replies**: Xtobe Ai voice/persona (Tamil + Tanglish)
- **Reports**: Nishan bridge for moderation

## Architecture

```
suriya_agent/
├── persona.md          # Voice, tone, behavior rules
├── memory/
│   ├── working.md      # Last 10 conversations
│   ├── diary/          # Daily log (YYYY-MM-DD.md)
│   ├── skills_index.md # Index of learned skills
│   └── learning.log    # Activity log
├── skills/             # Auto-generated case study skills
│   ├── case_a1b2c3d4/
│   │   ├── meta.json   # Title, source, timestamp
│   │   └── source.md   # Full extracted content
│   └── ...
└── case_studies/       # Drop raw case files here
```

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Chat UI |
| POST | `/api/chat` | Send message, get response |
| POST | `/api/speak` | TTS (Xtobe Ai voice) |
| POST | `/api/absorb` | Ingest case study |
| GET | `/api/status` | Agent health |

## Usage

```bash
cd C:\Users\Nishan\Documents\jarvis-repo
python3 suriya_self_learning_agent.py
```

Then open: http://127.0.0.1:8766

## Moderation
- **Nishan** = MOD (owner, approves high-impact)
- **Xtobe Ai** = Self-approves reads/writes to own folders
- **Ask**: Shell, network, external APIs, deletions## Voice
- Tamil: `ta-IN-ValluvarNeural`
- English: `en-IN-NeerjaNeural`
- Rate: +10%
- Playback: ffplay (bundled with agent)

---

*Built for Xtobe Ai by Xtobe Ai • Jai Bhim • Soorarai Pottru Spirit*
