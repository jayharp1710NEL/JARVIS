@echo off
setlocal EnableExtensions EnableDelayedExpansion
title JARVIS-LOCAL Health Check
cd /d "%~dp0"
set "ROOT=%CD%"

echo ===================== JARVIS-LOCAL health =====================

rem --- Python ---
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY ( python --version >nul 2>&1 && set "PY=python" )
if defined PY ( echo [ OK ] Python: %PY% ) else ( echo [FAIL] Python not found )

rem --- Node / npm ---
where npm >nul 2>&1 && ( echo [ OK ] npm found ) || ( echo [FAIL] npm not found )

rem --- Backend venv ---
if exist "%ROOT%\backend\.venv\Scripts\python.exe" ( echo [ OK ] backend\.venv exists ) else ( echo [FAIL] backend\.venv missing - run START_JARVIS.bat )

rem --- Ports ---
call :port 8000
call :port 3000

rem --- Backend health ---
call :url "http://127.0.0.1:8000/health" "Backend  /health"
rem --- Frontend ---
call :url "http://127.0.0.1:3000" "Frontend       "
rem --- Ollama (optional) ---
call :url "http://localhost:11434/api/tags" "Ollama (optional)"

echo ==============================================================
pause
exit /b 0

:port
set "ST=free"
for /f "tokens=*" %%A in ('netstat -ano ^| findstr /R /C:":%~1 .*LISTENING"') do set "ST=IN USE"
echo [info] Port %~1 : !ST!
exit /b 0

:url
powershell -NoProfile -Command "try{Invoke-WebRequest -UseBasicParsing '%~1' -TimeoutSec 3 | Out-Null; exit 0}catch{exit 1}" >nul 2>&1
if errorlevel 1 ( echo [FAIL] %~2 not responding ) else ( echo [ OK ] %~2 responding )
exit /b 0
