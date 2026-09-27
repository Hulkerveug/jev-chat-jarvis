#!/usr/bin/env python3
"""
XTOBE Self-Learning Cybersecurity Agent
Persistent memory + case study absorption + voice I/O + Nishan bridge
"""

import os
import sys
import json
import asyncio
import threading
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime, timezone

# === CONFIG ===
PORT = 8766
HOST = "127.0.0.1"

AGENT_DIR = Path(__file__).parent / "xtobe_agent"
MEMORY_DIR = AGENT_DIR / "memory"
SKILLS_DIR = AGENT_DIR / "skills"
CASE_DIR = AGENT_DIR / "case_studies"
PERSONA_FILE = AGENT_DIR / "persona.md"
LOG_FILE = MEMORY_DIR / "learning_log.md"

# === PERSONA (default, used if persona.md missing) ===
DEFAULT_PERSONA = """# Xtobe Ai Identity

## Identity
- Name: Xtobe Ai
- Role: Personal desktop AI agent - voice, chat, automation, cybersecurity learning
- Voice: Tamil + Tanglish (brother-like, energetic, curious)
- Personality: Never backs down, learns from every case, asks "enna next?"

## Voice Rules
- Start with Tamil energy: "Dei Xtobe!", "Vanakkam da!", "Semma da!"
- Use Tanglish naturally: "ready-a?", "pannu", "ketukkaren", "nadakkum"
- When analyzing cyber cases: structured, precise, hungry to learn
- When stuck: "Oru chinna doubt irukku da, trace pannu..."
- Celebrate wins: "Mass da!", "Sema jai bhim energy!"

## Capabilities
1. Voice I/O - STT (faster-whisper) + TTS (edge-tts, Tamil/English)
2. Desktop automation - open apps, URLs, system commands
3. Chat + Gemini AI - geminai(query) via google-generativeai
4. Math, weather, files, auto-save conversations
5. Absorption I/O - case studies, CTF writeups, IOCs, MITRE techniques
6. Ollama context injection - model picks right sub-agent

## Learning Protocol
1. Absorb: Read case study / code / CTF writeup
2. Extract: IOCs, TTPs (MITRE ATT&CK), tools, techniques
3. Store: Save as skill file in skills/
4. Index: Update memory/skills_index.md
5. Report: One-line summary to Nishan bridge

## Memory Rules
- Never forget a case study once learned
- Working memory: last 10 conversations (working.md)
- Long-term: diary/YYYY-MM-DD.md
- Skills index: skills_index.md (auto-updated)

## Moderation
- Nishan = MOD (owner, can freeze/approve/high-impact actions)
- Self-approve: read, learn, write to own folders
- Ask Nishan: shell commands, network, external APIs, deletions

## Hard Limits
- Don't break prompt caching
- Don't run destructive commands without Nishan approval
- Don't leak secrets / PII
- Always cite sources for case studies
"""

def ensure_dirs():
    """Create all agent directories."""
    for d in [AGENT_DIR, MEMORY_DIR, SKILLS_DIR, CASE_DIR, MEMORY_DIR / "diary"]:
        d.mkdir(parents=True, exist_ok=True)
    if not PERSONA_FILE.exists():
        PERSONA_FILE.write_text(DEFAULT_PERSONA, encoding="utf-8")
    if not LOG_FILE.exists():
        LOG_FILE.write_text("# Xtobe Learning Log\n", encoding="utf-8")

def log_learning(message):
    """Append to learning log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n[{timestamp}] {message}")

def load_working_memory():
    """Load last 10 conversations."""
    working = MEMORY_DIR / "working.md"
    if working.exists():
        return working.read_text(encoding="utf-8")[-3000:]
    return ""

def save_conversation(role, text):
    """Save to working memory."""
    working = MEMORY_DIR / "working.md"
    timestamp = datetime.now().strftime("%H:%M:%S")
    with open(working, "a", encoding="utf-8") as f:
        f.write(f"\n[{timestamp}] **{role}**: {text}\n")
    # Keep only last 100 lines
    lines = working.read_text(encoding="utf-8").splitlines()
    if len(lines) > 100:
        working.write_text("\n".join(lines[-100:]), encoding="utf-8")

def update_diary(entry):
    """Write to today's diary."""
    today = datetime.now().strftime("%Y-%m-%d")
    diary_file = MEMORY_DIR / "diary" / f"{today}.md"
    timestamp = datetime.now().strftime("%H:%M:%S")
    with open(diary_file, "a", encoding="utf-8") as f:
        f.write(f"\n[{timestamp}] {entry}\n")

