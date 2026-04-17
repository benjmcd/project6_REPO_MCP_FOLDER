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
$localDevDefaults = @{
    SupabaseUrl = 'http://127.0.0.1:54321'
    DatabaseUrl = 'postgresql://postgres:postgres@127.0.0.1:54322/postgres'
    AnonKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0'
    ServiceRoleKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU'
    PublishableKey = 'sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH'
}
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
    'local-writeback' = 'a2a7672c9241802cd741d6d8fce9b847651c003c'
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

function Set-EnvValue {
    param(
        [string[]]$Lines,
        [string]$Key,
        [string]$Value
    )

    $pattern = '^{0}=' -f [regex]::Escape($Key)
    $updated = @()
    $matched = $false

    foreach ($line in $Lines) {
        if ($line -match $pattern) {
            $updated += "$Key=$Value"
            $matched = $true
        } else {
            $updated += $line
        }
    }

    if (-not $matched) {
        $updated += "$Key=$Value"
    }

    return ,$updated
}

function Ensure-ClientEnv {
    param(
        [string]$RepoRoot
    )

    $envPath = Join-Path $RepoRoot 'apps\web\client\.env'
    if (Test-Path $envPath) {
        Write-Host "Found existing client env: $envPath"
        return
    }

    $templatePath = Join-Path $RepoRoot 'apps\web\client\.env.example'
    if (-not (Test-Path $templatePath)) {
        throw "Missing client env template: $templatePath"
    }

    $lines = Get-Content $templatePath
    $lines = Set-EnvValue -Lines $lines -Key 'NEXT_PUBLIC_SUPABASE_URL' -Value $localDevDefaults.SupabaseUrl
    $lines = Set-EnvValue -Lines $lines -Key 'NEXT_PUBLIC_SUPABASE_ANON_KEY' -Value $localDevDefaults.AnonKey
    $lines = Set-EnvValue -Lines $lines -Key 'NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY' -Value $localDevDefaults.PublishableKey
    $lines = Set-EnvValue -Lines $lines -Key 'SUPABASE_DATABASE_URL' -Value $localDevDefaults.DatabaseUrl
    $lines = Set-EnvValue -Lines $lines -Key 'SUPABASE_SERVICE_ROLE_KEY' -Value $localDevDefaults.ServiceRoleKey
    $lines = Set-EnvValue -Lines $lines -Key 'OPENROUTER_API_KEY' -Value 'local-dev-placeholder'
    $lines = Set-EnvValue -Lines $lines -Key 'CSB_API_KEY' -Value 'local-dev-placeholder'
    $lines = Set-EnvValue -Lines $lines -Key 'NEXT_PUBLIC_SITE_URL' -Value 'http://127.0.0.1:3000'
    $lines = Set-EnvValue -Lines $lines -Key 'NEXT_PUBLIC_FEATURE_COLLABORATION' -Value 'false'
    Set-Content -Path $envPath -Value $lines

    Write-Host "Bootstrapped client env: $envPath"
    Write-Warning 'Client env uses local demo Supabase values and placeholder OpenRouter/Codesandbox keys. Replace CSB_API_KEY before importing new projects or creating sandboxes.'
}

function Ensure-DbEnv {
    param(
        [string]$RepoRoot
    )

    $envPath = Join-Path $RepoRoot 'packages\db\.env'
    if (Test-Path $envPath) {
        Write-Host "Found existing db env: $envPath"
        return
    }

    $templatePath = Join-Path $RepoRoot 'packages\db\.env.example'
    if (-not (Test-Path $templatePath)) {
        throw "Missing db env template: $templatePath"
    }

    $lines = Get-Content $templatePath
    $lines = Set-EnvValue -Lines $lines -Key 'SUPABASE_URL' -Value $localDevDefaults.SupabaseUrl
    $lines = Set-EnvValue -Lines $lines -Key 'SUPABASE_SERVICE_ROLE_KEY' -Value $localDevDefaults.ServiceRoleKey
    $lines = Set-EnvValue -Lines $lines -Key 'SUPABASE_DATABASE_URL' -Value $localDevDefaults.DatabaseUrl
    Set-Content -Path $envPath -Value $lines

    Write-Host "Bootstrapped db env: $envPath"
}

function Ensure-BunDependencies {
    param(
        [string]$RepoRoot
    )

    $nodeModulesPath = Join-Path $RepoRoot 'node_modules'
    if (Test-Path $nodeModulesPath) {
        Write-Host "Found existing dependencies: $nodeModulesPath"
        return
    }

    $bunExe = Join-Path $env:USERPROFILE '.bun\bin\bun.exe'
    if (-not (Test-Path $bunExe)) {
        throw "Missing Bun executable at: $bunExe"
    }

    Write-Host "Installing Onlook dependencies in $RepoRoot"
    Push-Location $RepoRoot
    try {
        & $bunExe install
        if ($LASTEXITCODE -ne 0) {
            throw "bun install failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }

    if (-not (Test-Path $nodeModulesPath)) {
        throw "Dependencies were not materialized at $nodeModulesPath"
    }

    $postInstallStatus = ((git -C $RepoRoot status --short) | Out-String).Trim()
    if ($postInstallStatus) {
        $statusLines = @($postInstallStatus -split "`r?`n" | Where-Object { $_ })
        $nonLockDrift = @($statusLines | Where-Object { $_ -notmatch '^\s*[A-Z?]{1,2}\s+bun\.lock$' })

        if ($nonLockDrift.Count -gt 0) {
            throw "Dependency install left tracked drift:`n$postInstallStatus"
        }

        Invoke-Git -Arguments @('-C', $RepoRoot, 'restore', '--worktree', '--source=HEAD', '--', 'bun.lock')
        $postInstallStatus = ((git -C $RepoRoot status --short) | Out-String).Trim()
        if ($postInstallStatus) {
            throw "Dependency install still left tracked drift after bun.lock restore:`n$postInstallStatus"
        }
    }

    Write-Host "Installed dependencies: $nodeModulesPath"
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

Ensure-ClientEnv -RepoRoot $targetPath
Ensure-DbEnv -RepoRoot $targetPath
Ensure-BunDependencies -RepoRoot $targetPath

Write-Host "Restored Onlook clone at $targetPath"
Write-Host "Patch set: $PatchSet"
Write-Host "Base commit: $baseCommit"
Write-Host "Current commit: $headCommit"
Write-Host "Tree hash: $treeHash"
Write-Host "Current branch: $restoreBranch"
Write-Host ''
Write-Host 'Next steps:'
Write-Host "  ./tools/start-onlook-web.ps1 -OnlookDir $(Split-Path -Leaf $targetPath)"
Write-Host "  Edit $(Join-Path (Split-Path -Leaf $targetPath) 'apps\\web\\client\\.env') if you need a real CSB_API_KEY for import and sandbox creation."
