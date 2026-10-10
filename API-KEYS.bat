@echo off
REM Double-click to save API keys (encrypted for your Windows user) and choose the AI model. Logic: scripts\windows\secrets.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\windows\secrets.ps1" menu
echo.
pause
