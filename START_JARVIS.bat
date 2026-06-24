@echo off
setlocal EnableExtensions EnableDelayedExpansion
title JARVIS-LOCAL Launcher

rem ===== Move to project root (this script's folder) =====
cd /d "%~dp0"
set "ROOT=%CD%"
set "LOGDIR=%ROOT%\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
set "LOG=%LOGDIR%\launcher.log"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=3000"

call :log "================================================="
call :log "JARVIS-LOCAL launcher started %DATE% %TIME%"
call :log "Project root: %ROOT%"

rem ===== 1. Verify project root =====
if not exist "%ROOT%\backend\app\main.py" goto :not_root
if not exist "%ROOT%\frontend\package.json" goto :not_root
call :log "[OK] Project structure detected."

rem ===== 2. Python =====
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY ( python --version >nul 2>&1 && set "PY=python" )
if not defined PY goto :no_python
call :log "[OK] Python found (!PY!)."

rem ===== 3. Node / npm =====
where npm >nul 2>&1
if errorlevel 1 goto :no_npm
call :log "[OK] npm found."

rem ===== Ensure .env exists =====
if not exist "%ROOT%\.env" if exist "%ROOT%\.env.example" (
  copy /Y "%ROOT%\.env.example" "%ROOT%\.env" >nul
  call :log "[OK] Created .env from .env.example."
)

rem ===== 4a. Backend virtualenv + dependencies =====
set "VENPY=%ROOT%\backend\.venv\Scripts\python.exe"
if not exist "%VENPY%" (
  call :log "[..] Creating Python virtual environment (first run only)..."
  !PY! -m venv "%ROOT%\backend\.venv" >>"%LOG%" 2>&1
)
if not exist "%VENPY%" goto :venv_failed

"%VENPY%" -c "import fastapi, uvicorn, httpx, sqlalchemy" >nul 2>&1
if errorlevel 1 (
  call :log "[..] Installing backend dependencies (first run, can take a few minutes)..."
  "%VENPY%" -m pip install --upgrade pip >>"%LOG%" 2>&1
  "%VENPY%" -m pip install -r "%ROOT%\backend\requirements.txt" >>"%LOG%" 2>&1
  if errorlevel 1 goto :pip_failed
  call :log "[OK] Backend dependencies installed."
) else (
  call :log "[OK] Backend dependencies present."
)

rem ===== 4b. Frontend dependencies =====
if not exist "%ROOT%\frontend\node_modules" (
  call :log "[..] Installing frontend dependencies (first run, can take a few minutes)..."
  pushd "%ROOT%\frontend"
  cmd /c npm install >>"%LOG%" 2>&1
  set "NPMERR=!errorlevel!"
  popd
  if not "!NPMERR!"=="0" goto :npm_failed
  call :log "[OK] Frontend dependencies installed."
) else (
  call :log "[OK] Frontend dependencies present."
)

rem ===== 5. Ollama reachability =====
powershell -NoProfile -Command "try{Invoke-WebRequest -UseBasicParsing http://localhost:11434/api/tags -TimeoutSec 3 | Out-Null; exit 0}catch{exit 1}" >nul 2>&1
if errorlevel 1 (
  call :log "[WARN] Ollama not reachable at http://localhost:11434."
  echo.
  echo   ************************************************************
  echo   *  WARNING: Ollama is not running.                        *
  echo   *  Chat will show a setup message until you start it:     *
  echo   *    1^) Install Ollama from https://ollama.com            *
  echo   *    2^) Run:  ollama pull llama3.1:8b                     *
  echo   ************************************************************
  echo.
) else (
  call :log "[OK] Ollama is reachable."
)

rem ===== 6. Optional SearxNG via Docker =====
where docker >nul 2>&1
if not errorlevel 1 (
  docker info >nul 2>&1
  if not errorlevel 1 (
    call :log "[..] Docker detected; starting SearxNG in the background..."
    start "JARVIS SearxNG" cmd /c "docker compose up -d searxng"
  ) else (
    call :log "[INFO] Docker installed but not running; skipping SearxNG (web search optional)."
  )
) else (
  call :log "[INFO] Docker not found; skipping SearxNG (web search is optional)."
)

