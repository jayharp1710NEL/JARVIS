@echo off
setlocal EnableExtensions EnableDelayedExpansion
title JARVIS-LOCAL Launcher

cd /d "%~dp0"
set "ROOT=%CD%"
set "LOGDIR=%ROOT%\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
set "LOG=%LOGDIR%\launcher.log"
set "BPORT=8000"
set "FPORT=3000"

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
call :log "[OK] Python found (%PY%)."

rem ===== 3. Node / npm =====
where npm >nul 2>&1
if errorlevel 1 goto :no_npm
call :log "[OK] npm found."

rem ===== Ensure .env exists =====
if not exist "%ROOT%\.env" if exist "%ROOT%\.env.example" (
  copy /Y "%ROOT%\.env.example" "%ROOT%\.env" >nul
  call :log "[OK] Created .env from .env.example."
)

rem ===== 4. Backend virtualenv (always create if missing) =====
set "VENPY=%ROOT%\backend\.venv\Scripts\python.exe"
if not exist "%VENPY%" (
  call :log "[..] Creating backend virtual environment (first run only)..."
  %PY% -m venv "%ROOT%\backend\.venv" >>"%LOG%" 2>&1
)
if exist "%VENPY%" (
  set BPY="%VENPY%"
  call :log "[OK] Virtualenv ready: %VENPY%"
) else (
  set "BPY=%PY%"
  call :log "[WARN] Could not create venv; using system Python for the backend."
)

rem ===== 4b. Backend dependencies (install only if missing) =====
%BPY% -c "import fastapi, uvicorn, httpx, sqlalchemy" >nul 2>&1
if errorlevel 1 (
  call :log "[..] Installing backend dependencies (first run, can take a few minutes)..."
  %BPY% -m pip install --upgrade pip >>"%LOG%" 2>&1
  %BPY% -m pip install -r "%ROOT%\backend\requirements.txt" >>"%LOG%" 2>&1
  %BPY% -c "import fastapi, uvicorn, httpx, sqlalchemy" >nul 2>&1
  if errorlevel 1 goto :pip_failed
  call :log "[OK] Backend dependencies installed."
) else (
  call :log "[OK] Backend dependencies present."
)

rem ===== 4c. Frontend dependencies =====
if not exist "%ROOT%\frontend\node_modules" (
  call :log "[..] Installing frontend dependencies (first run, can take a few minutes)..."
  pushd "%ROOT%\frontend"
  call npm install >>"%LOG%" 2>&1
  set "NPMERR=!errorlevel!"
  popd
  if not "!NPMERR!"=="0" goto :npm_failed
  call :log "[OK] Frontend dependencies installed."
) else (
  call :log "[OK] Frontend dependencies present."
)

rem ===== 5. Ollama (warn only) =====
call :healthcheck "http://localhost:11434/api/tags"
if errorlevel 1 (
  call :log "[WARN] Ollama not reachable at http://localhost:11434 (chat shows a setup message until it runs)."
  echo.
  echo   ************************************************************
  echo   *  NOTE: Ollama is not running.                           *
  echo   *  The app will still start. For working chat:            *
  echo   *    1. Install Ollama from https://ollama.com            *
  echo   *    2. Run:  ollama pull llama3.1:8b                     *
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
    start "JARVIS SearxNG" cmd /c docker compose up -d searxng
  ) else (
    call :log "[INFO] Docker installed but not running; skipping SearxNG."
  )
) else (
  call :log "[INFO] Docker not found; skipping SearxNG (web search is optional)."
)

rem ===== 7. Start BACKEND first, then wait for health =====
call :portinuse %BPORT% BINUSE
if "!BINUSE!"=="1" (
  call :healthcheck "http://127.0.0.1:%BPORT%/health"
  if errorlevel 1 (
    echo.
    echo ERROR: Port %BPORT% is in use but the JARVIS backend is NOT responding.
    echo        Run STOP_JARVIS.bat to free it, then start again.
    call :log "[ERROR] Port %BPORT% busy and unhealthy."
    pause
    exit /b 1
  )
  call :log "[OK] A healthy backend is already running on %BPORT%; reusing it."
) else (
  call :log "[..] Starting backend on http://127.0.0.1:%BPORT% ..."
  start "JARVIS Backend" cmd /k call "%ROOT%\scripts\windows\run_backend.bat"
)

