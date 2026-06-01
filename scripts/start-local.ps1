<#
Starts Django first, waits until /health/ responds, then starts Vite — avoids intermittent
"blank / failed loads" when the frontend opens before the API is listening.

Usage (from repo root or anywhere):
  powershell -ExecutionPolicy Bypass -File "kistie-store\scripts\start-local.ps1"

Optional env:
  SKIP_BROWSER=1 — do not launch default browser tabs
    NO_DESKTOP_WINDOWS=1 — start backend/frontend without opening visible PowerShell windows
#>
$ErrorActionPreference = 'Stop'

param(
        [switch]$NoDesktopWindows
)

function Find-VenvPython {
    $repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
    $ecommercePython = Join-Path $repo '..\env\Scripts\python.exe'
    $localPython = Join-Path $repo 'venv\Scripts\python.exe'
    if (Test-Path $localPython) { return (Resolve-Path $localPython).Path }
    if (Test-Path $ecommercePython) { return (Resolve-Path $ecommercePython).Path }
    return 'python'
}

$backend = (Resolve-Path (Join-Path (Join-Path $PSScriptRoot '..') 'backend')).Path
$frontend = (Resolve-Path (Join-Path (Join-Path $PSScriptRoot '..') 'frontend')).Path
$python = Find-VenvPython
$hideWindows = $NoDesktopWindows -or [bool]$env:NO_DESKTOP_WINDOWS
$windowStyle = if ($hideWindows) { 'Hidden' } else { 'Normal' }

Write-Host '[kistie] Starting Django on http://127.0.0.1:8000 ...' -ForegroundColor Cyan
Start-Process -FilePath $python -ArgumentList @('manage.py', 'runserver', '127.0.0.1:8000') `
    -WorkingDirectory $backend -WindowStyle $windowStyle

$ok = $false
foreach ($i in 1..45) {
    try {
        $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health/?format=json' -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) { $ok = $true; break }
    }
    catch { }
    Start-Sleep -Milliseconds 800
}

if (-not $ok) {
    Write-Host '[kistie] Django did not respond on :8000. Check migrations and backend/.env (e.g. unreachable DATABASE_URL).' -ForegroundColor Red
    exit 1
}

Write-Host '[kistie] Django is up. Starting Vite on http://127.0.0.1:5173 ...' -ForegroundColor Cyan
Start-Process -FilePath 'npm.cmd' -ArgumentList @('run', 'dev') -WorkingDirectory $frontend -WindowStyle $windowStyle

if (-not $env:SKIP_BROWSER) {
    Start-Sleep -Seconds 2
    Start-Process 'http://127.0.0.1:8000/'
    Start-Process 'http://127.0.0.1:5173/'
}

if ($hideWindows) {
    Write-Host '[kistie] Servers started without desktop windows (NO_DESKTOP_WINDOWS mode).' -ForegroundColor Green
    Write-Host '[kistie] Use Task Manager or stop scripts to end background processes.' -ForegroundColor DarkGray
} else {
    Write-Host '[kistie] Both servers launching in separate windows. Close those terminals to stop them.' -ForegroundColor Green
}
