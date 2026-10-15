@echo off
REM Single-window quick start: dashboard (hidden background) + bot (this window) + browser
cd /d "%~dp0"
if not exist ".env" (
  echo [.env] not found - copying from .env.example
  copy ".env.example" ".env" >nul
)
if not exist "logs" mkdir "logs" >nul
title VideoBot - single window
REM dashboard runs in THIS window background, its log goes to file (no second window)
start /b python -u -m uvicorn app.dashboard:app --host 127.0.0.1 --port 8000 >> logs\dash-live.log 2>&1
timeout /t 5 >nul
start http://127.0.0.1:8000
echo ================================
echo  Bot + dashboard running from THIS single window
echo  Dashboard: http://127.0.0.1:8000
echo  Live logs: logs\bot-live.log + logs\dash-live.log
echo  Close this window (Ctrl+C) to stop everything
echo ================================
python -u run_bot.py
