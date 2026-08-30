#Requires -Version 5.1

[CmdletBinding()]
param(
  [string]$PythonPath = 'C:\Users\benny\AppData\Local\Programs\Python\Python312\python.exe'
)

Set-StrictMode -Version 5.1
$ErrorActionPreference = 'Stop'

$Subject = Join-Path $PSScriptRoot 'sciencebase-instrument-acquisition.ps1'
$PowerShellExe = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
$ExpectedItemId = '63d1a3c6d34e06fef15006be'
$ExpectedFileName = 'mcs2023-germa_salient.csv'
$ExpectedHeader = 'DataSource,Commodity,Year,USprod_Primary_kg,USprod_Secondary_kg,Imports_Metal_kg,Imports_GeO2_kg,Exports_kg,Shipments_Gov_kg,Consump_kg,Price_Metal_dkg,Price_GeO2_dkg,NIR_pct'
$ExpectedHeaderSha256 = '048f103704744d4b39125ec28cb830ac94c0e18b9de93680f57844e5eec96394'
$ExpectedDownloadUri = 'https://www.sciencebase.gov/catalog/file/get/63d1a3c6d34e06fef15006be?f=__disk__7e%2F49%2Fe8%2F7e49e8a4a53eb2219837f97defb22a25a286cdbc'
$ExpectedCurlSha256 = '73d24149ff289afc49ec41f08918ef9faa727d39ad993e929757dc2ddafab805'
$ExpectedPythonSha256 = '4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a'

$PositiveSearch = 'C:\p6-sb-char-2\search-ce9b88f9569c481fa714940b2afe3124\body.part'
$PositiveHydrate = 'C:\p6-sb-char-2\hydrate-3f033238441d488580891defe30357a9\body.part'
$PositiveDownload = 'C:\p6-sb-char-2\mcs2023-germa_salient.c8eacb7b8df0aa12b45eeb383d79d5cf95d7e002dfed7c07736e5aad3dca930c.csv'
$NegativeSearch = 'C:\p6-sb-char\search-2b46f6b2479748058162a0ca5eb5ddca\body.part'
$PositiveSearchHeaders = 'C:\p6-sb-char-2\search-ce9b88f9569c481fa714940b2afe3124\headers.part'
$PositiveHydrateHeaders = 'C:\p6-sb-char-2\hydrate-3f033238441d488580891defe30357a9\headers.part'
$PositiveDownloadHeaders = 'C:\p6-sb-char-2\download-b74f9868da754cad9889b25870391156\headers.part'

function Assert-True {
  param(
    [Parameter(Mandatory = $true)][bool]$Condition,
    [Parameter(Mandatory = $true)][string]$Message
  )
  if (-not $Condition) { throw $Message }
}

function Assert-Equal {
  param(
    [AllowNull()]$Actual,
    [AllowNull()]$Expected,
    [Parameter(Mandatory = $true)][string]$Message
  )
  if ($Actual -cne $Expected) {
    throw ("{0} Expected={1} Actual={2}" -f $Message, $Expected, $Actual)
  }
}

function Write-BytesCreateOnce {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][AllowEmptyCollection()][byte[]]$Bytes
  )
  $stream = [System.IO.File]::Open(
    $Path,
    [System.IO.FileMode]::CreateNew,
    [System.IO.FileAccess]::Write,
    [System.IO.FileShare]::None
  )
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

function Assert-Fixture {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][long]$Bytes,
    [Parameter(Mandatory = $true)][string]$Sha256
  )
  Assert-True (Test-Path -LiteralPath $Path -PathType Leaf) ("Missing retained fixture: {0}" -f $Path)
  Assert-Equal ([long](Get-Item -LiteralPath $Path).Length) $Bytes ("Fixture byte drift: {0}." -f $Path)
  Assert-Equal ((Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()) $Sha256 ("Fixture hash drift: {0}." -f $Path)
}

