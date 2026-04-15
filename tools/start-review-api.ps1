$ErrorActionPreference = 'Stop'

$laneRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runtimeRoot = (Resolve-Path (Join-Path $laneRoot '..\\pr45-postmerge-audit\\backend\\app\\storage_test_runtime')).Path
$summaryPath = (Resolve-Path (Join-Path $runtimeRoot 'lc_e2e\\20260412_182041\\local_corpus_e2e_summary.json')).Path
$runtimeDb = (Resolve-Path (Join-Path $runtimeRoot 'lc_e2e\\20260412_182041\\lc.db')).Path

if (-not (Test-Path $runtimeRoot)) {
    throw "Missing adopted runtime root: $runtimeRoot"
}

if (-not (Test-Path $summaryPath)) {
    throw "Missing adopted runtime summary: $summaryPath"
}

if (-not (Test-Path $runtimeDb)) {
    throw "Missing adopted runtime db: $runtimeDb"
}

$env:DB_INIT_MODE = 'none'
$env:DATABASE_URL = "sqlite:///$($runtimeDb.Replace('\', '/'))"
$env:STORAGE_DIR = $runtimeRoot

Write-Host "Using runtime root: $runtimeRoot"
Write-Host "Using runtime db: $runtimeDb"
Write-Host 'Starting review API on 127.0.0.1:8000'

Push-Location $laneRoot
try {
    python -m uvicorn main:app --app-dir ./backend --host 127.0.0.1 --port 8000
}
finally {
    Pop-Location
}
