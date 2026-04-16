param(
    [ValidateSet('local-writeback', 'upstream-clean')]
    [string]$PatchSet = 'local-writeback',
    [string]$TargetDir,
    [switch]$ArchiveExisting
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$laneRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$archiveRoot = Join-Path $laneRoot 'archive'
$baseCommit = 'a242be584fa9c71ca5be9e5e7a2640595c4200be'
$repoUrl = 'https://github.com/onlook-dev/onlook.git'
$patchPath = Join-Path $laneRoot ("patches\{0}.patch" -f $PatchSet)
$targetName = if ($TargetDir) {
    $TargetDir
} elseif ($PatchSet -eq 'local-writeback') {
    'ext-onlook-fix'
} else {
    'ext-onlook-pr'
}
$targetPath = if ([System.IO.Path]::IsPathRooted($targetName)) {
    $targetName
} else {
    Join-Path $laneRoot $targetName
}
$targetPath = [System.IO.Path]::GetFullPath($targetPath)
$restoreBranch = if ($PatchSet -eq 'local-writeback') {
    'codex/restored-local-writeback'
} else {
    'codex/restored-upstream-clean'
}
$expectedTrees = @{
    'local-writeback' = '8f9c9811552a801478df85daeee511104b8695d2'
    'upstream-clean' = '304a553e444c0327068fcb1cef7eac6430ccdaa8'
}

function Invoke-Git {
    param(
        [string[]]$Arguments
    )

    & git @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

if (-not (Test-Path $patchPath)) {
    throw "Missing tracked patch archive: $patchPath"
}

if (Test-Path $targetPath) {
    if (-not $ArchiveExisting) {
        throw "Target already exists: $targetPath. Rerun with -ArchiveExisting to move it into archive first."
    }

    if (-not (Test-Path $archiveRoot)) {
        New-Item -ItemType Directory -Path $archiveRoot | Out-Null
    }

    $timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $leafName = Split-Path -Leaf $targetPath
    $archivePath = Join-Path $archiveRoot "$leafName.$timestamp"
    Move-Item -LiteralPath $targetPath -Destination $archivePath
    Write-Host "Archived existing target to $archivePath"
}

Invoke-Git -Arguments @('clone', $repoUrl, $targetPath)
Invoke-Git -Arguments @('-C', $targetPath, 'checkout', $baseCommit)
Invoke-Git -Arguments @('-C', $targetPath, 'switch', '-c', $restoreBranch)
Invoke-Git -Arguments @('-C', $targetPath, 'am', '--3way', $patchPath)

$headCommit = ((git -C $targetPath rev-parse HEAD) | Out-String).Trim()
$treeHash = ((git -C $targetPath rev-parse "HEAD^{tree}") | Out-String).Trim()
$status = ((git -C $targetPath status --short) | Out-String).Trim()
if ($status) {
    throw "Restored clone is dirty:`n$status"
}

$expectedTree = $expectedTrees[$PatchSet]
if ($treeHash -ne $expectedTree) {
    throw "Restored tree hash $treeHash does not match expected $expectedTree for patch set $PatchSet"
}

Write-Host "Restored Onlook clone at $targetPath"
Write-Host "Patch set: $PatchSet"
Write-Host "Base commit: $baseCommit"
Write-Host "Current commit: $headCommit"
Write-Host "Tree hash: $treeHash"
Write-Host "Current branch: $restoreBranch"
Write-Host ''
Write-Host 'Next steps:'
Write-Host "  ./tools/start-onlook-web.ps1 -OnlookDir $(Split-Path -Leaf $targetPath) -SkipCommitCheck"