function Invoke-Subject {
  param(
    [Parameter(Mandatory = $true)][string]$SearchBody,
    [Parameter(Mandatory = $true)][string]$HydrateBody,
    [Parameter(Mandatory = $true)][string]$DownloadBody,
    [Parameter(Mandatory = $true)][string]$SearchHeaders,
    [Parameter(Mandatory = $true)][string]$HydrateHeaders,
    [Parameter(Mandatory = $true)][string]$DownloadHeaders
  )
  $arguments = @(
    '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
    '-File', $Subject,
    '-ValidateOnly',
    '-SearchBody', $SearchBody,
    '-HydrateBody', $HydrateBody,
    '-DownloadBody', $DownloadBody,
    '-SearchHeaders', $SearchHeaders,
    '-HydrateHeaders', $HydrateHeaders,
    '-DownloadHeaders', $DownloadHeaders,
    '-PythonPath', $PythonPath
  )
  $raw = @(& $PowerShellExe @arguments 2>&1)
  $exitCode = $LASTEXITCODE
  $text = (@($raw | ForEach-Object { [string]$_ }) -join [Environment]::NewLine).Trim()
  return [pscustomobject]@{
    ExitCode = $exitCode
    Text = $text
  }
}

function Assert-Hold {
  param(
    [Parameter(Mandatory = $true)]$Result,
    [Parameter(Mandatory = $true)][string]$Code
  )
  Assert-True ($Result.ExitCode -ne 0) ("Expected HOLD {0}, but validation exited zero." -f $Code)
  Assert-True ($Result.Text.Contains('terminal=hold:' + $Code)) ("Expected HOLD {0}. Output: {1}" -f $Code, $Result.Text)
}

Assert-True (Test-Path -LiteralPath $Subject -PathType Leaf) ("RED: production script missing: {0}" -f $Subject)
Assert-True (Test-Path -LiteralPath $PowerShellExe -PathType Leaf) 'Windows PowerShell 5.1 executable is unavailable.'

Assert-Fixture -Path $PositiveSearch -Bytes 737 -Sha256 '55e3c10d928ef29a51a4bdd31c3863a321b12035f04a6ca857ab4088440aa215'
Assert-Fixture -Path $PositiveHydrate -Bytes 8991 -Sha256 '56efa301bab2a0b589c6df5b305838ab4cae25edc4f54dea35093ddcf566509a'
Assert-Fixture -Path $PositiveDownload -Bytes 510 -Sha256 'c8eacb7b8df0aa12b45eeb383d79d5cf95d7e002dfed7c07736e5aad3dca930c'
Assert-Fixture -Path $NegativeSearch -Bytes 11720 -Sha256 'f5cd654a84271a1e443d3e76ff08d5ccf3d7428d9edbc02e9859265d2be183a2'
Assert-Fixture -Path $PositiveSearchHeaders -Bytes 3234 -Sha256 '085e6c398a3a805e5c2ff83dbacdc1d14a68ff232a76723c50ca37f276d41d0b'
Assert-Fixture -Path $PositiveHydrateHeaders -Bytes 3280 -Sha256 '8471a6c3a94f5f004b602fbc0d1a21771285f79853803b0597bf979b5933d77c'
Assert-Fixture -Path $PositiveDownloadHeaders -Bytes 3401 -Sha256 '5fcfe79d0add22df6f6658121174f67e1ef9b5bbfd82d2b4389d9a6f95bc68d3'

