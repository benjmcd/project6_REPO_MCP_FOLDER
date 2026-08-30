#Requires -Version 5.1

[CmdletBinding(DefaultParameterSetName = 'Validate')]
param(
  [Parameter(Mandatory = $true, ParameterSetName = 'Live')]
  [switch]$Live,

  [Parameter(Mandatory = $true, ParameterSetName = 'Validate')]
  [switch]$ValidateOnly,

  [Parameter(ParameterSetName = 'Live')]
  [string]$RunRoot,

  [Parameter(Mandatory = $true, ParameterSetName = 'Live')]
  [AllowEmptyString()]
  [string]$AuthorizingOwnerToken,

  [Parameter(Mandatory = $true, ParameterSetName = 'Live')]
  [AllowEmptyString()]
  [string]$Reviewer,

  [Parameter(Mandatory = $true, ParameterSetName = 'Live')]
  [AllowEmptyString()]
  [string]$SourceCommit,

  [Parameter(Mandatory = $true, ParameterSetName = 'Live')]
  [AllowEmptyString()]
  [string]$ExpectedScriptSha256,

  [Parameter(Mandatory = $true, ParameterSetName = 'Validate')]
  [string]$SearchBody,

  [Parameter(Mandatory = $true, ParameterSetName = 'Validate')]
  [string]$HydrateBody,

  [Parameter(Mandatory = $true, ParameterSetName = 'Validate')]
  [string]$DownloadBody,

  [Parameter(Mandatory = $true, ParameterSetName = 'Validate')]
  [string]$SearchHeaders,

  [Parameter(Mandatory = $true, ParameterSetName = 'Validate')]
  [string]$HydrateHeaders,

  [Parameter(Mandatory = $true, ParameterSetName = 'Validate')]
  [string]$DownloadHeaders,

  [string]$PythonPath = 'C:\Users\benny\AppData\Local\Programs\Python\Python312\python.exe'
)

Set-StrictMode -Version 5.1
$ErrorActionPreference = 'Stop'

$CurlPath = 'C:\Windows\System32\curl.exe'
$CurlSha256 = '73d24149ff289afc49ec41f08918ef9faa727d39ad993e929757dc2ddafab805'
$CurlBytes = 818512L
$PythonSha256 = '4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a'
$PythonBytes = 104952L
$Doi = '10.5066/P9WCYUI6'
$ExpectedItemId = '63d1a3c6d34e06fef15006be'
$ExpectedFileName = 'mcs2023-germa_salient.csv'
$ExpectedHeader = 'DataSource,Commodity,Year,USprod_Primary_kg,USprod_Secondary_kg,Imports_Metal_kg,Imports_GeO2_kg,Exports_kg,Shipments_Gov_kg,Consump_kg,Price_Metal_dkg,Price_GeO2_dkg,NIR_pct'
$ExpectedHeaderSha256 = '048f103704744d4b39125ec28cb830ac94c0e18b9de93680f57844e5eec96394'
$SearchUrl = 'https://www.sciencebase.gov/catalog/items?q=Mineral%20Commodity%20Summaries%202023%20GERMANIUM&format=json'
$HydrateUrl = 'https://www.sciencebase.gov/catalog/item/63d1a3c6d34e06fef15006be?format=json'
$OutputBase = 'C:\owner-controlled\project6-acq'
$MetadataMaxBytes = 64MB
$ArtifactMaxBytes = 64MB
$ConnectTimeoutSeconds = 10
$MetadataStageSeconds = 30
$ArtifactStageSeconds = 30
$MaximumRequests = 3

function Stop-Hold {
  param([Parameter(Mandatory = $true)][string]$Code)
  $exception = New-Object System.InvalidOperationException($Code)
  $exception.Data['Code'] = $Code
  throw $exception
}

function Get-HoldCode {
  param([Parameter(Mandatory = $true)]$Exception)
  if ($Exception.Data.Contains('Code')) { return [string]$Exception.Data['Code'] }
  return 'internal_error'
}

function Get-UtcTimestamp {
  return [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ss.fffZ', [System.Globalization.CultureInfo]::InvariantCulture)
}

function Get-Sha256Bytes {
  param([Parameter(Mandatory = $true)][AllowEmptyCollection()][byte[]]$Bytes)
  $sha = [System.Security.Cryptography.SHA256]::Create()
  try {
    return ([System.BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-', '').ToLowerInvariant()
  } finally {
    $sha.Dispose()
  }
}

function Get-Sha256File {
  param([Parameter(Mandatory = $true)][string]$Path)
  return Get-Sha256Bytes ([System.IO.File]::ReadAllBytes($Path))
}

function Write-BytesCreateOnce {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][AllowEmptyCollection()][byte[]]$Bytes
  )
  try {
    $stream = [System.IO.File]::Open(
      $Path,
      [System.IO.FileMode]::CreateNew,
      [System.IO.FileAccess]::Write,
      [System.IO.FileShare]::None
    )
  } catch {
    if (Test-Path -LiteralPath $Path) { Stop-Hold 'output_collision' }
    throw
  }
  try {
    $stream.Write($Bytes, 0, $Bytes.Length)
    $stream.Flush($true)
  } finally {
    $stream.Dispose()
  }
}

function Write-Utf8CreateOnce {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][AllowEmptyString()][string]$Text
  )
  $encoding = New-Object System.Text.UTF8Encoding($false, $true)
  Write-BytesCreateOnce -Path $Path -Bytes $encoding.GetBytes($Text)
}

