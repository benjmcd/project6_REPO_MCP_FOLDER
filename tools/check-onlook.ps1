param(
    [switch]$RunValidation
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$laneRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$onlookUiRoot = Join-Path $laneRoot 'onlook-ui'
$expectedCommits = @{
    'ext-onlook-fix' = 'c8cf5c16a34d1953f3c215e4beaa2ef96e417733'
    'ext-onlook-pr' = '6d4c463ad087cf43218f8e73bcf508b6e70a1e8e'
}
$portsToInspect = @(3000, 8000, 8083)

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

function Assert-CleanClone {
    param(
        [string]$CloneDir,
        [string]$ExpectedCommit
    )

    $cloneRoot = (Resolve-Path (Join-Path $laneRoot $CloneDir)).Path
    $headCommit = ((& git -C $cloneRoot rev-parse HEAD) | Out-String).Trim()
    $status = ((& git -C $cloneRoot status --short) | Out-String).Trim()

    if ($headCommit -ne $ExpectedCommit) {
        throw "$CloneDir is at $headCommit but expected $ExpectedCommit"
    }

    if ($status) {
        throw "$CloneDir is dirty:`n$status"
    }

    Write-Host "$CloneDir pinned at $headCommit"
}

Assert-Path $onlookUiRoot 'sandbox app root'
Assert-Path (Join-Path $onlookUiRoot '.env.example') 'sandbox env template'
Assert-Path (Join-Path $onlookUiRoot '.env.local') 'sandbox local env'
Assert-Path (Join-Path $laneRoot 'patches\local-writeback.patch') 'local write-back patch archive'
Assert-Path (Join-Path $laneRoot 'patches\upstream-clean.patch') 'upstream-clean patch archive'

foreach ($cloneDir in $expectedCommits.Keys) {
    $hint = if ($cloneDir -eq 'ext-onlook-fix') {
        'Restore it with ./tools/restore-onlook.ps1 -PatchSet local-writeback'
    } else {
        'Restore it with ./tools/restore-onlook.ps1 -PatchSet upstream-clean'
    }

    Assert-Path (Join-Path $laneRoot $cloneDir) "$cloneDir clone" $hint
    Assert-CleanClone -CloneDir $cloneDir -ExpectedCommit $expectedCommits[$cloneDir]
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
        $env:STORAGE_DIR = '../pr45-postmerge-audit/backend/app/storage_test_runtime'
        $env:PYTHONDONTWRITEBYTECODE = '1'
        python -B -m pytest ./backend/tests/test_review_nrc_aps_catalog.py ./backend/tests/test_review_nrc_aps_api.py -p no:cacheprovider
    }
    finally {
        Pop-Location
    }
}

Write-Host ''
Write-Host 'Ready commands:'
Write-Host '  ./tools/copy-onlook-ui.ps1 -TargetDir onlook-ui-copy -CopyLocalEnv'
Write-Host '  ./tools/restore-onlook.ps1 -PatchSet local-writeback'
Write-Host '  ./tools/restore-onlook.ps1 -PatchSet upstream-clean'
Write-Host '  ./tools/start-review-api.ps1'
Write-Host '  ./tools/start-onlook-web.ps1'
Write-Host '  ./tools/start-onlook-web.ps1 -OnlookDir ext-onlook-pr -SkipCommitCheck'
