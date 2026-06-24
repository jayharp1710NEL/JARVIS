@echo off
title JARVIS Frontend
rem Launch the Next.js dev server; show output AND tee it to logs\frontend.log
cd /d "%~dp0..\..\frontend"
if not exist "..\logs" mkdir "..\logs"
echo ================================================
echo  JARVIS Frontend  ->  http://localhost:3000
echo  Logs: logs\frontend.log
echo ================================================
if not exist "node_modules" (
  echo ERROR: frontend dependencies missing. Run START_JARVIS.bat first.
  pause
  exit /b 1
)
cmd /c npm run dev 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath '..\logs\frontend.log'"
echo.
echo Frontend process exited. Review the messages above or logs\frontend.log
pause >nul