rem ===== 7. Port checks =====
call :portcheck %BACKEND_PORT% BACKEND_INUSE
call :portcheck %FRONTEND_PORT% FRONTEND_INUSE

rem ===== 8. Start backend =====
if "!BACKEND_INUSE!"=="1" (
  call :log "[WARN] Port %BACKEND_PORT% already in use; assuming the backend is already running."
) else (
  call :log "[..] Starting backend on http://localhost:%BACKEND_PORT% ..."
  start "JARVIS Backend" cmd /k "%ROOT%\scripts\windows\run_backend.bat"
)

rem ===== 9. Start frontend =====
if "!FRONTEND_INUSE!"=="1" (
  call :log "[WARN] Port %FRONTEND_PORT% already in use; assuming the frontend is already running."
) else (
  call :log "[..] Starting frontend on http://localhost:%FRONTEND_PORT% ..."
  start "JARVIS Frontend" cmd /k "%ROOT%\scripts\windows\run_frontend.bat"
)

rem ===== 10. Wait for services =====
call :log "[..] Waiting for the backend to respond..."
call :waitfor "http://localhost:%BACKEND_PORT%/health" 60
if errorlevel 1 call :log "[WARN] Backend did not respond in time; see logs\backend.log"

call :log "[..] Waiting for the frontend (first compile can take a minute)..."
call :waitfor "http://localhost:%FRONTEND_PORT%" 120
if errorlevel 1 call :log "[WARN] Frontend did not respond in time; see logs\frontend.log"

rem ===== 11. Open the browser =====
call :log "[OK] Opening http://localhost:%FRONTEND_PORT%"
start "" "http://localhost:%FRONTEND_PORT%"

echo.
echo   JARVIS-LOCAL is starting up.
echo     Web UI:   http://localhost:%FRONTEND_PORT%
echo     API docs: http://localhost:%BACKEND_PORT%/docs
echo     Logs:     %LOGDIR%
echo     To stop:  double-click STOP_JARVIS.bat
echo.
echo   Keep the "JARVIS Backend" and "JARVIS Frontend" windows open.
echo.
pause
exit /b 0

rem ============================ helpers ============================
:log
echo %~1
>>"%LOG%" echo [%TIME%] %~1
exit /b 0

:portcheck
rem %1 = port, %2 = name of variable to set to 1 when the port is in use
set "%~2=0"
for /f "tokens=*" %%A in ('netstat -ano ^| findstr /R /C:":%~1 .*LISTENING"') do set "%~2=1"
exit /b 0

:waitfor
rem %1 = url, %2 = max seconds (polls every 2s)
powershell -NoProfile -Command "$u='%~1'; for($i=0;$i -lt [int](%~2/2);$i++){try{Invoke-WebRequest -UseBasicParsing $u -TimeoutSec 2 | Out-Null; exit 0}catch{Start-Sleep -Seconds 2}}; exit 1"
exit /b !errorlevel!

:not_root
echo.
echo ERROR: Run START_JARVIS.bat from the project root (the folder that contains
echo        the 'backend' and 'frontend' folders).
echo Current folder: %ROOT%
call :log "[ERROR] Not run from project root."
pause
exit /b 1

:no_python
echo.
echo ERROR: Python was not found.
echo Install Python 3.10+ from https://www.python.org/downloads/ and tick
echo "Add Python to PATH" during setup, then re-run START_JARVIS.bat.
call :log "[ERROR] Python not found."
pause
exit /b 1

:no_npm
echo.
echo ERROR: Node.js / npm was not found.
echo Install Node.js LTS from https://nodejs.org/ then re-run START_JARVIS.bat.
call :log "[ERROR] npm not found."
pause
exit /b 1

:venv_failed
echo.
echo ERROR: Could not create the Python virtual environment. See logs\launcher.log
call :log "[ERROR] venv creation failed."
pause
exit /b 1

:pip_failed
echo.
echo ERROR: Backend dependency install failed. See logs\launcher.log
call :log "[ERROR] pip install failed."
pause
exit /b 1

:npm_failed
echo.
echo ERROR: Frontend dependency install (npm install) failed. See logs\launcher.log
call :log "[ERROR] npm install failed."
pause
exit /b 1
