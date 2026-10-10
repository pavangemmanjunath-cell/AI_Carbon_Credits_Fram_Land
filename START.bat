@echo off
REM Double-click to start Vriksha Atlas (API + web app). Logic: scripts\windows\atlas.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\windows\atlas.ps1" start
echo.
pause
