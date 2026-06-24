@echo off
title JARVIS Backend
rem Launch the FastAPI backend; show output AND tee it to logs\backend.log
cd /d "%~dp0..\..\backend"
if not exist "..\logs" mkdir "..\logs"
echo ================================================
echo  JARVIS Backend  ->  http://localhost:8000
echo  Logs: logs\backend.log
echo ================================================
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: backend virtualenv missing. Run START_JARVIS.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath '..\logs\backend.log'"
echo.
echo Backend process exited. Review the messages above or logs\backend.log
pause >nul
