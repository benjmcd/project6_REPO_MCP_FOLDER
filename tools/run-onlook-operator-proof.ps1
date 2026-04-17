param(
    [string]$AppDir = 'onlook-ui-copy',
    [string]$CanonicalDir = 'onlook-ui',
    [string]$OnlookDir = 'ext-onlook-fix',
    [string]$BindHost = '127.0.0.1',
    [int]$OnlookPort = 3011,
    [int]$ApiPort = 8000,
    [int]$ReadyTimeoutSeconds = 300,
    [switch]$LeaveServicesRunning
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$laneRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$operatorScript = Join-Path $laneRoot 'tools\onlook-operator-proof.mjs'
$wbPrepScript = Join-Path $laneRoot 'tools\validate_wb_prep.py'
$apiStartScript = Join-Path $laneRoot 'tools\start-review-api.ps1'
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

function Assert-Path {
    param(
        [string]$Path,
        [string]$Label
    )

    if (-not (Test-Path $Path)) {
        throw "Missing ${Label}: $Path"
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

function Assert-ReviewApiPopulated {
    param(
        [string]$Url,
        [string[]]$ExpectedRunIds = @()
    )

    $payload = Invoke-RestMethod -Uri $Url -UseBasicParsing -TimeoutSec 15
    if ($null -eq $payload) {
        throw "Review API returned an empty payload at $Url"
    }

    $runs = @($payload.runs)
    if ($runs.Count -lt 1) {
        throw "Review API returned zero runs at $Url"
    }

    $reviewableRuns = @($runs | Where-Object { $_.reviewable -eq $true })
    if ($reviewableRuns.Count -lt 1) {
        throw "Review API returned runs but none were reviewable at $Url"
    }

    $reviewableRunIds = @(
        $reviewableRuns |
            ForEach-Object { [string]$_.run_id } |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    )

    foreach ($expectedRunId in @($ExpectedRunIds | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })) {
        if ($reviewableRunIds -notcontains $expectedRunId) {
            throw "Review API at $Url did not expose expected reviewable run $expectedRunId. Available reviewable runs: $($reviewableRunIds -join ', ')"
        }
    }
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

function Set-EnvValueInFile {
    param(
        [string]$Path,
        [string]$Name,
        [string]$Value
    )

    $originalContent = [System.IO.File]::ReadAllText($Path)
    $updatedContent = if ($originalContent -match ("(?m)^" + [regex]::Escape($Name) + "=")) {
        [regex]::Replace(
            $originalContent,
            "(?m)^" + [regex]::Escape($Name) + "=.*$",
            ($Name + '=' + $Value),
            1
        )
    } else {
        $separator = if ($originalContent.Length -eq 0 -or $originalContent.EndsWith("`r`n") -or $originalContent.EndsWith("`n")) {
            ''
        } else {
            "`r`n"
        }
        $originalContent + $separator + ($Name + '=' + $Value + "`r`n")
    }

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $updatedContent, $utf8NoBom)
    return $originalContent
}

function Restore-FileContent {
    param(
        [string]$Path,
        [string]$Content
    )

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
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
        [pscustomobject]$PrepSummary,
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
            --document-trace-path ([string]$PrepSummary.recommended_urls.baseline_trace) `
            --workbench-path ([string]$PrepSummary.recommended_urls.workbench_compare) `
            --candidate-b-path ([string]$PrepSummary.recommended_urls.candidate_b_trace) `
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
Assert-Path $wbPrepScript 'compare prep validator'
Assert-Path $apiStartScript 'review API start helper'
Assert-Path $onlookStartScript 'Onlook web start helper'
Assert-Path $onlookRoot 'Onlook source clone'
Assert-Path $appRoot 'duplicate sandbox app'
Assert-Path $canonicalRoot 'canonical sandbox app'
Assert-Path $uploadEnvPath 'upload-safe duplicate env'
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

$browserChannel = Resolve-BrowserChannel

Push-Location $laneRoot
try {
    $prepOutput = python ./tools/validate_wb_prep.py | Out-String
    if ($LASTEXITCODE -ne 0) {
        throw "validate_wb_prep.py failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

$prepSummary = $prepOutput | ConvertFrom-Json
if (-not $prepSummary.passed) {
    throw 'validate_wb_prep.py did not return a passing prep summary.'
}

$expectedReviewRunIds = @(
    [string]$prepSummary.selection.baseline_run_id
    [string]$prepSummary.selection.candidate_a_run_id
) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique

$apiUrl = "http://$BindHost`:$ApiPort/api/v1/review/nrc-aps/runs"
$onlookLoginUrl = "http://$BindHost`:$OnlookPort/login"
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("onlook-operator-" + [System.Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tempRoot | Out-Null
$apiOut = Join-Path $tempRoot 'api.out.log'
$apiErr = Join-Path $tempRoot 'api.err.log'
$uiOut = Join-Path $tempRoot 'ui.out.log'
$uiErr = Join-Path $tempRoot 'ui.err.log'

$apiProcess = $null
$uiProcess = $null
$startedSupabase = $false
$reusedOnlookWeb = $false
$originalUploadEnv = $null

try {
    $originalUploadEnv = Set-EnvValueInFile -Path $uploadEnvPath -Name 'NEXT_PUBLIC_REVIEW_API_BASE' -Value ("http://$BindHost`:$ApiPort/api/v1/review/nrc-aps")

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

    if (Test-HttpReady -Url $apiUrl) {
        Write-Host "Reusing review API at $apiUrl"
    } else {
        if (Test-PortListening -Port $ApiPort) {
            throw "Review API port $ApiPort is already listening but did not answer $apiUrl"
        }

        $apiProcess = Start-Process -FilePath 'powershell.exe' `
            -ArgumentList @(
                '-NoProfile',
                '-ExecutionPolicy',
                'Bypass',
                '-File',
                './tools/start-review-api.ps1',
                '-Port',
                $ApiPort
            ) `
            -WorkingDirectory $laneRoot `
            -RedirectStandardOutput $apiOut `
            -RedirectStandardError $apiErr `
            -PassThru

        Wait-HttpReady -Url $apiUrl -TimeoutSeconds $ReadyTimeoutSeconds
    }

    Assert-ReviewApiPopulated -Url $apiUrl -ExpectedRunIds $expectedReviewRunIds

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
            -PrepSummary $prepSummary `
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
                -PrepSummary $prepSummary `
                -ProofFile $proofFile `
                -ProofMarker $proofMarker
        } else {
            throw
        }
    }
}
finally {
    if ($null -ne $originalUploadEnv) {
        Restore-FileContent -Path $uploadEnvPath -Content $originalUploadEnv
    }

    if (-not $LeaveServicesRunning) {
        if ($uiProcess) {
            Stop-ProcessTree -Process $uiProcess -Label 'Onlook web'
        }

        if ($apiProcess) {
            Stop-ProcessTree -Process $apiProcess -Label 'review API'
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
