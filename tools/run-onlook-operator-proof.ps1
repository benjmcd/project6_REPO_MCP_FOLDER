param(
    [string]$AppDir = 'onlook-ui-copy',
    [string]$CanonicalDir = 'onlook-ui',
    [string]$OnlookDir = 'ext-onlook-fix',
    [string]$BindHost = '127.0.0.1',
    [int]$OnlookPort = 3011,
    [int]$ReadyTimeoutSeconds = 300,
    [switch]$LeaveServicesRunning
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$laneRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$operatorScript = Join-Path $laneRoot 'tools\onlook-operator-proof.mjs'
$onlookStartScript = Join-Path $laneRoot 'tools\start-onlook-web.ps1'
$onlookRoot = Join-Path $laneRoot $OnlookDir
$appRoot = if ([System.IO.Path]::IsPathRooted($AppDir)) {
    [System.IO.Path]::GetFullPath($AppDir)
} else {
    [System.IO.Path]::GetFullPath((Join-Path $laneRoot $AppDir))
}
$canonicalRoot = if ([System.IO.Path]::IsPathRooted($CanonicalDir)) {
    [System.IO.Path]::GetFullPath($CanonicalDir)
} else {
    [System.IO.Path]::GetFullPath((Join-Path $laneRoot $CanonicalDir))
}
$proofFile = 'app/page.tsx'
$proofMarker = 'onlook-operator-proof-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$uploadEnvPath = Join-Path $appRoot '.env'
$fixturePath = Join-Path $canonicalRoot 'data\fixture.json'
$duplicateFixturePath = Join-Path $appRoot 'data\fixture.json'
$duplicateApiRoutePath = Join-Path $appRoot 'app\api\[...slug]\route.ts'

function Assert-Path {
    param(
        [string]$Path,
        [string]$Label
    )

    if (-not (Test-Path $Path)) {
        throw "Missing ${Label}: $Path"
    }
}

function Assert-LiteralPath {
    param(
        [string]$Path,
        [string]$Label
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Missing ${Label}: $Path"
    }
}

function Get-EnvValue {
    param(
        [string]$Path,
        [string]$Name
    )

    foreach ($line in Get-Content -LiteralPath $Path) {
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

function Assert-DuplicateImportContract {
    param(
        [string]$AppRoot,
        [string]$UploadEnvPath,
        [string]$FixturePath,
        [string]$ApiRoutePath
    )

    Assert-LiteralPath $UploadEnvPath 'upload-safe duplicate env'
    Assert-LiteralPath $FixturePath 'duplicate fixture snapshot'
    Assert-LiteralPath $ApiRoutePath 'duplicate fixture API route'

    $publicApiBase = Get-EnvValue -Path $UploadEnvPath -Name 'NEXT_PUBLIC_REVIEW_API_BASE'
    if ($publicApiBase -ne '/api/v1/review/nrc-aps') {
        throw "Duplicate upload env must use the same-origin fixture API base. Expected /api/v1/review/nrc-aps, found: $publicApiBase"
    }

    $fixtureFile = Get-Item -LiteralPath $FixturePath
    if ($fixtureFile.Length -gt 10MB) {
        throw "Duplicate fixture snapshot exceeds the current Onlook import size ceiling: $($fixtureFile.Length) bytes at $FixturePath"
    }
}

function Test-PortListening {
    param([int]$Port)

    $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return @($listeners).Count -gt 0
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

    throw "Timed out waiting for ports to listen: $($Ports -join ', ')"
}

function Test-HttpReady {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 400
    } catch {
        return $false
    }
}

function Wait-HttpReady {
    param(
        [string]$Url,
        [int]$TimeoutSeconds
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-HttpReady -Url $Url) {
            return
        }

        Start-Sleep -Seconds 2
    }

    throw "Timed out waiting for HTTP readiness at $Url"
}

function Stop-ProcessTree {
    param(
        [System.Diagnostics.Process]$Process,
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
    taskkill /PID $Process.Id /T /F | Out-Null
}

function Get-PortOwnerIds {
    param([int[]]$Ports)

    return @(
        Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
            Where-Object { $Ports -contains $_.LocalPort } |
            Select-Object -ExpandProperty OwningProcess -Unique
    )
}

function Get-ProcessCommandLine {
    param([int]$ProcessId)

    return (
        Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty CommandLine -ErrorAction SilentlyContinue
    )
}

function Test-OnlookWebOwnerMatchesExpectedClone {
    param(
        [int]$Port,
        [string]$ExpectedRoot
    )

    foreach ($ownerId in (Get-PortOwnerIds -Ports @($Port))) {
        $commandLine = Get-ProcessCommandLine -ProcessId $ownerId
        if ($commandLine -and $commandLine.IndexOf($ExpectedRoot, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
            return $true
        }
    }

    return $false
}

function Get-FixtureRoutes {
    param([string]$Path)

    $fixture = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    if (-not $fixture.routes) {
        throw "Fixture file does not expose route metadata: $Path"
    }

    return $fixture.routes
}

function Stop-ListeningPortProcessTrees {
    param(
        [int[]]$Ports,
        [string]$Label
    )

    foreach ($ownerId in (Get-PortOwnerIds -Ports $Ports)) {
        $ownerProcess = Get-Process -Id $ownerId -ErrorAction SilentlyContinue
        if ($ownerProcess) {
            Stop-ProcessTree -Process $ownerProcess -Label "$Label (PID $ownerId)"
        }
    }
}

function Start-OnlookWebProcess {
    param(
        [string]$LaneRoot,
        [string]$OnlookDir,
        [int]$OnlookPort,
        [int]$ReadyTimeoutSeconds,
        [string]$UiOut,
        [string]$UiErr,
        [string]$OnlookLoginUrl
    )

    $process = Start-Process -FilePath 'powershell.exe' `
        -ArgumentList @(
            '-NoProfile',
            '-ExecutionPolicy',
            'Bypass',
            '-File',
            './tools/start-onlook-web.ps1',
            '-OnlookDir',
            $OnlookDir,
            '-Port',
            $OnlookPort
        ) `
        -WorkingDirectory $LaneRoot `
        -RedirectStandardOutput $UiOut `
        -RedirectStandardError $UiErr `
        -PassThru

    Wait-HttpReady -Url $OnlookLoginUrl -TimeoutSeconds $ReadyTimeoutSeconds
    return $process
}

function Invoke-OperatorProofNode {
    param(
        [string]$LaneRoot,
        [string]$BindHost,
        [int]$OnlookPort,
        [string]$AppRoot,
        [string]$CanonicalRoot,
        [string]$BrowserChannel,
        [string]$DocumentTracePath,
        [string]$WorkbenchPath,
        [string]$CandidateBPath,
        [string]$ProofFile,
        [string]$ProofMarker
    )

    Push-Location $LaneRoot
    try {
        node ./tools/onlook-operator-proof.mjs `
            --base-url ("http://$BindHost`:$OnlookPort") `
            --app-dir $AppRoot `
            --canonical-dir $CanonicalRoot `
            --browser-channel $BrowserChannel `
            --document-trace-path $DocumentTracePath `
            --workbench-path $WorkbenchPath `
            --candidate-b-path $CandidateBPath `
            --proof-file $ProofFile `
            --proof-marker $ProofMarker
        if ($LASTEXITCODE -ne 0) {
            throw "onlook-operator-proof.mjs failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
}

function Resolve-BrowserChannel {
    $edgePath = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
    $chromePath = 'C:\Program Files\Google\Chrome\Application\chrome.exe'

    if (Test-Path $edgePath) {
        return 'msedge'
    }

    if (Test-Path $chromePath) {
        return 'chrome'
    }

    throw 'Missing supported system browser. Install Microsoft Edge or Google Chrome before running the Onlook operator proof.'
}

Assert-Path $operatorScript 'operator proof script'
Assert-Path $onlookStartScript 'Onlook web start helper'
Assert-Path $onlookRoot 'Onlook source clone'
Assert-Path $appRoot 'duplicate sandbox app'
Assert-Path $canonicalRoot 'canonical sandbox app'
Assert-Path $fixturePath 'sandbox fixture snapshot'
Assert-Path (Join-Path $appRoot $proofFile) 'duplicate proof file'
Assert-Path (Join-Path $canonicalRoot $proofFile) 'canonical proof file'

if (-not $appRoot.StartsWith($laneRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Duplicate sandbox app must stay inside the lane root: $laneRoot"
}

if (-not $canonicalRoot.StartsWith($laneRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Canonical sandbox app must stay inside the lane root: $laneRoot"
}

if ($appRoot -eq $canonicalRoot) {
    throw 'Operator proof must target a duplicate sandbox app, not canonical onlook-ui/.'
}

Assert-DuplicateImportContract `
    -AppRoot $appRoot `
    -UploadEnvPath $uploadEnvPath `
    -FixturePath $duplicateFixturePath `
    -ApiRoutePath $duplicateApiRoutePath

$browserChannel = Resolve-BrowserChannel
$fixtureRoutes = Get-FixtureRoutes -Path $fixturePath
$documentTracePath = [string]$fixtureRoutes.document_trace
$workbenchPath = [string]$fixtureRoutes.workbench_compare
$candidateBPath = [string]$fixtureRoutes.candidate_b_trace
$onlookLoginUrl = "http://$BindHost`:$OnlookPort/login"
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("onlook-operator-" + [System.Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tempRoot | Out-Null
$uiOut = Join-Path $tempRoot 'ui.out.log'
$uiErr = Join-Path $tempRoot 'ui.err.log'

$uiProcess = $null
$startedSupabase = $false
$reusedOnlookWeb = $false

try {
    if (-not ((Test-PortListening -Port 54321) -and (Test-PortListening -Port 54322))) {
        Write-Host "Starting local Onlook backend stack from $OnlookDir"
        Push-Location $onlookRoot
        try {
            cmd /d /c bun backend:start
            if ($LASTEXITCODE -ne 0) {
                throw "bun backend:start failed with exit code $LASTEXITCODE"
            }
        }
        finally {
            Pop-Location
        }

        Wait-PortListening -Ports @(54321, 54322) -TimeoutSeconds $ReadyTimeoutSeconds
        $startedSupabase = $true
    }

    if (Test-HttpReady -Url $onlookLoginUrl) {
        if (-not (Test-OnlookWebOwnerMatchesExpectedClone -Port $OnlookPort -ExpectedRoot $onlookRoot)) {
            throw "Onlook web at $onlookLoginUrl did not appear to belong to $OnlookDir at $onlookRoot. Stop the conflicting listener before running the operator proof."
        }

        Write-Host "Reusing local Onlook web at $onlookLoginUrl"
        $reusedOnlookWeb = $true
    } else {
        if (Test-PortListening -Port $OnlookPort) {
            throw "Onlook web port $OnlookPort is already listening but did not answer $onlookLoginUrl"
        }

        $uiProcess = Start-OnlookWebProcess `
            -LaneRoot $laneRoot `
            -OnlookDir $OnlookDir `
            -OnlookPort $OnlookPort `
            -ReadyTimeoutSeconds $ReadyTimeoutSeconds `
            -UiOut $uiOut `
            -UiErr $uiErr `
            -OnlookLoginUrl $onlookLoginUrl
    }

    try {
        Invoke-OperatorProofNode `
            -LaneRoot $laneRoot `
            -BindHost $BindHost `
            -OnlookPort $OnlookPort `
            -AppRoot $appRoot `
            -CanonicalRoot $canonicalRoot `
            -BrowserChannel $browserChannel `
            -DocumentTracePath $documentTracePath `
            -WorkbenchPath $workbenchPath `
            -CandidateBPath $candidateBPath `
            -ProofFile $proofFile `
            -ProofMarker $proofMarker
    }
    catch {
        if ($reusedOnlookWeb) {
            Write-Warning "Operator proof failed while reusing local Onlook web. Restarting the expected clone once and retrying."
            Stop-ListeningPortProcessTrees -Ports @($OnlookPort, 8083) -Label 'stale Onlook runtime'
            $uiProcess = Start-OnlookWebProcess `
                -LaneRoot $laneRoot `
                -OnlookDir $OnlookDir `
                -OnlookPort $OnlookPort `
                -ReadyTimeoutSeconds $ReadyTimeoutSeconds `
                -UiOut $uiOut `
                -UiErr $uiErr `
                -OnlookLoginUrl $onlookLoginUrl

            Invoke-OperatorProofNode `
                -LaneRoot $laneRoot `
                -BindHost $BindHost `
                -OnlookPort $OnlookPort `
                -AppRoot $appRoot `
                -CanonicalRoot $canonicalRoot `
                -BrowserChannel $browserChannel `
                -DocumentTracePath $documentTracePath `
                -WorkbenchPath $workbenchPath `
                -CandidateBPath $candidateBPath `
                -ProofFile $proofFile `
                -ProofMarker $proofMarker
        } else {
            throw
        }
    }
}
finally {
    if (-not $LeaveServicesRunning) {
        if ($uiProcess) {
            Stop-ProcessTree -Process $uiProcess -Label 'Onlook web'
        }

        if ($startedSupabase) {
            Write-Host "Stopping local Onlook backend stack from $OnlookDir"
            Push-Location $onlookRoot
            try {
                cmd /d /c bun --filter @onlook/backend stop
            }
            finally {
                Pop-Location
            }
        }
    }

    Write-Host "Operator proof logs: $tempRoot"
}
