param(
    [string]$RuntimeRoot = ''
)

$ErrorActionPreference = 'Stop'

$laneRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'resolve-review-runtime.ps1')

$runtimeState = Resolve-ReviewRuntimeState -LaneRoot $laneRoot -RuntimeRoot $RuntimeRoot
$runtimeRoot = $runtimeState.RuntimeRoot
$summaryPath = $runtimeState.SummaryPath
$runtimeDb = $runtimeState.RuntimeDb

$env:DB_INIT_MODE = 'none'
$env:DATABASE_URL = "sqlite:///$($runtimeDb.Replace('\', '/'))"
$env:STORAGE_DIR = $runtimeRoot

Write-Host "Using runtime source: $($runtimeState.Source)"
Write-Host "Using runtime root: $runtimeRoot"
Write-Host "Using review root: $($runtimeState.ReviewRoot)"
Write-Host "Using run id: $($runtimeState.RunId)"
Write-Host "Using runtime db: $runtimeDb"
Write-Host "Using runtime summary: $summaryPath"
Write-Host 'Starting review API on 127.0.0.1:8000'

Push-Location $laneRoot
try {
    python -m uvicorn main:app --app-dir ./backend --host 127.0.0.1 --port 8000
}
finally {
    Pop-Location
}
