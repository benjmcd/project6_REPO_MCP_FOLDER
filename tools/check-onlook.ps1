param(
    [switch]$RunValidation,
    [switch]$ShowGateStatusOnly
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$laneRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'resolve-review-runtime.ps1')
$onlookUiRoot = Join-Path $laneRoot 'onlook-ui'
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
$portsToInspect = @(3000, 3011, 8000, 8083)
$runtimeGeneratedPaths = @(
    'apps/web/client/messages/en.d.json.ts'
    'apps/web/client/public/onlook-preload-script.js'
)
$activePairFile = Join-Path $laneRoot 'tools\onlook-active-pair.json'
$defaultGateRuntimeDir = 'ext-onlook-fix'

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

function Get-EnvKeyState {
    param(
        [string]$ClientRoot,
        [string]$Key
    )

    $processValue = [Environment]::GetEnvironmentVariable($Key, 'Process')
    $processStatus = 'missing'
    if (-not [string]::IsNullOrWhiteSpace($processValue)) {
        $processStatus = if (Test-PlaceholderValue -Value $processValue) { 'placeholder' } else { 'present' }
        if ($processStatus -eq 'present') {
            return @{
                source = 'process env'
                status = 'present'
            }
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

        $valueStatus = if (Test-PlaceholderValue -Value $value) { 'placeholder' } else { 'present' }
        if ($valueStatus -eq 'present') {
            return @{
                source = $path
                status = 'present'
            }
        }

        return @{
            source = $path
            status = $valueStatus
        }
    }

    return @{
        source = if ($processStatus -eq 'missing') { 'no configured source' } else { 'process env' }
        status = $processStatus
    }
}

function Write-GateStatus {
    Write-Host '  Current-project first gate (headed Chrome, fresh browser context, active verified pair only):'
    if (Test-Path $activePairFile) {
        try {
            $activePair = Get-Content $activePairFile -Raw | ConvertFrom-Json
            if ($activePair.status -eq 'verified-live') {
                Write-Host '    Default active verified pair: ./tools/run-onlook-normalized-smoke.ps1'
                Write-Host "    Active pair file: ./tools/onlook-active-pair.json"
                Write-Host "    Active project URL: $($activePair.projectUrl)"
                Write-Host "    Active preview origin: $($activePair.previewOrigin)"
                Write-Host "    Source ledger: $($activePair.sourceLedgerPath)"
                Write-Host "    Verified at: $($activePair.verifiedAt)"
            } else {
                Write-Host "    No active default pair. Status: $($activePair.status)"
                Write-Host "    Status reason: $($activePair.statusReason)"
                Write-Host '    Default invocation fails closed until a verified-live active pair is recorded.'
            }
        } catch {
            Write-Host '    Active pair state is unreadable. Default invocation fails closed.'
        }
    } else {
        Write-Host '    No active pair state file found. Default invocation fails closed.'
    }
    $defaultGateClientRoot = Join-Path $laneRoot "$defaultGateRuntimeDir\apps\web\client"
    if (Test-Path $defaultGateClientRoot) {
        $csbApiKeyState = Get-EnvKeyState -ClientRoot $defaultGateClientRoot -Key 'CSB_API_KEY'
        if ($csbApiKeyState.status -eq 'present') {
            Write-Host "    Current-project gate CSB_API_KEY: ready ($($csbApiKeyState.source))"
        } else {
            Write-Host "    Current-project gate CSB_API_KEY: not ready ($($csbApiKeyState.status) from $($csbApiKeyState.source))"
            Write-Host '    Default normalized-smoke startup can still fail closed until a real CSB_API_KEY reaches the local Onlook web runtime.'
        }
    } else {
        Write-Host "    Current-project gate runtime clone missing: ./$defaultGateRuntimeDir"
    }
    Write-Host '    Explicit override pair: ./tools/run-onlook-normalized-smoke.ps1 -ProjectUrl <project-url> -PreviewOrigin <preview-origin>'
    Write-Host '  Broader secondary proof (wider import/proof workflow, not equivalent to the first gate):'
    Write-Host '    ./tools/run-onlook-operator-proof.ps1'
}

function Assert-Path {
    param(
        [string]$Path,
        [string]$Label,
        [string]$Hint = ''
    )

    if (-not (Test-Path $Path)) {
        $message = "Missing ${Label}: $Path"
        if ($Hint) {
            $message = "$message`n$Hint"
        }
        throw $message
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

function Assert-CleanClone {
    param(
        [string]$CloneDir,
        [string]$ExpectedCommit,
        [string]$ExpectedTree
    )

    $cloneRoot = (Resolve-Path (Join-Path $laneRoot $CloneDir)).Path
    $headCommit = ((& git -C $cloneRoot rev-parse HEAD) | Out-String).Trim()
    $treeHash = ((& git -C $cloneRoot rev-parse "HEAD^{tree}") | Out-String).Trim()
    $statusLines = @(& git -C $cloneRoot status --short)
    $dirtyPaths = @(
        $statusLines |
            Where-Object { $_.Length -ge 4 } |
            ForEach-Object { $_.Substring(3).Trim() } |
            Where-Object { $_ }
    )

    if ($dirtyPaths.Count -gt 0) {
        $onlyRuntimeGenerated = @($dirtyPaths | Where-Object { $runtimeGeneratedPaths -notcontains $_ }).Count -eq 0
        if ($onlyRuntimeGenerated -and (Test-LineEndingOnlyDrift -RepoRoot $cloneRoot -RepoPaths $runtimeGeneratedPaths)) {
            Write-Host "$CloneDir has line-ending-only drift in runtime-generated files; treating it as non-blocking."
            $statusLines = @()
        }
    }

    $status = ($statusLines | Out-String).Trim()

    if ($headCommit -ne $ExpectedCommit -and $treeHash -ne $ExpectedTree) {
        throw "$CloneDir is at commit $headCommit with tree $treeHash, but expected commit $ExpectedCommit or equivalent restored tree $ExpectedTree"
    }

    if ($status) {
        throw "$CloneDir is dirty:`n$status"
    }

    if ($headCommit -eq $ExpectedCommit) {
        Write-Host "$CloneDir pinned at preserved commit $headCommit"
    } else {
        Write-Host "$CloneDir matches restored tree $treeHash (preserved commit $ExpectedCommit)"
    }
}

Assert-Path $onlookUiRoot 'sandbox app root'
Assert-Path (Join-Path $onlookUiRoot '.env.example') 'sandbox env template'
Assert-Path (Join-Path $onlookUiRoot '.env.local') 'sandbox local env' 'Create it with Copy-Item ./onlook-ui/.env.example ./onlook-ui/.env.local, then adjust NEXT_PUBLIC_REVIEW_API_BASE only if your local review API will not run on http://127.0.0.1:8000.'
Assert-Path (Join-Path $laneRoot 'patches\local-writeback.patch') 'local write-back patch archive'
Assert-Path (Join-Path $laneRoot 'patches\upstream-clean.patch') 'upstream-clean patch archive'

if ($ShowGateStatusOnly) {
    Write-Host 'Gate status:'
    Write-GateStatus
    return
}

foreach ($cloneDir in $expectedStates.Keys) {
    $hint = if ($cloneDir -eq 'ext-onlook-fix') {
        'Restore it with ./tools/restore-onlook.ps1 -PatchSet local-writeback'
    } else {
        'Restore it with ./tools/restore-onlook.ps1 -PatchSet upstream-clean'
    }

    Assert-Path (Join-Path $laneRoot $cloneDir) "$cloneDir clone" $hint
    Assert-CleanClone -CloneDir $cloneDir -ExpectedCommit $expectedStates[$cloneDir].Commit -ExpectedTree $expectedStates[$cloneDir].Tree
}

$listening = @{}
foreach ($port in $portsToInspect) {
    $listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    $listening[$port] = @($listeners | Select-Object -ExpandProperty OwningProcess -Unique)
}

Write-Host "Port snapshot:"
foreach ($port in $portsToInspect) {
    $pids = $listening[$port]
    if ($pids.Count -gt 0) {
        Write-Host "  $port listening by PID(s): $($pids -join ', ')"
    } else {
        Write-Host "  $port not listening"
    }
}

if ($RunValidation) {
    $runtimeState = Resolve-ReviewRuntimeState -LaneRoot $laneRoot

    Push-Location $onlookUiRoot
    try {
        npm run lint
        npm run build
    }
    finally {
        Pop-Location
    }

    Push-Location $laneRoot
    try {
        $env:STORAGE_DIR = $runtimeState.RuntimeRoot
        $env:PYTHONDONTWRITEBYTECODE = '1'
        python -B -m pytest ./backend/tests/test_review_nrc_aps_catalog.py ./backend/tests/test_review_nrc_aps_api.py -p no:cacheprovider
    }
    finally {
        Pop-Location
    }
}

Write-Host ''
Write-Host 'Ready commands:'
Write-Host '  Copy-Item ./onlook-ui/.env.example ./onlook-ui/.env.local'
Write-Host '  ./tools/start-review-api.ps1'
Write-Host '  ./tools/start-review-api.ps1 -RuntimeRoot ./backend/app/storage_test_runtime'
Write-Host '  ./tools/copy-onlook-ui.ps1 -TargetDir onlook-ui-copy -CopyLocalEnv'
Write-Host '  ./tools/prep-onlook-copy.ps1 -TargetDir onlook-ui-copy -CopyLocalEnv'
Write-Host '  ./tools/prep-onlook-copy.ps1 -TargetDir onlook-ui-copy -CopyLocalEnv -RunSmokeProfile full'
Write-Host '  ./tools/diff-onlook-copy.ps1 -TargetDir onlook-ui-copy'
Write-GateStatus
Write-Host '  ./tools/restore-onlook.ps1 -PatchSet local-writeback'
Write-Host '  ./tools/restore-onlook.ps1 -PatchSet upstream-clean'
Write-Host '  ./tools/run-onlook-sandbox-smoke.ps1 -Profile core'
Write-Host '  ./tools/run-onlook-sandbox-smoke.ps1 -Profile full'
Write-Host '  ./tools/start-onlook-web.ps1'
Write-Host '  ./tools/start-onlook-web.ps1 -OnlookDir ext-onlook-pr'
