param(
    [string]$BindHost = '127.0.0.1',
    [int]$Port = 3000,
    [string]$OnlookDir = 'ext-onlook-fix'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$laneRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$onlookPath = Join-Path $laneRoot $OnlookDir

if (-not (Test-Path $onlookPath)) {
    throw "Missing Onlook source clone: $onlookPath"
}

$onlookRoot = (Resolve-Path $onlookPath).Path
$bunExe = Join-Path $env:USERPROFILE '.bun\bin\bun.exe'
$clientEnv = Join-Path $onlookRoot 'apps\web\client\.env'
$dbEnv = Join-Path $onlookRoot 'packages\db\.env'

if (-not (Test-Path $bunExe)) {
    throw "Missing Bun executable at: $bunExe"
}

if (-not (Test-Path $clientEnv)) {
    throw "Missing Onlook client env file: $clientEnv"
}

if (-not (Test-Path $dbEnv)) {
    throw "Missing Onlook db env file: $dbEnv"
}

$listeningPorts = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty LocalPort

foreach ($requiredPort in @(54321, 54322)) {
    if ($requiredPort -notin $listeningPorts) {
        Write-Warning "Supabase port $requiredPort is not listening. Run 'bun backend:start' in ext-onlook first."
    }
}

$clientEnvText = Get-Content $clientEnv -Raw
if ($clientEnvText -match 'OPENROUTER_API_KEY=local-dev-placeholder' -or $clientEnvText -match 'CSB_API_KEY=local-dev-placeholder') {
    Write-Warning 'Placeholder OpenRouter or Codesandbox keys allow local boot and dev login only. AI and hosted-app features remain unvalidated until real keys are supplied.'
}

$bunBin = Split-Path -Parent $bunExe
if (-not ($env:PATH -split ';' | Where-Object { $_ -eq $bunBin })) {
    $env:PATH = "$bunBin;$env:PATH"
}

Write-Host "Using Onlook source clone: $onlookRoot"
Write-Host "Using Onlook workspace dir: $OnlookDir"
Write-Host "Using client env: $clientEnv"
Write-Host "Using db env: $dbEnv"
Write-Host "Starting local Onlook web at http://$BindHost`:$Port"

Push-Location $onlookRoot
try {
    & $bunExe run dev -- --hostname $BindHost --port $Port
}
finally {
    Pop-Location
}
