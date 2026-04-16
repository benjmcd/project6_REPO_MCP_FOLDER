param(
    [string]$TargetDir = 'onlook-ui-copy',
    [switch]$CopyLocalEnv,
    [switch]$ArchiveExisting,
    [switch]$AllowDirtySource
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$laneRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$sourceRoot = (Resolve-Path (Join-Path $laneRoot 'onlook-ui')).Path
$targetPath = if ([System.IO.Path]::IsPathRooted($TargetDir)) {
    $TargetDir
} else {
    Join-Path $laneRoot $TargetDir
}
$targetPath = [System.IO.Path]::GetFullPath($targetPath)
$archiveRoot = Join-Path $laneRoot 'archive'
$skipDirs = @('.git', '.next', 'node_modules')
$copyLocalEnvPath = Join-Path $sourceRoot '.env.local'
$sourceStatus = ((& git -C $laneRoot status --short --untracked-files=all -- onlook-ui) | Out-String).Trim()

function Copy-Tree {
    param(
        [string]$SourceDir,
        [string]$DestDir
    )

    if (-not (Test-Path $DestDir)) {
        New-Item -ItemType Directory -Path $DestDir | Out-Null
    }

    foreach ($entry in Get-ChildItem $SourceDir -Force) {
        if ($entry.PSIsContainer) {
            if ($skipDirs -contains $entry.Name) {
                continue
            }

            Copy-Tree -SourceDir $entry.FullName -DestDir (Join-Path $DestDir $entry.Name)
            continue
        }

        if ($entry.Name -eq '.env.local' -and -not $CopyLocalEnv) {
            continue
        }

        Copy-Item -LiteralPath $entry.FullName -Destination (Join-Path $DestDir $entry.Name) -Force
    }
}

if (-not (Test-Path $sourceRoot)) {
    throw "Missing sandbox source: $sourceRoot"
}

if (-not $AllowDirtySource -and $sourceStatus) {
    throw "Sandbox source onlook-ui is dirty:`n$sourceStatus`nCommit or stash those changes first, or rerun with -AllowDirtySource if you intentionally want to duplicate an in-progress tree."
}

if (Test-Path $targetPath) {
    if (-not $ArchiveExisting) {
        throw "Target already exists: $targetPath. Rerun with -ArchiveExisting to move it into archive first."
    }

    if (-not (Test-Path $archiveRoot)) {
        New-Item -ItemType Directory -Path $archiveRoot | Out-Null
    }

    $timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $targetName = Split-Path -Leaf $targetPath
    $archivePath = Join-Path $archiveRoot "$targetName.$timestamp"
    Move-Item -LiteralPath $targetPath -Destination $archivePath
    Write-Host "Archived existing target to $archivePath"
}

Copy-Tree -SourceDir $sourceRoot -DestDir $targetPath

if (-not $CopyLocalEnv -and (Test-Path (Join-Path $sourceRoot '.env.example'))) {
    Copy-Item -LiteralPath (Join-Path $sourceRoot '.env.example') -Destination (Join-Path $targetPath '.env.example') -Force
}

Write-Host "Copied sandbox app from $sourceRoot"
Write-Host "Copied sandbox app to   $targetPath"

if ($CopyLocalEnv -and (Test-Path $copyLocalEnvPath)) {
    Write-Host 'Copied .env.local into the duplicate.'
} else {
    Write-Host 'Skipped .env.local by default. Use -CopyLocalEnv if the duplicate should point at the same local review API.'
}

Write-Host ''
Write-Host 'Next steps:'
Write-Host "  Set-Location $targetPath"
Write-Host '  npm install'
Write-Host '  npm run lint'
Write-Host '  npm run build'
