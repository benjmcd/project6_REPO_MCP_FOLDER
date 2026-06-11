#Requires -Version 5.1
<#
.SYNOPSIS
    Layer 3 production compose smoke test (Windows PowerShell 5.1)

.DESCRIPTION
    Spins up the full compose stack (app + postgres + nginx auth proxy) with
    ephemeral credentials, runs an assertion matrix, then tears down.

    Write-class probe route: POST /api/v1/layer3/handoff/export/prepare
      Payload: {} (empty JSON object — auth is validated first, then workbench
      returns 400 client_request_id_required; HTTP 400 proves auth PASSED for owner)

    Assertion matrix:
      (a) No credentials           -> 401
      (b) Auditor GET /operator/identity -> 200 (read, auditor admitted)
      (c) Auditor POST write route  -> 403 (auditor forbidden on write)
      (d) Owner POST write route    -> 400 (auth passed, workbench validation)
      (e) Auditor + spoofed role header -> 403 (spoof rejected by proxy overwrite)
      (f) GET /ready               -> 200 (readiness probe)
      (g) Direct app port 8000     -> connection refused (no host port mapping)

.PARAMETER KeepUp
    If specified, leave the stack running after the test (skip docker compose down).

.EXAMPLE
    .\deploy\smoke.ps1
    .\deploy\smoke.ps1 -KeepUp