$source = [System.IO.File]::ReadAllText($Subject)
foreach ($forbidden in @('dual_live_', 'AppContainer', 'spent-marker', 'harness', 'signature', 'provisioning', 'Invoke-WebRequest', 'Start-BitsTransfer')) {
  Assert-True ($source.IndexOf($forbidden, [System.StringComparison]::OrdinalIgnoreCase) -lt 0) ("Forbidden dependency or path present: {0}." -f $forbidden)
}
Assert-True (-not [regex]::IsMatch($source, '(?im)&\s*\$[A-Za-z][A-Za-z0-9_]*\s+-c(?:\s|$)')) 'Validator uses the forbidden native python -c form.'
foreach ($requiredSourceToken in @(
  "[switch]`$Live",
  "[switch]`$ValidateOnly",
  '[string]$SourceCommit',
  '[string]$ExpectedScriptSha256',
  '$identity = $null',
  'IsNullOrWhiteSpace($AuthorizingOwnerToken)',
  "'--disable'", "'--proto', '=https'", "'--noproxy', '*'", "'--globoff'", "'--max-redirs', '0'"
)) {
  Assert-True ($source.Contains($requiredSourceToken)) ("Required source token missing: {0}." -f $requiredSourceToken)
}
foreach ($stageName in @('search', 'hydrate', 'download')) {
  $stagePattern = "Invoke-Stage -Stage '" + $stageName + "'"
  Assert-Equal ([regex]::Matches($source, [regex]::Escape($stagePattern)).Count) 1 ("Live stage invocation count drift: {0}." -f $stageName)
}

$positive = Invoke-Subject `
  -SearchBody $PositiveSearch `
  -HydrateBody $PositiveHydrate `
  -DownloadBody $PositiveDownload `
  -SearchHeaders $PositiveSearchHeaders `
  -HydrateHeaders $PositiveHydrateHeaders `
  -DownloadHeaders $PositiveDownloadHeaders
Assert-Equal $positive.ExitCode 0 ("Positive validation failed: {0}" -f $positive.Text)
$summary = $positive.Text | ConvertFrom-Json
Assert-Equal $summary.mode 'offline_validation' 'Wrong validation mode.'
Assert-Equal ([int]$summary.request_count) 0 'Validate-only mode reached a request path.'
Assert-Equal ([int]$summary.search_membership.exact_matches) 1 'Search target cardinality drift.'
Assert-Equal ([int]$summary.search_membership.returned_items) 1 'Positive search fixture item count drift.'
Assert-Equal $summary.observed_download_uri $ExpectedDownloadUri 'Observed download URI drift.'
Assert-True ([bool]$summary.content_contract.header_match) 'Header contract did not pass.'
Assert-Equal ([int]$summary.content_contract.columns) 13 'Column count drift.'
Assert-Equal ([int]$summary.content_contract.rows) 5 'Data row count drift.'
Assert-Equal $summary.content_contract.header_sha256 $ExpectedHeaderSha256 'Header hash drift.'
Assert-Equal $summary.artifact_sha256 'c8eacb7b8df0aa12b45eeb383d79d5cf95d7e002dfed7c07736e5aad3dca930c' 'Artifact hash drift.'
Assert-Equal ([long]$summary.artifact_bytes) 510 'Artifact byte count drift.'
Assert-Equal $summary.runtime.curl_sha256 $ExpectedCurlSha256 'Curl identity drift.'
Assert-Equal $summary.runtime.python_sha256 $ExpectedPythonSha256 'Python identity drift.'
Assert-Equal $summary.validator_transport 'stdin-python-dash' 'Validator transport drift.'
Assert-True ([bool]$summary.record_schema.validated) 'Record builder/schema probe failed.'
Assert-Equal $summary.record_schema.schema 'project6.instrument-acquisition.v1' 'Record schema drift.'
Assert-Equal ([int]$summary.headers.search.header_lines) 22 'Search header-line count drift.'
Assert-Equal ([int]$summary.headers.hydrate.header_lines) 23 'Hydrate header-line count drift.'
Assert-Equal ([int]$summary.headers.download.header_lines) 26 'Download header-line count drift.'
Assert-Equal ([int]$summary.headers.search.location_lines) 0 'Unexpected retained search Location.'
Assert-True ([bool]$summary.headers.search.cookies_redacted) 'Search cookie-redaction claim is false.'