function Get-PhysicalLineCount {
  param([Parameter(Mandatory = $true)][AllowEmptyString()][string]$Text)
  $reader = New-Object System.IO.StringReader($Text)
  $count = 0
  try {
    while ($null -ne $reader.ReadLine()) { $count += 1 }
  } finally {
    $reader.Dispose()
  }
  return $count
}

function ConvertTo-SanitizedHeaders {
  param([Parameter(Mandatory = $true)][AllowEmptyCollection()][byte[]]$Bytes)
  $latin1 = [System.Text.Encoding]::GetEncoding(28591)
  $text = $latin1.GetString($Bytes)
  $state = [pscustomobject]@{ Count = 0 }
  $regex = New-Object System.Text.RegularExpressions.Regex(
    '^((?:Set-Cookie|Cookie)\s*:\s*)([^\r\n]*)',
    ([System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor [System.Text.RegularExpressions.RegexOptions]::Multiline)
  )
  $evaluator = [System.Text.RegularExpressions.MatchEvaluator]{
    param($match)
    $state.Count += 1
    return $match.Groups[1].Value + ('*' * $match.Groups[2].Value.Length)
  }
  $sanitized = $regex.Replace($text, $evaluator)
  $sanitizedBytes = $latin1.GetBytes($sanitized)
  if ($sanitizedBytes.Length -ne $Bytes.Length) { Stop-Hold 'header_redaction_failed' }
  $locationLines = [regex]::Matches($sanitized, '(?im)^Location\s*:').Count
  return [pscustomobject]@{
    Text = $sanitized
    Bytes = $sanitizedBytes
    HeaderLines = Get-PhysicalLineCount $sanitized
    LocationLines = [int]$locationLines
    CookieHeadersObserved = [int]$state.Count
    CookiesRedacted = $true
  }
}

function Get-HeaderInfoFromPath {
  param([Parameter(Mandatory = $true)][string]$Path)
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { Stop-Hold 'header_fixture_missing' }
  return ConvertTo-SanitizedHeaders ([System.IO.File]::ReadAllBytes($Path))
}

$ValidatorCode = @'
import hashlib
import json
import pathlib
import sys

class Hold(Exception):
    pass

def pairs(values):
    out = {}
    for key, value in values:
        if key in out:
            raise ValueError("duplicate JSON key")
        out[key] = value
    return out

def load_json(path, stage):
    try:
        raw = pathlib.Path(path).read_bytes()
        return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=pairs)
    except Exception as exc:
        raise Hold(stage + "_json_invalid") from exc

def first_line(payload):
    cr = payload.find(b"\r")
    lf = payload.find(b"\n")
    candidates = [value for value in (cr, lf) if value >= 0]
    if not candidates:
        return payload, b""
    index = min(candidates)
    width = 2 if payload[index:index + 2] == b"\r\n" else 1
    return payload[:index], payload[index + width:]

mode = sys.argv[1]
path = sys.argv[2]
item_id = sys.argv[3]
file_name = sys.argv[4]
expected_header = sys.argv[5].encode("utf-8")
expected_header_sha256 = sys.argv[6]
artifact_cap = int(sys.argv[7])