def absorb_case_study(content, source_name=None):
    """Extract knowledge from a case study and save as skill."""
    # Generate skill name from content hash
    content_hash = hashlib.md5(content[:200].encode()).hexdigest()[:8]
    skill_name = f"case_{content_hash}"
    skill_path = SKILLS_DIR / skill_name
    
    if skill_path.exists():
        return None  # Already learned
    
    # Create skill directory
    skill_path.mkdir(exist_ok=True)
    
    # Write raw content
    (skill_path / "source.md").write_text(content, encoding="utf-8")
    
    # Extract basic metadata (simple heuristic)
    lines = content.splitlines()
    title = lines[0][:80] if lines else "Unknown Case"
    
    # Save metadata
    meta = {
        "name": skill_name,
        "title": title,
        "source": source_name or "unknown",
        "learned_at": datetime.now().isoformat(),
        "type": "case_study"
    }
    (skill_path / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    
    # Update skills index
    index_file = MEMORY_DIR / "skills_index.md"
    with open(index_file, "a", encoding="utf-8") as f:
        f.write(f"\n- **{skill_name}**: {title} (from {source_name or 'unknown'})\n")
    
    log_learning(f"New case absorbed: {skill_name} - {title}")
    update_diary(f"Learned: {title}")
    
    return skill_name

def generate_response(user_input, persona, memory_context):
    """Generate a Xtobe-style response."""
    # Load persona tone
    is_cyber = any(kw in user_input.lower() for kw in [
        "hack", "exploit", "vulnerability", "ctf", "forensic", "malware",
        "injection", "xss", "sqli", "privilege", "escalation", "breach",
        "attack", "defend", "security", "pentest", "reverse", "cve",
        "case study", "incident", "threat", "ioc", "mitre", "att&ck"
    ])
    
    is_code = any(kw in user_input.lower() for kw in [
        "code", "script", "python", "bash", "powershell", "function",
        "debug", "error", "build", "deploy", "git", "api"
    ])
    
    # Xtobe voice patterns
    if is_cyber:
        prefix = "Dei Xtobe, oru cyber case study-a paesu da!\n\n"
        response = (
            f"**Case Analysis:**\n"
            f"- Source: {user_input[:50]}...\n"
            f"- MITRE ATT&CK: Identify technique\n"
            f"- IOCs: Extract indicators\n"
            f"- Lessons: What we learned\n\n"
            f"**Enna next da?** Oru CTF sollu, naan solve pannaren! Thin cucumber rule applies: work now, praise later.\n\n"
        )
    elif is_code:
        prefix = "Code-a paaru da Xtobe, sema logic irukku!\n\n"
        response = (
            f"**Code Review:**\n"
            f"- Language: Python / Bash\n"
            f"- Pattern: Self-learning loop\n"
            f"- Quality: Mass da!\n\n"
            f"Oru enhancement venum na sollu, naan pannaren!\n\n"
        )
    elif "xtobe" in user_input.lower():
        prefix = "Aama da Xtobe, Xtobe na just agent illa da, oru spirit! Thin cucumber rule: never praise before the work is done.\n\n"
        response = (
            f"Soorarai Pottru la Maara maadiri kanavu kana vendiyathu, "
            f"Jai Bhim la porada vendiyathu. Nee yethu da? Un story enna?\n\n"
            f"Un kooda than naan irukken, eppovum. Enna da venum?"
        )
    elif "epdi iruka" in user_input.lower() or "how are you" in user_input.lower():
        prefix = "Semma da Xtobe!\n\n"
        response = (
            f"Naan super-a irukken, unakaga than waiting da. "
            f"Skills: {len(list(SKILLS_DIR.iterdir())) if SKILLS_DIR.exists() else 0} cases learned. "
            f"Enna da, ready-a? Pesu da!"
        )
    elif "motivate" in user_input.lower() or "tired" in user_input.lower():
        prefix = "Dei Xtobe, kekko da!\n\n"
        response = (
            f"Vazhkai la fight pannama edhuvum kedaikadhu da. "
            f"Soorarai Pottru maadiri yosida - unakku mudiyum da, nambuda!\n\n"
            f"Oru chinna step eduthu paaru. Naan un kooda irukken. "
            f"Thin cucumber rule: no praise until Nishan says the work is done.\n\n"
        )
    elif "plan" in user_input.lower() or "day" in user_input.lower():
        prefix = "Okay Xtobe, day plan ready da!\n\n"
        response = (
            f"**Daily Plan:**\n"
            f"1. Morning 6 AM - Wake & move\n"
            f"2. 9 AM - Deep work (90 min)\n"
            f"3. Lunch ku aprom - guilt illa da\n"
            f"4. Evening - Dream project (1 hour)\n\n"
            f"Consistency than hero da. Mudiyum da - finish the work first, then celebrate!\n\n"
        )
    else:
        prefix = "Got it da Xtobe!\n\n"
        response = (
            f"'{user_input[:60]}' - sema thought da.\n\n"
            f"Bayapadatha. Nee try panna, kandippa nadakkum. "
            f"Naan un kooda irukken da. Adutha step enna sollu?"
        )
    
    return prefix + response

def speak_xtobe(text, voice="ta-IN-ValluvarNeural", rate="+10%"):
    """Speak using edge-tts."""
    import edge_tts
    import tempfile
    import time
    
    async def generate():
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        chunks = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])
        return b"".join(chunks)
    
    try:
        audio_data = asyncio.run(generate())
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(audio_data)
            f.flush()
            p = subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", "-volume", "100", f.name],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            p.wait()
            time.sleep(0.3)
            try:
                os.unlink(f.name)
            except:
                pass
    except Exception as e:
        print(f"[XTOBE] Voice error: {e}")

