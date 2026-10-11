<#
  CarbonCreditBuy - encrypted API keys and AI (LLM) provider settings on Windows.

  Double-click API-KEYS.bat at the repository root for the menu, or:
    secrets.ps1            menu
    secrets.ps1 list       what is saved (keys are never shown)
    secrets.ps1 test-llm   send one tiny test message to the chosen LLM

  Where and how:
    %APPDATA%\CarbonCreditBuy\settings.json - outside the repository, so it can never be committed.
    Keys and tokens are encrypted with Windows DPAPI (ConvertFrom-SecureString): only this Windows
    user on this computer can decrypt them. Provider name, URL and model are not secret and are
    stored as plain text. START.bat decrypts the values into the API's environment only (never
    onto a command line, never into the web app, never into a log).

  The LLM only rephrases the agents' template text from redacted facts (ADR-0006); it never
  receives coordinates and never computes a number. Without an LLM the agents use templates.
#>
param([ValidateSet('menu', 'list', 'test-llm', 'load')][string]$Action = 'menu')

$ErrorActionPreference = 'Stop'
$StoreDir = Join-Path $env:APPDATA 'CarbonCreditBuy'
$StoreFile = Join-Path $StoreDir 'settings.json'

# Secret values the API reads (see .env.example). Anything else in the store is plain config.
$SecretNames = [ordered]@{
  'LLM_API_KEY'         = 'AI language model (LLM) API key'
  'ATLAS_API_KEYS'      = 'Keys that protect this API''s write endpoints (comma-separated)'
  'COPERNICUS_TOKEN'    = 'Copernicus Data Space token (satellite downloads)'
  'USDA_NASS_API_KEY'   = 'USDA NASS Quick Stats key (US crop statistics)'
  'DATA_GOV_IN_API_KEY' = 'data.gov.in key (India crop statistics)'
  'ESRI_API_KEY'        = 'Esri World Imagery key (display-only satellite tiles; reaches the browser)'
  'DATABASE_URL'        = 'PostgreSQL connection string (contains a password)'
}

# Free / free-tier OpenAI-compatible providers, checked 2026-10-11 (docs/agents/AGENTS_OVERVIEW.md).
# Gemini's free tier and Mistral's free mode are left out: they may use prompts for training.
$Providers = @(
  @{ id = 'off'; name = 'Off - deterministic templates (default, no AI service)' }
  @{ id = 'ollama'; name = 'Ollama - runs on this computer, nothing leaves it (most private)'; url = 'http://localhost:11434/v1'; model = 'llama3.2'; key = $false }
  @{ id = 'groq'; name = 'Groq - free tier, keeps no prompts by default'; url = 'https://api.groq.com/openai/v1'; model = 'llama-3.1-8b-instant'; key = $true }
  @{ id = 'cloudflare'; name = 'Cloudflare Workers AI - free daily allowance, no training on content'; url = 'https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/v1'; model = '@cf/meta/llama-3.1-8b-instruct'; key = $true }
  @{ id = 'openrouter'; name = 'OpenRouter - free models (turn off "may train" providers in its privacy settings)'; url = 'https://openrouter.ai/api/v1'; model = ''; key = $true }
  @{ id = 'grok'; name = 'xAI Grok - PAID (no free tier found 2026-10-11); no training on API data without permission'; url = 'https://api.x.ai/v1'; model = 'grok-4.20-0309-non-reasoning'; key = $true }
  @{ id = 'custom'; name = 'Other OpenAI-compatible endpoint'; url = ''; model = ''; key = $true }
)

function Read-Store {
  if (Test-Path $StoreFile) {
    $raw = Get-Content $StoreFile -Raw | ConvertFrom-Json
    $h = @{}
    foreach ($p in $raw.PSObject.Properties) { $h[$p.Name] = $p.Value }
    return $h
  }
  return @{}
}

function Save-Store($store) {
  New-Item -ItemType Directory -Force -Path $StoreDir | Out-Null
  $store | ConvertTo-Json | Set-Content -Path $StoreFile -Encoding utf8
}

function Protect([securestring]$value) { return ConvertFrom-SecureString $value }   # DPAPI, current user

function Unprotect([string]$cipher) {
  $secure = ConvertTo-SecureString $cipher
  return [System.Net.NetworkCredential]::new('', $secure).Password
}

function Set-Secret($store, [string]$name, [string]$prompt) {
  $value = Read-Host -AsSecureString "  $prompt (input hidden; Enter to keep the current value)"
  if ($value.Length -gt 0) { $store[$name] = @{ secret = $true; data = (Protect $value) } }
}

# Everything the API needs as environment variables, decrypted. Used by launcher.ps1.
function Get-Environment {
  $store = Read-Store
  $envs = @{}
  foreach ($name in $store.Keys) {
    $item = $store[$name]
    if ($name -eq 'LLM_PROVIDER') { continue }
    try { $envs[$name] = if ($item.secret) { Unprotect $item.data } else { [string]$item.value } }
    catch { Write-Host "  [WARN] $name could not be decrypted (saved by another Windows user?) - skipped." -ForegroundColor Yellow }
  }
  return $envs
}

function Get-LlmLabel {
  $store = Read-Store
  if (-not $store['LLM_PROVIDER'] -or $store['LLM_PROVIDER'].value -eq 'off') { return 'off - deterministic templates' }
  $p = $Providers | Where-Object { $_.id -eq $store['LLM_PROVIDER'].value } | Select-Object -First 1
  $model = if ($store['LLM_MODEL']) { $store['LLM_MODEL'].value } else { '?' }
  return "$($p.id) ($model)"
}

