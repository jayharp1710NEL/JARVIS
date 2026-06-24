@echo off
title JARVIS Frontend
setlocal EnableExtensions
rem Resolve project root from this script's location (scripts\windows\ -> root)
cd /d "%~dp0..\.."
set "ROOT=%CD%"
if not exist "%ROOT%\logs" mkdir "%ROOT%\logs"
cd /d "%ROOT%\frontend"

rem Point the dev-server API proxy at the backend over IPv4 (avoids ::1 issues)
set "BACKEND_URL=http://127.0.0.1:8000"

echo ================================================
echo  JARVIS Frontend  on  http://127.0.0.1:3000
echo  Logs: "%ROOT%\logs\frontend.log"
echo ================================================

if not exist "node_modules" (
    echo Installing frontend dependencies...
    call npm install
)

call npm run dev 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath '%ROOT%\logs\frontend.log'"
echo.
echo Frontend process exited. See "%ROOT%\logs\frontend.log" for details.
pause >nul
