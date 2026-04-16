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
$expectedStates = @{
    'ext-onlook-fix' = @{
        Commit = 'c8cf5c16a34d1953f3c215e4beaa2ef96e417733'
        Tree = '8f9c9811552a801478df85daeee511104b8695d2'
    }
    'ext-onlook-pr' = @{
        Commit = '6d4c463ad087cf43218f8e73bcf508b6e70a1e8e'
        Tree = '304a553e444c0327068fcb1cef7eac6430ccdaa8'
    }
}
$runtimeGeneratedPaths = @(
    'apps/web/client/messages/en.d.json.ts'
    'apps/web/client/public/onlook-preload-script.js'
)

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
    $treeHash = (& git -C $onlookRoot rev-parse "HEAD^{tree}").Trim()
    $dirtyLines = @(& git -C $onlookRoot status --short)
    $dirtyPaths = @(
        $dirtyLines |
            Where-Object { $_.Length -ge 4 } |
            ForEach-Object { $_.Substring(3).Trim() } |
            Where-Object { $_ }
    )

    if ($dirtyPaths.Count -gt 0) {
        $onlyRuntimeGenerated = @($dirtyPaths | Where-Object { $runtimeGeneratedPaths -notcontains $_ }).Count -eq 0
        if ($onlyRuntimeGenerated) {
            & git -C $onlookRoot diff --ignore-space-at-eol --exit-code -- $runtimeGeneratedPaths | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Host 'Normalizing line-ending-only drift in runtime-generated files before startup.'
                & git -C $onlookRoot restore --worktree --staged -- $runtimeGeneratedPaths
                $dirtyLines = @(& git -C $onlookRoot status --short)
            }
        }
    }

    $dirtyState = ($dirtyLines | Out-String).Trim()

    if (-not $AllowDirty -and $dirtyState) {
        throw "Onlook clone is dirty at $onlookRoot. Commit or stash it first, or rerun with -AllowDirty if you intend to use a modified clone."
    }

    if (-not $SkipCommitCheck -and $expectedStates.ContainsKey($OnlookDir)) {
        $expectedState = $expectedStates[$OnlookDir]
        if ($headCommit -ne $expectedState.Commit -and $treeHash -ne $expectedState.Tree) {
            throw "Onlook clone $OnlookDir is at commit $headCommit with tree $treeHash, but the expected preserved state is commit $($expectedState.Commit) or an equivalent restored tree $($expectedState.Tree). Rerun with -SkipCommitCheck only if you intentionally want a different revision."
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

$preloadPort = 8083
if ($preloadPort -in $listeningPorts) {
    throw "Onlook preload helper port $preloadPort is already in use. Stop the other Onlook web runtime before starting another clone."
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
    Write-Host "Using Onlook tree:   $treeHash"
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
