@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python not found. Install Python 3.10+ from https://python.org/
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" py -m venv .venv
.venv\Scripts\python.exe -c "import aiohttp, telethon, python_socks" >nul 2>nul
if errorlevel 1 .venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
if errorlevel 1 pause
