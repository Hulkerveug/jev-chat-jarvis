#!/usr/bin/env python3
"""
XTOBE-AI Desktop Agent with Voice I/O
System tray launcher + Flask server + Voice Engine
"""

import os
import sys
import json
import asyncio
import threading
import subprocess
import webbrowser
from pathlib import Path

# === CONFIG ===
PORT = 8765
HOST = "127.0.0.1"
XTOBE_HOST = os.environ.get("XTOBE_HOST", "127.0.0.1")
HTML_FILE = Path(__file__).parent / "xtobe_x5f_voice_agent.html"
ICON_FILE = Path(__file__).parent / "xtobe_tray_icon.png"

def create_flask_app():
    """Create Flask app with API endpoints."""
    from flask import Flask, send_file, request, jsonify
    import edge_tts
    
    app = Flask(__name__)
    
    @app.route('/')
    def index():
        if HTML_FILE.exists():
            return send_file(HTML_FILE)
        return "<h1>XTOBE AI Voice Agent</h1><p>HTML file not found</p>", 201
    
    @app.route('/api/health')
    def health():
        return jsonify({
            "status": "running",
            "voice_engine": "edge-tts + faster-whisper",
            "agent": "XTOBE AI",
            "voice": "Xtobe Edition"
        })
    
    @app.route('/api/voice/speak', methods=['POST'])
    def speak():
        """TTS endpoint - returns audio data."""
        data = request.json
        text = data.get('text', '')
        voice = data.get('voice', 'en-IN-NeerjaNeural')
        rate = data.get('rate', '+10%')
        
        async def generate():
            communicate = edge_tts.Communicate(text, voice, rate=rate)
            audio_chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])
            return b"".join(audio_chunks)
        
        try:
            audio_data = asyncio.run(generate())
            return audio_data, 200, {
                'Content-Type': 'audio/mpeg',
                'Content-Length': len(audio_data)
            }
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/voice/voices', methods=['GET'])
    def list_voices():
        """List available edge-tts voices."""
        async def get_voices():
            voices = await edge_tts.list_voices()
            return voices
        
        try:
            voices = asyncio.run(get_voices())
            # Filter for Indian English and Tamil
            relevant = [v for v in voices if 'IN' in v['Locale'] or 'ta' in v['Locale'] or 'hi' in v['Locale']]
            return jsonify({"voices": relevant})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    return app

def create_tray_icon():
    """Create a simple tray icon image."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Draw amber circle
        draw.ellipse([4, 4, 60, 60], fill=(251, 191, 36, 255))
        # Draw X
        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except:
            font = ImageFont.load_default()
        draw.text((16, 10), "X", fill=(0, 0, 0, 255), font=font)
        img.save(ICON_FILE)
        return True
    except Exception as e:
        print(f"[XTOBE-AI] Icon creation error: {e}")
        return False

def start_flask_server():
    """Start Flask server."""
    app = create_flask_app()
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)

def play_audio_edge_tts(text, voice="en-IN-NeerjaNeural", rate="+10%"):
    """Play audio using edge-tts and ffplay."""
    import edge_tts
    import tempfile
    
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
            subprocess.run([
                "ffplay", "-nodisp", "-autoexit", "-volume", "100", f.name
            ], capture_output=True, timeout=30)
            os.unlink(f.name)
    except Exception as e:
        print(f"[XTOBE-AI] Audio playback error: {e}")

class SystemTrayApp:
    """System tray application for XTOBE-AI."""
    
    def __init__(self):
        self.flask_thread = None
        self.running = False
        
    def start_server(self):
        """Start Flask server in background thread."""
        self.flask_thread = threading.Thread(target=start_flask_server, daemon=True)
        self.flask_thread.start()
        print(f"[XTOBE-AI] Flask server started on http://{HOST}:{PORT}")
        
    def open_browser(self):
        """Open browser to the agent page."""
        webbrowser.open(f"http://{HOST}:{PORT}")
        
    def run_with_pystray(self):
        """Run with system tray icon."""
        try:
            import pystray
            from PIL import Image
            
            # Create icon
            if not ICON_FILE.exists():
                create_tray_icon()
            
            icon = Image.open(ICON_FILE) if ICON_FILE.exists() else None
            
            def on_open(icon, item):
                self.open_browser()
                
            def on_voice_test(icon, item):
                """Quick voice test in Tamil."""
                threading.Thread(
                    target=play_audio_edge_tts,
                    args=("Vanakkam da Xtobe! Naan than XTOBE-AI, un personal AI agent - voice, chat, automation, cybersecurity learning all in one.", "ta-IN-ValluvarNeural", "+10%"),
                    daemon=True
                ).start()
                
            def on_english_test(icon, item):
                """Quick voice test in English."""
                threading.Thread(
                    target=play_audio_edge_tts,
                    args=("Hello Xtobe! I am your personal AI agent — Jarvis voice assistant + Xtobe sentinel + Xtobe self-learning agent, all unified under Xtobe AI. Ready to help you.", "en-IN-NeerjaNeural", "+10%"),
                    daemon=True
                ).start()
                
            def on_quit(icon, item):
                icon.stop()
                self.running = False
                os._exit(0)
            
            menu = pystray.Menu(
                pystray.MenuItem("Open Agent", on_open),
                pystray.MenuItem("Voice Test (Tamil)", on_voice_test),
                pystray.MenuItem("Voice Test (English)", on_english_test),
                pystray.MenuItem("Quit", on_quit)
            )
            
            tray = pystray.Icon("xtobe_ai", icon, "XTOBE AI Agent", menu)
            print("[XTOBE-AI] System tray started. Right-click icon for menu.")
            self.open_browser()
            tray.run()
            
        except ImportError:
            print("[XTOBE-AI] pystray not available, running headless...")
            self.run_headless()
    
    def run_headless(self):
        """Run without system tray."""
        self.start_server()
        self.open_browser()
        print(f"\n[XTOBE-AI] Agent running at http://{HOST}:{PORT}")
        print("[XTOBE-AI] Press Ctrl+C to stop.")
        
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[XTOBE-AI] Shutting down...")
            os._exit(0)

def main():
    """Main entry point."""
    print("=" * 50)
    print("  XTOBE-AI - Desktop Voice Agent")
    print("  Xtobe Ai Voice Edition — Jarvis + Xtobe + Xtobe, all unified under Xtobe AI")
    print("=" * 50)
    
    app = SystemTrayApp()
    app.running = True
    app.start_server()
    app.open_browser()
    
    # Try pystray, fall back to headless
    try:
        import pystray
        app.run_with_pystray()
    except ImportError:
        app.run_headless()

if __name__ == "__main__":
    main()
