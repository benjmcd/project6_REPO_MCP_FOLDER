param(
    [string]$TargetDir = 'onlook-ui-copy',
    [ValidateSet('full', 'stat', 'name-only')]
    [string]$Mode = 'full'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$laneRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$sourceRoot = (Resolve-Path (Join-Path $laneRoot 'onlook-ui')).Path
$targetPath = if ([System.IO.Path]::IsPathRooted($TargetDir)) {
    [System.IO.Path]::GetFullPath($TargetDir)
} else {
    [System.IO.Path]::GetFullPath((Join-Path $laneRoot $TargetDir))
}
$skipDirs = @('.next', 'node_modules')
$skipFiles = @('.env.local')

function Get-RelativeRepoPath {
    param(
        [string]$RootPath,
        [string]$FullPath
    )

    return $FullPath.Substring($RootPath.Length).TrimStart('\', '/').Replace('\', '/')
}

function Get-FilteredFiles {
    param([string]$RootPath)

    $result = @{}
    foreach ($file in Get-ChildItem $RootPath -Recurse -Force -File) {
        $relativePath = Get-RelativeRepoPath -RootPath $RootPath -FullPath $file.FullName
        $segments = @($relativePath -split '/')
        if (@($segments | Where-Object { $skipDirs -contains $_ }).Count -gt 0) {
            continue
        }
        if ($skipFiles -contains $file.Name) {
            continue
        }

        $result[$relativePath] = $file.FullName
    }

    return $result
}

if (-not $targetPath.StartsWith($laneRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Duplicate target must stay inside the lane root: $laneRoot"
}

if (-not (Test-Path $sourceRoot)) {
    throw "Missing canonical sandbox source: $sourceRoot"
}

if (-not (Test-Path $targetPath)) {
    throw "Missing duplicate target: $targetPath"
}

if ($sourceRoot -eq $targetPath) {
    throw 'Duplicate target matches canonical onlook-ui; choose a separate target directory.'
}

$sourceFiles = Get-FilteredFiles -RootPath $sourceRoot
$targetFiles = Get-FilteredFiles -RootPath $targetPath
$allPaths = @(
    $sourceFiles.Keys
    $targetFiles.Keys
) | Sort-Object -Unique

$changes = @()
foreach ($relativePath in $allPaths) {
    $sourceExists = $sourceFiles.ContainsKey($relativePath)
    $targetExists = $targetFiles.ContainsKey($relativePath)

    if (-not $sourceExists) {
        $changes += [pscustomobject]@{
            Change = 'added'
            Path = $relativePath
            Source = $null
            Target = $targetFiles[$relativePath]
        }
        continue
    }

    if (-not $targetExists) {
        $changes += [pscustomobject]@{
            Change = 'removed'
            Path = $relativePath
            Source = $sourceFiles[$relativePath]
            Target = $null
        }
        continue
    }

    $sourceHash = (Get-FileHash -LiteralPath $sourceFiles[$relativePath] -Algorithm SHA256).Hash
    $targetHash = (Get-FileHash -LiteralPath $targetFiles[$relativePath] -Algorithm SHA256).Hash
    if ($sourceHash -ne $targetHash) {
        $changes += [pscustomobject]@{
            Change = 'modified'
            Path = $relativePath
            Source = $sourceFiles[$relativePath]
            Target = $targetFiles[$relativePath]
        }
    }
}

if ($changes.Count -eq 0) {
    Write-Host 'No meaningful duplicate-to-canonical differences found.'
    Write-Host ''
    Write-Host 'Promotion boundary:'
    Write-Host '  1. Review duplicate-to-canonical sandbox changes here.'
    Write-Host '  2. Port approved changes into onlook-ui/ through normal repo review.'
    Write-Host '  3. Treat any later move into backend/app/review_ui/static/* as a separate explicit decision.'
    return
}

switch ($Mode) {
    'name-only' {
        $changes | ForEach-Object { Write-Output $_.Path }
    }
    'stat' {
        foreach ($change in $changes) {
            Write-Output ('{0,-8} {1}' -f $change.Change.ToUpperInvariant(), $change.Path)
        }
    }
    'full' {
        foreach ($change in $changes) {
            Write-Host ''
            Write-Host ('=== {0} {1} ===' -f $change.Change.ToUpperInvariant(), $change.Path)
            if ($change.Change -ne 'modified') {
                continue
            }

            & git diff --no-index --no-ext-diff --no-color --ignore-cr-at-eol -- $change.Source $change.Target
            if ($LASTEXITCODE -gt 1) {
                throw "git diff failed for $($change.Path) with exit code $LASTEXITCODE"
            }
        }
    }
}

Write-Host ''
Write-Host 'Promotion boundary:'
Write-Host '  1. Review duplicate-to-canonical sandbox changes here.'
Write-Host '  2. Port approved changes into onlook-ui/ through normal repo review.'
Write-Host '  3. Treat any later move into backend/app/review_ui/static/* as a separate explicit decision.'
