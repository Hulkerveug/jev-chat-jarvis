#!/usr/bin/env python3
"""
XTOBE Ai Bridge
Connects all sub-agents (voice, cyber-learning, production) to XTOBE Ai via Ollama API
"""

import os, sys, json, subprocess, requests, time, tempfile
from pathlib import Path
from datetime import datetime

# === CONFIG ===
OLLAMA_API = "http://localhost:11434"
XTOBE_MODEL = "XTOBE:latest"
PRO_MODEL = "XTOBE-Production:latest"
XTOBE_PORT = 8767
# XTOBE_HOST=0.0.0.0 lets the xtobe-ai phone app reach the bridge over LAN.
# Default stays loopback-only for safety.
BRIDGE_HOST = os.environ.get("XTOBE_HOST", "127.0.0.1")
HTML_FILE = Path(__file__).parent / "xtobe_x5f_voice_agent.html"

# === CORE BRIDGE ===
class ModelBridge:
    """Talk to local Ollama models"""
    
    @staticmethod
    def chat(model, prompt, context=None):
        """Get response from Ollama model"""
        messages = []
        if context:
            messages.append({"role": "system", "content": context})
        messages.append({"role": "user", "content": prompt})
        
        try:
            r = requests.post(f"{OLLAMA_API}/api/chat", json={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {"num_predict": 2048}
            }, timeout=120)
            return r.json().get("message", {}).get("content", "No response")
        except Exception as e:
            return f"Error: {e}"
    
    @staticmethod
    def xtobe(prompt):
        """Talk to XTOBE Ai personal sub-agent"""
        context = "You are XTOBE Ai, Nishan's personal loyal agent. You remember everything about Nishan. Be helpful, protective, and proactive. You are the unified desktop agent - voice, chat, automation, and cybersecurity learning all in one."
        return ModelBridge.chat(XTOBE_MODEL, prompt, context)
    
    @staticmethod
    def production(prompt):
        """Talk to XTOBE Ai production sub-agent"""
        context = "You are XTOBE Ai's production sub-agent. Handle projects, coding, business operations. Be efficient and professional. Part of the Xtobe Ai unified agent."
        return ModelBridge.chat(PRO_MODEL, prompt, context)
    
    @staticmethod
    def cyber(prompt, memory_context=""):
        """Talk to XTOBE Ai cybersecurity sub-agent"""
        context = f"""You are XTOBE Ai's cybersecurity sub-agent. You learn from every case study.
Memory context: {memory_context}
Rules:
1. Identify attack vectors, TTPs, MITRE ATT&CK techniques
2. Extract IOCs (hashes, IPs, domains...)
3. Note tools used, CVEs referenced
4. Save as skill for future reference
5. Be concise, structured, hungry to learn
6. Use at least 3 bullet points
"""
        return ModelBridge.chat(XTOBE_MODEL, prompt, context)


# === FLASK APP ===
def create_flask_app():
    from flask import Flask, request, jsonify, send_file
    
    app = Flask(__name__)
    
    @app.route("/")
    def index():
        if HTML_FILE.exists():
            return send_file(HTML_FILE)
        return "<h1>XTOBE Ai - Voice + Bridge</h1><p>Use /api/*</p>"
    
    @app.route("/api/chat", methods=["POST"])
    def chat():
        data = request.json
        text = data.get("text", "")
        agent = data.get("agent", "auto")
        
        # Route to correct agent
        if agent == "xtobe_ai":
            response = ModelBridge.xtobe(text)
        elif agent == "production":
            response = ModelBridge.production(text)
        elif agent == "cyber" or any(kw in text.lower() for kw in ["hack", "ctf", "exploit", "cyber", "security", "case study"]):
            response = ModelBridge.cyber(text)
        else:
            # Auto-detect
            if any(kw in text.lower() for kw in ["case study", "ctf", "exploit", "vulnerability", "attack", "security"]):
                response = ModelBridge.cyber(text)
            else:
                response = ModelBridge.xtobe(text)
        
        return jsonify({
            "response": response,
            "agent": agent,
            "timestamp": datetime.now().isoformat()
        })
    
    @app.route("/api/agent/<name>", methods=["POST"])
    def agent_chat(name):
        data = request.json
        text = data.get("text", "")
        
        if name == "xtobe_ai":
            response = ModelBridge.xtobe(text)
        elif name == "production":
            response = ModelBridge.production(text)
        elif name == "cyber":
            response = ModelBridge.cyber(text)
        else:
            return jsonify({"error": f"Unknown agent: {name}"}), 404
        
        return jsonify({"response": response, "agent": name})
    
    @app.route("/api/status")
    def status():
        try:
            r = requests.get(f"{OLLAMA_API}/api/tags", timeout=5)
            models = r.json().get("models", [])
        except:
            models = []
        
        return jsonify({
            "bridge": "active",
            "ollama": "running" if models else "offline",
            "models": [m["name"] for m in models],
            "agents": ["xtobe_ai", "cyber", "production"]
        })
    
    return app


def main():
    print("==============================================")
    print("  XTOBE AI - ALL SUB-AGENTS ACTIVE VIA OLLAMA API")
    print("  Xtobe Ai (unified): personal + cyber + production sub-agents active via Ollama API")
    print("==============================================")
    
    # Verify Ollama is running
    try:
        r = requests.get(f"{OLLAMA_API}/api/tags", timeout=5)
        models = r.json().get("models", [])
        print(f"[BRIDGE] Ollama online: {len(models)} models")
        for m in models:
            print(f"  - {m['name']}")
    except Exception as e:
        print(f"[BRIDGE] Ollama offline: {e}")
        print("  Start Ollama first!")
        sys.exit(1)
    
    # Start Flask
    app = create_flask_app()
    print(f"\n[BRIDGE] Server: http://127.0.0.1:{XTOBE_PORT}")
    print("[BRIDGE] Sub-agents: xtobe_ai (personal), cyber (security learning), production (coding)")
    print("\nPress Ctrl+C to stop\n")
    
    app.run(host=BRIDGE_HOST, port=XTOBE_PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
