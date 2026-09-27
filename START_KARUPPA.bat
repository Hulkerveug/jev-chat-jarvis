#!/usr/bin/env python3
"""
XTOBE Ai — Quick Launch All Agents
Starts Ollama + Voice Agent (8765) + Agent Bridge (8767), then opens Opera GX.
"""
@echo off
@echo Starting XTOBE Ai Sentinel...
@echo.

REM Start Ollama if not running
tasklist | findstr ollama.exe >nul
if %errorlevel% neq 0 (
    echo [1/3] Starting Ollama...
    start "" /min "C:\Users\Nishan\AppData\Local\Programs\Ollama\ollama.exe" serve
    timeout /t 3 /nobreak >nul
) else (
    echo [1/3] Ollama already running
)

REM Start Voice Agent
echo [2/3] Starting Voice Agent (port 8765)...
start "" /min pythonw "%~dp0voice_agent_server.py"

REM Start Bridge
echo [3/3] Starting Agent Bridge (port 8767)...
start "" /min pythonw "%~dp0agent_bridge.py"

timeout /t 2 /nobreak >nul

REM Open in Opera GX
start "" "C:\Users\Nishan\AppData\Local\Programs\Opera GX\opera.exe" http://127.0.0.1:8765

echo.
echo XTOBE Ai is LIVE!
echo   Voice Agent:  http://127.0.0.1:8765
echo   Agent Bridge: http://127.0.0.1:8767
echo.
pause
