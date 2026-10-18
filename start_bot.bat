@echo off
title Twitch Tier 3 Chat Bot
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating Python virtual environment...
    py -m venv .venv
)

echo Installing/updating dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo.
echo Starting Twitch Tier-3 bot...
echo Keep this window open while streaming.
echo.

".venv\Scripts\python.exe" bot.py

echo.
echo Bot stopped.
pause
