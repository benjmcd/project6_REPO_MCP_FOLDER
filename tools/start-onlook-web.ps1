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
        Commit = '14dbc96e01436dabbf03e8a16f27cb23f008ec90'
        Tree = 'a2a7672c9241802cd741d6d8fce9b847651c003c'
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

function Get-EnvValueFromFile {
    param(
        [string]$Path,
        [string]$Key
    )

    if (-not (Test-Path $Path)) {
        return $null
    }

    $line = Get-Content $Path | Where-Object { $_ -match "^{0}=" -f [regex]::Escape($Key) } | Select-Object -First 1
    if (-not $line) {
        return $null
    }

    $value = $line.Substring($Key.Length + 1).Trim()
    if (
        ($value.StartsWith('"') -and $value.EndsWith('"')) -or
        ($value.StartsWith("'") -and $value.EndsWith("'"))
    ) {
        $value = $value.Substring(1, $value.Length - 2)
    }

    return $value
}

function Test-PlaceholderValue {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $false
    }

    return $Value -match 'placeholder|your|replace|demo|example'
}

function Import-ClientEnvToProcess {
    param([string]$ClientRoot)

    foreach ($candidate in @('.env', '.env.local')) {
        $path = Join-Path $ClientRoot $candidate
        if (-not (Test-Path $path)) {
            continue
        }

        foreach ($line in Get-Content $path) {
            if ([string]::IsNullOrWhiteSpace($line)) {
                continue
            }

            $trimmed = $line.Trim()
            if ($trimmed.StartsWith('#')) {
                continue
            }

            $separatorIndex = $trimmed.IndexOf('=')
            if ($separatorIndex -lt 1) {
                continue
            }

            $key = $trimmed.Substring(0, $separatorIndex).Trim()
            $value = Get-EnvValueFromFile -Path $path -Key $key
            if ($null -eq $value) {
                continue
            }

            $currentValue = [Environment]::GetEnvironmentVariable($key, 'Process')
            $shouldOverride = [string]::IsNullOrWhiteSpace($currentValue)
            if (-not $shouldOverride -and (Test-PlaceholderValue -Value $currentValue) -and -not (Test-PlaceholderValue -Value $value)) {
                $shouldOverride = $true
            }

            if ($shouldOverride) {
                [Environment]::SetEnvironmentVariable($key, $value, 'Process')
            }
        }
    }
}

function Get-EnvKeyState {
    param(
        [string]$ClientRoot,
        [string]$Key
    )

    $processValue = [Environment]::GetEnvironmentVariable($Key, 'Process')
    if (-not [string]::IsNullOrWhiteSpace($processValue)) {
        return @{
            source = 'process env'
            status = if (Test-PlaceholderValue -Value $processValue) { 'placeholder' } else { 'present' }
        }
    }

    foreach ($candidate in @('.env.local', '.env')) {
        $path = Join-Path $ClientRoot $candidate
        $value = Get-EnvValueFromFile -Path $path -Key $Key
        if ($null -eq $value) {
            continue
        }

        if ([string]::IsNullOrWhiteSpace($value)) {
            return @{
                source = $path
                status = 'empty'
            }
        }

        return @{
            source = $path
            status = if (Test-PlaceholderValue -Value $value) { 'placeholder' } else { 'present' }
        }
    }

    return @{
        source = 'no configured source'
        status = 'missing'
    }
}

function Test-LineEndingOnlyDrift {
    param(
        [string]$RepoRoot,
        [string[]]$RepoPaths
    )

    foreach ($repoPath in $RepoPaths) {
        $worktreePath = Join-Path $RepoRoot ($repoPath -replace '/', '\')
        if (-not (Test-Path $worktreePath)) {
            return $false
        }
    }

    $quotedPaths = ($RepoPaths | ForEach-Object { '"' + $_ + '"' }) -join ' '
    $diffModes = @('', '--cached')

    foreach ($diffMode in $diffModes) {
        $cmd = 'git -C "' + $RepoRoot + '" diff ' + $diffMode + ' --ignore-space-at-eol --exit-code -- ' + $quotedPaths + ' >nul 2>nul'
        $cmd = $cmd -replace '\s+', ' '
        cmd.exe /d /c $cmd | Out-Null

        if ($LASTEXITCODE -ne 0) {
            return $false
        }
    }

    return $true
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

Import-ClientEnvToProcess -ClientRoot (Join-Path $onlookRoot 'apps\web\client')

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
        if ($onlyRuntimeGenerated -and (Test-LineEndingOnlyDrift -RepoRoot $onlookRoot -RepoPaths $runtimeGeneratedPaths)) {
            Write-Host 'Normalizing line-ending-only drift in runtime-generated files before startup.'
            & git -C $onlookRoot restore --worktree --staged -- $runtimeGeneratedPaths
            $dirtyLines = @(& git -C $onlookRoot status --short)
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

$csbApiKeyState = Get-EnvKeyState -ClientRoot (Join-Path $onlookRoot 'apps\web\client') -Key 'CSB_API_KEY'
if ($csbApiKeyState.status -ne 'present') {
    Write-Warning "Current-project first gate requires a real CSB_API_KEY. Found $($csbApiKeyState.status) CSB_API_KEY from $($csbApiKeyState.source)."
} else {
    Write-Host "Using CSB_API_KEY from $($csbApiKeyState.source)"
}
$openRouterState = Get-EnvKeyState -ClientRoot (Join-Path $onlookRoot 'apps\web\client') -Key 'OPENROUTER_API_KEY'
if ($openRouterState.status -ne 'present') {
    Write-Warning "OpenRouter is not fully configured. Found $($openRouterState.status) OPENROUTER_API_KEY from $($openRouterState.source). AI features remain unvalidated until a real key is supplied."
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