$broadSearch = Invoke-Subject `
  -SearchBody $NegativeSearch `
  -HydrateBody $PositiveHydrate `
  -DownloadBody $PositiveDownload `
  -SearchHeaders $PositiveSearchHeaders `
  -HydrateHeaders $PositiveHydrateHeaders `
  -DownloadHeaders $PositiveDownloadHeaders
Assert-Hold $broadSearch 'search_expected_item_not_unique'

$syntheticRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('p6-acq-offline-' + [guid]::NewGuid().ToString('N'))
[void](New-Item -ItemType Directory -Path $syntheticRoot -ErrorAction Stop)
$wrongHeaderPath = Join-Path $syntheticRoot 'wrong-header.csv'
$shortRowPath = Join-Path $syntheticRoot 'row-12.csv'
$emptyPath = Join-Path $syntheticRoot 'empty.csv'
$noRowsPath = Join-Path $syntheticRoot 'no-rows.csv'
$redirectPath = Join-Path $syntheticRoot 'redirect.headers'
$cookiePath = Join-Path $syntheticRoot 'cookie.headers'
$duplicateSearchPath = Join-Path $syntheticRoot 'duplicate-search.json'
$badHostHydratePath = Join-Path $syntheticRoot 'bad-host.json'
$missingAliasHydratePath = Join-Path $syntheticRoot 'missing-alias.json'
$fractionalSizeHydratePath = Join-Path $syntheticRoot 'fractional-size.json'

Write-Utf8CreateOnce -Path $wrongHeaderPath -Text (('Wrong,' + (($ExpectedHeader.Split(',') | Select-Object -Skip 1) -join ',')) + "`r`n" + ((1..13) -join ',') + "`r`n")
Write-Utf8CreateOnce -Path $shortRowPath -Text ($ExpectedHeader + "`r`n" + ((1..12) -join ',') + "`r`n")
Write-BytesCreateOnce -Path $emptyPath -Bytes ([byte[]]@())
Write-Utf8CreateOnce -Path $noRowsPath -Text ($ExpectedHeader + "`r`n")
Write-Utf8CreateOnce -Path $redirectPath -Text "HTTP/1.1 302 Found`r`nLocation: https://www.sciencebase.gov/other`r`n`r`n"
Write-Utf8CreateOnce -Path $cookiePath -Text "HTTP/1.1 200 OK`r`nSet-Cookie: OFFLINE-SECRET=must-not-escape`r`n`r`n"
Write-Utf8CreateOnce -Path $duplicateSearchPath -Text ('{"items":[{"id":"' + $ExpectedItemId + '","id":"' + $ExpectedItemId + '"}]}')
Write-Utf8CreateOnce -Path $badHostHydratePath -Text ('{"id":"' + $ExpectedItemId + '","files":[{"name":"' + $ExpectedFileName + '","size":510,"url":"https://example.invalid/file","downloadUri":"https://example.invalid/file"}]}')
Write-Utf8CreateOnce -Path $missingAliasHydratePath -Text ('{"id":"' + $ExpectedItemId + '","files":[{"name":"' + $ExpectedFileName + '","size":510,"downloadUri":"' + $ExpectedDownloadUri + '"}]}')
Write-Utf8CreateOnce -Path $fractionalSizeHydratePath -Text ('{"id":"' + $ExpectedItemId + '","files":[{"name":"' + $ExpectedFileName + '","size":510.5,"url":"' + $ExpectedDownloadUri + '","downloadUri":"' + $ExpectedDownloadUri + '"}]}')

