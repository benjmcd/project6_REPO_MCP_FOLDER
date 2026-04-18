param(
    [string]$ProjectUrl,
    [string]$PreviewOrigin,
    [string]$BindHost = '127.0.0.1',
    [int]$OnlookPort = 3011,
    [string]$OnlookDir = 'ext-onlook-fix',
    [int]$ReadyTimeoutSeconds = 300,
    [switch]$LeaveServicesRunning
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$laneRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$smokeScript = Join-Path $laneRoot 'tools\onlook-normalized-smoke.mjs'
$activePairPath = Join-Path $laneRoot 'tools\onlook-active-pair.json'
$startScript = Join-Path $laneRoot 'tools\start-onlook-web.ps1'
$logRoot = Join-Path $laneRoot 'archive\onlook-normalized-smoke'
$runId = '{0}-{1}' -f (Get-Date -Format 'yyyyMMdd-HHmmss'), ([guid]::NewGuid().ToString('N').Substring(0, 8))
$runRoot = Join-Path $logRoot $runId
$ledgerPath = Join-Path $runRoot 'ledger.json'
$backendOut = Join-Path $runRoot 'onlook-backend.out.log'
$backendErr = Join-Path $runRoot 'onlook-backend.err.log'
$webOut = Join-Path $runRoot 'onlook-web.out.log'
$webErr = Join-Path $runRoot 'onlook-web.err.log'
$baseUrl = "http://$BindHost`:$OnlookPort/"
$onlookRoot = Join-Path $laneRoot $OnlookDir
$bunExe = Join-Path $env:USERPROFILE '.bun\bin\bun.exe'
$resolvedProjectUrl = $null
$resolvedPreviewOrigin = $null
$projectUrlSource = $null
$previewOriginSource = $null
$hasExplicitProjectUrl = $PSBoundParameters.ContainsKey('ProjectUrl')
$hasExplicitPreviewOrigin = $PSBoundParameters.ContainsKey('PreviewOrigin')
$routeCoverage = @(
    @{ route = 'Workbench Compare'; expectedPath = '/workbench-compare' },
    @{ route = 'Document Trace'; expectedPath = '/document-trace' }
)
$laneHelperPaths = @(
    'tools/run-onlook-normalized-smoke.ps1',
    'tools/onlook-normalized-smoke.mjs',
    'tools/start-onlook-web.ps1'
)
$runtimeGeneratedPaths = @(
    'apps/web/client/messages/en.d.json.ts',
    'apps/web/client/public/onlook-preload-script.js'
)

function Assert-Path {
    param(
        [string]$Path,
        [string]$Label
    )

    if (-not (Test-Path $Path)) {
        throw "Missing ${Label}: $Path"
    }
}

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

    return $line.Substring($Key.Length + 1)
}

function Get-CsbApiKeyState {
    param([string]$RepoRoot)

    if ($env:CSB_API_KEY) {
        return @{
            source = 'process env'
            status = if ($env:CSB_API_KEY -match 'placeholder|your|replace|demo|example') { 'placeholder' } else { 'present' }
        }
    }

    $clientRoot = Join-Path $RepoRoot 'apps\web\client'
    foreach ($candidate in @('.env.local', '.env')) {
        $path = Join-Path $clientRoot $candidate
        $value = Get-EnvValueFromFile -Path $path -Key 'CSB_API_KEY'
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
            status = if ($value -match 'placeholder|your|replace|demo|example') { 'placeholder' } else { 'present' }
        }
    }

    return @{
        source = 'no configured source'
        status = 'missing'
    }
}

function Test-PortListening {
    param([int]$Port)

    $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return @($listeners).Count -gt 0
}

function Get-PortProcessInfo {
    param([int]$Port)

    $processIds = @(
        Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    )

    $processInfo = @()
    foreach ($processId in $processIds) {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
        if ($process) {
            $processInfo += $process
        }
    }

    return @($processInfo)
}

function Wait-PortListening {
    param(
        [int[]]$Ports,
        [int]$TimeoutSeconds
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $allListening = $true
        foreach ($port in $Ports) {
            if (-not (Test-PortListening -Port $port)) {
                $allListening = $false
                break
            }
        }

        if ($allListening) {
            return
        }

        Start-Sleep -Seconds 2
    }

    throw "Timed out waiting for backend ports to listen: $($Ports -join ', ')"
}