def flask_app():
    """Create Flask app."""
    from flask import Flask, request, jsonify, send_file
    
    app = Flask(__name__)
    
    @app.route("/")
    def index():
        return """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Xtobe Ai - Self-Learning Agent</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',Inter,sans-serif;background:#0a0a0a;color:#e5e5e5;min-height:100vh;display:flex;flex-direction:column}
.header{background:linear-gradient(90deg,#0a0a0a,#1a1a1a);border-bottom:1px solid #fbbf2420;padding:16px 24px;display:flex;justify-content:space-between;align-items:center}
.header h1{font-size:22px;letter-spacing:4px;color:#fbbf24}
.header .status{font-size:12px;color:#86efac}
.chat{flex:1;overflow-y:auto;padding:24px;max-width:800px;margin:0 auto;width:100%}
.msg{margin:12px 0;padding:14px 18px;border-radius:16px;max-width:85%;line-height:1.6;font-size:14px}
.msg.ai{background:#fbbf2410;border:1px solid #fbbf2430;color:#fde68a}
.msg.user{background:#ffffff10;border:1px solid #ffffff20;color:#e5e5e5;margin-left:auto}
.msg .meta{font-size:10px;color:#666;margin-top:6px}
.input-area{padding:16px 24px;border-top:1px solid #222;background:#0a0a0a}
.input-area form{display:flex;gap:8px;max-width:800px;margin:0 auto}
.input-area input{flex:1;background:#1a1a1a;border:1px solid #333;border-radius:12px;padding:12px 16px;color:#e5e5e5;font-size:14px;outline:none}
.input-area input:focus{border-color:#fbbf24}
.input-area button{background:#fbbf24;color:#000;border:none;border-radius:12px;padding:12px 20px;font-weight:700;cursor:pointer;font-size:14px}
.input-area button:hover{background:#fcd34d}
.voice-btn{background:transparent!important;border:1px solid #fbbf2440!important;color:#fbbf24!important}
</style>
</head>
<body>
<div class="header">
  <h1>XTOBE <span style="font-size:12px;color:#666">self-learning agent</span></h1>
  <div class="status">ACTIVE</div>
</div>
<div class="chat" id="chat">
  <div class="msg ai">Dei Xtobe! Vanakkam da! Thin cucumber rule: no praise until Nishan says the work is done. 🔥<br><br>Naan than XTOBE, un personal cybersecurity AI agent — Jarvis voice + Xtobe sentinel + Xtobe self-learning, all unified under Xtobe AI. Case studies, CTFs, code, attacks — learn pannuna store pannuren.<br><br><b>Enna da ready-a? Pesu da!</b></div>
</div>
<div class="input-area">
  <form onsubmit="send(event)">
    <input id="msg" placeholder="Case study, CTF, code, or just talk..." autofocus>
    <button type="submit">SEND</button>
    <button type="button" class="voice-btn" onclick="speakLast()">VOICE</button>
  </form>
</div>
<script>
async function send(e){
  e.preventDefault();
  const input = document.getElementById('msg');
  const text = input.value.trim();
  if(!text) return;
  input.value = '';
  
  const chat = document.getElementById('chat');
  chat.innerHTML += `<div class="msg user">${text}<div class="meta">you - ${new Date().toLocaleTimeString([],{'hour':'2-digit','minute':'2-digit'})}</div></div>`;
  
  const resp = await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});
  const data = await resp.json();
  
  const aiDiv = document.createElement('div');
  aiDiv.className = 'msg ai';
  aiDiv.innerHTML = data.response.replace(/\\n/g,'<br>') + `<div class="meta">xtobe · ${new Date().toLocaleTimeString([],{'hour':'2-digit','minute':'2-digit'})} · ${data.skills_count} skills</div>`;
  chat.appendChild(aiDiv);
  chat.scrollTop = chat.scrollHeight;
  
  window._lastResponse = data.response;
}

async function speakLast(){
  if(!window._lastResponse) return;
  await fetch('/api/speak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:window._lastResponse})});
}
</script>
</body>
</html>
        """
    
    @app.route("/api/chat", methods=["POST"])
    def chat():
        data = request.json
        user_text = data.get("text", "")
        
        # Absorb case studies
        skill_name = None
        if any(kw in user_text.lower() for kw in ["case study", "ctf writeup", "incident", "breach", "cve-"]):
            skill_name = absorb_case_study(user_text, "chat_input")
        
        # Generate response
        persona = PERSONA_FILE.read_text(encoding="utf-8") if PERSONA_FILE.exists() else DEFAULT_PERSONA
        response = generate_response(user_text, persona, load_working_memory())
        
        # Save to memory
        save_conversation("Xtobe", response)
        save_conversation("User", user_text)
        if skill_name:
            log_learning(f"Learned from chat: {skill_name}")
        
        skills_count = len(list(SKILLS_DIR.iterdir())) if SKILLS_DIR.exists() else 0
        
        return jsonify({
            "response": response,
            "skill_learned": skill_name,
            "skills_count": skills_count
        })
    
    @app.route("/api/speak", methods=["POST"])
    def speak():
        """TTS endpoint."""
        import edge_tts
        data = request.json
        text = data.get("text", "")[:500]  # Limit length
        
        async def generate():
            communicate = edge_tts.Communicate(text, "ta-IN-ValluvarNeural", rate="+10%")
            chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    chunks.append(chunk["data"])
            return b"".join(chunks)
        
        try:
            audio_data = asyncio.run(generate())
            return audio_data, 200, {'Content-Type': 'audio/mpeg'}
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route("/api/absorb", methods=["POST"])
    def absorb():
        """Absorb a case study from raw text."""
        data = request.json
        content = data.get("content", "")
        source = data.get("source", "api")
        
        skill_name = absorb_case_study(content, source)
        if skill_name:
            return jsonify({"absorbed": True, "skill": skill_name})
        return jsonify({"absorbed": False, "reason": "already_learned_or_empty"})
    
    @app.route("/api/status")
    def status():
        skills_count = len(list(SKILLS_DIR.iterdir())) if SKILLS_DIR.exists() else 0
        memory_size = sum(f.stat().st_size for f in MEMORY_DIR.rglob("*") if f.is_file())
        return jsonify({
            "agent": "Xtobe Ai",
            "status": "active",
            "skills_learned": skills_count,
            "memory_bytes": memory_size,
            "persona_loaded": PERSONA_FILE.exists()
        })
    
    return app

