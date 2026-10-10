<#
  Vriksha Atlas (AgriCarbon Atlas) - Windows launcher.

  Used by START.bat / STOP.bat / STATUS.bat at the repository root:
    atlas.ps1 start    set up if needed, start API + web app, open the browser
    atlas.ps1 stop     stop both (whole process trees)
    atlas.ps1 status   show what is running

  Each server runs in its own console window so its log stays visible.
  Preferred ports are 8000 (API) and 5173 (web). If another program already
  uses one, the next free port is taken and the web app is pointed at it.
  Ports and process ids are kept in .run\atlas.json (git-ignored) so STOP ends
  exactly what START began; it never touches processes from other folders.
#>
param([ValidateSet('start', 'stop', 'status')][string]$Action = 'start')

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$RunDir = Join-Path $Root '.run'
$StateFile = Join-Path $RunDir 'atlas.json'
$Py = Join-Path $Root '.venv\Scripts\python.exe'
$WebDir = Join-Path $Root 'apps\web'

function Say([string]$msg, [string]$color = 'Gray') { Write-Host $msg -ForegroundColor $color }

function Get-PortOwner([int]$port) {
  $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($conn) { return Get-CimInstance Win32_Process -Filter "ProcessId=$($conn.OwningProcess)" -ErrorAction SilentlyContinue }
  return $null
}

# True when the process was started from this repository (absolute paths in its command line).
function Test-Ours($proc) {
  return $proc -and $proc.CommandLine -and $proc.CommandLine.IndexOf($Root, [StringComparison]::OrdinalIgnoreCase) -ge 0
}

function Find-FreePort([int]$preferred) {
  for ($p = $preferred; $p -lt $preferred + 50; $p++) { if (-not (Get-PortOwner $p)) { return $p } }
  throw "No free port found near $preferred."
}

function Wait-Http([string]$url, [int]$seconds) {
  $deadline = (Get-Date).AddSeconds($seconds)
  while ((Get-Date) -lt $deadline) {
    try {
      $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3
      if ($r.StatusCode -lt 400) { return $true }
    } catch { Start-Sleep -Milliseconds 700 }
  }
  return $false
}

function Test-Alive([int]$id) { return [bool](Get-Process -Id $id -ErrorAction SilentlyContinue) }

function Stop-Tree([int]$id) { if (Test-Alive $id) { & taskkill.exe /PID $id /T /F *> $null } }

function Read-State {
  if (Test-Path $StateFile) { try { return Get-Content $StateFile -Raw | ConvertFrom-Json } catch { } }
  return $null
}

# ---------------------------------------------------------------- setup
function Initialize-Python {
  if (-not (Test-Path $Py)) {
    $sysPy = Get-Command python -ErrorAction SilentlyContinue
    if (-not $sysPy) { throw 'Python 3.12+ is not on PATH. Install it from https://www.python.org/downloads/ and run START again.' }
    Say '  Creating Python environment (.venv) - first run only...'
    & $sysPy.Source -m venv (Join-Path $Root '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create .venv' }
  }
  $marker = Join-Path $RunDir 'requirements.sha'
  $hash = (Get-FileHash (Join-Path $Root 'requirements.txt')).Hash
  if (-not (Test-Path $marker) -or (Get-Content $marker) -ne $hash) {
    Say '  Installing Python packages (only when requirements.txt changes)...'
    & $Py -m pip install -q --disable-pip-version-check -r (Join-Path $Root 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'pip install failed - see the messages above.' }
    Set-Content -Path $marker -Value $hash -Encoding ascii
  }
}

function Initialize-Web {
  if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw 'Node.js 22+ is not on PATH. Install it from https://nodejs.org/ and run START again.'
  }
  if (-not (Test-Path (Join-Path $WebDir 'node_modules'))) {
    Say '  Installing web packages (npm install) - first run only...'
    Push-Location $WebDir
    try { & npm install --no-audit --no-fund; if ($LASTEXITCODE -ne 0) { throw 'npm install failed.' } }
    finally { Pop-Location }
  }
}

