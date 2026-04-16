param(
    [ValidateSet('core', 'full')]
    [string]$Profile = 'full',
    [string]$BindHost = '127.0.0.1',
    [int]$UiPort = 3007,
    [int]$ApiPort = 8000,
    [int]$ReadyTimeoutSeconds = 180
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$laneRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$onlookUiRoot = Join-Path $laneRoot 'onlook-ui'
$smokeScript = Join-Path $laneRoot 'tools\onlook-sandbox-smoke.mjs'
$wbPrepScript = Join-Path $laneRoot 'tools\validate_wb_prep.py'
$apiStartScript = Join-Path $laneRoot 'tools\start-review-api.ps1'

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
            Start-Sleep -Milliseconds 800
            continue
        }

        Start-Sleep -Milliseconds 800
    }

    throw "Timed out waiting for HTTP readiness at $Url"
}

function Stop-ProcessTree {
    param(
        [int]$ProcessId,
        [string]$Label
    )

    $existing = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if (-not $existing) {
        return
    }

    Write-Host "Stopping $Label process tree rooted at PID $ProcessId"
    taskkill /PID $ProcessId /T /F | Out-Null
}

Assert-Path $onlookUiRoot 'sandbox app root'
Assert-Path $smokeScript 'sandbox smoke script'
Assert-Path $wbPrepScript 'compare prep validator'
Assert-Path $apiStartScript 'review API start helper'

if (Test-PortListening -Port $UiPort) {
    throw "Sandbox UI port $UiPort is already listening. Stop the conflicting listener before running this smoke harness."
}

if (Test-PortListening -Port $ApiPort) {
    throw "Review API port $ApiPort is already listening. Stop the conflicting listener before running this smoke harness."
}

if ($Profile -eq 'full') {
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

    $documentTracePath = [string]$prepSummary.recommended_urls.baseline_trace
    $workbenchPath = [string]$prepSummary.recommended_urls.workbench_compare
    $candidateBPath = [string]$prepSummary.recommended_urls.candidate_b_trace
} else {
    $documentTracePath = '/document-trace'
    $workbenchPath = '/workbench-compare'
    $candidateBPath = '/candidate-b-trace'
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("onlook-smoke-" + [System.Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tempRoot | Out-Null

$apiOut = Join-Path $tempRoot 'api.out.log'
$apiErr = Join-Path $tempRoot 'api.err.log'
$uiOut = Join-Path $tempRoot 'ui.out.log'
$uiErr = Join-Path $tempRoot 'ui.err.log'

$apiProcess = $null
$uiProcess = $null
$smokeUrl = "http://$BindHost`:$UiPort"

try {
    $apiProcess = Start-Process -FilePath 'powershell.exe' `
        -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', './tools/start-review-api.ps1') `
        -WorkingDirectory $laneRoot `
        -RedirectStandardOutput $apiOut `
        -RedirectStandardError $apiErr `
        -PassThru

    Wait-HttpReady -Url "http://$BindHost`:$ApiPort/api/v1/review/nrc-aps/runs" -TimeoutSeconds $ReadyTimeoutSeconds

    $uiProcess = Start-Process -FilePath 'cmd.exe' `
        -ArgumentList @('/d', '/c', 'npm run dev -- --hostname ' + $BindHost + ' --port ' + $UiPort) `
        -WorkingDirectory $onlookUiRoot `
        -RedirectStandardOutput $uiOut `
        -RedirectStandardError $uiErr `
        -PassThru

    Wait-HttpReady -Url $smokeUrl -TimeoutSeconds $ReadyTimeoutSeconds

    Push-Location $laneRoot
    try {
        node ./tools/onlook-sandbox-smoke.mjs --base-url $smokeUrl --profile $Profile --document-trace-path $documentTracePath --workbench-path $workbenchPath --candidate-b-path $candidateBPath
        if ($LASTEXITCODE -ne 0) {
            throw "onlook-sandbox-smoke.mjs failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
}
finally {
    if ($uiProcess) {
        Stop-ProcessTree -ProcessId $uiProcess.Id -Label 'sandbox UI'
    }

    if ($apiProcess) {
        Stop-ProcessTree -ProcessId $apiProcess.Id -Label 'review API'
    }

    foreach ($port in @($UiPort, $ApiPort)) {
        if (Test-PortListening -Port $port) {
            Write-Warning "Port $port is still listening after shutdown. Inspect the temp logs under $tempRoot"
        }
    }

    Write-Host "Smoke harness logs: $tempRoot"
}