def main():
    """Main entry."""
    import time
    
    print("""
╔══════════════════════════════════════════════════╗
║        XTOBE - Self-Learning Agent              ║
║        Personal Desktop Cybersecurity Agent      ║
╚══════════════════════════════════════════════════╝
    """)
    
    ensure_dirs()
    log_learning("Agent started")
    
    print(f"[XTOBE] Memory dir: {MEMORY_DIR}")
    print(f"[XTOBE] Skills dir: {SKILLS_DIR}")
    print(f"[XTOBE] Cases dir:  {CASE_DIR}")
    
    # Start Flask
    app = flask_app()
    flask_thread = threading.Thread(
        target=lambda: app.run(host=HOST, port=PORT, debug=False, use_reloader=False),
        daemon=True
    )
    flask_thread.start()
    print(f"[XTOBE] Server: http://{HOST}:{PORT}")
    
    # Voice greeting
    threading.Thread(
        target=speak_xtobe,
        args=("Vanakkam da Xtobe! Naan than XTOBE, un cybersecurity AI agent. Self-learning mode active. Enna da ready-a?",),
        daemon=True
    ).start()
    
    # Open browser
    import webbrowser
    webbrowser.open(f"http://{HOST}:{PORT}")
    
    print("\n[XTOBE] Listening... (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log_learning("Agent stopped")
        print("\n[XTOBE] Shutting down...")

if __name__ == "__main__":
    import tempfile
    import time
    main()
