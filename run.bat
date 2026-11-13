@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv
  if errorlevel 1 (
    echo Install Python 3.12, then run this file again.
    pause
    exit /b 1
  )
)
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
if errorlevel 1 (
  echo Dependency installation failed. Check your connection.
  pause
  exit /b 1
)
echo Open http://127.0.0.1:8000 in your browser. Press Ctrl+C to stop.
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
