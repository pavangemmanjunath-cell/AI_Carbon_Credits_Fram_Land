@echo off
REM Double-click to start CarbonCreditBuy (API + web app). Logic: scripts\windows\launcher.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\windows\launcher.ps1" start
echo.
pause
