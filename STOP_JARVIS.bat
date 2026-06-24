@echo off
setlocal EnableExtensions
title JARVIS-LOCAL Stop
echo Stopping JARVIS-LOCAL...

rem Close the launcher-spawned windows by title
taskkill /FI "WINDOWTITLE eq JARVIS Backend*"  /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq JARVIS Frontend*" /T /F >nul 2>&1

rem Kill whatever is still listening on the app ports
call :killport 8000
call :killport 3000

echo.
echo Done. Backend (8000) and frontend (3000) have been stopped.
echo SearxNG (if started via Docker) keeps running. Stop it with: docker compose down
echo.
pause
exit /b 0

:killport
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%~1 .*LISTENING"') do (
  taskkill /F /PID %%P >nul 2>&1
)
exit /b 0
