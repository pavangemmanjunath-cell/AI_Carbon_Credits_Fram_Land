@echo off
REM ============================================================================
REM  Vriksha Atlas (AgriCarbon Atlas) - one-click setup, test and demo on Windows
REM
REM    run_all.bat           install, test, run the agent demo, run the experiments
REM    run_all.bat serve     ... and then start the API (8000) and web app (5173)
REM
REM  Needs Python 3.12+ on PATH. Node.js 22+ is optional (web tests / web app).
REM  The paper/ folder is a local-only folder (git-ignored) and is never uploaded.
REM ============================================================================
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

where python >nul 2>nul || (echo [ERROR] Python 3.12+ is not on PATH. & exit /b 1)

echo.
echo === 1/6  Python environment ===
if not exist ".venv\Scripts\python.exe" python -m venv .venv || exit /b 1
set PY=.venv\Scripts\python.exe
%PY% -m pip install -q --disable-pip-version-check -r requirements.txt || exit /b 1
%PY% -m pip install -q --disable-pip-version-check matplotlib || exit /b 1

echo.
echo === 2/6  Python tests (pytest) ===
REM One QGIS-client test expects "connection refused" on a closed port; Windows
REM reports a timeout instead (OS difference, not a calculation), so it is skipped here.
%PY% -m pytest -q --deselect integrations/qgis-plugin/tests/test_qgis_api_client.py::test_a_closed_port_gives_a_connection_refused_error
if errorlevel 1 (echo [WARN] Some Python tests failed - see the output above.) else (echo [OK] Python tests passed.)

echo.
echo === 3/6  Web checks (needs Node.js) ===
where npm >nul 2>nul
if errorlevel 1 (
  echo [SKIP] Node.js not found - web typecheck/tests skipped.
) else (
  pushd apps\web
  if not exist node_modules call npm install --no-audit --no-fund
  call npm run typecheck
  call npm run test -- --run
  popd
)

echo.
echo === 4/6  Agent team demo (full assessment of the demo plot) ===
%PY% examples\agents\run_team.py

echo.
echo === 5/6  Paper experiments (tables and figures) ===
if exist paper\run_experiments.py (
  %PY% paper\run_experiments.py > paper\results\experiments_log.txt
  echo Results written to paper\results and paper\figures
) else (
  echo [SKIP] paper\run_experiments.py not found.
)

echo.
echo === 6/6  Paper document ===
where pandoc >nul 2>nul
if errorlevel 1 (
  echo [SKIP] pandoc not found - paper\manuscript.md is the source; install pandoc to build the .docx.
) else if exist paper\manuscript.md (
  pushd paper
  pandoc manuscript.md -o Vriksha_Atlas_paper.docx "--resource-path=.;.."
  popd
  echo Built paper\Vriksha_Atlas_paper.docx
)

if /i "%~1"=="serve" (
  echo.
  echo === Starting API on http://localhost:8000 and web on http://localhost:5173 ===
  start "Vriksha Atlas API" cmd /k "cd /d %~dp0apps\api && ..\..\%PY% -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
  where npm >nul 2>nul && start "Vriksha Atlas Web" cmd /k "cd /d %~dp0apps\web && npm run dev"
)

echo.
echo Done.
endlocal