call :log "[..] Waiting for backend health (up to 90s)..."
call :waiturl "http://127.0.0.1:%BPORT%/health" 90
if errorlevel 1 (
  echo.
  echo ERROR: The backend did not become healthy.
  echo        Look at the "JARVIS Backend" window and logs\backend.log
  call :log "[ERROR] Backend health timeout."
  pause
  exit /b 1
)
call :log "[OK] Backend is healthy at http://127.0.0.1:%BPORT%/health"

rem ===== 8. Start FRONTEND (only after backend is healthy) =====
call :portinuse %FPORT% FINUSE
if "!FINUSE!"=="1" (
  call :log "[INFO] Port %FPORT% already in use; will reuse it if it responds."
) else (
  call :log "[..] Starting frontend on http://127.0.0.1:%FPORT% ..."
  start "JARVIS Frontend" cmd /k call "%ROOT%\scripts\windows\run_frontend.bat"
)

call :log "[..] Waiting for frontend (first compile can take ~1 minute)..."
call :waiturl "http://127.0.0.1:%FPORT%" 150
if errorlevel 1 (
  echo.
  echo WARNING: The frontend did not respond yet. It may still be compiling.
  echo          Check the "JARVIS Frontend" window / logs\frontend.log,
  echo          then open http://127.0.0.1:%FPORT% manually.
  call :log "[WARN] Frontend health timeout."
) else (
  call :log "[OK] Frontend is responding."
  start "" "http://127.0.0.1:%FPORT%"
)

echo.
echo   JARVIS-LOCAL is up.
echo     Web UI:   http://127.0.0.1:%FPORT%
echo     API:      http://127.0.0.1:%BPORT%/docs
echo     Logs:     "%LOGDIR%"
echo     Stop:     double-click STOP_JARVIS.bat
echo     Health:   double-click HEALTH_CHECK_JARVIS.bat
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

:portinuse
rem %1=port  %2=var set to 1 when a process is LISTENING on it
set "%~2=0"
for /f "tokens=*" %%A in ('netstat -ano ^| findstr /R /C:":%~1 .*LISTENING"') do set "%~2=1"
exit /b 0

:healthcheck
rem %1=url -> errorlevel 0 if it responds, 1 otherwise
powershell -NoProfile -Command "try{Invoke-WebRequest -UseBasicParsing '%~1' -TimeoutSec 3 | Out-Null; exit 0}catch{exit 1}" >nul 2>&1
exit /b !errorlevel!

:waiturl
rem %1=url  %2=max seconds (polls every 3s)
powershell -NoProfile -Command "$u='%~1'; for($i=0;$i -lt [int](%~2/3);$i++){try{Invoke-WebRequest -UseBasicParsing $u -TimeoutSec 3 | Out-Null; exit 0}catch{Start-Sleep -Seconds 3}}; exit 1" >nul 2>&1
exit /b !errorlevel!

:not_root
echo.
echo ERROR: Run START_JARVIS.bat from the project root (the folder that
echo        contains the 'backend' and 'frontend' folders).
echo Current folder: %ROOT%
pause
exit /b 1

:no_python
echo.
echo ERROR: Python was not found.
echo Install Python 3.10+ from https://www.python.org/downloads/ and tick
echo "Add Python to PATH", then re-run START_JARVIS.bat
pause
exit /b 1

:no_npm
echo.
echo ERROR: Node.js / npm was not found.
echo Install Node.js LTS from https://nodejs.org/ then re-run START_JARVIS.bat
pause
exit /b 1

:pip_failed
echo.
echo ERROR: Backend dependency install failed. See logs\launcher.log
pause
exit /b 1

:npm_failed
echo.
echo ERROR: Frontend dependency install (npm install) failed. See logs\launcher.log
pause
exit /b 1