foreach ($case in @(
  [pscustomobject]@{ Name = 'wrong header'; Download = $wrongHeaderPath; Code = 'artifact_header_mismatch' },
  [pscustomobject]@{ Name = '12-column row'; Download = $shortRowPath; Code = 'artifact_row_column_count' },
  [pscustomobject]@{ Name = 'empty artifact'; Download = $emptyPath; Code = 'artifact_empty' },
  [pscustomobject]@{ Name = 'zero data rows'; Download = $noRowsPath; Code = 'artifact_no_data_rows' }
)) {
  $result = Invoke-Subject `
    -SearchBody $PositiveSearch `
    -HydrateBody $PositiveHydrate `
    -DownloadBody $case.Download `
    -SearchHeaders $PositiveSearchHeaders `
    -HydrateHeaders $PositiveHydrateHeaders `
    -DownloadHeaders $PositiveDownloadHeaders
  Assert-Hold $result $case.Code
}

$redirect = Invoke-Subject `
  -SearchBody $PositiveSearch `
  -HydrateBody $PositiveHydrate `
  -DownloadBody $PositiveDownload `
  -SearchHeaders $redirectPath `
  -HydrateHeaders $PositiveHydrateHeaders `
  -DownloadHeaders $PositiveDownloadHeaders
Assert-Hold $redirect 'search_location_rejected'

$duplicateJson = Invoke-Subject `
  -SearchBody $duplicateSearchPath `
  -HydrateBody $PositiveHydrate `
  -DownloadBody $PositiveDownload `
  -SearchHeaders $PositiveSearchHeaders `
  -HydrateHeaders $PositiveHydrateHeaders `
  -DownloadHeaders $PositiveDownloadHeaders
Assert-Hold $duplicateJson 'search_json_invalid'

$badHost = Invoke-Subject `
  -SearchBody $PositiveSearch `
  -HydrateBody $badHostHydratePath `
  -DownloadBody $PositiveDownload `
  -SearchHeaders $PositiveSearchHeaders `
  -HydrateHeaders $PositiveHydrateHeaders `
  -DownloadHeaders $PositiveDownloadHeaders
Assert-Hold $badHost 'downloadUri_authority_rejected'

$missingAlias = Invoke-Subject `
  -SearchBody $PositiveSearch `
  -HydrateBody $missingAliasHydratePath `
  -DownloadBody $PositiveDownload `
  -SearchHeaders $PositiveSearchHeaders `
  -HydrateHeaders $PositiveHydrateHeaders `
  -DownloadHeaders $PositiveDownloadHeaders
Assert-Hold $missingAlias 'url_downloadUri_alias_missing'

$fractionalSize = Invoke-Subject `
  -SearchBody $PositiveSearch `
  -HydrateBody $fractionalSizeHydratePath `
  -DownloadBody $PositiveDownload `
  -SearchHeaders $PositiveSearchHeaders `
  -HydrateHeaders $PositiveHydrateHeaders `
  -DownloadHeaders $PositiveDownloadHeaders
Assert-Hold $fractionalSize 'hydrate_size_missing_or_nonpositive'

$cookie = Invoke-Subject `
  -SearchBody $PositiveSearch `
  -HydrateBody $PositiveHydrate `
  -DownloadBody $PositiveDownload `
  -SearchHeaders $cookiePath `
  -HydrateHeaders $PositiveHydrateHeaders `
  -DownloadHeaders $PositiveDownloadHeaders
Assert-Equal $cookie.ExitCode 0 ("Cookie-redaction validation failed: {0}" -f $cookie.Text)
Assert-True (-not $cookie.Text.Contains('OFFLINE-SECRET')) 'Cookie value escaped validation output.'
$cookieSummary = $cookie.Text | ConvertFrom-Json
Assert-Equal ([int]$cookieSummary.headers.search.cookie_headers_observed) 1 'Cookie header count drift.'
Assert-True ([bool]$cookieSummary.headers.search.cookies_redacted) 'Cookie redaction did not pass.'

Write-Output 'OFFLINE_TESTS_PASS=positive+retained-negative+synthetic-holds'
Write-Output ('SYNTHETIC_ROOT=' + $syntheticRoot)
