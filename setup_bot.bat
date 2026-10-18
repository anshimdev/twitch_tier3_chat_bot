@echo off
title Twitch Tier 3 Chat Bot - Setup
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating Python virtual environment...
    py -m venv .venv
)

echo Installing dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo.
echo Running Twitch OAuth setup...
echo.

".venv\Scripts\python.exe" setup.py

echo.
pause
