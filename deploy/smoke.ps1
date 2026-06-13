#Requires -Version 5.1
<#
.SYNOPSIS
    Layer 3 production compose smoke test (Windows PowerShell 5.1)

.DESCRIPTION
    Spins up the full compose stack (app + postgres + nginx auth proxy) with
    ephemeral credentials, runs an assertion matrix, then tears down.

    Write-class probe route: POST /api/v1/layer3/handoff/export/prepare
      Payload: {} (empty JSON object -- auth is validated first, then workbench
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

.PARAMETER Probe
    Run the product-flow probe (steps 1-4) after the auth matrix.

.PARAMETER Durability
    Run restart-survival durability check: seeds via probe steps 1-2, restarts
    the app container, then verifies the seeded record survived.

.PARAMETER Full
    Equivalent to running the auth matrix + -Probe + -Durability.

.PARAMETER BackupRestore
    Run a total-loss backup/restore round-trip: seeds a record, backs up all
    three volumes, destroys them, restores, and verifies byte-consistent
    recovery. Explicit opt-in -- NOT implied by -Full. Destroys and recreates
    named volumes; takes ~3 min. Mutually exclusive with -KeepUp.

.EXAMPLE
    .\deploy\smoke.ps1
    .\deploy\smoke.ps1 -KeepUp
    .\deploy\smoke.ps1 -Probe
    .\deploy\smoke.ps1 -Durability
    .\deploy\smoke.ps1 -Full
    .\deploy\smoke.ps1 -BackupRestore
#>
[CmdletBinding()]
param(
    [switch]$KeepUp,
    [switch]$Probe,
    [switch]$Durability,
    [switch]$Full,
    [switch]$BackupRestore
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Mutual exclusion: -BackupRestore destroys volumes so -KeepUp is contradictory.
if ($BackupRestore -and $KeepUp) {
    Write-Host "ERROR: -BackupRestore and -KeepUp are mutually exclusive. -BackupRestore destroys and recreates volumes; the stack cannot be kept up in a meaningful state." -ForegroundColor Red
    exit 1
}

# Expand combined flags
if ($Full) {
    $Probe = $true
    $Durability = $true
}

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
        [hashtable]$ExtraHeaders = @{},
        [string]$ContentType = "application/json"
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
        $headers["Content-Type"] = $ContentType
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
        return $resp
    } catch [System.Net.WebException] {
        $webEx = $_.Exception
        if ($null -ne $webEx.Response) {
            # Return a synthetic object with status code. IWR may have already
            # drained the response stream to build the exception message; fall
            # back to ErrorDetails, which PS populates with the body text.
            $reader = New-Object System.IO.StreamReader($webEx.Response.GetResponseStream())
            $responseBody = $reader.ReadToEnd()
            $reader.Close()
            if ($responseBody -eq "" -and $null -ne $_.ErrorDetails) {
                $responseBody = [string]$_.ErrorDetails.Message
            }
            return [PSCustomObject]@{
                StatusCode = [int]$webEx.Response.StatusCode
                Content    = $responseBody
            }
        }
        return [PSCustomObject]@{ StatusCode = -1; Content = "" }
    } catch {
        return [PSCustomObject]@{ StatusCode = -1; Content = "" }
    }
}

function Invoke-ProbeRequestStatusOnly {
    param(
        [string]$Url,
        [string]$Method = "GET",
        [string]$Username = "",
        [string]$Password = "",
        [string]$Body = "",
        [hashtable]$ExtraHeaders = @{}
    )
    $resp = Invoke-ProbeRequest -Url $Url -Method $Method -Username $Username -Password $Password -Body $Body -ExtraHeaders $ExtraHeaders
    return $resp.StatusCode
}

function Invoke-MultipartProbeRequest {
    param(
        [string]$Url,
        [string]$Username,
        [string]$Password,
        [hashtable]$Fields,
        [string]$FilePath,
        [string]$FileName
    )
    # Build a multipart/form-data body manually (PS5.1 has no built-in multipart).
    # RFC 2046 requires CRLF delimiters in multipart boundaries.
    $boundary = [System.Guid]::NewGuid().ToString("N")
    $CRLF = "`r`n"
    $bodyParts = [System.Collections.Generic.List[byte[]]]::new()

    foreach ($key in $Fields.Keys) {
        $partHeader = "--$boundary${CRLF}Content-Disposition: form-data; name=`"$key`"${CRLF}${CRLF}"
        $partHeaderBytes = [System.Text.Encoding]::UTF8.GetBytes($partHeader)
        $partValueBytes  = [System.Text.Encoding]::UTF8.GetBytes($Fields[$key])
        $partEndBytes    = [System.Text.Encoding]::UTF8.GetBytes($CRLF)
        $bodyParts.Add($partHeaderBytes)
        $bodyParts.Add($partValueBytes)
        $bodyParts.Add($partEndBytes)
    }

    $fileBytes = [System.IO.File]::ReadAllBytes($FilePath)
    # text/plain: the bounded source-intake preview only admits text media types
    # (source_intake_preview_media_type_not_admitted otherwise), and the probe
    # uploads plain-text artifacts.
    $fileHeader = "--$boundary${CRLF}Content-Disposition: form-data; name=`"file`"; filename=`"$FileName`"${CRLF}Content-Type: text/plain${CRLF}${CRLF}"
    $fileHeaderBytes = [System.Text.Encoding]::UTF8.GetBytes($fileHeader)
    $fileEndBytes    = [System.Text.Encoding]::UTF8.GetBytes($CRLF)
    $bodyParts.Add($fileHeaderBytes)
    $bodyParts.Add($fileBytes)
    $bodyParts.Add($fileEndBytes)

    $finalBoundaryBytes = [System.Text.Encoding]::UTF8.GetBytes("--$boundary--$CRLF")
    $bodyParts.Add($finalBoundaryBytes)

    $totalLength = 0
    foreach ($part in $bodyParts) { $totalLength += $part.Length }
    $fullBody = New-Object byte[] $totalLength
    $offset = 0
    foreach ($part in $bodyParts) {
        [System.Buffer]::BlockCopy($part, 0, $fullBody, $offset, $part.Length)
        $offset += $part.Length
    }

    $pair = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${Username}:${Password}"))
    $headers = @{
        "Authorization" = "Basic $pair"
        "Content-Type"  = "multipart/form-data; boundary=$boundary"
    }

    try {
        $resp = Invoke-WebRequest -Uri $Url -Method POST -Headers $headers -Body $fullBody -UseBasicParsing -TimeoutSec 30
        return $resp
    } catch [System.Net.WebException] {
        $webEx = $_.Exception
        if ($null -ne $webEx.Response) {
            $reader = New-Object System.IO.StreamReader($webEx.Response.GetResponseStream())
            $responseBody = $reader.ReadToEnd()
            $reader.Close()
            if ($responseBody -eq "" -and $null -ne $_.ErrorDetails) {
                $responseBody = [string]$_.ErrorDetails.Message
            }
            return [PSCustomObject]@{
                StatusCode = [int]$webEx.Response.StatusCode
                Content    = $responseBody
            }
        }
        return [PSCustomObject]@{ StatusCode = -1; Content = "" }
    } catch {
        return [PSCustomObject]@{ StatusCode = -1; Content = "" }
    }
}

function Wait-AppHealthy {
    param(
        [string]$ComposeFile,
        [string]$OverrideFile,
        [string]$EnvFile,
        [string]$ServiceName = 'app',
        [int]$MaxWait = 180,
        [int]$Interval = 5
    )
    $Elapsed = 0
    while ($Elapsed -lt $MaxWait) {
        $ContainerId = (& docker compose -f $ComposeFile -f $OverrideFile --env-file $EnvFile ps -q $ServiceName | Select-Object -First 1)
        $HealthStatus = "starting"
        if ($ContainerId) {
            $HealthStatus = & docker inspect --format "{{.State.Health.Status}}" $ContainerId
        }
        if ($HealthStatus -eq "healthy") {
            Write-Host "$ServiceName is healthy after ${Elapsed}s." -ForegroundColor Green
            return $true
        }
        Start-Sleep -Seconds $Interval
        $Elapsed += $Interval
        Write-Host "  ... waited ${Elapsed}s (status: $HealthStatus)" -ForegroundColor Gray
    }
    return $false
}

function Invoke-GnuTarBackup {
    param(
        [string]$VolumeName,
        [string]$ArchivePath
    )
    # Use debian:bookworm-slim for GNU tar (avoids busybox/alpine tar quirks).
    # Host path uses forward slashes for docker volume mount compatibility.
    $ArchiveDir  = (Split-Path -Parent $ArchivePath) -replace '\\','/'
    $ArchiveFile = Split-Path -Leaf $ArchivePath

    # Discard stdout (image-pull/tar listing) so the function returns ONLY the
    # boolean; a leaked Object[] would break Write-Check's [bool] param. Exit
    # code is preserved by $LASTEXITCODE.
    $null = & docker run --rm `
        -v "${VolumeName}:/data:ro" `
        -v "${ArchiveDir}:/out" `
        debian:bookworm-slim `
        tar czf "/out/$ArchiveFile" -C /data . --numeric-owner
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  FAIL  Invoke-GnuTarBackup: tar czf failed for volume $VolumeName" -ForegroundColor Red
        return $false
    }

    # Verify archive integrity (list contents; exit 0 = intact). Discard the listing.
    $null = & docker run --rm `
        -v "${ArchiveDir}:/out:ro" `
        debian:bookworm-slim `
        tar -tzf "/out/$ArchiveFile"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  FAIL  Invoke-GnuTarBackup: archive integrity check failed for $ArchiveFile" -ForegroundColor Red
        return $false
    }
    return $true
}

function Invoke-GnuTarRestore {
    param(
        [string]$VolumeName,
        [string]$ArchivePath
    )
    $ArchiveDir  = (Split-Path -Parent $ArchivePath) -replace '\\','/'
    $ArchiveFile = Split-Path -Leaf $ArchivePath

    # Restore with numeric owner, then chown to 1001:1001 (appuser/appgroup).
    # --numeric-owner alone is insufficient: the helper image uid/gid table
    # may remap owners during extraction; explicit chown guarantees the
    # non-root app can read and write its restored tree.
    # Discard stdout so the function returns ONLY the boolean (see Invoke-GnuTarBackup).
    $null = & docker run --rm `
        -v "${VolumeName}:/data" `
        -v "${ArchiveDir}:/backup:ro" `
        debian:bookworm-slim `
        sh -c "tar xzf /backup/$ArchiveFile -C /data --numeric-owner"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  FAIL  Invoke-GnuTarRestore: tar xzf failed for volume $VolumeName" -ForegroundColor Red
        return $false
    }

    $null = & docker run --rm `
        -v "${VolumeName}:/data" `
        debian:bookworm-slim `
        chown -R 1001:1001 /data
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  FAIL  Invoke-GnuTarRestore: chown 1001:1001 failed for volume $VolumeName" -ForegroundColor Red
        return $false
    }
    return $true
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

