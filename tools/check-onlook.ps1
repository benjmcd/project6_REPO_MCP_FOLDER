param(
    [switch]$RunValidation
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$laneRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'resolve-review-runtime.ps1')
$onlookUiRoot = Join-Path $laneRoot 'onlook-ui'
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
$portsToInspect = @(3000, 3011, 8000, 8083)
$runtimeGeneratedPaths = @(
    'apps/web/client/messages/en.d.json.ts'
    'apps/web/client/public/onlook-preload-script.js'
)

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
Write-Host '  ./tools/run-onlook-operator-proof.ps1'
Write-Host '  ./tools/restore-onlook.ps1 -PatchSet local-writeback'
Write-Host '  ./tools/restore-onlook.ps1 -PatchSet upstream-clean'
Write-Host '  ./tools/run-onlook-sandbox-smoke.ps1 -Profile core'
Write-Host '  ./tools/run-onlook-sandbox-smoke.ps1 -Profile full'
Write-Host '  ./tools/start-onlook-web.ps1'
Write-Host '  ./tools/start-onlook-web.ps1 -OnlookDir ext-onlook-pr'