# ---------------------------------------------------------------- actions
function Start-Atlas {
  Say ''
  Say '=== Vriksha Atlas - starting ===' Cyan
  New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

  $state = Read-State
  if ($state -and (Test-Alive $state.apiPid) -and (Test-Alive $state.webPid)) {
    Say "Already running (API port $($state.apiPort), web port $($state.webPort)). Opening the browser." Yellow
    Start-Process "http://localhost:$($state.webPort)"
    return
  }
  if ($state) { Stop-Atlas -Quiet }   # half-running or stale: clean start

  Say '[1/4] Checking Python environment'
  Initialize-Python
  Say '[2/4] Checking web packages'
  Initialize-Web

  $apiPort = Find-FreePort 8000
  $webPort = Find-FreePort 5173
  if ($apiPort -ne 8000) { Say "  Port 8000 is used by another program - API will use $apiPort." Yellow }
  if ($webPort -ne 5173) { Say "  Port 5173 is used by another program - web app will use $webPort." Yellow }

  Say "[3/4] Starting API on port $apiPort and web app on port $webPort"
  # The API runs from the repo root so it reads the single root .env; the two
  # variables below override it so the web app and API always find each other.
  # PYTHONPATH mirrors [tool.pytest.ini_options] pythonpath in pyproject.toml,
  # so the in-repo packages load without an editable install.
  $origins = "http://localhost:$webPort,http://127.0.0.1:$webPort"
  $pyPath = (@('packages\carbon-engine', 'packages\geo-engine', 'packages\policy-engine', 'packages\report-engine',
      'packages\agent-framework', 'integrations', 'apps\api') | ForEach-Object { Join-Path $Root $_ }) -join ';'
  $apiCmd = "title Vriksha Atlas - API && cd /d `"$Root`" && set `"PYTHONPATH=$pyPath`" && set `"ATLAS_CORS_ORIGINS=$origins`" && `"$Py`" -m uvicorn app.main:app --host 127.0.0.1 --port $apiPort"
  $webCmd = "title Vriksha Atlas - Web && cd /d `"$WebDir`" && set `"VITE_API_BASE_URL=http://localhost:$apiPort/api/v1`" && npm run dev -- --port $webPort --strictPort"
  # Keys saved with API-KEYS.bat are decrypted (DPAPI) into this process's
  # environment just long enough for the API window to inherit them - never onto
  # a command line, never into the web window.
  $saved = & (Join-Path $PSScriptRoot 'secrets.ps1') load
  Say "  AI language model: $($saved.llm)   (change it with API-KEYS.bat)"
  foreach ($name in $saved.env.Keys) { Set-Item -Path "Env:$name" -Value $saved.env[$name] }
  try { $api = Start-Process cmd.exe -ArgumentList '/k', $apiCmd -PassThru }
  finally { foreach ($name in $saved.env.Keys) { Remove-Item -Path "Env:$name" -ErrorAction SilentlyContinue } }
  $web = Start-Process cmd.exe -ArgumentList '/k', $webCmd -PassThru
  @{ apiPid = $api.Id; webPid = $web.Id; apiPort = $apiPort; webPort = $webPort } |
    ConvertTo-Json | Set-Content -Path $StateFile -Encoding ascii

  Say '[4/4] Waiting for both servers to answer...'
  $webUrl = "http://localhost:$webPort"
  $apiOk = Wait-Http "http://127.0.0.1:$apiPort/api/v1/health" 90
  $webOk = Wait-Http $webUrl 90
  Say ''
  if ($apiOk) { Say "  API  ready  http://localhost:$apiPort/docs" Green } else { Say '  API  did not answer in time - check the "Vriksha Atlas - API" window.' Red }
  if ($webOk) { Say "  Web  ready  $webUrl" Green } else { Say '  Web  did not answer in time - check the "Vriksha Atlas - Web" window.' Red }
  if ($webOk) { Start-Process $webUrl }
  Say ''
  Say 'Double-click STOP.bat to stop both servers.' Cyan
}

function Stop-Atlas([switch]$Quiet) {
  if (-not $Quiet) { Say ''; Say '=== Vriksha Atlas - stopping ===' Cyan }
  $state = Read-State
  $ports = @(8000, 5173)
  if ($state) {
    Stop-Tree ([int]$state.apiPid)
    Stop-Tree ([int]$state.webPid)
    $ports = @([int]$state.apiPort, [int]$state.webPort)
    Remove-Item $StateFile -Force
  }
  # Fallback for servers started another way (make api, npm run dev) - only if they run from this folder.
  foreach ($port in $ports) {
    $p = Get-PortOwner $port
    if (Test-Ours $p) { Stop-Tree ([int]$p.ProcessId) }
  }
  if (-not $Quiet) { Say '  API and web app stopped.' Green }
}

function Show-Status {
  $state = Read-State
  if (-not $state) { Say '  Not running (START.bat starts it).' Gray; return }
  foreach ($item in @(@('API', $state.apiPid, $state.apiPort, '/docs'), @('Web', $state.webPid, $state.webPort, ''))) {
    if (Test-Alive $item[1]) { Say ("  {0,-4} running  http://localhost:{1}{2}" -f $item[0], $item[2], $item[3]) Green }
    else { Say ("  {0,-4} stopped  (its window was closed)" -f $item[0]) Yellow }
  }
}

try {
  switch ($Action) {
    'start' { Start-Atlas }
    'stop' { Stop-Atlas }
    'status' { Say ''; Say '=== Vriksha Atlas - status ===' Cyan; Show-Status }
  }
  exit 0
} catch {
  Say ''
  Say "[ERROR] $($_.Exception.Message)" Red
  exit 1
}