# Generate random POSTGRES_PASSWORD (32 hex chars -- only [a-f0-9], always URL-safe)
$RandBytes = New-Object byte[] 16
[Security.Cryptography.RNGCryptoServiceProvider]::Create().GetBytes($RandBytes)
$PostgresPassword = ([BitConverter]::ToString($RandBytes) -replace "-","").ToLower()

# Generate ephemeral LAYER3_SIGNED_REFERENCE_SECRET (64 hex chars)
$SecretBytes = New-Object byte[] 32
[Security.Cryptography.RNGCryptoServiceProvider]::Create().GetBytes($SecretBytes)
$SignedReferenceSecret = ([BitConverter]::ToString($SecretBytes) -replace "-","").ToLower()

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
LAYER3_SIGNED_REFERENCE_SECRET=$SignedReferenceSecret
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
# docker compose on Windows accepts /c/... or C:/... -- use C:/ form
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

    # NOTE: no 2>$null here -- under $ErrorActionPreference=Stop, PS5.1
    # promotes redirected native stderr to a terminating error.
    $AppHealthy = Wait-AppHealthy -ComposeFile $ComposeFile -OverrideFile $OverrideFile -EnvFile $EnvFile

    if (-not $AppHealthy) {
        Write-Host "ERROR: App container did not become healthy within 180s" -ForegroundColor Red
        & docker compose -f $ComposeFile -f $OverrideFile --env-file $EnvFile logs app | Select-Object -Last 40
        exit 1
    }
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
    $StatusA = Invoke-ProbeRequestStatusOnly -Url $IdentityUrl -Method GET
    $PassA = ($StatusA -eq 401)
    Write-Check "(a) No credentials -> 401 (got $StatusA)" $PassA
    if (-not $PassA) { $AllPass = $false }

    # (b) Auditor GET /operator/identity -> 200
    $StatusB = Invoke-ProbeRequestStatusOnly -Url $IdentityUrl -Method GET -Username "smoke-auditor" -Password $AuditorPassword
    $PassB = ($StatusB -eq 200)
    Write-Check "(b) Auditor GET /operator/identity -> 200 (got $StatusB)" $PassB
    if (-not $PassB) { $AllPass = $false }

    # (c) Auditor POST write route -> 403
    $StatusC = Invoke-ProbeRequestStatusOnly -Url $WriteUrl -Method POST -Username "smoke-auditor" -Password $AuditorPassword -Body $WriteBody
    $PassC = ($StatusC -eq 403)
    Write-Check "(c) Auditor POST write route -> 403 (got $StatusC)" $PassC
    if (-not $PassC) { $AllPass = $false }

    # (d) Owner POST write route -> 400 (auth passed, workbench validation error)
    $StatusD = Invoke-ProbeRequestStatusOnly -Url $WriteUrl -Method POST -Username "smoke-owner" -Password $OwnerPassword -Body $WriteBody
    $PassD = ($StatusD -eq 400)
    Write-Check "(d) Owner POST write route -> 400 (auth passed; got $StatusD)" $PassD
    if (-not $PassD) { $AllPass = $false }

    # (e) Auditor + spoofed X-Forwarded-Roles: owner -> 403 (spoof rejected)
    $SpoofHeaders = @{ "X-Forwarded-Roles" = "owner" }
    $StatusE = Invoke-ProbeRequestStatusOnly -Url $WriteUrl -Method POST -Username "smoke-auditor" -Password $AuditorPassword -Body $WriteBody -ExtraHeaders $SpoofHeaders
    $PassE = ($StatusE -eq 403)
    Write-Check "(e) Auditor + spoofed role header -> 403 (spoof rejected; got $StatusE)" $PassE
    if (-not $PassE) { $AllPass = $false }

    # (f) GET /ready -> 200
    $StatusF = Invoke-ProbeRequestStatusOnly -Url $ReadyUrl -Method GET -Username "smoke-owner" -Password $OwnerPassword
    $PassF = ($StatusF -eq 200)
    Write-Check "(f) GET /ready -> 200 (got $StatusF)" $PassF
    if (-not $PassF) { $AllPass = $false }

    # (g) Direct app port 8000 -> connection refused (-1)
    $StatusG = Invoke-ProbeRequestStatusOnly -Url $AppDirect -Method GET
    $PassG = ($StatusG -eq -1)
    Write-Check "(g) Direct localhost:8000 -> connection refused (got $StatusG)" $PassG
    if (-not $PassG) { $AllPass = $false }

    Write-Host ""

    # -----------------------------------------------------------------------
    # Product-flow probe (-Probe or -Full)
    # -----------------------------------------------------------------------
    $ProbeSourceIntakeRecordId = ""
    $ProbeComplete = $false

    # -Durability alone must NOT require the full probe: the durability block
    # has its own steps-1-2 seeding path and only needs an intake record.
    if ($Probe) {
        Write-Host "=== Product-Flow Probe ===" -ForegroundColor Cyan
        Write-Host ""

        # NOTE: The probe implements the longest HTTP chain that the repo's own
        # tests prove works from a clean DB over HTTP routes (no ORM seeding).
        # The proven chain for the source-intake path ends at gate-b admission
        # (step 4).  All post-gate-b tests (gate-c, plan/preview, plan/approve,
        # execution/*, package/*) either (a) seed L3Session rows directly via
        # ORM service calls, or (b) use dataset_version/aps_content_document
        # sources that also require ORM-seeded source authority -- neither
        # qualifies as an HTTP-proven chain from upload.  The probe therefore
        # stops honestly at step 4 with a clear note.
        #
        # Proving reference:
        #   Step 1: test_layer3_bootstrap_contract.py (bootstrap route)
        #   Step 2: test_layer3_source_intake.py:318-319 (_upload_source_intake)
        #   Step 3: test_layer3_source_intake.py:321 (GET .../preview)
        #   Step 4: test_layer3_source_intake.py:325-332 (POST gate-b/decision)

        $ApiBase = "$BaseUrl/api/v1/layer3"
        $ProbePass = $true
        $LongestStep = 0

        function Invoke-ProbeStep {
            param(
                [string]$StepNum,
                [string]$Label,
                [string]$Url,
                [string]$Method = "POST",
                [string]$Body = "",
                [string]$ContentType = "application/json",
                [int]$ExpectedStatus = 200
            )
            $resp = Invoke-ProbeRequest -Url $Url -Method $Method -Username "smoke-owner" -Password $OwnerPassword -Body $Body -ContentType $ContentType
            $ok = ($resp.StatusCode -eq $ExpectedStatus)
            if ($ok) {
                Write-Host "  PASS  Step $StepNum $Label (HTTP $($resp.StatusCode))" -ForegroundColor Green
            } else {
                $excerpt = if ($resp.Content.Length -gt 400) { $resp.Content.Substring(0, 400) } else { $resp.Content }
                Write-Host "  FAIL  Step $StepNum $Label (HTTP $($resp.StatusCode)): $excerpt" -ForegroundColor Red
            }
            return $resp
        }

        # Use script-scope variables for cross-step data
        $script:ClientRequestId = [System.Guid]::NewGuid().ToString()
        $script:SourceIntakeRecordId = ""
        $script:MaterialPreviewId = ""
        $script:MaterialPreviewHash = ""
        $script:MaterialCandidateId = ""
        $script:MaterialSourceRef = ""
        $script:MaterialQueryBasis = ""
        $script:MaterialProvenanceRef = ""
        $script:MaterialSourceIdentity = $null
        $script:MaterialSourceProvenance = $null
        $script:MaterialPayload = $null
        $script:MaterialLoadSummary = $null
        $script:SessionId = ""

        # -- Step 1: Bootstrap --
        # test_layer3_bootstrap_contract.py: GET /api/v1/layer3/bootstrap -> 200
        $r1 = Invoke-ProbeStep -StepNum "1" -Label "GET /bootstrap" -Url "$ApiBase/bootstrap" -Method GET -ExpectedStatus 200
        if ($r1.StatusCode -ne 200) { $ProbePass = $false }
        if ($ProbePass) { $LongestStep = 1 }

        # -- Step 2: Source intake upload --
        # test_layer3_source_intake.py:318-319 (_upload_source_intake -> POST /source/intake/upload -> 201)
        if ($ProbePass) {
            $TmpFile = Join-Path $SmokeDir "probe_upload.txt"
            Write-FileLfNoBom -Path $TmpFile -Content "Layer 3 smoke probe upload artifact"
            $Fields = @{
                client_request_id = $script:ClientRequestId
                operator_decision  = "record_operator_uploaded_source"
                source_label       = "Smoke probe upload"
                source_family      = "operator_uploaded_single_source"
            }
            $r2 = Invoke-MultipartProbeRequest -Url "$ApiBase/source/intake/upload" -Username "smoke-owner" -Password $OwnerPassword -Fields $Fields -FilePath $TmpFile -FileName "probe_upload.txt"
            $ok2 = ($r2.StatusCode -eq 201)
            if ($ok2) {
                Write-Host "  PASS  Step 2 POST /source/intake/upload (HTTP $($r2.StatusCode))" -ForegroundColor Green
                try {
                    $body2 = $r2.Content | ConvertFrom-Json
                    $script:SourceIntakeRecordId = $body2.source_intake_record_id
                } catch {
                    Write-Host "  WARN  Step 2: could not parse response JSON" -ForegroundColor Yellow
                }
                $LongestStep = 2
            } else {
                $excerpt = if ($r2.Content.Length -gt 400) { $r2.Content.Substring(0, 400) } else { $r2.Content }
                Write-Host "  FAIL  Step 2 POST /source/intake/upload (HTTP $($r2.StatusCode)): $excerpt" -ForegroundColor Red
                $ProbePass = $false
            }
        }

        # Record for durability use
        $ProbeSourceIntakeRecordId = $script:SourceIntakeRecordId

        # -- Step 3: Source intake material preview --
        # test_layer3_source_intake.py:321,244-281 (GET /source/intake/{id}/preview -> 200,
        #   body contains material_preview_id, material_preview_hash, material_candidate)
        if ($ProbePass) {
            $r3 = Invoke-ProbeStep -StepNum "3" -Label "GET /source/intake/{id}/preview" -Url "$ApiBase/source/intake/$($script:SourceIntakeRecordId)/preview" -Method GET -ExpectedStatus 200
            if ($r3.StatusCode -ne 200) { $ProbePass = $false }
            if ($ProbePass) {
                try {
                    $parsed3 = $r3.Content | ConvertFrom-Json
                    $script:MaterialPreviewId = $parsed3.material_preview_id
                    $script:MaterialPreviewHash = $parsed3.material_preview_hash
                    $candidate = $parsed3.material_candidate
                    $script:MaterialCandidateId = $candidate.candidate_id
                    $script:MaterialSourceRef = $candidate.source_ref
                    $script:MaterialQueryBasis = $candidate.query_basis
                    $script:MaterialProvenanceRef = $candidate.provenance_ref
                    $script:MaterialSourceIdentity = $candidate.source_identity
                    $script:MaterialSourceProvenance = $candidate.source_provenance
                    $script:MaterialPayload = $candidate.payload
                    $script:MaterialLoadSummary = $candidate.load_summary
                } catch { }
                $LongestStep = 3
            }
        }

        # -- Step 4: Gate-B decision --
        # test_layer3_source_intake.py:325-332 (POST /gate-b/decision -> 200,
        #   body.status=="ok", body.next_state=="gate_c_preview_ready", body.session_id present)
        if ($ProbePass) {
            $decisionBasisObj = @{
                source_ref        = $script:MaterialSourceRef
                query_basis       = $script:MaterialQueryBasis
                provenance_ref    = $script:MaterialProvenanceRef
                source_identity   = $script:MaterialSourceIdentity
                source_provenance = $script:MaterialSourceProvenance
                payload           = $script:MaterialPayload
                load_summary      = $script:MaterialLoadSummary
            }
            $candidateDecisionObj = @{
                candidate_id    = $script:MaterialCandidateId
                decision        = "approved"
                operator_reason = "Smoke probe gate-b admission of source-intake record."
                decision_basis  = $decisionBasisObj
            }
            $gateBPayload = @{
                client_request_id    = $script:ClientRequestId
                preflight_id         = "smoke-probe-preflight-$($script:ClientRequestId)"
                source_set_id        = "smoke-probe-source-set-$($script:ClientRequestId)"
                material_preview_id  = $script:MaterialPreviewId
                material_preview_hash = $script:MaterialPreviewHash
                actor                = "operator"
                candidate_decisions  = @($candidateDecisionObj)
                commit_reason        = "Smoke probe gate-b admission."
            }
            $gateBBody = $gateBPayload | ConvertTo-Json -Depth 10 -Compress
            $r4 = Invoke-ProbeStep -StepNum "4" -Label "POST /gate-b/decision" -Url "$ApiBase/gate-b/decision" -Body $gateBBody -ExpectedStatus 200
            if ($r4.StatusCode -ne 200) { $ProbePass = $false }
            if ($ProbePass) {
                try {
                    $parsed4 = $r4.Content | ConvertFrom-Json
                    $script:SessionId = $parsed4.session_id
                } catch { }
                $LongestStep = 4
                $ProbeComplete = $true
            }
        }

        Write-Host ""
        Write-Host "  NOTE: Proven HTTP chain ends at step 4 (gate-b admission)." -ForegroundColor Yellow
        Write-Host "        Post-gate-b routes (gate-c, plan/preview, execution/*, package/*)" -ForegroundColor Yellow
        Write-Host "        are tested only with ORM-seeded sessions, not from an HTTP-only" -ForegroundColor Yellow
        Write-Host "        source-intake upload chain. Probe stops here honestly." -ForegroundColor Yellow
        Write-Host ""
        if ($ProbePass) {
            Write-Host "  Product-flow probe: ALL STEPS PASSED (longest: $LongestStep/4)" -ForegroundColor Green
        } else {
            Write-Host "  Product-flow probe: FAILED at step $($LongestStep + 1) (longest prefix reached: $LongestStep/4)" -ForegroundColor Red
            $AllPass = $false
        }
        Write-Host ""
    }

    # -----------------------------------------------------------------------
    # Durability check (-Durability or -Full)
    # -----------------------------------------------------------------------
    if ($Durability -and -not $AllPass) {
        Write-Host "=== Durability Check skipped: earlier checks failed ===" -ForegroundColor Yellow
        Write-Host ""
    }
    if ($Durability -and $AllPass) {
        Write-Host "=== Durability Check ===" -ForegroundColor Cyan
        Write-Host ""

        # Seed steps 1-2 if probe was not already run
        if (-not $Probe -or $ProbeSourceIntakeRecordId -eq "") {
            Write-Host "  Seeding via steps 1-2 ..." -ForegroundColor Yellow
            $ApiBase = "$BaseUrl/api/v1/layer3"

            # Step 1: Bootstrap
            $rs1 = Invoke-ProbeRequest -Url "$ApiBase/bootstrap" -Method GET -Username "smoke-owner" -Password $OwnerPassword
            if ($rs1.StatusCode -ne 200) {
                Write-Host "  FAIL  Durability seed step 1 (bootstrap) returned HTTP $($rs1.StatusCode)" -ForegroundColor Red
                $AllPass = $false
            }

            if ($AllPass) {
                # Step 2: Source intake upload
                $TmpFile = Join-Path $SmokeDir "durability_upload.txt"
                Write-FileLfNoBom -Path $TmpFile -Content "Layer 3 durability probe upload artifact"
                $SeedClientId = [System.Guid]::NewGuid().ToString()
                $Fields = @{
                    client_request_id = $SeedClientId
                    operator_decision  = "record_operator_uploaded_source"
                    source_label       = "Durability probe upload"
                    source_family      = "operator_uploaded_single_source"
                }
                $rs2 = Invoke-MultipartProbeRequest -Url "$ApiBase/source/intake/upload" -Username "smoke-owner" -Password $OwnerPassword -Fields $Fields -FilePath $TmpFile -FileName "durability_upload.txt"
                if ($rs2.StatusCode -eq 201) {
                    try {
                        $parsed = $rs2.Content | ConvertFrom-Json
                        $ProbeSourceIntakeRecordId = [string]$parsed.source_intake_record_id
                    } catch { }
                    if ($ProbeSourceIntakeRecordId -eq "") {
                        # Fail closed: an empty id would vacuously skip every
                        # subsequent durability assertion.
                        Write-Host "  FAIL  Durability seed: upload returned 201 but no source_intake_record_id could be parsed" -ForegroundColor Red
                        $AllPass = $false
                    } else {
                        Write-Host "  Seeded source_intake_record_id: $ProbeSourceIntakeRecordId" -ForegroundColor Gray
                    }
                } else {
                    $excerpt = if ($rs2.Content.Length -gt 300) { $rs2.Content.Substring(0, 300) } else { $rs2.Content }
                    Write-Host "  FAIL  Durability seed step 2 (upload) returned HTTP $($rs2.StatusCode): $excerpt" -ForegroundColor Red
                    $AllPass = $false
                }
            }
        } else {
            Write-Host "  Using seeded source_intake_record_id from probe: $ProbeSourceIntakeRecordId" -ForegroundColor Gray
        }

        if ($AllPass -and $ProbeSourceIntakeRecordId -ne "") {
            # Restart the app container
            Write-Host "  Stopping app container ..." -ForegroundColor Yellow
            & docker compose -f $ComposeFile -f $OverrideFile --env-file $EnvFile stop app
            if ($LASTEXITCODE -ne 0) {
                Write-Host "  FAIL  docker compose stop app failed" -ForegroundColor Red
                $AllPass = $false
            }
        }

        if ($AllPass -and $ProbeSourceIntakeRecordId -ne "") {
            Write-Host "  Starting app container ..." -ForegroundColor Yellow
            & docker compose -f $ComposeFile -f $OverrideFile --env-file $EnvFile start app
            if ($LASTEXITCODE -ne 0) {
                Write-Host "  FAIL  docker compose start app failed" -ForegroundColor Red
                $AllPass = $false
            }
        }

        if ($AllPass -and $ProbeSourceIntakeRecordId -ne "") {
            Write-Host "  Waiting for app to become healthy again (up to 180s) ..." -ForegroundColor Yellow
            $Restarted = Wait-AppHealthy -ComposeFile $ComposeFile -OverrideFile $OverrideFile -EnvFile $EnvFile
            if (-not $Restarted) {
                Write-Host "  FAIL  App did not become healthy after restart within 180s" -ForegroundColor Red
                $AllPass = $false
            }
        }

        if ($AllPass -and $ProbeSourceIntakeRecordId -ne "") {
            # Verify the seeded record survived restart by fetching its preview
            $ApiBase = "$BaseUrl/api/v1/layer3"
            $DurUrl = "$ApiBase/source/intake/$ProbeSourceIntakeRecordId/preview"
            $rdur = Invoke-ProbeRequest -Url $DurUrl -Method GET -Username "smoke-owner" -Password $OwnerPassword
            $PassDur = ($rdur.StatusCode -eq 200)
            Write-Check "Durability: source intake record survived restart (GET /source/intake/{id}/preview -> 200, got $($rdur.StatusCode))" $PassDur
            if (-not $PassDur) {
                $excerpt = if ($rdur.Content.Length -gt 300) { $rdur.Content.Substring(0, 300) } else { $rdur.Content }
                Write-Host "    Response excerpt: $excerpt" -ForegroundColor Red
                $AllPass = $false
            }
        }

        Write-Host ""
    }

    # -----------------------------------------------------------------------
    # BackupRestore check (-BackupRestore)
    # -----------------------------------------------------------------------
    if ($BackupRestore -and -not $AllPass) {
        Write-Host "=== BackupRestore Check skipped: earlier checks failed ===" -ForegroundColor Yellow
        Write-Host ""
    }
    if ($BackupRestore -and $AllPass) {
        Write-Host "=== BackupRestore Check ===" -ForegroundColor Cyan
        Write-Host ""

        $BrDir = Join-Path $SmokeDir "br_backups"
        New-Item -ItemType Directory -Force -Path $BrDir | Out-Null

        try {
            $ApiBase = "$BaseUrl/api/v1/layer3"

            # ---------------------------------------------------------------
            # BR-0: derive compose project name + assert db_data volume present
            # ---------------------------------------------------------------
            Write-Host "  BR-0: Deriving compose project name ..." -ForegroundColor Yellow
            $ComposeProject = $null
            try {
                $configJson = & docker compose -f $ComposeFile -f $OverrideFile --env-file $EnvFile config --format json 2>$null
                $configObj  = $configJson | ConvertFrom-Json
                $ComposeProject = [string]$configObj.name
            } catch { }
            if (-not $ComposeProject) {
                Write-Host "  FAIL  BR-0: could not derive compose project name from config --format json" -ForegroundColor Red
                $AllPass = $false
            } else {
                Write-Host "  Compose project: $ComposeProject" -ForegroundColor Gray
            }

            if ($AllPass) {
                $DbDataVolume     = "${ComposeProject}_db_data"
                $AppStorageVolume = "${ComposeProject}_app_storage"
                $ExportDataVolume = "${ComposeProject}_export_data"

                # Assert db_data volume is present (anchored filter)
                $DbDataPresent = & docker volume ls -q --filter "name=^${DbDataVolume}$"
                $PassBR0 = ($DbDataPresent -eq $DbDataVolume)
                Write-Check "BR-0: db_data volume present (${DbDataVolume})" $PassBR0
                if (-not $PassBR0) { $AllPass = $false }
            }

            if ($AllPass) {
                # Capture pre-destroy volume CreatedAt for identity comparison later (BR-7)
                $BrDbDataPreId = & docker volume inspect -f "{{.CreatedAt}}" $DbDataVolume
                Write-Host "  Pre-destroy db_data CreatedAt: $BrDbDataPreId" -ForegroundColor Gray
            }

            # ---------------------------------------------------------------
            # BR-0b: validate POSTGRES_PASSWORD URL-safety
            # ---------------------------------------------------------------
            if ($AllPass) {
                Write-Host "  BR-0b: Validating POSTGRES_PASSWORD URL-safety ..." -ForegroundColor Yellow
                $EnvFileContent = Get-Content -Raw $EnvFile
                $PgPassMatch = [regex]::Match($EnvFileContent, '(?m)^POSTGRES_PASSWORD=(.+)$')
                $PgPassValue = if ($PgPassMatch.Success) { $PgPassMatch.Groups[1].Value.Trim() } else { "" }
                $PassBR0b = ($PgPassValue -match '^[A-Za-z0-9_-]+$')
                Write-Check "BR-0b: POSTGRES_PASSWORD is URL-safe [A-Za-z0-9_-]" $PassBR0b
                if (-not $PassBR0b) {
                    Write-Host "    POSTGRES_PASSWORD contains characters that would misparse the DATABASE_URL DSN." -ForegroundColor Red
                    $AllPass = $false
                }
            }

            # ---------------------------------------------------------------
            # BR-1: seed (bootstrap GET + multipart upload)
            # ---------------------------------------------------------------
            $BrRecordId      = ""
            $BrContentSha256 = ""

            if ($AllPass) {
                Write-Host "  BR-1: Seeding source intake record ..." -ForegroundColor Yellow

                # Step 1a: Bootstrap
                $brBoot = Invoke-ProbeRequest -Url "$ApiBase/bootstrap" -Method GET -Username "smoke-owner" -Password $OwnerPassword
                $PassBR1Boot = ($brBoot.StatusCode -eq 200)
                Write-Check "BR-1 bootstrap GET /bootstrap -> 200 (got $($brBoot.StatusCode))" $PassBR1Boot
                if (-not $PassBR1Boot) {
                    $AllPass = $false
                }
            }

            if ($AllPass) {
                # Step 1b: multipart upload with a unique nonce so content is
                # byte-distinct from any other smoke run (guards against
                # content-addressed storage reuse masking a restore failure).
                $BrNonce = [System.Guid]::NewGuid().ToString("N")
                $BrUploadContent = "Layer 3 backup-restore probe artifact`nNONCE: $BrNonce`n"
                $BrTmpFile = Join-Path $SmokeDir "br_seed.txt"
                Write-FileLfNoBom -Path $BrTmpFile -Content $BrUploadContent

                $BrClientId = [System.Guid]::NewGuid().ToString()
                $BrFields = @{
                    client_request_id = $BrClientId
                    operator_decision  = "record_operator_uploaded_source"
                    source_label       = "BackupRestore probe seed"
                    source_family      = "operator_uploaded_single_source"
                }
                $brUpload = Invoke-MultipartProbeRequest `
                    -Url "$ApiBase/source/intake/upload" `
                    -Username "smoke-owner" -Password $OwnerPassword `
                    -Fields $BrFields -FilePath $BrTmpFile -FileName "br_seed.txt"

                # Fail closed: empty id must not be silently skipped.
                if ($brUpload.StatusCode -ne 201) {
                    $excerpt = if ($brUpload.Content.Length -gt 300) { $brUpload.Content.Substring(0, 300) } else { $brUpload.Content }
                    Write-Host "  FAIL  BR-1: upload returned HTTP $($brUpload.StatusCode) (expected 201): $excerpt" -ForegroundColor Red
                    $AllPass = $false
                } else {
                    try {
                        $brBody = $brUpload.Content | ConvertFrom-Json
                        $BrRecordId      = [string]$brBody.source_intake_record_id
                        # The 201 response exposes content_sha256 as a top-level field
                        # (confirmed in _record_response() in layer3_source_intake.py).
                        $BrContentSha256 = [string]$brBody.content_sha256
                    } catch { }

                    if ($BrRecordId -eq "") {
                        Write-Host "  FAIL  BR-1: upload returned 201 but source_intake_record_id is empty -- cannot proceed (not skipping)" -ForegroundColor Red
                        $AllPass = $false
                    } else {
                        Write-Host "  Seeded source_intake_record_id: $BrRecordId" -ForegroundColor Gray
                        Write-Host "  content_sha256 (from 201):      $BrContentSha256" -ForegroundColor Gray
                        Write-Check "BR-1: upload 201 + non-empty record id" $true
                    }
                }
            }

            # ---------------------------------------------------------------
            # BR-1b: export sentinel (proves export_data restore is real)
            # ---------------------------------------------------------------
            if ($AllPass) {
                Write-Host "  BR-1b: Writing export sentinel ..." -ForegroundColor Yellow
                $BrSentinelNonce = [System.Guid]::NewGuid().ToString("N")
                & docker compose -f $ComposeFile -f $OverrideFile --env-file $EnvFile `
                    exec -T app sh -c "printf '$BrSentinelNonce' > /app/export-outbox/.br_sentinel"
                $PassBR1b = ($LASTEXITCODE -eq 0)
                Write-Check "BR-1b: export sentinel written to /app/export-outbox/.br_sentinel" $PassBR1b
                if (-not $PassBR1b) { $AllPass = $false }
            }

            # ---------------------------------------------------------------
            # BR-2: pre-existence verify (record is real before destruction)
            # ---------------------------------------------------------------
            if ($AllPass) {
                Write-Host "  BR-2: Pre-existence verify ..." -ForegroundColor Yellow
                $brPreview = Invoke-ProbeRequest -Url "$ApiBase/source/intake/$BrRecordId/preview" -Method GET -Username "smoke-owner" -Password $OwnerPassword
                $PassBR2Status = ($brPreview.StatusCode -eq 200)
                Write-Check "BR-2: GET /source/intake/{id}/preview -> 200 (got $($brPreview.StatusCode))" $PassBR2Status
                if (-not $PassBR2Status) { $AllPass = $false }

                if ($AllPass) {
                    # If content_sha256 was not in 201 (should always be, but be safe),
                    # capture it from the preview response's material_candidate.content_sha256.
                    if ($BrContentSha256 -eq "") {
                        try {
                            $prevBody = $brPreview.Content | ConvertFrom-Json
                            $BrContentSha256 = [string]$prevBody.material_candidate.content_sha256
                            Write-Host "  content_sha256 (from preview):  $BrContentSha256" -ForegroundColor Gray
                        } catch { }
                    }
                    $PassBR2Hash = ($BrContentSha256 -ne "")
                    Write-Check "BR-2: content_sha256 captured (non-empty)" $PassBR2Hash
                    if (-not $PassBR2Hash) { $AllPass = $false }
                }
            }

            # ---------------------------------------------------------------
            # BR-2b: quiesce app (backup-side consistency window)
            # ---------------------------------------------------------------
            if ($AllPass) {
                Write-Host "  BR-2b: Quiescing app for consistent backup ..." -ForegroundColor Yellow
                & docker compose -f $ComposeFile -f $OverrideFile --env-file $EnvFile stop app
                $PassBR2b = ($LASTEXITCODE -eq 0)
                Write-Check "BR-2b: docker compose stop app (quiesce)" $PassBR2b
                if (-not $PassBR2b) { $AllPass = $false }
            }

            # ---------------------------------------------------------------
            # BR-3: pg_dump via cmd redirect (binary fidelity)
            # ---------------------------------------------------------------
            if ($AllPass) {
                Write-Host "  BR-3: pg_dump ..." -ForegroundColor Yellow
                $DumpPath = Join-Path $BrDir "db.pgdump"
                $DumpPathFwd = $DumpPath -replace '\\','/'
                # cmd /c redirect preserves binary fidelity -- PowerShell pipelines
                # re-encode bytes and corrupt pg_dump's binary custom format.
                cmd /c "docker compose -f `"$ComposeFile`" -f `"$OverrideFile`" --env-file `"$EnvFile`" exec -T db pg_dump -U app -d layer3 --format=custom --compress=6 > `"$DumpPath`""
                $PassBR3Exit = ($LASTEXITCODE -eq 0)
                $PassBR3Size = ($PassBR3Exit -and (Test-Path $DumpPath) -and ((Get-Item $DumpPath).Length -gt 0))
                Write-Check "BR-3: pg_dump exit 0 + file non-empty" $PassBR3Size
                if (-not $PassBR3Size) { $AllPass = $false }
            }

            # ---------------------------------------------------------------
            # BR-3b: capture alembic version set
            # ---------------------------------------------------------------
            $BrAlembicSet = @()
            if ($AllPass) {
                Write-Host "  BR-3b: Capturing alembic version set ..." -ForegroundColor Yellow
                $alembicRaw = & docker compose -f $ComposeFile -f $OverrideFile --env-file $EnvFile `
                    exec -T db psql -U app -d layer3 -Atc "SELECT version_num FROM alembic_version ORDER BY version_num"
                $BrAlembicSet = @($alembicRaw | Where-Object { $_ -ne "" } | Sort-Object)
                $PassBR3b = ($BrAlembicSet.Count -gt 0)
                Write-Check "BR-3b: alembic_version set non-empty ($($BrAlembicSet.Count) rows)" $PassBR3b
                if (-not $PassBR3b) { $AllPass = $false }
                else { Write-Host "  Alembic set: $($BrAlembicSet -join ', ')" -ForegroundColor Gray }
            }

            # ---------------------------------------------------------------
            # BR-4: tar app_storage
            # ---------------------------------------------------------------
            if ($AllPass) {
                Write-Host "  BR-4: Backing up app_storage ..." -ForegroundColor Yellow
                $AppStorageArchive = Join-Path $BrDir "app_storage.tar.gz"
                $PassBR4 = Invoke-GnuTarBackup -VolumeName $AppStorageVolume -ArchivePath $AppStorageArchive
                Write-Check "BR-4: app_storage backup + integrity check" $PassBR4
                if (-not $PassBR4) { $AllPass = $false }
            }

            # ---------------------------------------------------------------
            # BR-5: tar export_data
            # ---------------------------------------------------------------
            if ($AllPass) {
                Write-Host "  BR-5: Backing up export_data ..." -ForegroundColor Yellow
                $ExportDataArchive = Join-Path $BrDir "export_data.tar.gz"
                $PassBR5 = Invoke-GnuTarBackup -VolumeName $ExportDataVolume -ArchivePath $ExportDataArchive
                Write-Check "BR-5: export_data backup + integrity check" $PassBR5
                if (-not $PassBR5) { $AllPass = $false }
            }

            # ---------------------------------------------------------------
            # BR-6: destroy stack + verify all three volumes absent
            # ---------------------------------------------------------------
            if ($AllPass) {
                Write-Host "  BR-6: Destroying stack (down -v) ..." -ForegroundColor Yellow
                & docker compose -f $ComposeFile -f $OverrideFile --env-file $EnvFile down -v --remove-orphans
                $PassBR6Down = ($LASTEXITCODE -eq 0)
                Write-Check "BR-6: docker compose down -v exit 0" $PassBR6Down
                if (-not $PassBR6Down) { $AllPass = $false }
            }

            if ($AllPass) {
                # Anchored volume absence checks -- each is its own fail-closed assertion.
                $AbsDb     = & docker volume ls -q --filter "name=^${DbDataVolume}$"
                $PassAbsDb = ($AbsDb -eq "" -or $null -eq $AbsDb)
                Write-Check "BR-6: db_data volume absent after down -v" $PassAbsDb
                if (-not $PassAbsDb) {
                    Write-Host "    Volume still present: $AbsDb" -ForegroundColor Red
                    $AllPass = $false
                }

                $AbsApp     = & docker volume ls -q --filter "name=^${AppStorageVolume}$"
                $PassAbsApp = ($AbsApp -eq "" -or $null -eq $AbsApp)
                Write-Check "BR-6: app_storage volume absent after down -v" $PassAbsApp
                if (-not $PassAbsApp) {
                    Write-Host "    Volume still present: $AbsApp" -ForegroundColor Red
                    $AllPass = $false
                }

                $AbsExp     = & docker volume ls -q --filter "name=^${ExportDataVolume}$"
                $PassAbsExp = ($AbsExp -eq "" -or $null -eq $AbsExp)
                Write-Check "BR-6: export_data volume absent after down -v" $PassAbsExp
                if (-not $PassAbsExp) {
                    Write-Host "    Volume still present: $AbsExp" -ForegroundColor Red
                    $AllPass = $false
                }
            }

            # ---------------------------------------------------------------
            # BR-7: start fresh db + verify new volume ID differs from pre-destroy
            # ---------------------------------------------------------------
            if ($AllPass) {
                Write-Host "  BR-7: Starting fresh db ..." -ForegroundColor Yellow
                & docker compose -f $ComposeFile -f $OverrideFile --env-file $EnvFile up -d db
                if ($LASTEXITCODE -ne 0) {
                    Write-Host "  FAIL  BR-7: docker compose up -d db failed" -ForegroundColor Red
                    $AllPass = $false
                }
            }

            if ($AllPass) {
                $DbWait = Wait-AppHealthy -ComposeFile $ComposeFile -OverrideFile $OverrideFile -EnvFile $EnvFile -ServiceName 'db'
                Write-Check "BR-7: db service healthy after fresh start" $DbWait
                if (-not $DbWait) { $AllPass = $false }
            }

            if ($AllPass) {
                $BrDbDataPostId = & docker volume inspect -f "{{.CreatedAt}}" $DbDataVolume
                $PassBR7Id = ($BrDbDataPostId -ne $BrDbDataPreId)
                Write-Check "BR-7: new db_data CreatedAt differs from pre-destroy (proves real recreation)" $PassBR7Id
                if (-not $PassBR7Id) {
                    Write-Host "    Pre: $BrDbDataPreId  Post: $BrDbDataPostId" -ForegroundColor Red
                    $AllPass = $false
                }
            }

            # ---------------------------------------------------------------
            # BR-8: assert app container is NOT running
            # ---------------------------------------------------------------
            if ($AllPass) {
                $AppContainers = & docker compose -f $ComposeFile -f $OverrideFile --env-file $EnvFile ps -q app
                $PassBR8 = ($AppContainers -eq "" -or $null -eq $AppContainers)
                Write-Check "BR-8: app container not running (do not start before pg_restore)" $PassBR8
                if (-not $PassBR8) { $AllPass = $false }
            }

            # ---------------------------------------------------------------
            # BR-8b: KEYSTONE -- affirmative empty-DB proof before restore
            # ---------------------------------------------------------------
            if ($AllPass) {
                Write-Host "  BR-8b: Affirmative empty-DB check (keystone) ..." -ForegroundColor Yellow
                # Check whether the table even exists yet (fresh DB has no schema).
                $tableCheck = & docker compose -f $ComposeFile -f $OverrideFile --env-file $EnvFile `
                    exec -T db psql -U app -d layer3 -Atc "SELECT to_regclass('public.l3_source_intake_record')"
                $tableCheckStr = [string]$tableCheck
                if ($tableCheckStr.Trim() -eq "" -or $tableCheckStr.Trim() -eq "\N" -or $tableCheckStr.Trim() -eq "null") {
                    # Table does not exist yet -- fresh DB with no schema. This is
                    # the expected state immediately after 'up -d db' on a new volume
                    # before any alembic migrations (app has not started yet).
                    Write-Check "BR-8b: l3_source_intake_record table absent (fresh DB -- correct before restore)" $true
                } else {
                    # Table exists -- assert seeded row is not present. Parse fail-closed:
                    # a non-integer (query error) must FAIL, never masquerade as count 0.
                    $rowCount = & docker compose -f $ComposeFile -f $OverrideFile --env-file $EnvFile `
                        exec -T db psql -U app -d layer3 -Atc "SELECT COUNT(*) FROM l3_source_intake_record WHERE source_intake_record_id='$BrRecordId'"
                    $rowCountStr = ([string]$rowCount).Trim()
                    if ($rowCountStr -match '^\d+$') {
                        $PassBR8b = ([int]$rowCountStr -eq 0)
                    } else {
                        $PassBR8b = $false
                    }
                    Write-Check "BR-8b: seeded row absent in fresh DB (count=$rowCountStr, expected 0)" $PassBR8b
                    if (-not $PassBR8b) {
                        Write-Host "    FAIL: row present (or count query failed) before restore -- volume was NOT destroyed (false-pass risk)" -ForegroundColor Red
                        $AllPass = $false
                    }
                }
            }

            # ---------------------------------------------------------------
            # BR-9: pg_restore via cmd redirect
            # ---------------------------------------------------------------
            if ($AllPass) {
                Write-Host "  BR-9: pg_restore ..." -ForegroundColor Yellow
                $DumpPath = Join-Path $BrDir "db.pgdump"
                cmd /c "docker compose -f `"$ComposeFile`" -f `"$OverrideFile`" --env-file `"$EnvFile`" exec -T db pg_restore -U app -d layer3 --no-owner --role=app --clean --if-exists --exit-on-error --format=custom < `"$DumpPath`""
                $PassBR9 = ($LASTEXITCODE -eq 0)
                Write-Check "BR-9: pg_restore exit 0" $PassBR9
                if (-not $PassBR9) { $AllPass = $false }
            }

            # ---------------------------------------------------------------
            # BR-9b: verify alembic set AND seeded row present after restore
            # ---------------------------------------------------------------
            if ($AllPass) {
                Write-Host "  BR-9b: Verifying restored DB ..." -ForegroundColor Yellow
                $alembicPost = & docker compose -f $ComposeFile -f $OverrideFile --env-file $EnvFile `
                    exec -T db psql -U app -d layer3 -Atc "SELECT version_num FROM alembic_version ORDER BY version_num"
                $BrAlembicSetPost = @($alembicPost | Where-Object { $_ -ne "" } | Sort-Object)

                $PassBR9bAlembic = (($BrAlembicSetPost -join ",") -eq ($BrAlembicSet -join ","))
                Write-Check "BR-9b: alembic_version SET matches backup set ($($BrAlembicSetPost -join ', '))" $PassBR9bAlembic
                if (-not $PassBR9bAlembic) {
                    Write-Host "    Expected: $($BrAlembicSet -join ', ')  Got: $($BrAlembicSetPost -join ', ')" -ForegroundColor Red
                    $AllPass = $false
                }

                if ($AllPass) {
                    $rowCountPost = & docker compose -f $ComposeFile -f $OverrideFile --env-file $EnvFile `
                        exec -T db psql -U app -d layer3 -Atc "SELECT COUNT(*) FROM l3_source_intake_record WHERE source_intake_record_id='$BrRecordId'"
                    # Parse fail-closed: non-integer (query error) must FAIL, not pass.
                    $rowCountPostStr = ([string]$rowCountPost).Trim()
                    if ($rowCountPostStr -match '^\d+$') {
                        $PassBR9bRow = ([int]$rowCountPostStr -eq 1)
                    } else {
                        $PassBR9bRow = $false
                    }
                    Write-Check "BR-9b: seeded row present after pg_restore (count=$rowCountPostStr, expected 1)" $PassBR9bRow
                    if (-not $PassBR9bRow) { $AllPass = $false }
                }
            }

            # ---------------------------------------------------------------
            # BR-10: recreate empty file volumes + restore app_storage
            # ---------------------------------------------------------------
            if ($AllPass) {
                Write-Host "  BR-10: Recreating empty volumes + restoring app_storage ..." -ForegroundColor Yellow
                & docker compose -f $ComposeFile -f $OverrideFile --env-file $EnvFile up --no-start
                if ($LASTEXITCODE -ne 0) {
                    Write-Host "  FAIL  BR-10: docker compose up --no-start failed" -ForegroundColor Red
                    $AllPass = $false
                }
            }

            if ($AllPass) {
                $AppStorageArchive = Join-Path $BrDir "app_storage.tar.gz"
                $PassBR10 = Invoke-GnuTarRestore -VolumeName $AppStorageVolume -ArchivePath $AppStorageArchive
                Write-Check "BR-10: app_storage restored (tar xzf + chown 1001:1001)" $PassBR10
                if (-not $PassBR10) { $AllPass = $false }
            }

            # ---------------------------------------------------------------
            # BR-11: restore export_data + verify sentinel
            # ---------------------------------------------------------------
            if ($AllPass) {
                Write-Host "  BR-11: Restoring export_data ..." -ForegroundColor Yellow
                $ExportDataArchive = Join-Path $BrDir "export_data.tar.gz"
                $PassBR11Restore = Invoke-GnuTarRestore -VolumeName $ExportDataVolume -ArchivePath $ExportDataArchive
                Write-Check "BR-11: export_data restored (tar xzf + chown 1001:1001)" $PassBR11Restore
                if (-not $PassBR11Restore) { $AllPass = $false }
            }

            if ($AllPass) {
                # Verify sentinel fidelity from the restored volume
                $sentinelContent = & docker run --rm `
                    -v "${ExportDataVolume}:/data:ro" `
                    debian:bookworm-slim `
                    sh -c "cat /data/.br_sentinel 2>/dev/null || echo ''"
                $sentinelStr = [string]$sentinelContent
                $PassBR11Sentinel = ($sentinelStr.Trim() -eq $BrSentinelNonce.Trim())
                Write-Check "BR-11: export sentinel content matches nonce after restore" $PassBR11Sentinel
                if (-not $PassBR11Sentinel) {
                    Write-Host "    Expected: '$BrSentinelNonce'  Got: '$($sentinelStr.Trim())'" -ForegroundColor Red
                    $AllPass = $false
                }
            }

            # ---------------------------------------------------------------
            # BR-12: full up + wait healthy (larger budget: 240s)
            # ---------------------------------------------------------------
            if ($AllPass) {
                Write-Host "  BR-12: Starting full stack ..." -ForegroundColor Yellow
                & docker compose -f $ComposeFile -f $OverrideFile --env-file $EnvFile up -d app proxy
                if ($LASTEXITCODE -ne 0) {
                    Write-Host "  FAIL  BR-12: docker compose up -d app proxy failed" -ForegroundColor Red
                    $AllPass = $false
                }
            }

            if ($AllPass) {
                # Budget: 240s > start-period(120s) + retries*interval(3*30s=90s) = 210s worst-case.
                $BrAppHealthy = Wait-AppHealthy `
                    -ComposeFile $ComposeFile -OverrideFile $OverrideFile -EnvFile $EnvFile `
                    -ServiceName 'app' -MaxWait 240
                Write-Check "BR-12: app healthy after full restore up (budget 240s)" $BrAppHealthy
                if (-not $BrAppHealthy) { $AllPass = $false }
            }

            # ---------------------------------------------------------------
            # BR-13: FINAL -- content-hash proof (must be reached unconditionally
            #         when matrix-passed; empty id -> explicit FAIL, not skip)
            # ---------------------------------------------------------------
            Write-Host "  BR-13: Final content-hash proof ..." -ForegroundColor Yellow
            if ($BrRecordId -eq "") {
                # Empty id is an explicit failure, not a skip.
                Write-Check "BR-13: record id is non-empty (required for final assertion)" $false
                $AllPass = $false
            } else {
                $brFinal = Invoke-ProbeRequest -Url "$ApiBase/source/intake/$BrRecordId/preview" -Method GET -Username "smoke-owner" -Password $OwnerPassword
                $PassBR13Status = ($brFinal.StatusCode -eq 200)
                Write-Check "BR-13: GET /source/intake/{id}/preview -> 200 (got $($brFinal.StatusCode))" $PassBR13Status
                if (-not $PassBR13Status) {
                    $AllPass = $false
                } else {
                    # Assert content_sha256 from the restored preview matches what
                    # was captured at upload time. This proves the DB row AND the
                    # uploaded file bytes both survived the destroy+restore cycle
                    # byte-consistently.
                    $FinalSha256 = ""
                    try {
                        $finalBody = $brFinal.Content | ConvertFrom-Json
                        $FinalSha256 = [string]$finalBody.material_candidate.content_sha256
                    } catch { }
                    $PassBR13Hash = ($FinalSha256 -ne "" -and $FinalSha256 -eq $BrContentSha256)
                    Write-Check "BR-13: content_sha256 matches backup value ($FinalSha256)" $PassBR13Hash
                    if (-not $PassBR13Hash) {
                        Write-Host "    Expected: '$BrContentSha256'  Got: '$FinalSha256'" -ForegroundColor Red
                        $AllPass = $false
                    }
                }
            }

            Write-Host ""

        } finally {
            # BR-fin: remove backup artifacts
            if (Test-Path $BrDir) {
                Remove-Item -Recurse -Force $BrDir
            }
        }
    }

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
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
            down -v --remove-orphans
    } elseif ($KeepUp) {
        Write-Host ""
        Write-Host "-KeepUp specified: stack left running on port $ProxyPort" -ForegroundColor Yellow
        Write-Host "Smoke artifacts preserved in $SmokeDir (the running stack's mounts and env point there)." -ForegroundColor Yellow
        Write-Host "Tear down later with:" -ForegroundColor Yellow
        Write-Host "  docker compose -f `"$ComposeFile`" -f `"$OverrideFile`" --env-file `"$EnvFile`" down -v" -ForegroundColor Yellow
        Write-Host "then delete $SmokeDir." -ForegroundColor Yellow
    }
    # Only remove the ephemeral credentials when the stack is gone -- a kept
    # stack still bind-mounts htpasswd/roles.map from this directory and needs
    # the .env/override files for its eventual teardown.
    if (-not $KeepUp -and (Test-Path $SmokeDir)) {
        Remove-Item -Recurse -Force $SmokeDir
    }
}

if (-not $AllPass) {
    exit 1
}
