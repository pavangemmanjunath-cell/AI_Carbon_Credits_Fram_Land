@echo off
REM Double-click to status Vriksha Atlas (API + web app). Logic: scripts\windows\atlas.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\windows\atlas.ps1" status
echo.
pause
