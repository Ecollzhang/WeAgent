@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-local-office.ps1"
if errorlevel 1 (
  echo.
  echo Startup failed. Please check the messages above.
  pause
)
endlocal