function Wait-PortClosed {
    param(
        [int]$Port,
        [int]$TimeoutSeconds
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (-not (Test-PortListening -Port $Port)) {
            return
        }

        Start-Sleep -Seconds 1
    }

    throw "Timed out waiting for port $Port to close"
}

function Wait-HttpReady {
    param(
        [string]$Url,
        [int]$TimeoutSeconds
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
                return
            }
        } catch {
            Start-Sleep -Seconds 2
            continue
        }

        Start-Sleep -Seconds 2
    }

    throw "Timed out waiting for HTTP readiness at $Url"
}

function Get-GitHead {
    param([string]$RepoRoot)

    try {
        return ((& git -C $RepoRoot rev-parse HEAD) | Out-String).Trim()
    } catch {
        return $null
    }
}

function Get-GitTree {
    param([string]$RepoRoot)

    try {
        return ((& git -C $RepoRoot rev-parse "HEAD^{tree}") | Out-String).Trim()
    } catch {
        return $null
    }
}

function Get-GitDirtyPaths {
    param([string]$RepoRoot)

    try {
        $statusLines = @(& git -C $RepoRoot status --short)
        return @(
            $statusLines |
                Where-Object { $_.Trim() } |
                ForEach-Object { ($_ -replace '^[\sA-Z?!]{1,3}', '').Trim() } |
                Where-Object { $_ }
        )
    } catch {
        return @()
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

function Read-JsonFile {
    param(
        [string]$Path,
        [string]$Label
    )

    Assert-Path $Path $Label
    try {
        return (Get-Content $Path -Raw | ConvertFrom-Json)
    } catch {
        throw "Invalid ${Label}: $Path`n$($_.Exception.Message)"
    }
}

function Get-RuntimeCloneState {
    $runtimeDirtyPaths = @(Get-GitDirtyPaths -RepoRoot $onlookRoot)
    if ($runtimeDirtyPaths.Count -gt 0) {
        $onlyRuntimeGenerated = @($runtimeDirtyPaths | Where-Object { $runtimeGeneratedPaths -notcontains $_ }).Count -eq 0
        if ($onlyRuntimeGenerated -and (Test-LineEndingOnlyDrift -RepoRoot $onlookRoot -RepoPaths $runtimeGeneratedPaths)) {
            $runtimeDirtyPaths = @()
        }
    }

    return @{
        head = Get-GitHead -RepoRoot $onlookRoot
        tree = Get-GitTree -RepoRoot $onlookRoot
        hasLocalDiffPaths = $runtimeDirtyPaths.Count -gt 0
        localDiffPaths = $runtimeDirtyPaths
        localDiffSummary = if ($runtimeDirtyPaths.Count -gt 0) { "$($runtimeDirtyPaths.Count) local diff path(s)" } else { 'clean' }
    }
}

function Get-LaneHelperHashes {
    $hashes = [ordered]@{}

    foreach ($repoPath in $laneHelperPaths) {
        $fullPath = Join-Path $laneRoot ($repoPath -replace '/', '\')
        Assert-Path $fullPath "lane helper file"
        $content = [IO.File]::ReadAllText($fullPath).Replace("`r`n", "`n").Replace("`r", "`n")
        $bytes = [Text.Encoding]::UTF8.GetBytes($content)
        $sha256 = [Security.Cryptography.SHA256]::Create()
        try {
            $hashes[$repoPath] = ([BitConverter]::ToString($sha256.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant()
        } finally {
            $sha256.Dispose()
        }
    }

    return $hashes
}

function Assert-LaneHelperState {
    param(
        [object]$ActivePairState,
        [object]$Ledger,
        [string]$ActivePairPath,
        [string]$CurrentLaneHead
    )

    $helperFiles = $Ledger.scope.lane.helperFiles
    if (-not $helperFiles) {
        if ($ActivePairState.laneHead -ne $CurrentLaneHead) {
            throw "Active pair provenance does not match current lane/runtime state in $ActivePairPath. Provide -ProjectUrl and -PreviewOrigin explicitly."
        }

        return
    }

    $currentHelperHashes = Get-LaneHelperHashes
    $mismatches = @()

    foreach ($property in $helperFiles.PSObject.Properties) {
        $repoPath = [string]$property.Name
        $expectedHash = [string]$property.Value
        if (-not $currentHelperHashes.Contains($repoPath)) {
            $mismatches += "$repoPath (missing locally)"
            continue
        }

        $currentHash = [string]$currentHelperHashes[$repoPath]
        if ($currentHash -ne $expectedHash.ToLowerInvariant()) {
            $mismatches += "$repoPath ($currentHash != $expectedHash)"
        }
    }

    if ($mismatches.Count -gt 0) {
        throw "Active pair helper provenance does not match current lane helper state in $ActivePairPath. Provide -ProjectUrl and -PreviewOrigin explicitly. Mismatches: $($mismatches -join '; ')"
    }
}

function Resolve-LedgerPath {
    param([string]$Path)

    if ([IO.Path]::IsPathRooted($Path)) {
        return $Path
    }

    return (Join-Path $laneRoot ($Path -replace '/', '\'))
}

function Get-RelativeRepoPath {
    param(
        [string]$BasePath,
        [string]$TargetPath
    )

    $baseFull = [IO.Path]::GetFullPath($BasePath).TrimEnd('\') + '\'
    $targetFull = [IO.Path]::GetFullPath($TargetPath)
    $baseUri = [Uri]$baseFull
    $targetUri = [Uri]$targetFull
    return $baseUri.MakeRelativeUri($targetUri).ToString().Replace('\', '/')
}

function Resolve-PairSelection {
    $hasProject = $hasExplicitProjectUrl
    $hasPreview = $hasExplicitPreviewOrigin

    if ($hasProject -xor $hasPreview) {
        throw 'Default invocation requires either both -ProjectUrl and -PreviewOrigin, or an active verified pair file.'
    }

    if ($hasProject -and $hasPreview) {
        return @{
            projectUrl = $ProjectUrl
            previewOrigin = $PreviewOrigin
            projectUrlSource = 'explicit'
            previewOriginSource = 'explicit'
        }
    }

    $state = Read-JsonFile -Path $activePairPath -Label 'active pair state'
    $requiredFields = @(
        'projectUrl',
        'previewOrigin',
        'sourceLedgerPath',
        'verifiedAt',
        'laneHead',
        'runtimeCloneHead',
        'runtimeCloneTree',
        'runtimeCloneHasLocalDiffPaths',
        'runtimeCloneLocalDiffSummary',
        'status',
        'statusReason'
    )

    foreach ($field in $requiredFields) {
        if (-not ($state.PSObject.Properties.Name -contains $field)) {
            throw "Invalid active pair state: missing $field in $activePairPath"
        }
    }

    if ($state.status -ne 'verified-live') {
        throw "No active verified pair available in $activePairPath; status=$($state.status); reason=$($state.statusReason). Provide -ProjectUrl and -PreviewOrigin explicitly."
    }

    $runtimeState = Get-RuntimeCloneState
    $laneHead = Get-GitHead -RepoRoot $laneRoot
    if (
        $state.runtimeCloneTree -ne $runtimeState.tree -or
        [bool]$state.runtimeCloneHasLocalDiffPaths -ne [bool]$runtimeState.hasLocalDiffPaths -or
        $state.runtimeCloneLocalDiffSummary -ne $runtimeState.localDiffSummary
    ) {
        throw "Active pair provenance does not match current lane/runtime state in $activePairPath. Provide -ProjectUrl and -PreviewOrigin explicitly."
    }

    $ledgerPath = Resolve-LedgerPath -Path $state.sourceLedgerPath
    $ledger = Read-JsonFile -Path $ledgerPath -Label 'active pair source ledger'
    if ($ledger.status -ne 'pass') {
        throw "Active pair source ledger is not a passing normalized-smoke artifact: $ledgerPath"
    }

    if (
        $ledger.projectUrl -ne $state.projectUrl -or
        $ledger.previewOrigin -ne $state.previewOrigin -or
        $ledger.scope.lane.head -ne $state.laneHead -or
        $ledger.scope.runtimeClone.head -ne $state.runtimeCloneHead -or
        $ledger.scope.runtimeClone.tree -ne $state.runtimeCloneTree
    ) {
        throw "Active pair source ledger does not match the active pair state in $activePairPath. Provide -ProjectUrl and -PreviewOrigin explicitly."
    }

    Assert-LaneHelperState -ActivePairState $state -Ledger $ledger -ActivePairPath $activePairPath -CurrentLaneHead $laneHead

    return @{
        projectUrl = [string]$state.projectUrl
        previewOrigin = [string]$state.previewOrigin
        projectUrlSource = 'active-verified-pair'
        previewOriginSource = 'active-verified-pair'
    }
}

function Stop-ProcessTree {
    param(
        [object]$Process,
        [string]$Label
    )

    if (-not $Process) {
        return
    }

    $existing = Get-Process -Id $Process.Id -ErrorAction SilentlyContinue
    if (-not $existing) {
        return
    }

    Write-Host "Stopping $Label process tree rooted at PID $($Process.Id)"
    try {
        taskkill /PID $Process.Id /T /F 2>$null | Out-Null
    } catch {
        # Ignore already-exited child-process noise during cleanup.
    }
}

function Get-WrapperFailureClassification {
    param([string]$Message)

    if (
        $Message -like '*Timed out waiting for HTTP readiness*' -or
        $Message -like '*preload helper port 8083*' -or
        $Message -like '*Timed out waiting for port 8083 to close*'
    ) {
        return @{
            bucket = 1
            label = 'host startup / 3011 unavailable'
        }
    }

    return @{
        bucket = 9
        label = 'unclassified normalization/tooling failure'
    }
}

function Get-ScopeRecord {
    param([string]$HostStartMode)

    $repoRoot = Split-Path -Parent (Split-Path -Parent $laneRoot)
    $runtimeState = Get-RuntimeCloneState

    return @{
        lane = @{
            worktreePath = Get-RelativeRepoPath -BasePath $repoRoot -TargetPath $laneRoot
            head = Get-GitHead -RepoRoot $laneRoot
        }
        runtimeClone = @{
            dir = $OnlookDir
            head = $runtimeState.head
            tree = $runtimeState.tree
            hasLocalDiffPaths = $runtimeState.hasLocalDiffPaths
            localDiffPaths = $runtimeState.localDiffPaths
            localDiffSummary = $runtimeState.localDiffSummary
        }
        currentPair = @{
            projectUrl = $resolvedProjectUrl
            previewOrigin = $resolvedPreviewOrigin
            projectUrlSource = if ($projectUrlSource) { $projectUrlSource } else { 'no-active-default' }
            previewOriginSource = if ($previewOriginSource) { $previewOriginSource } else { 'no-active-default' }
        }
        browser = @{
            channel = 'chrome'
            headed = $true
            freshContext = $true
        }
        hostStartMode = $HostStartMode
        routesCovered = $routeCoverage
    }
}

function Write-FailureLedger {
    param(
        [string]$Path,
        [string]$FailureReason,
        [string]$HostStartMode,
        [bool]$StartedBackend,
        [bool]$StartedWeb
    )

    $classification = Get-WrapperFailureClassification -Message $FailureReason
    $ledger = @{
        status = 'fail'
        browser = @{
            channel = 'chrome'
            headed = $true
        }
        projectUrl = $resolvedProjectUrl
        previewOrigin = $resolvedPreviewOrigin
        scope = Get-ScopeRecord -HostStartMode $HostStartMode
        normalization = $null
        routes = @()
        classification = $classification
        failureReason = $FailureReason
        wrapper = @{
            startedBackend = $StartedBackend
            startedWeb = $StartedWeb
        }
    }

    $ledger | ConvertTo-Json -Depth 10 | Set-Content -Path $Path -Encoding utf8
}

Assert-Path $smokeScript 'normalized smoke script'
Assert-Path $startScript 'Onlook startup script'
Assert-Path $onlookRoot 'Onlook workspace root'
Assert-Path $bunExe 'Bun executable'

New-Item -ItemType Directory -Force -Path $runRoot | Out-Null

$startedBackend = $false
$backendProcess = $null
$startedWeb = $false
$webProcess = $null
$hostStartMode = if (Test-PortListening -Port $OnlookPort) { 'host-already-up' } else { 'host-started-by-wrapper' }

try {
    $pairSelection = Resolve-PairSelection
    $resolvedProjectUrl = $pairSelection.projectUrl
    $resolvedPreviewOrigin = $pairSelection.previewOrigin
    $projectUrlSource = $pairSelection.projectUrlSource
    $previewOriginSource = $pairSelection.previewOriginSource

    $csbApiKeyState = Get-CsbApiKeyState -RepoRoot $onlookRoot
    if ($csbApiKeyState.status -ne 'present') {
        throw "Current-project first gate requires a real CSB_API_KEY because sandbox.start must create a browser session for the active sandbox. Found $($csbApiKeyState.status) CSB_API_KEY from $($csbApiKeyState.source)."
    }

    if ((-not (Test-PortListening -Port 54321)) -or (-not (Test-PortListening -Port 54322))) {
        $startedBackend = $true
        $backendProcess = Start-Process -FilePath $bunExe `
            -ArgumentList @('run', 'backend:start') `
            -WorkingDirectory $onlookRoot `
            -RedirectStandardOutput $backendOut `
            -RedirectStandardError $backendErr `
            -PassThru

        Wait-PortListening -Ports @(54321, 54322) -TimeoutSeconds $ReadyTimeoutSeconds
    }

    if (-not (Test-PortListening -Port $OnlookPort)) {
        if (Test-PortListening -Port 8083) {
            $preloadProcesses = @(Get-PortProcessInfo -Port 8083)
            $recoverablePreload = @(
                $preloadProcesses |
                    Where-Object {
                        $_.Name -eq 'bun.exe' -and
                        $_.CommandLine -like '*--watch server/index.ts*'
                    }
            )
            $unexpectedPreload = @(
                $preloadProcesses |
                    Where-Object {
                        $_.Name -ne 'bun.exe' -or
                        $_.CommandLine -notlike '*--watch server/index.ts*'
                    }
            )

            if ($preloadProcesses.Count -gt 0 -and $unexpectedPreload.Count -eq 0) {
                foreach ($preloadProcess in $recoverablePreload) {
                    Stop-ProcessTree -Process (Get-Process -Id $preloadProcess.ProcessId -ErrorAction SilentlyContinue) -Label 'stale preload helper'
                }
                Wait-PortClosed -Port 8083 -TimeoutSeconds 30
            } else {
                $summary = ($preloadProcesses | ForEach-Object {
                    "$($_.Name) [$($_.ProcessId)] $($_.CommandLine)"
                }) -join '; '
                throw "Onlook preload helper port 8083 is already in use by an unrecoverable process: $summary"
            }
        }

        $startedWeb = $true
        $webProcess = Start-Process -FilePath 'powershell.exe' `
            -ArgumentList @(
                '-NoProfile',
                '-ExecutionPolicy',
                'Bypass',
                '-File',
                './tools/start-onlook-web.ps1',
                '-BindHost',
                $BindHost,
                '-Port',
                $OnlookPort.ToString(),
                '-OnlookDir',
                $OnlookDir,
                '-AllowDirty',
                '-SkipCommitCheck'
            ) `
            -WorkingDirectory $laneRoot `
            -RedirectStandardOutput $webOut `
            -RedirectStandardError $webErr `
            -PassThru

        Wait-HttpReady -Url $baseUrl -TimeoutSeconds $ReadyTimeoutSeconds
    }

    Push-Location $laneRoot
    try {
        node ./tools/onlook-normalized-smoke.mjs `
            --project-url $resolvedProjectUrl `
            --project-url-source $projectUrlSource `
            --preview-origin $resolvedPreviewOrigin `
            --preview-origin-source $previewOriginSource `
            --browser-channel chrome `
            --runtime-dir $OnlookDir `
            --host-start-mode $hostStartMode `
            --json-out $ledgerPath

        if ($LASTEXITCODE -ne 0) {
            throw "onlook-normalized-smoke.mjs failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
}
catch {
    if (-not (Test-Path $ledgerPath)) {
        Write-FailureLedger -Path $ledgerPath -FailureReason $_.Exception.Message -HostStartMode $hostStartMode -StartedBackend $startedBackend -StartedWeb $startedWeb
    }
    throw
}
finally {
    if ($startedWeb -and -not $LeaveServicesRunning) {
        Stop-ProcessTree -Process $webProcess -Label 'Onlook web'
    }

    if ($startedBackend -and -not $LeaveServicesRunning) {
        Stop-ProcessTree -Process $backendProcess -Label 'Onlook backend'
    }

    Write-Host "Normalized smoke artifacts: $runRoot"
}