try:
    if mode == "search":
        payload = load_json(path, "search")
        if type(payload) is not dict or type(payload.get("items")) is not list:
            raise Hold("search_shape_invalid")
        items = payload["items"]
        if any(type(item) is not dict for item in items):
            raise Hold("search_shape_invalid")
        matches = [item for item in items if type(item.get("id")) is str and item["id"] == item_id]
        if len(matches) != 1:
            raise Hold("search_expected_item_not_unique")
        result = {"exact_matches": len(matches), "returned_items": len(items)}
    elif mode == "hydrate":
        payload = load_json(path, "hydrate")
        if type(payload) is not dict or type(payload.get("id")) is not str or payload["id"] != item_id:
            raise Hold("hydrate_item_id_mismatch")
        files = payload.get("files")
        if type(files) is not list or any(type(entry) is not dict for entry in files):
            raise Hold("hydrate_shape_invalid")
        matches = [entry for entry in files if type(entry.get("name")) is str and entry["name"] == file_name]
        if len(matches) != 1:
            raise Hold("hydrate_expected_file_not_unique")
        entry = matches[0]
        download_uri = entry.get("downloadUri")
        if type(download_uri) is not str or not download_uri.strip():
            raise Hold("downloadUri_missing")
        if "url" not in entry:
            raise Hold("url_downloadUri_alias_missing")
        if type(entry["url"]) is not str or entry["url"] != download_uri:
            raise Hold("url_downloadUri_alias_mismatch")
        advertised = entry.get("size")
        if type(advertised) is int:
            pass
        elif type(advertised) is str and advertised and all("0" <= char <= "9" for char in advertised):
            advertised = int(advertised)
        else:
            raise Hold("hydrate_size_missing_or_nonpositive")
        if advertised <= 0:
            raise Hold("hydrate_size_missing_or_nonpositive")
        if advertised > artifact_cap:
            raise Hold("hydrate_size_exceeds_artifact_cap")
        result = {"download_uri": download_uri, "advertised_size": advertised, "file_matches": 1}
    elif mode == "csv":
        raw = pathlib.Path(path).read_bytes()
        if not raw:
            raise Hold("artifact_empty")
        if raw.startswith(b"\xef\xbb\xbf"):
            payload = raw[3:]
        elif raw.startswith((b"\xff\xfe", b"\xfe\xff", b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")):
            raise Hold("artifact_encoding_rejected")
        else:
            payload = raw
        if not payload:
            raise Hold("artifact_empty")
        header, row_bytes = first_line(payload)
        header_sha256 = hashlib.sha256(header).hexdigest()
        if header != expected_header or header_sha256 != expected_header_sha256:
            raise Hold("artifact_header_mismatch")
        try:
            row_text = row_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise Hold("artifact_encoding_rejected") from exc
        rows = row_text.splitlines()
        if not rows:
            raise Hold("artifact_no_data_rows")
        for row in rows:
            if row.count(",") + 1 != 13:
                raise Hold("artifact_row_column_count")
        result = {
            "header_match": True,
            "columns": 13,
            "rows": len(rows),
            "header_sha256": header_sha256,
        }
    else:
        raise Hold("validator_mode_invalid")
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
except Hold as exc:
    print("HOLD:" + str(exc), file=sys.stderr)
    raise SystemExit(2)
'@

function Invoke-PythonValidator {
  param(
    [Parameter(Mandatory = $true)][ValidateSet('search', 'hydrate', 'csv')][string]$Mode,
    [Parameter(Mandatory = $true)][string]$Path
  )
  $prior = $ErrorActionPreference
  try {
    $ErrorActionPreference = 'Continue'
    $output = @($ValidatorCode | & $PythonPath - $Mode $Path $ExpectedItemId $ExpectedFileName $ExpectedHeader $ExpectedHeaderSha256 ([string]$ArtifactMaxBytes) 2>&1)
    $validatorExit = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $prior
  }
  $text = (@($output | ForEach-Object { [string]$_ }) -join [Environment]::NewLine).Trim()
  if ($validatorExit -ne 0) {
    $match = [regex]::Match($text, 'HOLD:([A-Za-z0-9_]+)')
    if ($match.Success) { Stop-Hold $match.Groups[1].Value }
    Stop-Hold ($Mode + '_validator_failed')
  }
  if ($output.Count -ne 1 -or [string]::IsNullOrWhiteSpace($text)) { Stop-Hold ($Mode + '_validator_output_invalid') }
  try {
    return $text | ConvertFrom-Json
  } catch {
    Stop-Hold ($Mode + '_validator_output_invalid')
  }
}

function Assert-DownloadAuthority {
  param([Parameter(Mandatory = $true)][string]$RawUrl)
  $hasControl = @($RawUrl.ToCharArray() | Where-Object { ([int]$_ -lt 0x20) -or ([int]$_ -eq 0x7F) }).Count -ne 0
  if ([string]::IsNullOrWhiteSpace($RawUrl) -or $RawUrl -cne $RawUrl.Trim() -or $hasControl -or $RawUrl.Contains([string][char]92)) {
    Stop-Hold 'downloadUri_authority_rejected'
  }
  $parsed = $null
  if (-not [uri]::TryCreate($RawUrl, [System.UriKind]::Absolute, [ref]$parsed)) { Stop-Hold 'downloadUri_authority_rejected' }
  if (
    $parsed.Scheme -cne 'https' -or
    $parsed.DnsSafeHost -cne 'www.sciencebase.gov' -or
    -not $parsed.IsDefaultPort -or
    $parsed.Port -ne 443 -or
    $parsed.UserInfo.Length -ne 0 -or
    $parsed.Fragment.Length -ne 0 -or
    $parsed.AbsoluteUri -cne $RawUrl
  ) {
    Stop-Hold 'downloadUri_authority_rejected'
  }
}

function Assert-RuntimeIdentity {
  if (-not (Test-Path -LiteralPath $CurlPath -PathType Leaf)) { Stop-Hold 'curl_missing' }
  if ([long](Get-Item -LiteralPath $CurlPath).Length -ne $CurlBytes) { Stop-Hold 'curl_identity_mismatch' }
  $actualCurlSha256 = Get-Sha256File $CurlPath
  if ($actualCurlSha256 -cne $CurlSha256) { Stop-Hold 'curl_identity_mismatch' }
  if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) { Stop-Hold 'python_missing' }
  if ([long](Get-Item -LiteralPath $PythonPath).Length -ne $PythonBytes) { Stop-Hold 'python_identity_mismatch' }
  $actualPythonSha256 = Get-Sha256File $PythonPath
  if ($actualPythonSha256 -cne $PythonSha256) { Stop-Hold 'python_identity_mismatch' }
  return [pscustomobject]@{
    CurlSha256 = $actualCurlSha256
    PythonSha256 = $actualPythonSha256
  }
}

function Get-BodyRecord {
  param([Parameter(Mandatory = $true)][string]$Path)
  $bytes = [System.IO.File]::ReadAllBytes($Path)
  return [pscustomobject]@{
    Bytes = [long]$bytes.Length
    Sha256 = Get-Sha256Bytes $bytes
  }
}

function Get-ValidatedInputs {
  param(
    [Parameter(Mandatory = $true)][string]$SearchBodyPath,
    [Parameter(Mandatory = $true)][string]$HydrateBodyPath,
    [Parameter(Mandatory = $true)][string]$DownloadBodyPath,
    [Parameter(Mandatory = $true)]$SearchHeaderInfo,
    [Parameter(Mandatory = $true)]$HydrateHeaderInfo,
    [Parameter(Mandatory = $true)]$DownloadHeaderInfo
  )
  foreach ($fixture in @($SearchBodyPath, $HydrateBodyPath, $DownloadBodyPath)) {
    if (-not (Test-Path -LiteralPath $fixture -PathType Leaf)) { Stop-Hold 'body_fixture_missing' }
  }
  if ($SearchHeaderInfo.LocationLines -ne 0) { Stop-Hold 'search_location_rejected' }
  if ($HydrateHeaderInfo.LocationLines -ne 0) { Stop-Hold 'hydrate_location_rejected' }
  if ($DownloadHeaderInfo.LocationLines -ne 0) { Stop-Hold 'download_location_rejected' }
  $search = Invoke-PythonValidator -Mode 'search' -Path $SearchBodyPath
  $hydrate = Invoke-PythonValidator -Mode 'hydrate' -Path $HydrateBodyPath
  Assert-DownloadAuthority ([string]$hydrate.download_uri)
  $content = Invoke-PythonValidator -Mode 'csv' -Path $DownloadBodyPath
  $downloadMeta = Get-BodyRecord $DownloadBodyPath
  if ($downloadMeta.Bytes -ne [long]$hydrate.advertised_size) { Stop-Hold 'artifact_size_mismatch' }
  return [pscustomobject]@{
    Search = $search
    Hydrate = $hydrate
    Content = $content
    SearchHeaders = $SearchHeaderInfo
    HydrateHeaders = $HydrateHeaderInfo
    DownloadHeaders = $DownloadHeaderInfo
    SearchBody = Get-BodyRecord $SearchBodyPath
    HydrateBody = Get-BodyRecord $HydrateBodyPath
    DownloadBody = $downloadMeta
  }
}

function ConvertTo-NativeArgument {
  param([AllowEmptyString()][string]$Value)
  if ($Value.Length -eq 0) { return '""' }
  if ($Value -notmatch '[\s"]') { return $Value }
  $builder = New-Object System.Text.StringBuilder
  [void]$builder.Append('"')
  $slashes = 0
  foreach ($character in $Value.ToCharArray()) {
    if ($character -eq [char]92) {
      $slashes += 1
      continue
    }
    if ($character -eq [char]34) {
      if ($slashes -gt 0) { [void]$builder.Append(('\' * ($slashes * 2))) }
      [void]$builder.Append('\"')
      $slashes = 0
      continue
    }
    if ($slashes -gt 0) {
      [void]$builder.Append(('\' * $slashes))
      $slashes = 0
    }
    [void]$builder.Append($character)
  }
  if ($slashes -gt 0) { [void]$builder.Append(('\' * ($slashes * 2))) }
  [void]$builder.Append('"')
  return $builder.ToString()
}

function Invoke-NativeSeparated {
  param(
    [Parameter(Mandatory = $true)][string]$FilePath,
    [Parameter(Mandatory = $true)][string[]]$Arguments
  )
  $start = New-Object System.Diagnostics.ProcessStartInfo
  $start.FileName = $FilePath
  $start.Arguments = (($Arguments | ForEach-Object { ConvertTo-NativeArgument ([string]$_) }) -join ' ')
  $start.UseShellExecute = $false
  $start.CreateNoWindow = $true
  $start.RedirectStandardOutput = $true
  $start.RedirectStandardError = $true
  $process = New-Object System.Diagnostics.Process
  $process.StartInfo = $start
  if (-not $process.Start()) { Stop-Hold 'native_start_failed' }
  $stdoutBuffer = New-Object System.IO.MemoryStream
  $stdoutTask = $process.StandardOutput.BaseStream.CopyToAsync($stdoutBuffer)
  $stderrTask = $process.StandardError.ReadToEndAsync()
  $process.WaitForExit()
  $stdoutTask.Wait()
  $stdoutBytes = $stdoutBuffer.ToArray()
  $stdoutBuffer.Dispose()
  $stderr = $stderrTask.Result
  $exitCode = $process.ExitCode
  $process.Dispose()
  return [pscustomobject]@{
    ExitCode = $exitCode
    StdoutBytes = $stdoutBytes
    Stderr = $stderr
  }
}

function Get-MetricValue {
  param(
    [Parameter(Mandatory = $true)][AllowEmptyString()][string]$Text,
    [Parameter(Mandatory = $true)][string]$Name
  )
  $match = [regex]::Match($Text, ('(?m)^' + [regex]::Escape($Name) + '=([^\r\n]*)$'))
  if (-not $match.Success) { return '' }
  return $match.Groups[1].Value
}

function Invoke-Stage {
  param(
    [Parameter(Mandatory = $true)][ValidateSet('search', 'hydrate', 'download')][string]$Stage,
    [Parameter(Mandatory = $true)][string]$Url,
    [Parameter(Mandatory = $true)][string]$Accept,
    [Parameter(Mandatory = $true)][long]$MaxBytes,
    [Parameter(Mandatory = $true)][int]$StageSeconds,
    [Parameter(Mandatory = $true)][ref]$RequestCount,
    [Parameter(Mandatory = $true)][string]$Root
  )
  $RequestCount.Value += 1
  if ($RequestCount.Value -gt $MaximumRequests) { Stop-Hold 'request_budget_exceeded' }
  $stageRoot = Join-Path $Root $Stage
  try {
    [void](New-Item -ItemType Directory -Path $stageRoot -ErrorAction Stop)
  } catch {
    if (Test-Path -LiteralPath $stageRoot) { Stop-Hold 'output_collision' }
    throw
  }
  $bodyPath = Join-Path $stageRoot 'body.part'
  $headerPath = Join-Path $stageRoot 'headers.txt'
  $token = [guid]::NewGuid().ToString('N')
  $metricsMarker = '__PROJECT6_ACQ_METRICS_' + $token + '__'
  $writeOut = "%{stderr}`n$metricsMarker`nHTTP_CODE=%{http_code}`nTIME_CONNECT=%{time_connect}`nTIME_TOTAL=%{time_total}`nSIZE_DOWNLOAD=%{size_download}`nURL_EFFECTIVE=%{url_effective}`n"
  $curlArgs = @(
    '--disable', '--silent', '--show-error',
    '--proto', '=https',
    '--noproxy', '*',
    '--globoff',
    '--request', 'GET',
    '--max-redirs', '0',
    '--connect-timeout', [string]$ConnectTimeoutSeconds,
    '--max-time', [string]$StageSeconds,
    '--max-filesize', [string]$MaxBytes,
    '--header', ('Accept: ' + $Accept),
    '--dump-header', '-',
    '--no-clobber',
    '--output', $bodyPath,
    '--write-out', $writeOut,
    '--', $Url
  )
  $startedAt = Get-UtcTimestamp
  $native = Invoke-NativeSeparated -FilePath $CurlPath -Arguments $curlArgs
  $endedAt = Get-UtcTimestamp
  $markerIndex = $native.Stderr.LastIndexOf($metricsMarker, [System.StringComparison]::Ordinal)
  if ($markerIndex -lt 0) {
    $metricsText = ''
  } else {
    $metricsText = $native.Stderr.Substring($markerIndex + $metricsMarker.Length).TrimStart([char[]]@([char]13, [char]10))
  }
  $headers = ConvertTo-SanitizedHeaders $native.StdoutBytes
  Write-BytesCreateOnce -Path $headerPath -Bytes $headers.Bytes
  if (-not (Test-Path -LiteralPath $bodyPath -PathType Leaf)) {
    Write-BytesCreateOnce -Path $bodyPath -Bytes ([byte[]]@())
  }
  $statusText = Get-MetricValue -Text $metricsText -Name 'HTTP_CODE'
  $status = if ($statusText -match '^\d{3}$') { [int]$statusText } else { 0 }
  return [pscustomobject]@{
    Stage = $Stage
    Url = $Url
    ExitCode = [int]$native.ExitCode
    HttpStatus = $status
    BodyPath = $bodyPath
    HeaderPath = $headerPath
    HeaderInfo = $headers
    StartedAt = $startedAt
    EndedAt = $endedAt
  }
}

function Require-Clean200 {
  param([Parameter(Mandatory = $true)]$Result)
  if ($Result.HeaderInfo.LocationLines -ne 0) { Stop-Hold ($Result.Stage + '_location_rejected') }
  if ($Result.ExitCode -eq 28) { Stop-Hold ($Result.Stage + '_timeout') }
  if ($Result.ExitCode -eq 63) { Stop-Hold ($Result.Stage + '_response_too_large') }
  if ($Result.ExitCode -ne 0) { Stop-Hold ($Result.Stage + '_transport_failed') }
  if ($Result.HttpStatus -ne 200) { Stop-Hold ($Result.Stage + '_http_status') }
}

function New-StageRecord {
  param([Parameter(Mandatory = $true)]$Result)
  $body = Get-BodyRecord $Result.BodyPath
  return [ordered]@{
    url = $Result.Url
    http_status = [int]$Result.HttpStatus
    header_lines = [int]$Result.HeaderInfo.HeaderLines
    location_lines = [int]$Result.HeaderInfo.LocationLines
    body_bytes = [long]$body.Bytes
    body_sha256 = $body.Sha256
    started_at = $Result.StartedAt
    ended_at = $Result.EndedAt
  }
}

function New-AcquisitionRecord {
  param(
    [Parameter(Mandatory = $true)]$Stages,
    [Parameter(Mandatory = $true)][string]$ObservedDownloadUri,
    [Parameter(Mandatory = $true)][string]$ArtifactSha256,
    [Parameter(Mandatory = $true)][long]$ArtifactBytes,
    [Parameter(Mandatory = $true)]$ContentContract,
    [Parameter(Mandatory = $true)][AllowEmptyString()][string]$OwnerToken,
    [Parameter(Mandatory = $true)][string]$ReviewerValue,
    [Parameter(Mandatory = $true)][string]$SourceCommitValue,
    [Parameter(Mandatory = $true)][string]$ScriptSha256,
    [Parameter(Mandatory = $true)]$Runtime
  )
  return [ordered]@{
    schema = 'project6.instrument-acquisition.v1'
    doi = $Doi
    item_id = $ExpectedItemId
    filename = $ExpectedFileName
    observed_download_uri = $ObservedDownloadUri
    license = 'CC0 1.0'
    license_source = 'asserted'
    stages = [ordered]@{
      search = $Stages.Search
      hydrate = $Stages.Hydrate
      download = $Stages.Download
    }
    redirect_posture = 'max-redirs=0, no Location observed'
    artifact_sha256 = $ArtifactSha256
    artifact_bytes = $ArtifactBytes
    content_contract = [ordered]@{
      header_match = [bool]$ContentContract.header_match
      columns = [int]$ContentContract.columns
      rows = [int]$ContentContract.rows
      header_sha256 = [string]$ContentContract.header_sha256
    }
    authorizing_owner_token = $OwnerToken
    reviewer = $ReviewerValue
    source_commit = $SourceCommitValue
    script_sha256 = $ScriptSha256
    curl_sha256 = $Runtime.CurlSha256
    python_sha256 = $Runtime.PythonSha256
    no_credential = $true
    cookies_redacted = $true
  }
}

function Assert-RecordSchema {
  param([Parameter(Mandatory = $true)]$Record)
  $topLevel = @(
    'schema', 'doi', 'item_id', 'filename', 'observed_download_uri', 'license', 'license_source',
    'stages', 'redirect_posture', 'artifact_sha256', 'artifact_bytes', 'content_contract',
    'authorizing_owner_token', 'reviewer', 'source_commit', 'script_sha256', 'curl_sha256',
    'python_sha256', 'no_credential', 'cookies_redacted'
  )
  foreach ($name in $topLevel) {
    if (-not $Record.Contains($name)) { Stop-Hold 'record_schema_invalid' }
  }
  if ($Record.Count -ne $topLevel.Count -or $Record.schema -cne 'project6.instrument-acquisition.v1') { Stop-Hold 'record_schema_invalid' }
  $stageFields = @('url', 'http_status', 'header_lines', 'location_lines', 'body_bytes', 'body_sha256', 'started_at', 'ended_at')
  foreach ($stageName in @('search', 'hydrate', 'download')) {
    if (-not $Record.stages.Contains($stageName)) { Stop-Hold 'record_schema_invalid' }
    $stage = $Record.stages[$stageName]
    foreach ($field in $stageFields) {
      if (-not $stage.Contains($field)) { Stop-Hold 'record_schema_invalid' }
    }
    if ($stage.Count -ne $stageFields.Count -or [int]$stage.location_lines -ne 0) { Stop-Hold 'record_schema_invalid' }
    if ([string]$stage.body_sha256 -cnotmatch '^[0-9a-f]{64}$') { Stop-Hold 'record_schema_invalid' }
    if (-not ([string]$stage.started_at).EndsWith('Z') -or -not ([string]$stage.ended_at).EndsWith('Z')) { Stop-Hold 'record_schema_invalid' }
  }
  if ($Record.stages.download.url -cne $Record.observed_download_uri) { Stop-Hold 'record_schema_invalid' }
  if ($Record.stages.download.body_sha256 -cne $Record.artifact_sha256) { Stop-Hold 'record_schema_invalid' }
  if ([long]$Record.stages.download.body_bytes -ne [long]$Record.artifact_bytes) { Stop-Hold 'record_schema_invalid' }
  if ($Record.artifact_sha256 -cnotmatch '^[0-9a-f]{64}$' -or $Record.source_commit -cnotmatch '^[0-9a-f]{40}$') { Stop-Hold 'record_schema_invalid' }
  if ($Record.script_sha256 -cnotmatch '^[0-9a-f]{64}$' -or $Record.curl_sha256 -cnotmatch '^[0-9a-f]{64}$' -or $Record.python_sha256 -cnotmatch '^[0-9a-f]{64}$') { Stop-Hold 'record_schema_invalid' }
  if (-not [bool]$Record.no_credential -or -not [bool]$Record.cookies_redacted) { Stop-Hold 'record_schema_invalid' }
  return $true
}

function New-ProbeStageRecord {
  param(
    [Parameter(Mandatory = $true)][string]$Url,
    [Parameter(Mandatory = $true)]$Body,
    [Parameter(Mandatory = $true)]$Headers
  )
  $timestamp = Get-UtcTimestamp
  return [ordered]@{
    url = $Url
    http_status = 200
    header_lines = [int]$Headers.HeaderLines
    location_lines = [int]$Headers.LocationLines
    body_bytes = [long]$Body.Bytes
    body_sha256 = $Body.Sha256
    started_at = $timestamp
    ended_at = $timestamp
  }
}

function Invoke-ValidateOnly {
  param([Parameter(Mandatory = $true)]$Runtime)
  $searchHeaderInfo = Get-HeaderInfoFromPath $SearchHeaders
  $hydrateHeaderInfo = Get-HeaderInfoFromPath $HydrateHeaders
  $downloadHeaderInfo = Get-HeaderInfoFromPath $DownloadHeaders
  $validated = Get-ValidatedInputs `
    -SearchBodyPath $SearchBody `
    -HydrateBodyPath $HydrateBody `
    -DownloadBodyPath $DownloadBody `
    -SearchHeaderInfo $searchHeaderInfo `
    -HydrateHeaderInfo $hydrateHeaderInfo `
    -DownloadHeaderInfo $downloadHeaderInfo
  $stages = [pscustomobject]@{
    Search = New-ProbeStageRecord -Url $SearchUrl -Body $validated.SearchBody -Headers $validated.SearchHeaders
    Hydrate = New-ProbeStageRecord -Url $HydrateUrl -Body $validated.HydrateBody -Headers $validated.HydrateHeaders
    Download = New-ProbeStageRecord -Url ([string]$validated.Hydrate.download_uri) -Body $validated.DownloadBody -Headers $validated.DownloadHeaders
  }
  $scriptSha256 = Get-Sha256File $PSCommandPath
  $probe = New-AcquisitionRecord `
    -Stages $stages `
    -ObservedDownloadUri ([string]$validated.Hydrate.download_uri) `
    -ArtifactSha256 $validated.DownloadBody.Sha256 `
    -ArtifactBytes $validated.DownloadBody.Bytes `
    -ContentContract $validated.Content `
    -OwnerToken 'OFFLINE-TEST-NOT-AUTHORIZATION' `
    -ReviewerValue 'offline-validation' `
    -SourceCommitValue (('0' * 39) + '1') `
    -ScriptSha256 $scriptSha256 `
    -Runtime $Runtime
  [void](Assert-RecordSchema $probe)
  return [ordered]@{
    mode = 'offline_validation'
    request_count = 0
    search_membership = [ordered]@{
      exact_matches = [int]$validated.Search.exact_matches
      returned_items = [int]$validated.Search.returned_items
    }
    observed_download_uri = [string]$validated.Hydrate.download_uri
    content_contract = [ordered]@{
      header_match = [bool]$validated.Content.header_match
      columns = [int]$validated.Content.columns
      rows = [int]$validated.Content.rows
      header_sha256 = [string]$validated.Content.header_sha256
    }
    artifact_sha256 = $validated.DownloadBody.Sha256
    artifact_bytes = [long]$validated.DownloadBody.Bytes
    headers = [ordered]@{
      search = [ordered]@{
        header_lines = [int]$validated.SearchHeaders.HeaderLines
        location_lines = [int]$validated.SearchHeaders.LocationLines
        cookie_headers_observed = [int]$validated.SearchHeaders.CookieHeadersObserved
        cookies_redacted = [bool]$validated.SearchHeaders.CookiesRedacted
      }
      hydrate = [ordered]@{
        header_lines = [int]$validated.HydrateHeaders.HeaderLines
        location_lines = [int]$validated.HydrateHeaders.LocationLines
        cookie_headers_observed = [int]$validated.HydrateHeaders.CookieHeadersObserved
        cookies_redacted = [bool]$validated.HydrateHeaders.CookiesRedacted
      }
      download = [ordered]@{
        header_lines = [int]$validated.DownloadHeaders.HeaderLines
        location_lines = [int]$validated.DownloadHeaders.LocationLines
        cookie_headers_observed = [int]$validated.DownloadHeaders.CookieHeadersObserved
        cookies_redacted = [bool]$validated.DownloadHeaders.CookiesRedacted
      }
    }
    runtime = [ordered]@{
      curl_sha256 = $Runtime.CurlSha256
      python_sha256 = $Runtime.PythonSha256
    }
    validator_transport = 'stdin-python-dash'
    record_schema = [ordered]@{
      schema = 'project6.instrument-acquisition.v1'
      validated = $true
    }
  }
}

function Assert-NonElevated {
  $identity = $null
  try {
    $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object System.Security.Principal.WindowsPrincipal($identity)
    if ($principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
      Stop-Hold 'elevated_process_rejected'
    }
  } catch {
    if ($_.Exception.Data.Contains('Code')) { throw }
    Stop-Hold 'privilege_check_failed'
  } finally {
    if ($null -ne $identity) { $identity.Dispose() }
  }
}

function Assert-LiveInputs {
  if ($SourceCommit -cnotmatch '^[0-9a-f]{40}$') { Stop-Hold 'source_commit_invalid' }
  if ($ExpectedScriptSha256 -cnotmatch '^[0-9a-f]{64}$') { Stop-Hold 'script_sha256_invalid' }
  if ([string]::IsNullOrWhiteSpace($AuthorizingOwnerToken) -or $AuthorizingOwnerToken -match '^<.*>$' -or $AuthorizingOwnerToken.StartsWith('OFFLINE-TEST')) {
    Stop-Hold 'owner_token_missing'
  }
  if ([string]::IsNullOrWhiteSpace($Reviewer) -or $Reviewer -ceq '<thread>') { Stop-Hold 'reviewer_missing' }
  $actualScriptSha256 = Get-Sha256File $PSCommandPath
  if ($actualScriptSha256 -cne $ExpectedScriptSha256) { Stop-Hold 'script_sha256_mismatch' }
  return $actualScriptSha256
}

function New-RunRoot {
  param([AllowEmptyString()][string]$RequestedRoot)
  $base = [System.IO.Path]::GetFullPath($OutputBase).TrimEnd([char[]]@([char]92, [char]47))
  if (-not (Test-Path -LiteralPath $base -PathType Container)) { Stop-Hold 'output_base_missing' }
  $baseItem = Get-Item -LiteralPath $base
  if (($baseItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) { Stop-Hold 'output_base_reparse_rejected' }
  if ([string]::IsNullOrWhiteSpace($RequestedRoot)) {
    $runId = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ', [System.Globalization.CultureInfo]::InvariantCulture) + '-' + [guid]::NewGuid().ToString('N')
    $RequestedRoot = Join-Path $base $runId
  }
  $full = [System.IO.Path]::GetFullPath($RequestedRoot).TrimEnd([char[]]@([char]92, [char]47))
  $parent = [System.IO.Path]::GetDirectoryName($full).TrimEnd([char[]]@([char]92, [char]47))
  if (-not $parent.Equals($base, [System.StringComparison]::OrdinalIgnoreCase)) { Stop-Hold 'run_root_outside_base' }
  if (Test-Path -LiteralPath $full) { Stop-Hold 'output_collision' }
  try {
    [void](New-Item -ItemType Directory -Path $full -ErrorAction Stop)
  } catch {
    if (Test-Path -LiteralPath $full) { Stop-Hold 'output_collision' }
    throw
  }
  $created = Get-Item -LiteralPath $full
  if (($created.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) { Stop-Hold 'run_root_reparse_rejected' }
  return $full
}

function Invoke-LiveAcquisition {
  param([Parameter(Mandatory = $true)]$Runtime)
  $scriptSha256 = Assert-LiveInputs
  Assert-NonElevated
  $root = New-RunRoot $RunRoot
  $requestCount = 0

  $search = Invoke-Stage -Stage 'search' -Url $SearchUrl -Accept 'application/json' `
    -MaxBytes $MetadataMaxBytes -StageSeconds $MetadataStageSeconds `
    -RequestCount ([ref]$requestCount) -Root $root
  Require-Clean200 $search
  $searchValidation = Invoke-PythonValidator -Mode 'search' -Path $search.BodyPath

  $hydrate = Invoke-Stage -Stage 'hydrate' -Url $HydrateUrl -Accept 'application/json' `
    -MaxBytes $MetadataMaxBytes -StageSeconds $MetadataStageSeconds `
    -RequestCount ([ref]$requestCount) -Root $root
  Require-Clean200 $hydrate
  $hydrateValidation = Invoke-PythonValidator -Mode 'hydrate' -Path $hydrate.BodyPath
  Assert-DownloadAuthority ([string]$hydrateValidation.download_uri)

  $download = Invoke-Stage -Stage 'download' -Url ([string]$hydrateValidation.download_uri) -Accept '*/*' `
    -MaxBytes ([long]$hydrateValidation.advertised_size) -StageSeconds $ArtifactStageSeconds `
    -RequestCount ([ref]$requestCount) -Root $root
  Require-Clean200 $download
  $content = Invoke-PythonValidator -Mode 'csv' -Path $download.BodyPath
  $downloadBody = Get-BodyRecord $download.BodyPath
  if ($downloadBody.Bytes -ne [long]$hydrateValidation.advertised_size) { Stop-Hold 'artifact_size_mismatch' }
  if ($requestCount -ne 3) { Stop-Hold 'request_budget_incomplete' }

  $artifactPath = Join-Path $root $ExpectedFileName
  $artifactBytes = [System.IO.File]::ReadAllBytes($download.BodyPath)
  Write-BytesCreateOnce -Path $artifactPath -Bytes $artifactBytes
  $delivered = Get-BodyRecord $artifactPath
  if ($delivered.Bytes -ne $downloadBody.Bytes -or $delivered.Sha256 -cne $downloadBody.Sha256) { Stop-Hold 'artifact_persist_failed' }

  $stages = [pscustomobject]@{
    Search = New-StageRecord $search
    Hydrate = New-StageRecord $hydrate
    Download = New-StageRecord $download
  }
  $record = New-AcquisitionRecord `
    -Stages $stages `
    -ObservedDownloadUri ([string]$hydrateValidation.download_uri) `
    -ArtifactSha256 $delivered.Sha256 `
    -ArtifactBytes $delivered.Bytes `
    -ContentContract $content `
    -OwnerToken $AuthorizingOwnerToken `
    -ReviewerValue $Reviewer `
    -SourceCommitValue $SourceCommit `
    -ScriptSha256 $scriptSha256 `
    -Runtime $Runtime
  [void](Assert-RecordSchema $record)
  $recordPath = Join-Path $root 'acquisition-record.json'
  Write-Utf8CreateOnce -Path $recordPath -Text ($record | ConvertTo-Json -Depth 10)
  return [ordered]@{
    terminal = 'acquired'
    request_count = $requestCount
    run_root = $root
    artifact = $artifactPath
    acquisition_record = $recordPath
    artifact_sha256 = $delivered.Sha256
    artifact_bytes = [long]$delivered.Bytes
    source_commit = $SourceCommit
    script_sha256 = $scriptSha256
  }
}

try {
  $runtimeIdentity = Assert-RuntimeIdentity
  if ($ValidateOnly) {
    $result = Invoke-ValidateOnly $runtimeIdentity
  } else {
    $result = Invoke-LiveAcquisition $runtimeIdentity
  }
  Write-Output ($result | ConvertTo-Json -Depth 10 -Compress)
  exit 0
} catch {
  $code = Get-HoldCode $_.Exception
  Write-Output ('terminal=hold:' + $code)
  Write-Output ('code=' + $code)
  exit 2
}