#>
[CmdletBinding()]
param(
    [switch]$KeepUp
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

function Write-Check {
    param([string]$Label, [bool]$Passed, [string]$Detail = "")
    if ($Passed) {
        Write-Host "  PASS  $Label" -ForegroundColor Green
    } else {
        Write-Host "  FAIL  $Label$(if ($Detail) { ": $Detail" })" -ForegroundColor Red
    }
}

function Write-FileLfNoBom {
    # PS5.1 Set-Content -Encoding UTF8 writes a BOM and CRLF newlines.
    # A BOM breaks docker compose --env-file parsing and nginx htpasswd
    # username matching; a trailing CR corrupts bcrypt hash fields.
    param([string]$Path, [string]$Content)
    $normalized = $Content -replace "`r`n", "`n" -replace "`r", "`n"
    if (-not $normalized.EndsWith("`n")) { $normalized += "`n" }
    [System.IO.File]::WriteAllText($Path, $normalized, (New-Object System.Text.UTF8Encoding($false)))
}

function Invoke-ProbeRequest {
    param(
        [string]$Url,
        [string]$Method = "GET",
        [string]$Username = "",
        [string]$Password = "",
        [string]$Body = "",
        [hashtable]$ExtraHeaders = @{}
    )
    $headers = @{}
    foreach ($kv in $ExtraHeaders.GetEnumerator()) {
        $headers[$kv.Key] = $kv.Value
    }
    if ($Username -ne "") {
        $pair = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${Username}:${Password}"))
        $headers["Authorization"] = "Basic $pair"
    }
    if ($Method -eq "POST" -and $Body -ne "") {
        $headers["Content-Type"] = "application/json"
    }

    try {
        $params = @{
            Uri             = $Url
            Method          = $Method
            Headers         = $headers
            UseBasicParsing = $true
            TimeoutSec      = 15
        }
        if ($Method -eq "POST" -and $Body -ne "") {
            $params["Body"] = $Body
        }
        $resp = Invoke-WebRequest @params
        return $resp.StatusCode
    } catch [System.Net.WebException] {
        $webEx = $_.Exception
        if ($null -ne $webEx.Response) {
            return [int]$webEx.Response.StatusCode
        }
        # Connection refused or network failure — return -1
        return -1
    } catch {
        # Any other error (timeout, etc.) — return -1
        return -1
    }
}

# ---------------------------------------------------------------------------
# Check docker availability
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "=== Layer 3 Production Compose Smoke Test ===" -ForegroundColor Cyan
Write-Host ""

try {
    $null = & docker version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: docker is not available or not running. Install Docker Desktop and ensure it is started." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "ERROR: docker command not found. Install Docker Desktop and ensure it is on your PATH." -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SmokeDir  = Join-Path $ScriptDir ".smoke"
$ComposeFile = Join-Path $ScriptDir "docker-compose.production.yml"

if (-not (Test-Path $ComposeFile)) {
    Write-Host "ERROR: Cannot find $ComposeFile" -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------------------
# Create ephemeral smoke directory
# ---------------------------------------------------------------------------
Write-Host "Creating ephemeral smoke environment in $SmokeDir ..." -ForegroundColor Yellow

if (Test-Path $SmokeDir) {
    Remove-Item -Recurse -Force $SmokeDir
}
New-Item -ItemType Directory -Force -Path $SmokeDir | Out-Null

# Generate random POSTGRES_PASSWORD (32 hex chars)
$RandBytes = New-Object byte[] 16
[Security.Cryptography.RNGCryptoServiceProvider]::Create().GetBytes($RandBytes)
$PostgresPassword = ([BitConverter]::ToString($RandBytes) -replace "-","").ToLower()

# Generate random passwords for smoke users
$OwnerPwBytes = New-Object byte[] 12
[Security.Cryptography.RNGCryptoServiceProvider]::Create().GetBytes($OwnerPwBytes)
$OwnerPassword = ([BitConverter]::ToString($OwnerPwBytes) -replace "-","").ToLower()

$AuditorPwBytes = New-Object byte[] 12
[Security.Cryptography.RNGCryptoServiceProvider]::Create().GetBytes($AuditorPwBytes)
$AuditorPassword = ([BitConverter]::ToString($AuditorPwBytes) -replace "-","").ToLower()

# Decide proxy port (avoid conflicts by using a high ephemeral port)
$ProxyPort = 18080

# Write deploy/.smoke/.env
$EnvContent = @"
POSTGRES_PASSWORD=$PostgresPassword
PROXY_HTTP_PORT=$ProxyPort
ALLOWED_ORIGINS=https://smoke.invalid
LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED=false
"@
$EnvFile = Join-Path $SmokeDir ".env"
Write-FileLfNoBom -Path $EnvFile -Content $EnvContent

# Generate htpasswd hashes via docker httpd image (bcrypt -B)
Write-Host "Generating htpasswd hashes via docker httpd:2.4-alpine ..." -ForegroundColor Yellow

# htpasswd output may arrive as a multi-line array (hash line + blank line);
# keep only the user:hash line so the joined file stays well-formed.
$OwnerHash = @(& docker run --rm httpd:2.4-alpine htpasswd -nbB smoke-owner $OwnerPassword) |
    Where-Object { $_ -match ":" } | Select-Object -First 1
if ($LASTEXITCODE -ne 0 -or -not $OwnerHash) {
    Write-Host "ERROR: Failed to generate htpasswd hash for smoke-owner" -ForegroundColor Red
    exit 1
}
$AuditorHash = @(& docker run --rm httpd:2.4-alpine htpasswd -nbB smoke-auditor $AuditorPassword) |
    Where-Object { $_ -match ":" } | Select-Object -First 1
if ($LASTEXITCODE -ne 0 -or -not $AuditorHash) {
    Write-Host "ERROR: Failed to generate htpasswd hash for smoke-auditor" -ForegroundColor Red
    exit 1
}

$HtpasswdContent = "$OwnerHash`n$AuditorHash"
$HtpasswdFile = Join-Path $SmokeDir "htpasswd"
Write-FileLfNoBom -Path $HtpasswdFile -Content $HtpasswdContent

# Write roles.map
$RolesMapContent = @'
"smoke-owner" "owner";
"smoke-auditor" "auditor";
'@
$RolesMapFile = Join-Path $SmokeDir "roles.map"
Write-FileLfNoBom -Path $RolesMapFile -Content $RolesMapContent

# Write compose override to mount .smoke files instead of deploy/proxy/* files
$NginxConfPath = (Join-Path $ScriptDir "proxy\nginx.conf") -replace "\\","/"
$HtpasswdPath  = $HtpasswdFile -replace "\\","/"
$RolesMapPath  = $RolesMapFile -replace "\\","/"

# Convert Windows paths (C:/...) to the format docker understands on Windows
# docker compose on Windows accepts /c/... or C:/... — use C:/ form
$OverrideContent = @"
services:
  proxy:
    volumes:
      - ${NginxConfPath}:/etc/nginx/nginx.conf:ro
      - ${HtpasswdPath}:/etc/nginx/htpasswd:ro
      - ${RolesMapPath}:/etc/nginx/roles.map:ro
"@
$OverrideFile = Join-Path $SmokeDir "override.yml"
Write-FileLfNoBom -Path $OverrideFile -Content $OverrideContent

# ---------------------------------------------------------------------------
# Bring up the stack
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "Starting compose stack (this will build the app image if needed) ..." -ForegroundColor Yellow
Write-Host "  Compose file : $ComposeFile" -ForegroundColor Gray
Write-Host "  Override     : $OverrideFile" -ForegroundColor Gray
Write-Host "  Proxy port   : $ProxyPort" -ForegroundColor Gray
Write-Host ""

$StackUp = $false
try {
    & docker compose `
        -f $ComposeFile `
        -f $OverrideFile `
        --env-file $EnvFile `
        up -d --build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: docker compose up failed (exit $LASTEXITCODE)" -ForegroundColor Red
        exit 1
    }
    $StackUp = $true

    # -----------------------------------------------------------------------
    # Wait for app container health = healthy (bounded ~180s)
    # -----------------------------------------------------------------------
    Write-Host "Waiting for app container to become healthy (up to 180s) ..." -ForegroundColor Yellow
    $MaxWait   = 180
    $Elapsed   = 0
    $Interval  = 5
    $AppHealthy = $false

    while ($Elapsed -lt $MaxWait) {
        # NOTE: no 2>$null here — under $ErrorActionPreference=Stop, PS5.1
        # promotes redirected native stderr to a terminating error.
        $AppContainerId = (& docker compose -f $ComposeFile -f $OverrideFile --env-file $EnvFile ps -q app | Select-Object -First 1)
        $HealthStatus = "starting"
        if ($AppContainerId) {
            $HealthStatus = & docker inspect --format "{{.State.Health.Status}}" $AppContainerId
        }
        if ($HealthStatus -eq "healthy") {
            $AppHealthy = $true
            break
        }
        Start-Sleep -Seconds $Interval
        $Elapsed += $Interval
        Write-Host "  ... waited ${Elapsed}s (status: $HealthStatus)" -ForegroundColor Gray
    }

    if (-not $AppHealthy) {
        Write-Host "ERROR: App container did not become healthy within ${MaxWait}s" -ForegroundColor Red
        & docker compose -f $ComposeFile -f $OverrideFile --env-file $EnvFile logs app | Select-Object -Last 40
        exit 1
    }
    Write-Host "App is healthy after ${Elapsed}s." -ForegroundColor Green
    Write-Host ""

    # -----------------------------------------------------------------------
    # Assertion matrix
    # -----------------------------------------------------------------------
    $BaseUrl    = "http://localhost:$ProxyPort"
    $AppDirect  = "http://localhost:8000"
    $IdentityUrl = "$BaseUrl/api/v1/layer3/operator/identity"
    $WriteUrl    = "$BaseUrl/api/v1/layer3/handoff/export/prepare"
    $ReadyUrl    = "$BaseUrl/ready"
    $WriteBody   = "{}"

    Write-Host "=== Assertion Matrix ===" -ForegroundColor Cyan
    Write-Host ""

    $AllPass = $true

    # (a) No credentials -> 401
    $StatusA = Invoke-ProbeRequest -Url $IdentityUrl -Method GET
    $PassA = ($StatusA -eq 401)
    Write-Check "(a) No credentials -> 401 (got $StatusA)" $PassA
    if (-not $PassA) { $AllPass = $false }

    # (b) Auditor GET /operator/identity -> 200
    $StatusB = Invoke-ProbeRequest -Url $IdentityUrl -Method GET -Username "smoke-auditor" -Password $AuditorPassword
    $PassB = ($StatusB -eq 200)
    Write-Check "(b) Auditor GET /operator/identity -> 200 (got $StatusB)" $PassB
    if (-not $PassB) { $AllPass = $false }

    # (c) Auditor POST write route -> 403
    $StatusC = Invoke-ProbeRequest -Url $WriteUrl -Method POST -Username "smoke-auditor" -Password $AuditorPassword -Body $WriteBody
    $PassC = ($StatusC -eq 403)
    Write-Check "(c) Auditor POST write route -> 403 (got $StatusC)" $PassC
    if (-not $PassC) { $AllPass = $false }

    # (d) Owner POST write route -> 400 (auth passed, workbench validation error)
    $StatusD = Invoke-ProbeRequest -Url $WriteUrl -Method POST -Username "smoke-owner" -Password $OwnerPassword -Body $WriteBody
    $PassD = ($StatusD -eq 400)
    Write-Check "(d) Owner POST write route -> 400 (auth passed; got $StatusD)" $PassD
    if (-not $PassD) { $AllPass = $false }

    # (e) Auditor + spoofed X-Forwarded-Roles: owner -> 403 (spoof rejected)
    $SpoofHeaders = @{ "X-Forwarded-Roles" = "owner" }
    $StatusE = Invoke-ProbeRequest -Url $WriteUrl -Method POST -Username "smoke-auditor" -Password $AuditorPassword -Body $WriteBody -ExtraHeaders $SpoofHeaders
    $PassE = ($StatusE -eq 403)
    Write-Check "(e) Auditor + spoofed role header -> 403 (spoof rejected; got $StatusE)" $PassE
    if (-not $PassE) { $AllPass = $false }

    # (f) GET /ready -> 200
    $StatusF = Invoke-ProbeRequest -Url $ReadyUrl -Method GET -Username "smoke-owner" -Password $OwnerPassword
    $PassF = ($StatusF -eq 200)
    Write-Check "(f) GET /ready -> 200 (got $StatusF)" $PassF
    if (-not $PassF) { $AllPass = $false }

    # (g) Direct app port 8000 -> connection refused (-1)
    $StatusG = Invoke-ProbeRequest -Url $AppDirect -Method GET
    $PassG = ($StatusG -eq -1)
    Write-Check "(g) Direct localhost:8000 -> connection refused (got $StatusG)" $PassG
    if (-not $PassG) { $AllPass = $false }

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    Write-Host ""
    Write-Host "=== Summary ===" -ForegroundColor Cyan
    if ($AllPass) {
        Write-Host "ALL CHECKS PASSED" -ForegroundColor Green
    } else {
        Write-Host "ONE OR MORE CHECKS FAILED" -ForegroundColor Red
    }

} finally {
    if ($StackUp -and -not $KeepUp) {
        Write-Host ""
        Write-Host "Tearing down compose stack ..." -ForegroundColor Yellow
        & docker compose `
            -f $ComposeFile `
            -f $OverrideFile `
            --env-file $EnvFile `
            down -v
    } elseif ($KeepUp) {
        Write-Host ""
        Write-Host "-KeepUp specified: stack left running on port $ProxyPort" -ForegroundColor Yellow
        Write-Host "Smoke artifacts preserved in $SmokeDir (the running stack's mounts and env point there)." -ForegroundColor Yellow
        Write-Host "Tear down later with:" -ForegroundColor Yellow
        Write-Host "  docker compose -f `"$ComposeFile`" -f `"$OverrideFile`" --env-file `"$EnvFile`" down -v" -ForegroundColor Yellow
        Write-Host "then delete $SmokeDir." -ForegroundColor Yellow
    }
    # Only remove the ephemeral credentials when the stack is gone — a kept
    # stack still bind-mounts htpasswd/roles.map from this directory and needs
    # the .env/override files for its eventual teardown.
    if (-not $KeepUp -and (Test-Path $SmokeDir)) {
        Remove-Item -Recurse -Force $SmokeDir
    }
}

if (-not $AllPass) {
    exit 1
}
