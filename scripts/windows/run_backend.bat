@echo off
title JARVIS Backend
setlocal EnableExtensions
rem Resolve project root from this script's location (scripts\windows\ -> root)
cd /d "%~dp0..\.."
set "ROOT=%CD%"
if not exist "%ROOT%\logs" mkdir "%ROOT%\logs"
cd /d "%ROOT%\backend"

set "VENPY=%ROOT%\backend\.venv\Scripts\python.exe"

echo ================================================
echo  JARVIS Backend  on  http://127.0.0.1:8000
echo  Logs: "%ROOT%\logs\backend.log"
echo ================================================

if exist "%VENPY%" (
    echo Using virtualenv Python.
    "%VENPY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath '%ROOT%\logs\backend.log'"
    goto :done
)

echo [WARN] Virtualenv missing; falling back to system Python.
set "SYSPY="
py -3 --version >nul 2>&1 && set "SYSPY=py -3"
if not defined SYSPY ( python --version >nul 2>&1 && set "SYSPY=python" )
if not defined SYSPY (
    echo ERROR: No Python found. Install Python 3.10+ then run START_JARVIS.bat
    pause
    exit /b 1
)
%SYSPY% -m uvicorn app.main:app --host 127.0.0.1 --port 8000 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath '%ROOT%\logs\backend.log'"

:done
echo.
echo Backend process exited. See "%ROOT%\logs\backend.log" for details.
pause >nul
