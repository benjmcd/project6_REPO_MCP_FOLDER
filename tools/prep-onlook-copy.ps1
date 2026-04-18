param(
    [string]$TargetDir = 'onlook-ui-copy',
    [switch]$CopyLocalEnv,
    [switch]$ArchiveExisting,
    [switch]$AllowDirtySource,
    [switch]$AllowVisibleTarget,
    [ValidateSet('none', 'core', 'full')]
    [string]$RunSmokeProfile = 'none'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$laneRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$targetPath = if ([System.IO.Path]::IsPathRooted($TargetDir)) {
    [System.IO.Path]::GetFullPath($TargetDir)
} else {
    [System.IO.Path]::GetFullPath((Join-Path $laneRoot $TargetDir))
}
$targetName = $targetPath.Substring($laneRoot.Length).TrimStart('\', '/')
$targetIgnorePath = ($targetName.TrimEnd('\', '/')) + '/'
$uploadEnvPath = Join-Path $targetPath '.env'

function Get-EnvValue {
    param(
        [string]$Path,
        [string]$Name
    )

    if (-not (Test-Path $Path)) {
        return $null
    }

    foreach ($line in Get-Content $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#')) {
            continue
        }

        if ($trimmed -match ('^{0}=(.*)$' -f [regex]::Escape($Name))) {
            return $Matches[1]
        }
    }

    return $null
}

function Invoke-Checked {
    param(
        [string]$Label,
        [scriptblock]$Command
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

if (-not $targetPath.StartsWith($laneRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Duplicate target must stay inside the lane root: $laneRoot"
}

Push-Location $laneRoot
try {
    & git check-ignore --quiet -- $targetIgnorePath
    $isIgnoredTarget = $LASTEXITCODE -eq 0
    if (-not $AllowVisibleTarget -and -not $isIgnoredTarget) {
        throw "Duplicate target $targetName is not git-ignored. Use the default ignored target or rerun with -AllowVisibleTarget if you intentionally want a visible scratch tree."
    }

    $copyArgs = @(
        '-NoProfile',
        '-ExecutionPolicy',
        'Bypass',
        '-File',
        './tools/copy-onlook-ui.ps1',
        '-TargetDir',
        $TargetDir
    )

    if ($CopyLocalEnv) {
        $copyArgs += '-CopyLocalEnv'
    }
    if ($ArchiveExisting) {
        $copyArgs += '-ArchiveExisting'
    }
    if ($AllowDirtySource) {
        $copyArgs += '-AllowDirtySource'
    }

    Invoke-Checked -Label 'copy-onlook-ui.ps1' -Command {
        powershell.exe @copyArgs
    }

    $publicReviewApiBase = Get-EnvValue -Path (Join-Path $targetPath '.env.example') -Name 'NEXT_PUBLIC_REVIEW_API_BASE'
    if (-not $publicReviewApiBase) {
        $publicReviewApiBase = Get-EnvValue -Path (Join-Path $targetPath '.env.local') -Name 'NEXT_PUBLIC_REVIEW_API_BASE'
    }
    if ($publicReviewApiBase) {
        Set-Content -LiteralPath $uploadEnvPath -Value @(
            '# Upload-safe sandbox env for Onlook import.'
            '# Keep this limited to public variables only.'
            ('NEXT_PUBLIC_REVIEW_API_BASE={0}' -f $publicReviewApiBase)
            ''
        )
    }

    Push-Location $targetPath
    try {
        Invoke-Checked -Label 'npm install' -Command { npm install }
        Invoke-Checked -Label 'npm run lint' -Command { npm run lint }
        Invoke-Checked -Label 'npm run build' -Command { npm run build }
    }
    finally {
        Pop-Location
    }

    if ($RunSmokeProfile -ne 'none') {
        $smokeArgs = @(
            '-NoProfile',
            '-ExecutionPolicy',
            'Bypass',
            '-File',
            './tools/run-onlook-sandbox-smoke.ps1',
            '-Profile',
            $RunSmokeProfile,
            '-AppDir',
            $TargetDir
        )

        Invoke-Checked -Label 'run-onlook-sandbox-smoke.ps1' -Command {
            powershell.exe @smokeArgs
        }
    }
}
finally {
    Pop-Location
}

Write-Host "Prepared duplicate sandbox target: $targetPath"
Write-Host "Validated local install, lint, and build."
if (Test-Path $uploadEnvPath) {
    Write-Host "Materialized upload-safe .env for CodeSandbox import: $uploadEnvPath"
}
if ($RunSmokeProfile -ne 'none') {
    Write-Host "Validated browser smoke profile: $RunSmokeProfile"
}
Write-Host ''
Write-Host 'Next steps:'
Write-Host "  ./tools/diff-onlook-copy.ps1 -TargetDir $TargetDir"
Write-Host '  ./tools/start-onlook-web.ps1'
Write-Host "  Import $TargetDir into Onlook for duplicate-target editing"
Write-Host '  If you intentionally use a localhost review API override, start ./tools/start-review-api.ps1 before import or smoke.'