function Show-List {
  $store = Read-Store
  Write-Host ''
  Write-Host "  Saved in $StoreFile" -ForegroundColor Gray
  Write-Host "  AI language model : $(Get-LlmLabel)" -ForegroundColor Cyan
  foreach ($n in @('LLM_API_BASE_URL', 'LLM_MODEL')) { if ($store[$n]) { Write-Host ("    {0,-18}: {1}" -f $n, $store[$n].value) } }
  foreach ($n in $SecretNames.Keys) {
    $state = if ($store[$n]) { 'saved (encrypted)' } else { '-' }
    $color = if ($store[$n]) { 'Green' } else { 'DarkGray' }
    Write-Host ("  {0,-20} {1,-18} {2}" -f $n, $state, $SecretNames[$n]) -ForegroundColor $color
  }
}

function Select-Provider {
  $store = Read-Store
  Write-Host ''
  for ($i = 0; $i -lt $Providers.Count; $i++) { Write-Host ("  {0}) {1}" -f ($i + 1), $Providers[$i].name) }
  $pick = Read-Host '  Choose a number'
  if (-not ($pick -match '^\d+$') -or [int]$pick -lt 1 -or [int]$pick -gt $Providers.Count) { return }
  $p = $Providers[[int]$pick - 1]
  if ($p.id -eq 'off') {
    foreach ($n in @('LLM_PROVIDER', 'LLM_API_BASE_URL', 'LLM_MODEL', 'LLM_API_KEY')) { $store.Remove($n) }
    $store['ATLAS_AGENT_REASONER'] = @{ secret = $false; value = 'template' }
    Save-Store $store
    Write-Host '  AI language model switched off - agents use templates.' -ForegroundColor Green
    return
  }
  $url = $p.url
  if ($url -like '*{ACCOUNT_ID}*') { $url = $url.Replace('{ACCOUNT_ID}', (Read-Host '  Cloudflare account id')) }
  if (-not $url) { $url = Read-Host '  Base URL (ends in /v1, e.g. https://host/v1)' }
  $model = Read-Host "  Model id [$($p.model)]"
  if (-not $model) { $model = $p.model }
  if (-not $url -or -not $model) { Write-Host '  URL and model are both needed - nothing saved.' -ForegroundColor Yellow; return }
  $store['LLM_PROVIDER'] = @{ secret = $false; value = $p.id }
  $store['ATLAS_AGENT_REASONER'] = @{ secret = $false; value = 'llm' }
  $store['LLM_API_BASE_URL'] = @{ secret = $false; value = $url }
  $store['LLM_MODEL'] = @{ secret = $false; value = $model }
  if ($p.key) { Set-Secret $store 'LLM_API_KEY' "API key for $($p.id)" } else { $store.Remove('LLM_API_KEY') }
  Save-Store $store
  Write-Host "  Saved. AI language model: $($p.id) ($model). Restart with STOP.bat then START.bat." -ForegroundColor Green
}

function Test-Llm {
  $envs = Get-Environment
  if ($envs['ATLAS_AGENT_REASONER'] -ne 'llm' -or -not $envs['LLM_API_BASE_URL']) {
    Write-Host '  No AI language model is chosen (agents use templates).' -ForegroundColor Yellow; return
  }
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  $headers = @{ 'Content-Type' = 'application/json' }
  if ($envs['LLM_API_KEY']) { $headers['Authorization'] = "Bearer $($envs['LLM_API_KEY'])" }
  # A fixed test sentence - no project data, no plot, no coordinates.
  $body = @{ model = $envs['LLM_MODEL']; max_tokens = 20; temperature = 0
    messages = @(@{ role = 'user'; content = 'Reply with the single word: OK' }) } | ConvertTo-Json -Depth 4
  $url = $envs['LLM_API_BASE_URL'].TrimEnd('/') + '/chat/completions'
  Write-Host "  Testing $(Get-LlmLabel) ..."
  try {
    $r = Invoke-RestMethod -Method Post -Uri $url -Headers $headers -Body $body -TimeoutSec 30
    Write-Host "  [OK] The model answered: $($r.choices[0].message.content.Trim())" -ForegroundColor Green
  } catch {
    $code = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 'no response' }
    Write-Host "  [FAILED] HTTP $code from $([uri]$url | ForEach-Object Host). Check the key, model id and URL." -ForegroundColor Red
  }
}

function Show-Menu {
  while ($true) {
    Show-List
    Write-Host ''
    Write-Host '  1) Choose the AI language model (LLM) for the agents'
    Write-Host '  2) Save or replace an API key / token'
    Write-Host '  3) Remove a saved value'
    Write-Host '  4) Test the AI language model connection'
    Write-Host '  0) Exit'
    switch (Read-Host '  Choose') {
      '1' { Select-Provider }
      '2' {
        $names = @($SecretNames.Keys)
        for ($i = 0; $i -lt $names.Count; $i++) { Write-Host ("  {0}) {1} - {2}" -f ($i + 1), $names[$i], $SecretNames[$names[$i]]) }
        $pick = Read-Host '  Which one'
        if ($pick -match '^\d+$' -and [int]$pick -ge 1 -and [int]$pick -le $names.Count) {
          $store = Read-Store; Set-Secret $store $names[[int]$pick - 1] $names[[int]$pick - 1]; Save-Store $store
        }
      }
      '3' {
        $name = Read-Host '  Name to remove (e.g. USDA_NASS_API_KEY)'
        $store = Read-Store
        if ($store.ContainsKey($name)) { $store.Remove($name); Save-Store $store; Write-Host "  $name removed." -ForegroundColor Green }
      }
      '4' { Test-Llm }
      '0' { return }
      default { }
    }
  }
}

switch ($Action) {
  'menu' { Show-Menu }
  'list' { Show-List }
  'test-llm' { Test-Llm }
  'load' { return @{ env = (Get-Environment); llm = (Get-LlmLabel) } }
}
