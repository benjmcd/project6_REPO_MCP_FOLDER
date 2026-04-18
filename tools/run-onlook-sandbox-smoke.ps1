param(
    [ValidateSet('core', 'full')]
    [string]$Profile = 'full',
    [string]$AppDir = 'onlook-ui',
    [string]$BindHost = '127.0.0.1',
    [int]$UiPort = 3007,
    [int]$ReadyTimeoutSeconds = 180
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$laneRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$onlookUiRoot = if ([System.IO.Path]::IsPathRooted($AppDir)) {
    [System.IO.Path]::GetFullPath($AppDir)
} else {
    [System.IO.Path]::GetFullPath((Join-Path $laneRoot $AppDir))
}
$smokeScript = Join-Path $laneRoot 'tools\onlook-sandbox-smoke.mjs'
$fixturePath = Join-Path $onlookUiRoot 'data\fixture.json'

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

function Get-FixtureRoutes {
    param([string]$Path)

    $fixture = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    if (-not $fixture.routes) {
        throw "Fixture file does not expose route metadata: $Path"
    }

    return $fixture.routes
}

if (-not $onlookUiRoot.StartsWith($laneRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Sandbox app path must stay inside the lane root: $laneRoot"
}

Assert-Path $onlookUiRoot 'sandbox app root'
Assert-Path $smokeScript 'sandbox smoke script'
Assert-Path $fixturePath 'sandbox fixture snapshot'

if (Test-PortListening -Port $UiPort) {
    throw "Sandbox UI port $UiPort is already listening. Stop the conflicting listener before running this smoke harness."
}

$fixtureRoutes = Get-FixtureRoutes -Path $fixturePath
$documentTracePath = [string]$fixtureRoutes.document_trace
$workbenchPath = [string]$fixtureRoutes.workbench_compare
$candidateBPath = [string]$fixtureRoutes.candidate_b_trace

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("onlook-smoke-" + [System.Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tempRoot | Out-Null

$uiOut = Join-Path $tempRoot 'ui.out.log'
$uiErr = Join-Path $tempRoot 'ui.err.log'

$uiProcess = $null
$smokeUrl = "http://$BindHost`:$UiPort"

try {
    $uiProcess = Start-Process -FilePath 'powershell.exe' `
        -ArgumentList @(
            '-NoProfile',
            '-ExecutionPolicy',
            'Bypass',
            '-Command',
            "& { npm run dev -- --hostname '$BindHost' --port $UiPort }"
        ) `
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

    foreach ($port in @($UiPort)) {
        if (Test-PortListening -Port $port) {
            Write-Warning "Port $port is still listening after shutdown. Inspect the temp logs under $tempRoot"
        }
    }

    Write-Host "Smoke harness logs: $tempRoot"
}
