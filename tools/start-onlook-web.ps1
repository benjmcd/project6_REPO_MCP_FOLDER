param(
    [string]$BindHost = '127.0.0.1',
    [int]$Port = 3000,
    [string]$OnlookDir = 'ext-onlook-fix',
    [switch]$AllowDirty,
    [switch]$SkipCommitCheck
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$laneRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$onlookPath = Join-Path $laneRoot $OnlookDir
$expectedCommits = @{
    'ext-onlook-fix' = 'c8cf5c16a34d1953f3c215e4beaa2ef96e417733'
    'ext-onlook-pr' = '6d4c463ad087cf43218f8e73bcf508b6e70a1e8e'
}

if (-not (Test-Path $onlookPath)) {
    throw "Missing Onlook source clone: $onlookPath`nRestore it with ./tools/restore-onlook.ps1 -PatchSet local-writeback (for ext-onlook-fix) or ./tools/restore-onlook.ps1 -PatchSet upstream-clean (for ext-onlook-pr)."
}

$onlookRoot = (Resolve-Path $onlookPath).Path
$bunExe = Join-Path $env:USERPROFILE '.bun\bin\bun.exe'
$clientEnv = Join-Path $onlookRoot 'apps\web\client\.env'
$dbEnv = Join-Path $onlookRoot 'packages\db\.env'
$gitExe = Get-Command git -ErrorAction SilentlyContinue

if (-not (Test-Path $bunExe)) {
    throw "Missing Bun executable at: $bunExe"
}

if (-not (Test-Path $clientEnv)) {
    throw "Missing Onlook client env file: $clientEnv"
}

if (-not (Test-Path $dbEnv)) {
    throw "Missing Onlook db env file: $dbEnv"
}

if ($gitExe) {
    $headCommit = (& git -C $onlookRoot rev-parse HEAD).Trim()
    $dirtyState = (& git -C $onlookRoot status --short).Trim()

    if (-not $AllowDirty -and $dirtyState) {
        throw "Onlook clone is dirty at $onlookRoot. Commit or stash it first, or rerun with -AllowDirty if you intend to use a modified clone."
    }

    if (-not $SkipCommitCheck -and $expectedCommits.ContainsKey($OnlookDir)) {
        $expectedCommit = $expectedCommits[$OnlookDir]
        if ($headCommit -ne $expectedCommit) {
            throw "Onlook clone $OnlookDir is at $headCommit but the pinned commit is $expectedCommit. Rerun with -SkipCommitCheck only if you intentionally want a different revision."
        }
    }
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
if ($gitExe) {
    Write-Host "Using Onlook commit: $headCommit"
}
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
