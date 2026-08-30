#Requires -Version 5.1

[CmdletBinding(DefaultParameterSetName = 'Validate')]
param(
  [Parameter(Mandatory = $true, ParameterSetName = 'Live')]
  [switch]$Live,

  [Parameter(Mandatory = $true, ParameterSetName = 'Validate')]
  [switch]$ValidateOnly,

  [Parameter(ParameterSetName = 'Live')]
  [string]$OutputRoot,

  [Parameter(Mandatory = $true, ParameterSetName = 'Live')]
  [AllowEmptyString()]
  [string]$AuthorizingOwnerToken,

  [Parameter(Mandatory = $true, ParameterSetName = 'Live')]
  [AllowEmptyString()]
  [string]$Reviewer,

  [Parameter(Mandatory = $true, ParameterSetName = 'Live')]
  [AllowEmptyString()]
  [string]$SourceCommit,

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
  [string]$DownloadHeaders
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$CurlPath = 'C:\Windows\System32\curl.exe'
$CurlSha256 = '73D24149FF289AFC49EC41F08918EF9FAA727D39AD993E929757DC2DDAFAB805'
$CurlBytes = 818512L
$CurlVersionFirstLine = 'curl 8.21.0 (Windows) libcurl/8.21.0 Schannel zlib/1.3.2 WinIDN WinLDAP'
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
$SessionMaxBytes = 192MB
$ConnectTimeoutSeconds = 10
$MetadataStageSeconds = 30
$ArtifactStageSeconds = 30
$MaximumRequests = 3
$Notice = 'Public ScienceBase acquisition; no credential is used.'

function Stop-Hold {
  param([Parameter(Mandatory = $true)][string]$Code)
  $exception = New-Object System.InvalidOperationException($Code)
  $exception.Data['Terminal'] = 'hold:' + $Code
  $exception.Data['Code'] = $Code
  throw $exception
}

function Get-HoldCode {
  param([Parameter(Mandatory = $true)]$Exception)
  if ($Exception.Data.Contains('Code')) { return [string]$Exception.Data['Code'] }
  return 'internal_error'
}

function Stop-Terminal {
  param(
    [Parameter(Mandatory = $true)][string]$Terminal,
    [Parameter(Mandatory = $true)][string]$Code
  )
  $exception = New-Object System.InvalidOperationException($Code)
  $exception.Data['Terminal'] = $Terminal
  $exception.Data['Code'] = $Code
  throw $exception
}

function Get-ExceptionTerminal {
  param([Parameter(Mandatory = $true)]$Exception)
  if ($Exception.Data.Contains('Terminal')) {
    return [string]$Exception.Data['Terminal']
  }
  return 'hold:internal_error'
}

function Get-ExceptionCode {
  param([Parameter(Mandatory = $true)]$Exception)
  if ($Exception.Data.Contains('Code')) {
    return [string]$Exception.Data['Code']
  }
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
    if (Test-Path -LiteralPath $Path) {
      Stop-Terminal 'hold:output_collision' 'output_collision'
    }
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

function Redact-HeaderDump {
  param([Parameter(Mandatory = $true)][string]$Path)
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
    Write-BytesCreateOnce -Path $Path -Bytes ([byte[]]@())
  }
  $bytes = [System.IO.File]::ReadAllBytes($Path)
  $latin1 = [System.Text.Encoding]::GetEncoding(28591)
  $text = $latin1.GetString($bytes)
  $state = [pscustomobject]@{ Count = 0 }
  $regex = New-Object System.Text.RegularExpressions.Regex(
    '^(Set-Cookie\s*:\s*)([^\r\n]*)',
    ([System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor [System.Text.RegularExpressions.RegexOptions]::Multiline)
  )
  $evaluator = [System.Text.RegularExpressions.MatchEvaluator]{
    param($match)
    $state.Count += 1
    return $match.Groups[1].Value + ('*' * $match.Groups[2].Value.Length)
  }
  $redacted = $regex.Replace($text, $evaluator)
  $redactedBytes = $latin1.GetBytes($redacted)
  if ($redactedBytes.Length -ne $bytes.Length) {
    Stop-Terminal 'hold:header_redaction_failed' 'header_redaction_failed'
  }
  if ($state.Count -gt 0) {
    $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
    try {
      $stream.Position = 0
      $stream.Write($redactedBytes, 0, $redactedBytes.Length)
      $stream.SetLength($redactedBytes.Length)
      $stream.Flush($true)
    } finally {
      $stream.Dispose()
    }
  }
  return [pscustomobject]@{
    Text = $redacted
    CookieHeadersObserved = [int]$state.Count
    Sha256 = Get-Sha256Bytes $redactedBytes
  }
}

function Get-ExactProperty {
  param(
    [Parameter(Mandatory = $true)]$Object,
    [Parameter(Mandatory = $true)][string]$Name
  )
  if ($Object -is [System.Collections.Generic.Dictionary[string,object]]) {
    if ($Object.ContainsKey($Name)) {
      return [pscustomobject]@{ Present = $true; Value = $Object[$Name] }
    }
    return [pscustomobject]@{ Present = $false; Value = $null }
  }
  $matches = @($Object.PSObject.Properties | Where-Object { $_.Name -ceq $Name })
  if ($matches.Count -eq 0) {
    return [pscustomobject]@{ Present = $false; Value = $null }
  }
  return [pscustomobject]@{ Present = $true; Value = $matches[0].Value }
}

function Skip-JsonWhitespace {
  param([string]$Text, [ref]$Index)
  while (
    $Index.Value -lt $Text.Length -and
    $Text[$Index.Value] -in @([char]0x20, [char]0x09, [char]0x0A, [char]0x0D)
  ) {
    $Index.Value += 1
  }
}

function Read-StrictJsonString {
  param([string]$Text, [ref]$Index, [string]$Stage)
  if ($Index.Value -ge $Text.Length -or $Text[$Index.Value] -ne [char]34) {
    Stop-Terminal ("hold:{0}_json_invalid" -f $Stage) ("{0}_json_invalid" -f $Stage)
  }
  $Index.Value += 1
  $builder = New-Object System.Text.StringBuilder
  while ($Index.Value -lt $Text.Length) {
    $character = $Text[$Index.Value]
    $Index.Value += 1
    if ($character -eq [char]34) { return $builder.ToString() }
    if ([int]$character -lt 0x20) {
      Stop-Terminal ("hold:{0}_json_invalid" -f $Stage) ("{0}_json_invalid" -f $Stage)
    }
    if ($character -ne [char]92) {
      [void]$builder.Append($character)
      continue
    }
    if ($Index.Value -ge $Text.Length) {
      Stop-Terminal ("hold:{0}_json_invalid" -f $Stage) ("{0}_json_invalid" -f $Stage)
    }
    $escape = $Text[$Index.Value]
    $Index.Value += 1
    switch ($escape) {
      '"' { [void]$builder.Append([char]34) }
      '\' { [void]$builder.Append([char]92) }
      '/' { [void]$builder.Append([char]47) }
      'b' { [void]$builder.Append([char]8) }
      'f' { [void]$builder.Append([char]12) }
      'n' { [void]$builder.Append([char]10) }
      'r' { [void]$builder.Append([char]13) }
      't' { [void]$builder.Append([char]9) }
      'u' {
        if ($Index.Value + 4 -gt $Text.Length) {
          Stop-Terminal ("hold:{0}_json_invalid" -f $Stage) ("{0}_json_invalid" -f $Stage)
        }
        $hex = $Text.Substring($Index.Value, 4)
        if ($hex -notmatch '^[0-9a-fA-F]{4}$') {
          Stop-Terminal ("hold:{0}_json_invalid" -f $Stage) ("{0}_json_invalid" -f $Stage)
        }
        $code = [Convert]::ToInt32($hex, 16)
        $Index.Value += 4
        if ($code -ge 0xD800 -and $code -le 0xDBFF) {
          if ($Index.Value + 6 -gt $Text.Length -or $Text.Substring($Index.Value, 2) -cne '\u') {
            Stop-Terminal ("hold:{0}_json_invalid" -f $Stage) ("{0}_json_invalid" -f $Stage)
          }
          $lowHex = $Text.Substring($Index.Value + 2, 4)
          if ($lowHex -notmatch '^[0-9a-fA-F]{4}$') {
            Stop-Terminal ("hold:{0}_json_invalid" -f $Stage) ("{0}_json_invalid" -f $Stage)
          }
          $low = [Convert]::ToInt32($lowHex, 16)
          if ($low -lt 0xDC00 -or $low -gt 0xDFFF) {
            Stop-Terminal ("hold:{0}_json_invalid" -f $Stage) ("{0}_json_invalid" -f $Stage)
          }
          $Index.Value += 6
          [void]$builder.Append([char]$code)
          [void]$builder.Append([char]$low)
        } elseif ($code -ge 0xDC00 -and $code -le 0xDFFF) {
          Stop-Terminal ("hold:{0}_json_invalid" -f $Stage) ("{0}_json_invalid" -f $Stage)
        } else {
          [void]$builder.Append([char]$code)
        }
      }
      default {
        Stop-Terminal ("hold:{0}_json_invalid" -f $Stage) ("{0}_json_invalid" -f $Stage)
      }
    }
  }
  Stop-Terminal ("hold:{0}_json_invalid" -f $Stage) ("{0}_json_invalid" -f $Stage)
}

function Read-StrictJsonValue {
  param([string]$Text, [ref]$Index, [string]$Stage)
  Skip-JsonWhitespace $Text $Index
  if ($Index.Value -ge $Text.Length) {
    Stop-Terminal ("hold:{0}_json_invalid" -f $Stage) ("{0}_json_invalid" -f $Stage)
  }
  $character = $Text[$Index.Value]
  if ($character -eq [char]123) { return ,(Read-StrictJsonObject $Text $Index $Stage) }
  if ($character -eq [char]91) { return ,(Read-StrictJsonArray $Text $Index $Stage) }
  if ($character -eq [char]34) { return (Read-StrictJsonString $Text $Index $Stage) }
  $remaining = $Text.Substring($Index.Value)
  $literal = [regex]::Match($remaining, '^(?:true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)')
  if (-not $literal.Success) {
    Stop-Terminal ("hold:{0}_json_invalid" -f $Stage) ("{0}_json_invalid" -f $Stage)
  }
  $Index.Value += $literal.Length
  $token = $literal.Value
  if ($token -ceq 'true') { return $true }
  if ($token -ceq 'false') { return $false }
  if ($token -ceq 'null') { return $null }
  if ($token -notmatch '[.eE]') {
    [long]$integer = 0
    if ([long]::TryParse($token, [System.Globalization.NumberStyles]::Integer, [System.Globalization.CultureInfo]::InvariantCulture, [ref]$integer)) {
      return $integer
    }
    return $token
  }
  [double]$floating = 0.0
  if (-not [double]::TryParse($token, [System.Globalization.NumberStyles]::Float, [System.Globalization.CultureInfo]::InvariantCulture, [ref]$floating)) {
    Stop-Terminal ("hold:{0}_json_invalid" -f $Stage) ("{0}_json_invalid" -f $Stage)
  }
  return $floating
}

function Read-StrictJsonArray {
  param([string]$Text, [ref]$Index, [string]$Stage)
  $values = New-Object 'System.Collections.Generic.List[object]'
  $Index.Value += 1
  Skip-JsonWhitespace $Text $Index
  if ($Index.Value -lt $Text.Length -and $Text[$Index.Value] -eq [char]93) {
    $Index.Value += 1
    return ,([object[]]$values.ToArray())
  }
  while ($true) {
    $value = Read-StrictJsonValue $Text $Index $Stage
    [void]$values.Add($value)
    Skip-JsonWhitespace $Text $Index
    if ($Index.Value -ge $Text.Length) {
      Stop-Terminal ("hold:{0}_json_invalid" -f $Stage) ("{0}_json_invalid" -f $Stage)
    }
    if ($Text[$Index.Value] -eq [char]93) {
      $Index.Value += 1
      return ,([object[]]$values.ToArray())
    }
    if ($Text[$Index.Value] -ne [char]44) {
      Stop-Terminal ("hold:{0}_json_invalid" -f $Stage) ("{0}_json_invalid" -f $Stage)
    }
    $Index.Value += 1
  }
}

function Read-StrictJsonObject {
  param([string]$Text, [ref]$Index, [string]$Stage)
  $Index.Value += 1
  $object = New-Object 'System.Collections.Generic.Dictionary[string,object]' ([System.StringComparer]::Ordinal)
  Skip-JsonWhitespace $Text $Index
  if ($Index.Value -lt $Text.Length -and $Text[$Index.Value] -eq [char]125) {
    $Index.Value += 1
    return ,$object
  }
  while ($true) {
    Skip-JsonWhitespace $Text $Index
    $key = Read-StrictJsonString $Text $Index $Stage
    if ($object.ContainsKey($key)) {
      Stop-Terminal ("hold:{0}_json_invalid" -f $Stage) ("{0}_json_invalid" -f $Stage)
    }
    Skip-JsonWhitespace $Text $Index
    if ($Index.Value -ge $Text.Length -or $Text[$Index.Value] -ne [char]58) {
      Stop-Terminal ("hold:{0}_json_invalid" -f $Stage) ("{0}_json_invalid" -f $Stage)
    }
    $Index.Value += 1
    $value = Read-StrictJsonValue $Text $Index $Stage
    $object.Add($key, $value)
    Skip-JsonWhitespace $Text $Index
    if ($Index.Value -ge $Text.Length) {
      Stop-Terminal ("hold:{0}_json_invalid" -f $Stage) ("{0}_json_invalid" -f $Stage)
    }
    if ($Text[$Index.Value] -eq [char]125) {
      $Index.Value += 1
      return ,$object
    }
    if ($Text[$Index.Value] -ne [char]44) {
      Stop-Terminal ("hold:{0}_json_invalid" -f $Stage) ("{0}_json_invalid" -f $Stage)
    }
    $Index.Value += 1
  }
}

function ConvertFrom-StrictJsonObject {
  param(
    [Parameter(Mandatory = $true)][string]$Text,
    [Parameter(Mandatory = $true)][string]$Stage
  )
  $index = 0
  $parsed = Read-StrictJsonValue $Text ([ref]$index) $Stage
  Skip-JsonWhitespace $Text ([ref]$index)
  if ($index -ne $Text.Length) {
    Stop-Terminal ("hold:{0}_json_invalid" -f $Stage) ("{0}_json_invalid" -f $Stage)
  }
  if ($parsed -isnot [System.Collections.Generic.Dictionary[string,object]]) {
    Stop-Terminal ("hold:{0}_shape_invalid" -f $Stage) ("{0}_shape_invalid" -f $Stage)
  }
  return $parsed
}

function ConvertFrom-ArtifactBytes {
  param([Parameter(Mandatory = $true)][AllowEmptyCollection()][byte[]]$Bytes)
  if ($Bytes.Length -eq 0) {
    Stop-Terminal 'hold:artifact_empty' 'artifact_empty'
  }
  if ($Bytes.Length -ge 4 -and $Bytes[0] -eq 0xFF -and $Bytes[1] -eq 0xFE -and $Bytes[2] -eq 0x00 -and $Bytes[3] -eq 0x00) {
    $encoding = New-Object System.Text.UTF32Encoding($false, $true, $true)
    return [pscustomobject]@{ Text = $encoding.GetString($Bytes, 4, $Bytes.Length - 4); Encoding = 'utf-32le'; Bom = 'fffe0000' }
  }
  if ($Bytes.Length -ge 4 -and $Bytes[0] -eq 0x00 -and $Bytes[1] -eq 0x00 -and $Bytes[2] -eq 0xFE -and $Bytes[3] -eq 0xFF) {
    $encoding = New-Object System.Text.UTF32Encoding($true, $true, $true)
    return [pscustomobject]@{ Text = $encoding.GetString($Bytes, 4, $Bytes.Length - 4); Encoding = 'utf-32be'; Bom = '0000feff' }
  }
  if ($Bytes.Length -ge 2 -and $Bytes[0] -eq 0xFF -and $Bytes[1] -eq 0xFE) {
    $encoding = New-Object System.Text.UnicodeEncoding($false, $true, $true)
    return [pscustomobject]@{ Text = $encoding.GetString($Bytes, 2, $Bytes.Length - 2); Encoding = 'utf-16le'; Bom = 'fffe' }
  }
  if ($Bytes.Length -ge 2 -and $Bytes[0] -eq 0xFE -and $Bytes[1] -eq 0xFF) {
    $encoding = New-Object System.Text.UnicodeEncoding($true, $true, $true)
    return [pscustomobject]@{ Text = $encoding.GetString($Bytes, 2, $Bytes.Length - 2); Encoding = 'utf-16be'; Bom = 'feff' }
  }
  if ($Bytes.Length -ge 3 -and $Bytes[0] -eq 0xEF -and $Bytes[1] -eq 0xBB -and $Bytes[2] -eq 0xBF) {
    $encoding = New-Object System.Text.UTF8Encoding($false, $true)
    return [pscustomobject]@{ Text = $encoding.GetString($Bytes, 3, $Bytes.Length - 3); Encoding = 'utf-8'; Bom = 'efbbbf' }
  }
  $encoding = New-Object System.Text.UTF8Encoding($false, $true)
  return [pscustomobject]@{ Text = $encoding.GetString($Bytes); Encoding = 'utf-8'; Bom = 'none' }
}

function Add-CsvRecord {
  param(
    [System.Collections.ArrayList]$Rows,
    [System.Collections.Generic.List[string]]$Fields,
    [System.Text.StringBuilder]$Field,
    [System.Text.StringBuilder]$Raw
  )
  [void]$Fields.Add($Field.ToString())
  [void]$Rows.Add([pscustomobject]@{
    Raw = $Raw.ToString()
    Fields = @($Fields.ToArray())
    FieldCount = $Fields.Count
  })
  $Fields.Clear()
  [void]$Field.Clear()
  [void]$Raw.Clear()
}

function Measure-Csv {
  param([Parameter(Mandatory = $true)][string]$Text)
  $rows = New-Object System.Collections.ArrayList
  $fields = New-Object 'System.Collections.Generic.List[string]'
  $field = New-Object System.Text.StringBuilder
  $raw = New-Object System.Text.StringBuilder
  $inQuotes = $false
  $atFieldStart = $true
  for ($index = 0; $index -lt $Text.Length; $index += 1) {
    $character = $Text[$index]
    if ($inQuotes) {
      [void]$raw.Append($character)
      if ($character -eq [char]34) {
        if ($index + 1 -lt $Text.Length -and $Text[$index + 1] -eq [char]34) {
          [void]$raw.Append([char]34)
          [void]$field.Append([char]34)
          $index += 1
        } else {
          $inQuotes = $false
        }
      } else {
        [void]$field.Append($character)
      }
      continue
    }
    if ($character -eq [char]34 -and $atFieldStart) {
      [void]$raw.Append($character)
      $inQuotes = $true
      $atFieldStart = $false
      continue
    }
    if ($character -eq [char]44) {
      [void]$raw.Append($character)
      [void]$fields.Add($field.ToString())
      [void]$field.Clear()
      $atFieldStart = $true
      continue
    }
    if ($character -eq [char]13 -or $character -eq [char]10) {
      if ($character -eq [char]13 -and $index + 1 -lt $Text.Length -and $Text[$index + 1] -eq [char]10) {
        $index += 1
      }
      Add-CsvRecord -Rows $rows -Fields $fields -Field $field -Raw $raw
      $atFieldStart = $true
      continue
    }
    [void]$raw.Append($character)
    [void]$field.Append($character)
    $atFieldStart = $false
  }
  if ($inQuotes) { Stop-Terminal 'hold:csv_invalid' 'csv_invalid' }
  if ($raw.Length -gt 0 -or $field.Length -gt 0 -or $fields.Count -gt 0) {
    Add-CsvRecord -Rows $rows -Fields $fields -Field $field -Raw $raw
  }
  if ($rows.Count -eq 0 -or [string]::IsNullOrWhiteSpace([string]$rows[0].Raw)) {
    Stop-Terminal 'hold:csv_header_missing' 'csv_header_missing'
  }
  $counts = @($rows | ForEach-Object { [int]$_.FieldCount })
  $minimum = ($counts | Measure-Object -Minimum).Minimum
  $maximum = ($counts | Measure-Object -Maximum).Maximum
  return [pscustomobject]@{
    HeaderRaw = [string]$rows[0].Raw
    ColumnNames = @($rows[0].Fields)
    ColumnCount = [int]$rows[0].FieldCount
    DataRowCount = [Math]::Max(0, $rows.Count - 1)
    UniformRowWidth = ($minimum -eq $maximum)
    MinimumFieldCount = [int]$minimum
    MaximumFieldCount = [int]$maximum
    HasAtLeastOneDataRow = ($rows.Count -gt 1)
    HasAtLeastTwoColumns = ($rows[0].FieldCount -ge 2)
  }
}

function Assert-DownloadAuthority {
  param([Parameter(Mandatory = $true)][string]$RawUrl)
  $hasControlCharacter = @($RawUrl.ToCharArray() | Where-Object {
    ([int]$_ -lt 0x20) -or ([int]$_ -eq 0x7F)
  }).Count -ne 0
  if (
    [string]::IsNullOrWhiteSpace($RawUrl) -or
    $RawUrl -cne $RawUrl.Trim() -or
    $hasControlCharacter -or
    $RawUrl.Contains([string][char]92)
  ) {
    Stop-Terminal 'hold:downloadUri_authority_rejected' 'downloadUri_authority_rejected'
  }
  $parsed = $null
  if (-not [uri]::TryCreate($RawUrl, [System.UriKind]::Absolute, [ref]$parsed)) {
    Stop-Terminal 'hold:downloadUri_authority_rejected' 'downloadUri_authority_rejected'
  }
  if (
    $parsed.Scheme -cne 'https' -or
    $parsed.DnsSafeHost -cne 'www.sciencebase.gov' -or
    -not $parsed.IsDefaultPort -or
    $parsed.Port -ne 443 -or
    $parsed.UserInfo.Length -ne 0 -or
    $parsed.Fragment.Length -ne 0 -or
    $parsed.AbsoluteUri -cne $RawUrl
  ) {
    Stop-Terminal 'hold:downloadUri_authority_rejected' 'downloadUri_authority_rejected'
  }
}

function Get-NormalizedPath {
  param([Parameter(Mandatory = $true)][string]$Path)
  $full = [System.IO.Path]::GetFullPath($Path)
  $root = [System.IO.Path]::GetPathRoot($full)
  if ($full.Length -gt $root.Length) {
    $full = $full.TrimEnd([char[]]@([char]92, [char]47))
  }
  return $full
}

function Test-IsInsideOrEqual {
  param(
    [Parameter(Mandatory = $true)][string]$Candidate,
    [Parameter(Mandatory = $true)][string]$Container
  )
  $candidatePath = Get-NormalizedPath $Candidate
  $containerPath = Get-NormalizedPath $Container
  if ($candidatePath.Equals($containerPath, [System.StringComparison]::OrdinalIgnoreCase)) {
    return $true
  }
  $prefix = $containerPath
  if (-not $prefix.EndsWith([string][System.IO.Path]::DirectorySeparatorChar)) {
    $prefix += [System.IO.Path]::DirectorySeparatorChar
  }
  return $candidatePath.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)
}
function Get-RepoWorktreePaths {
  param([Parameter(Mandatory = $true)][string]$RepoRoot)
  $git = Get-Command git.exe -ErrorAction Stop
  $result = Invoke-NativeSeparated -FilePath $git.Source -Arguments @('-C', $RepoRoot, 'worktree', 'list', '--porcelain')
  if ($result.ExitCode -ne 0 -or -not [string]::IsNullOrWhiteSpace($result.Stderr)) {
    Stop-Terminal 'hold:worktree_enumeration_failed' 'worktree_enumeration_failed'
  }
  $paths = New-Object System.Collections.ArrayList
  foreach ($line in ($result.Stdout -split "`r?`n")) {
    if ($line.StartsWith('worktree ', [System.StringComparison]::Ordinal)) {
      [void]$paths.Add((Get-NormalizedPath $line.Substring(9)))
    }
  }
  if ($paths.Count -eq 0) {
    Stop-Terminal 'hold:worktree_enumeration_failed' 'worktree_enumeration_failed'
  }
  return @($paths)
}

function Assert-NoReparseAncestor {
  param([Parameter(Mandatory = $true)][string]$ParentPath)
  $current = Get-Item -LiteralPath $ParentPath -Force
  while ($null -ne $current) {
    if (($current.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
      Stop-Terminal 'hold:output_root_reparse_ancestor' 'output_root_reparse_ancestor'
    }
    if ($null -eq $current.Parent) { break }
    $current = $current.Parent
  }
}

function Get-CurlIdentity {
  if (-not (Test-Path -LiteralPath $CurlPath -PathType Leaf)) {
    Stop-Terminal 'hold:curl_identity_invalid' 'curl_identity_invalid'
  }
  $item = Get-Item -LiteralPath $CurlPath
  if ([long]$item.Length -ne $CurlBytes) {
    Stop-Terminal 'hold:curl_identity_invalid' 'curl_identity_invalid'
  }
  $hash = (Get-FileHash -LiteralPath $CurlPath -Algorithm SHA256).Hash
  if ($hash -cne $CurlSha256) {
    Stop-Terminal 'hold:curl_identity_invalid' 'curl_identity_invalid'
  }
  $version = Invoke-NativeSeparated -FilePath $CurlPath -Arguments @('--disable', '--version')
  if ($version.ExitCode -ne 0 -or -not [string]::IsNullOrWhiteSpace($version.Stderr)) {
    Stop-Terminal 'hold:curl_identity_invalid' 'curl_identity_invalid'
  }
  $lines = @($version.Stdout -split "`r?`n")
  if ($lines.Count -eq 0 -or $lines[0] -cne $CurlVersionFirstLine) {
    Stop-Terminal 'hold:curl_identity_invalid' 'curl_identity_invalid'
  }
  return [ordered]@{
    path = $CurlPath
    bytes = [long]$item.Length
    sha256 = $hash.ToLowerInvariant()
    version_first_line = $lines[0]
    version_output = $version.Stdout.TrimEnd()
  }
}

function Invoke-Preflight {
  $rootCandidate = $OutputRoot
  if ($rootCandidate -match '^[\\/]{2}[?.][\\/]') {
    Stop-Terminal 'hold:output_root_invalid' 'output_root_invalid'
  }
  $isFullyQualifiedDrive = $rootCandidate -match '^[A-Za-z]:[\\/]'
  if (
    [string]::IsNullOrWhiteSpace($rootCandidate) -or
    -not $isFullyQualifiedDrive
  ) {
    Stop-Terminal 'hold:output_root_invalid' 'output_root_invalid'
  }
  $fullOutputRoot = Get-NormalizedPath $rootCandidate
  $pathRoot = [System.IO.Path]::GetPathRoot($fullOutputRoot)
  if ($fullOutputRoot.Equals($pathRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    Stop-Terminal 'hold:output_root_invalid' 'output_root_invalid'
  }
  if (Test-Path -LiteralPath $fullOutputRoot) {
    Stop-Terminal 'hold:OUTPUT_ROOT_EXISTS' 'OUTPUT_ROOT_EXISTS'
  }
  $parent = Split-Path -Parent $fullOutputRoot
  if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
    Stop-Terminal 'hold:output_root_parent_invalid' 'output_root_parent_invalid'
  }
  Assert-NoReparseAncestor $parent
  $forbidden = @(
    [System.IO.Path]::GetTempPath(),
    [System.Environment]::GetFolderPath('Desktop'),
    (Join-Path ([System.Environment]::GetFolderPath('UserProfile')) 'Downloads')
  ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
  foreach ($path in $forbidden) {
    if (Test-IsInsideOrEqual -Candidate $fullOutputRoot -Container $path) {
      Stop-Terminal 'hold:output_root_forbidden' 'output_root_forbidden'
    }
  }
  $repoRoot = Get-NormalizedPath (Join-Path $PSScriptRoot '..')
  $worktrees = Get-RepoWorktreePaths $repoRoot
  foreach ($worktree in $worktrees) {
    if (Test-IsInsideOrEqual -Candidate $fullOutputRoot -Container $worktree) {
      Stop-Terminal 'hold:output_root_inside_worktree' 'output_root_inside_worktree'
    }
  }
  if ($PSVersionTable.PSVersion.Major -ne 5 -or $PSVersionTable.PSVersion.Minor -ne 1) {
    Stop-Terminal 'hold:powershell_identity_invalid' 'powershell_identity_invalid'
  }
  $curlIdentity = Get-CurlIdentity
  $duplicatesRejected = $false
  try { [void]('{"x":1,"x":2}' | ConvertFrom-Json) } catch { $duplicatesRejected = $true }
  return [pscustomobject]@{
    OutputRoot = $fullOutputRoot
    RepoRoot = $repoRoot
    Worktrees = @($worktrees)
    CurlIdentity = $curlIdentity
    PowerShellVersion = $PSVersionTable.PSVersion.ToString()
    ConvertFromJsonRejectsDuplicates = $duplicatesRejected
  }
}

function New-OutputRootOnce {
  param([Parameter(Mandatory = $true)][string]$Path)
  try {
    [void](New-Item -ItemType Directory -Path $Path -ErrorAction Stop)
  } catch {
    if (Test-Path -LiteralPath $Path) {
      Stop-Terminal 'hold:OUTPUT_ROOT_EXISTS' 'OUTPUT_ROOT_EXISTS'
    }
    Stop-Terminal 'hold:output_root_create_failed' 'output_root_create_failed'
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

function ConvertFrom-StrictStageBody {
  param(
    [Parameter(Mandatory = $true)][AllowEmptyCollection()][byte[]]$Bytes,
    [Parameter(Mandatory = $true)][string]$Stage
  )
  try {
    $decoded = ConvertFrom-ArtifactBytes $Bytes
    return ConvertFrom-StrictJsonObject -Text $decoded.Text -Stage $Stage
  } catch {
    $expected = $Stage + '_json_invalid'
    if (
      $_.Exception.Data.Contains('Code') -and
      ([string]$_.Exception.Data['Code']).StartsWith($Stage + '_', [System.StringComparison]::Ordinal)
    ) { throw }
    Stop-Terminal ('hold:' + $expected) $expected
  }
}

function Assert-SearchContract {
  param([Parameter(Mandatory = $true)][AllowEmptyCollection()][byte[]]$Bytes)
  $searchPayload = ConvertFrom-StrictStageBody -Bytes $Bytes -Stage 'search'
  $itemsProperty = Get-ExactProperty -Object $searchPayload -Name 'items'
  if (
    -not $itemsProperty.Present -or
    $itemsProperty.Value -isnot [System.Array] -or
    @($itemsProperty.Value | Where-Object {
      ($null -eq $_) -or ($_ -isnot [System.Collections.Generic.Dictionary[string,object]])
    }).Count -ne 0
  ) {
    Stop-Terminal 'hold:search_shape_invalid' 'search_shape_invalid'
  }
  $items = @($itemsProperty.Value)
  $matchingItems = @($items | Where-Object {
    $id = Get-ExactProperty -Object $_ -Name 'id'
    return $id.Present -and $id.Value -is [string] -and $id.Value -ceq $ExpectedItemId
  })
  if ($matchingItems.Count -ne 1) {
    Stop-Terminal 'hold:search_expected_item_not_unique' 'search_expected_item_not_unique'
  }
  return [pscustomobject]@{
    exact_matches = [int]$matchingItems.Count
    returned_items = [int]$items.Count
  }
}

function Assert-HydrateContract {
  param([Parameter(Mandatory = $true)][AllowEmptyCollection()][byte[]]$Bytes)
  $item = ConvertFrom-StrictStageBody -Bytes $Bytes -Stage 'hydrate'
  $itemId = Get-ExactProperty -Object $item -Name 'id'
  if (-not $itemId.Present -or $itemId.Value -isnot [string] -or $itemId.Value -cne $ExpectedItemId) {
    Stop-Terminal 'hold:hydrate_item_id_mismatch' 'hydrate_item_id_mismatch'
  }
  $filesProperty = Get-ExactProperty -Object $item -Name 'files'
  if (
    -not $filesProperty.Present -or
    $filesProperty.Value -isnot [System.Array] -or
    @($filesProperty.Value | Where-Object {
      ($null -eq $_) -or ($_ -isnot [System.Collections.Generic.Dictionary[string,object]])
    }).Count -ne 0
  ) {
    Stop-Terminal 'hold:hydrate_shape_invalid' 'hydrate_shape_invalid'
  }
  $files = @($filesProperty.Value)
  $matchingFiles = @($files | Where-Object {
    $name = Get-ExactProperty -Object $_ -Name 'name'
    return $name.Present -and $name.Value -is [string] -and $name.Value -ceq $ExpectedFileName
  })
  if ($matchingFiles.Count -ne 1) {
    Stop-Terminal 'hold:hydrate_expected_file_not_unique' 'hydrate_expected_file_not_unique'
  }
  $file = $matchingFiles[0]
  $downloadProperty = Get-ExactProperty -Object $file -Name 'downloadUri'
  $urlProperty = Get-ExactProperty -Object $file -Name 'url'
  if (-not $downloadProperty.Present -or $downloadProperty.Value -isnot [string] -or [string]::IsNullOrWhiteSpace($downloadProperty.Value)) {
    Stop-Terminal 'hold:downloadUri_missing' 'downloadUri_missing'
  }
  $downloadUri = [string]$downloadProperty.Value
  if (-not $urlProperty.Present) {
    Stop-Terminal 'hold:url_downloadUri_alias_missing' 'url_downloadUri_alias_missing'
  }
  if ($urlProperty.Value -isnot [string] -or [string]$urlProperty.Value -cne $downloadUri) {
    Stop-Terminal 'hold:url_downloadUri_alias_mismatch' 'url_downloadUri_alias_mismatch'
  }
  Assert-DownloadAuthority $downloadUri
  $sizeProperty = Get-ExactProperty -Object $file -Name 'size'
  [long]$advertisedSize = 0
  if (
    -not $sizeProperty.Present -or
    -not [long]::TryParse([string]$sizeProperty.Value, [System.Globalization.NumberStyles]::Integer, [System.Globalization.CultureInfo]::InvariantCulture, [ref]$advertisedSize) -or
    $advertisedSize -le 0
  ) {
    Stop-Terminal 'hold:hydrate_size_missing_or_nonpositive' 'hydrate_size_missing_or_nonpositive'
  }
  if ($advertisedSize -gt $ArtifactMaxBytes) {
    Stop-Terminal 'hold:hydrate_size_exceeds_artifact_cap' 'hydrate_size_exceeds_artifact_cap'
  }
  return [pscustomobject]@{
    download_uri = $downloadUri
    advertised_size = $advertisedSize
    file_matches = [int]$matchingFiles.Count
    r19_absolute_uri_roundtrip = $true
  }
}

function Assert-ArtifactContract {
  param(
    [Parameter(Mandatory = $true)][AllowEmptyCollection()][byte[]]$Bytes,
    [Parameter(Mandatory = $true)][long]$AdvertisedSize
  )
  try {
    $decoded = ConvertFrom-ArtifactBytes $Bytes
  } catch {
    if ($_.Exception.Data.Contains('Code')) { throw }
    Stop-Terminal 'hold:artifact_encoding_rejected' 'artifact_encoding_rejected'
  }
  $trimmed = $decoded.Text.TrimStart()
  if ([string]::IsNullOrWhiteSpace($trimmed)) {
    Stop-Terminal 'hold:artifact_empty_text' 'artifact_empty_text'
  }
  if ($trimmed.StartsWith('<') -or $trimmed.StartsWith('{') -or $trimmed.StartsWith('[')) {
    Stop-Terminal 'hold:artifact_markup_or_json_rejected' 'artifact_markup_or_json_rejected'
  }
  if ($trimmed -match '^(?i)(error|bad gateway|service unavailable|access denied|not found)\b') {
    Stop-Terminal 'hold:artifact_plaintext_error_rejected' 'artifact_plaintext_error_rejected'
  }
  if ($Bytes.Length -ne $AdvertisedSize) {
    Stop-Terminal 'hold:artifact_size_mismatch' 'artifact_size_mismatch'
  }
  if ($decoded.Encoding -cne 'utf-8') {
    Stop-Terminal 'hold:artifact_encoding_rejected' 'artifact_encoding_rejected'
  }
  $csv = Measure-Csv $decoded.Text
  $utf8 = New-Object System.Text.UTF8Encoding($false, $true)
  $headerBytes = $utf8.GetBytes($csv.HeaderRaw)
  $headerSha256 = Get-Sha256Bytes $headerBytes
  if ($csv.HeaderRaw -cne $ExpectedHeader -or $headerSha256 -cne $ExpectedHeaderSha256) {
    Stop-Terminal 'hold:artifact_header_mismatch' 'artifact_header_mismatch'
  }
  if ($csv.ColumnCount -ne 13 -or -not $csv.UniformRowWidth -or $csv.MinimumFieldCount -ne 13 -or $csv.MaximumFieldCount -ne 13) {
    Stop-Terminal 'hold:artifact_row_column_count' 'artifact_row_column_count'
  }
  if (-not $csv.HasAtLeastOneDataRow) {
    Stop-Terminal 'hold:artifact_no_data_rows' 'artifact_no_data_rows'
  }
  return [pscustomobject]@{
    header_match = $true
    columns = [int]$csv.ColumnCount
    rows = [int]$csv.DataRowCount
    uniform_width = [bool]$csv.UniformRowWidth
    header_sha256 = $headerSha256
    encoding = [string]$decoded.Encoding
    bom = [string]$decoded.Bom
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
    if (-not (Test-Path -LiteralPath $fixture -PathType Leaf)) { Stop-Terminal 'hold:body_fixture_missing' 'body_fixture_missing' }
  }
  if ($SearchHeaderInfo.LocationLines -ne 0) { Stop-Terminal 'hold:search_location_rejected' 'search_location_rejected' }
  if ($HydrateHeaderInfo.LocationLines -ne 0) { Stop-Terminal 'hold:hydrate_location_rejected' 'hydrate_location_rejected' }
  if ($DownloadHeaderInfo.LocationLines -ne 0) { Stop-Terminal 'hold:download_location_rejected' 'download_location_rejected' }
  $searchBytes = [System.IO.File]::ReadAllBytes($SearchBodyPath)
  $hydrateBytes = [System.IO.File]::ReadAllBytes($HydrateBodyPath)
  $downloadBytes = [System.IO.File]::ReadAllBytes($DownloadBodyPath)
  $search = Assert-SearchContract $searchBytes
  $hydrate = Assert-HydrateContract $hydrateBytes
  $content = Assert-ArtifactContract -Bytes $downloadBytes -AdvertisedSize ([long]$hydrate.advertised_size)
  return [pscustomobject]@{
    Search = $search
    Hydrate = $hydrate
    Content = $content
    SearchHeaders = $SearchHeaderInfo
    HydrateHeaders = $HydrateHeaderInfo
    DownloadHeaders = $DownloadHeaderInfo
    SearchBody = Get-BodyRecord $SearchBodyPath
    HydrateBody = Get-BodyRecord $HydrateBodyPath
    DownloadBody = Get-BodyRecord $DownloadBodyPath
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
  if (-not $process.Start()) { Stop-Terminal 'hold:native_start_failed' 'native_start_failed' }
  $stdoutBuffer = New-Object System.IO.MemoryStream
  $stdoutTask = $process.StandardOutput.BaseStream.CopyToAsync($stdoutBuffer)
  $stderrTask = $process.StandardError.ReadToEndAsync()
  $process.WaitForExit()
  $stdoutTask.Wait()
  $stdoutBytes = $stdoutBuffer.ToArray()
  $stdoutBuffer.Dispose()
  $stdout = (New-Object System.Text.UTF8Encoding($false, $false)).GetString($stdoutBytes)
  $stderr = $stderrTask.Result
  $exitCode = $process.ExitCode
  $process.Dispose()
  return [pscustomobject]@{
    ExitCode = $exitCode
    Stdout = $stdout
    StdoutBytes = $stdoutBytes
    Stderr = $stderr
  }
}

function Get-MetricValue {
  param([string]$Text, [string]$Name)
  $match = [regex]::Match($Text, ('(?m)^' + [regex]::Escape($Name) + '=(.*)$'))
  if (-not $match.Success) { return $null }
  return $match.Groups[1].Value.Trim()
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
  if ($RequestCount.Value -gt $MaximumRequests) { Stop-Terminal 'hold:request_budget_exceeded' 'request_budget_exceeded' }
  $token = [guid]::NewGuid().ToString('N')
  $stageRoot = Join-Path $Root ("{0}-{1}" -f $Stage, $token)
  try {
    [void](New-Item -ItemType Directory -Path $stageRoot -ErrorAction Stop)
  } catch {
    if (Test-Path -LiteralPath $stageRoot) { Stop-Terminal 'hold:output_collision' 'output_collision' }
    throw
  }
  $bodyPath = Join-Path $stageRoot 'body.part'
  $headerPath = Join-Path $stageRoot 'headers.part'
  $metricsPath = Join-Path $stageRoot 'metrics.txt'
  $stderrPath = Join-Path $stageRoot 'stderr.txt'
  $metricsMarker = '__PROJECT6_METRICS_' + $token + '__'
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
    $diagnosticText = [string]$native.Stderr
  } else {
    $diagnosticText = $native.Stderr.Substring(0, $markerIndex).TrimEnd([char[]]@([char]13, [char]10))
    $metricsText = $native.Stderr.Substring($markerIndex + $metricsMarker.Length).TrimStart([char[]]@([char]13, [char]10))
  }
  $unexpectedCurlFiles = @(Get-ChildItem -LiteralPath $stageRoot -Force | Where-Object {
    $_.Name -cne 'body.part'
  })
  if ($unexpectedCurlFiles.Count -ne 0) {
    Stop-Terminal 'hold:output_collision' 'output_collision'
  }
  Write-BytesCreateOnce -Path $headerPath -Bytes $native.StdoutBytes
  Write-Utf8CreateOnce -Path $metricsPath -Text $metricsText
  Write-Utf8CreateOnce -Path $stderrPath -Text $diagnosticText
  $redactedHeaders = Redact-HeaderDump -Path $headerPath
  $headers = [pscustomobject]@{
    Text = $redactedHeaders.Text
    HeaderLines = Get-PhysicalLineCount $redactedHeaders.Text
    LocationLines = [regex]::Matches($redactedHeaders.Text, '(?im)^Location\s*:').Count
    CookieHeadersObserved = [int]$redactedHeaders.CookieHeadersObserved
    CookiesRedacted = $true
  }
  if (-not (Test-Path -LiteralPath $bodyPath -PathType Leaf)) {
    Write-BytesCreateOnce -Path $bodyPath -Bytes ([byte[]]@())
  }
  $statusText = Get-MetricValue -Text $metricsText -Name 'HTTP_CODE'
  $status = if ($statusText -match '^\d{3}$') { [int]$statusText } else { 0 }
  return [pscustomobject]@{
    Stage = $Stage
    RequestOrdinal = $RequestCount.Value
    Url = $Url
    ExitCode = [int]$native.ExitCode
    HttpStatus = $status
    MetricsText = $metricsText
    BodyPath = $bodyPath
    HeaderPath = $headerPath
    HeaderInfo = $headers
    HeaderText = $redactedHeaders.Text
    HeaderSha256 = $redactedHeaders.Sha256
    CookieHeadersObserved = $redactedHeaders.CookieHeadersObserved
    MetricsPath = $metricsPath
    StderrPath = $stderrPath
    StartedAt = $startedAt
    EndedAt = $endedAt
    UrlEffective = Get-MetricValue -Text $metricsText -Name 'URL_EFFECTIVE'
    SizeDownload = Get-MetricValue -Text $metricsText -Name 'SIZE_DOWNLOAD'
  }
}

function Require-Clean200 {
  param([Parameter(Mandatory = $true)]$Result, [int]$StageSeconds)
  if ([regex]::IsMatch($Result.HeaderText, '(?im)^Location\s*:')) {
    Stop-Terminal ("hold:{0}_location_rejected" -f $Result.Stage) ("{0}_location_rejected" -f $Result.Stage)
  }
  if ($Result.ExitCode -eq 28) {
    $totalText = Get-MetricValue -Text $Result.MetricsText -Name 'TIME_TOTAL'
    $connectText = Get-MetricValue -Text $Result.MetricsText -Name 'TIME_CONNECT'
    [double]$total = 0.0
    [double]$connect = 0.0
    [void][double]::TryParse($totalText, [System.Globalization.NumberStyles]::Float, [System.Globalization.CultureInfo]::InvariantCulture, [ref]$total)
    [void][double]::TryParse($connectText, [System.Globalization.NumberStyles]::Float, [System.Globalization.CultureInfo]::InvariantCulture, [ref]$connect)
    if ($Result.HttpStatus -eq 0 -and $connect -eq 0 -and $total -gt 0 -and $total -lt $StageSeconds) {
      Stop-Terminal 'EXPERIMENT_BOUND_EXCEEDED:connect' 'connect'
    }
    Stop-Terminal ("hold:{0}_timeout" -f $Result.Stage) ("{0}_timeout" -f $Result.Stage)
  }
  if ($Result.ExitCode -eq 63) {
    Stop-Terminal ("hold:{0}_response_too_large" -f $Result.Stage) ("{0}_response_too_large" -f $Result.Stage)
  }
  if ($Result.ExitCode -ne 0) {
    Stop-Terminal ("hold:{0}_transport_failed" -f $Result.Stage) ("{0}_transport_failed" -f $Result.Stage)
  }
  if ($Result.HttpStatus -ne 200) {
    Stop-Terminal ("hold:{0}_http_status" -f $Result.Stage) ("{0}_http_status" -f $Result.Stage)
  }
}
function New-StageRecord {
  param([Parameter(Mandatory = $true)]$Result)
  $body = Get-BodyRecord $Result.BodyPath
  return [ordered]@{
    url = $Result.Url
    url_effective = [string]$Result.UrlEffective
    http_status = [int]$Result.HttpStatus
    header_lines = [int]$Result.HeaderInfo.HeaderLines
    location_lines = [int]$Result.HeaderInfo.LocationLines
    body_bytes = [long]$body.Bytes
    size_download = [long]([double]::Parse([string]$Result.SizeDownload, [System.Globalization.CultureInfo]::InvariantCulture))
    body_sha256 = $body.Sha256
    started_at = $Result.StartedAt
    ended_at = $Result.EndedAt
  }
}

function Add-StageBytes {
  param([ref]$TotalBytes, [long]$StageBytes)
  if ($StageBytes -lt 0 -or $StageBytes -gt $ArtifactMaxBytes) {
    Stop-Terminal 'hold:stage_response_too_large' 'stage_response_too_large'
  }
  $TotalBytes.Value += $StageBytes
  if ($TotalBytes.Value -gt $SessionMaxBytes) {
    Stop-Terminal 'hold:session_total_bytes_exceeded' 'session_total_bytes_exceeded'
  }
}

function New-AcquisitionRecord {
  param(
    [Parameter(Mandatory = $true)]$Stages,
    [Parameter(Mandatory = $true)][string]$ObservedDownloadUri,
    [Parameter(Mandatory = $true)][string]$ArtifactFinalizedName,
    [Parameter(Mandatory = $true)][string]$ArtifactSha256,
    [Parameter(Mandatory = $true)][long]$ArtifactBytes,
    [Parameter(Mandatory = $true)]$ContentContract,
    [Parameter(Mandatory = $true)][AllowEmptyString()][string]$OwnerToken,
    [Parameter(Mandatory = $true)][string]$ReviewerValue,
    [Parameter(Mandatory = $true)][string]$SourceCommitValue,
    [Parameter(Mandatory = $true)]$Runtime
  )
  return [ordered]@{
    schema = 'project6.instrument-acquisition.v1'
    doi = $Doi
    doi_source = 'asserted'
    item_id = $ExpectedItemId
    filename = $ExpectedFileName
    observed_download_uri = $ObservedDownloadUri
    license = 'CC0-1.0'
    license_source = 'asserted'
    stages = [ordered]@{
      search = $Stages.Search
      hydrate = $Stages.Hydrate
      download = $Stages.Download
    }
    redirect_posture = 'max-redirs=0, no Location observed'
    artifact_finalized_name = $ArtifactFinalizedName
    artifact_sha256 = $ArtifactSha256
    artifact_bytes = $ArtifactBytes
    encoding = [string]$ContentContract.encoding
    bom = [string]$ContentContract.bom
    content_contract = [ordered]@{
      header_match = [bool]$ContentContract.header_match
      columns = [int]$ContentContract.columns
      rows = [int]$ContentContract.rows
      uniform_width = [bool]$ContentContract.uniform_width
      header_sha256 = [string]$ContentContract.header_sha256
    }
    authorizing_owner_token = $OwnerToken
    reviewer = $ReviewerValue
    source_commit = $SourceCommitValue
    curl_sha256 = [string]$Runtime.CurlIdentity.sha256
    curl_bytes = [long]$Runtime.CurlIdentity.bytes
    python_used = $false
    no_credential = $true
    cookies_redacted = $true
    powershell_version = [string]$Runtime.PowerShellVersion
  }
}

function Assert-RecordSchema {
  param([Parameter(Mandatory = $true)]$Record)
  $topLevel = @(
    'schema', 'doi', 'doi_source', 'item_id', 'filename', 'observed_download_uri',
    'license', 'license_source', 'stages', 'redirect_posture', 'artifact_finalized_name',
    'artifact_sha256', 'artifact_bytes', 'encoding', 'bom', 'content_contract',
    'authorizing_owner_token', 'reviewer', 'source_commit', 'curl_sha256', 'curl_bytes',
    'python_used', 'no_credential', 'cookies_redacted', 'powershell_version'
  )
  foreach ($name in $topLevel) {
    if (-not $Record.Contains($name)) { Stop-Terminal 'hold:record_schema_invalid' 'record_schema_invalid' }
  }
  if ($Record.Count -ne $topLevel.Count -or $Record.schema -cne 'project6.instrument-acquisition.v1') {
    Stop-Terminal 'hold:record_schema_invalid' 'record_schema_invalid'
  }
  if (
    $Record.doi -cne $Doi -or
    $Record.doi_source -cne 'asserted' -or
    $Record.license -cne 'CC0-1.0' -or
    $Record.license_source -cne 'asserted'
  ) {
    Stop-Terminal 'hold:record_schema_invalid' 'record_schema_invalid'
  }
  $stageFields = @(
    'url', 'url_effective', 'http_status', 'header_lines', 'location_lines',
    'body_bytes', 'size_download', 'body_sha256', 'started_at', 'ended_at'
  )
  foreach ($stageName in @('search', 'hydrate', 'download')) {
    if (-not $Record.stages.Contains($stageName)) { Stop-Terminal 'hold:record_schema_invalid' 'record_schema_invalid' }
    $stage = $Record.stages[$stageName]
    foreach ($field in $stageFields) {
      if (-not $stage.Contains($field)) { Stop-Terminal 'hold:record_schema_invalid' 'record_schema_invalid' }
    }
    if (
      $stage.Count -ne $stageFields.Count -or
      [int]$stage.http_status -ne 200 -or
      [int]$stage.location_lines -ne 0 -or
      [long]$stage.body_bytes -ne [long]$stage.size_download -or
      [string]::IsNullOrWhiteSpace([string]$stage.url_effective)
    ) {
      Stop-Terminal 'hold:record_schema_invalid' 'record_schema_invalid'
    }
    if ([string]$stage.body_sha256 -cnotmatch '^[0-9a-f]{64}$') {
      Stop-Terminal 'hold:record_schema_invalid' 'record_schema_invalid'
    }
    if (-not ([string]$stage.started_at).EndsWith('Z') -or -not ([string]$stage.ended_at).EndsWith('Z')) {
      Stop-Terminal 'hold:record_schema_invalid' 'record_schema_invalid'
    }
  }
  $contentFields = @('header_match', 'columns', 'rows', 'uniform_width', 'header_sha256')
  foreach ($field in $contentFields) {
    if (-not $Record.content_contract.Contains($field)) { Stop-Terminal 'hold:record_schema_invalid' 'record_schema_invalid' }
  }
  if (
    $Record.content_contract.Count -ne $contentFields.Count -or
    -not [bool]$Record.content_contract.header_match -or
    [int]$Record.content_contract.columns -ne 13 -or
    [int]$Record.content_contract.rows -lt 1 -or
    -not [bool]$Record.content_contract.uniform_width -or
    [string]$Record.content_contract.header_sha256 -cne $ExpectedHeaderSha256
  ) {
    Stop-Terminal 'hold:record_schema_invalid' 'record_schema_invalid'
  }
  if ($Record.stages.download.url -cne $Record.observed_download_uri) {
    Stop-Terminal 'hold:record_schema_invalid' 'record_schema_invalid'
  }
  if ($Record.stages.download.body_sha256 -cne $Record.artifact_sha256) {
    Stop-Terminal 'hold:record_schema_invalid' 'record_schema_invalid'
  }
  if ([long]$Record.stages.download.body_bytes -ne [long]$Record.artifact_bytes) {
    Stop-Terminal 'hold:record_schema_invalid' 'record_schema_invalid'
  }
  $expectedFinalizedName = 'mcs2023-germa_salient.' + [string]$Record.artifact_sha256 + '.csv'
  if ($Record.artifact_finalized_name -cne $expectedFinalizedName) {
    Stop-Terminal 'hold:record_schema_invalid' 'record_schema_invalid'
  }
  if (
    $Record.artifact_sha256 -cnotmatch '^[0-9a-f]{64}$' -or
    $Record.source_commit -cnotmatch '^[0-9a-f]{40}$' -or
    $Record.curl_sha256 -cnotmatch '^[0-9a-f]{64}$' -or
    [long]$Record.curl_bytes -ne $CurlBytes -or
    [string]::IsNullOrWhiteSpace([string]$Record.powershell_version)
  ) {
    Stop-Terminal 'hold:record_schema_invalid' 'record_schema_invalid'
  }
  if (
    [bool]$Record.python_used -or
    -not [bool]$Record.no_credential -or
    -not [bool]$Record.cookies_redacted
  ) {
    Stop-Terminal 'hold:record_schema_invalid' 'record_schema_invalid'
  }
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
    url_effective = $Url
    http_status = 200
    header_lines = [int]$Headers.HeaderLines
    location_lines = [int]$Headers.LocationLines
    body_bytes = [long]$Body.Bytes
    size_download = [long]$Body.Bytes
    body_sha256 = $Body.Sha256
    started_at = $timestamp
    ended_at = $timestamp
  }
}

function Invoke-ValidateOnly {
  $searchHeaderInfo = Get-HeaderInfoFromPath $SearchHeaders
  $hydrateHeaderInfo = Get-HeaderInfoFromPath $HydrateHeaders
  $downloadHeaderInfo = Get-HeaderInfoFromPath $DownloadHeaders
  $validated = Get-ValidatedInputs -SearchBodyPath $SearchBody -HydrateBodyPath $HydrateBody -DownloadBodyPath $DownloadBody -SearchHeaderInfo $searchHeaderInfo -HydrateHeaderInfo $hydrateHeaderInfo -DownloadHeaderInfo $downloadHeaderInfo
  $stages = [pscustomobject]@{
    Search = New-ProbeStageRecord -Url $SearchUrl -Body $validated.SearchBody -Headers $validated.SearchHeaders
    Hydrate = New-ProbeStageRecord -Url $HydrateUrl -Body $validated.HydrateBody -Headers $validated.HydrateHeaders
    Download = New-ProbeStageRecord -Url ([string]$validated.Hydrate.download_uri) -Body $validated.DownloadBody -Headers $validated.DownloadHeaders
  }
  $runtime = [pscustomobject]@{
    CurlIdentity = [ordered]@{
      sha256 = $CurlSha256.ToLowerInvariant()
      bytes = [long]$CurlBytes
    }
    PowerShellVersion = $PSVersionTable.PSVersion.ToString()
  }
  $artifactFinalizedName = 'mcs2023-germa_salient.' + $validated.DownloadBody.Sha256 + '.csv'
  $probe = New-AcquisitionRecord -Stages $stages -ObservedDownloadUri ([string]$validated.Hydrate.download_uri) -ArtifactFinalizedName $artifactFinalizedName -ArtifactSha256 $validated.DownloadBody.Sha256 -ArtifactBytes $validated.DownloadBody.Bytes -ContentContract $validated.Content -OwnerToken 'OFFLINE-TEST-NOT-AUTHORIZATION' -ReviewerValue 'offline-validation' -SourceCommitValue (('0' * 39) + '1') -Runtime $runtime
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
      uniform_width = [bool]$validated.Content.uniform_width
      header_sha256 = [string]$validated.Content.header_sha256
    }
    artifact_finalized_name = $artifactFinalizedName
    artifact_sha256 = $validated.DownloadBody.Sha256
    artifact_bytes = [long]$validated.DownloadBody.Bytes
    encoding = [string]$validated.Content.encoding
    bom = [string]$validated.Content.bom
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
      curl_sha256 = $CurlSha256.ToLowerInvariant()
      curl_bytes = [long]$CurlBytes
      powershell_version = $PSVersionTable.PSVersion.ToString()
    }
    python_used = $false
    validator_engine = 'pure-powershell'
    r19_absolute_uri_roundtrip = [bool]$validated.Hydrate.r19_absolute_uri_roundtrip
    record_schema = [ordered]@{
      schema = 'project6.instrument-acquisition.v1'
      validated = $true
    }
  }
}

function Assert-LiveInputs {
  if ($SourceCommit -cnotmatch '^[0-9a-f]{40}$') {
    Stop-Terminal 'hold:source_commit_invalid' 'source_commit_invalid'
  }
  if (
    [string]::IsNullOrWhiteSpace($AuthorizingOwnerToken) -or
    $AuthorizingOwnerToken -match '^<.*>$' -or
    $AuthorizingOwnerToken.StartsWith('OFFLINE-TEST')
  ) {
    Stop-Terminal 'hold:owner_token_missing' 'owner_token_missing'
  }
  if ([string]::IsNullOrWhiteSpace($Reviewer) -or $Reviewer -ceq '<thread>') {
    Stop-Terminal 'hold:reviewer_missing' 'reviewer_missing'
  }
}

function Assert-SourceCommit {
  param(
    [Parameter(Mandatory = $true)][string]$RepoRoot,
    [Parameter(Mandatory = $true)][string]$ExpectedCommit
  )
  $git = Get-Command git.exe -ErrorAction Stop
  $headResult = Invoke-NativeSeparated -FilePath $git.Source -Arguments @('-C', $RepoRoot, 'rev-parse', 'HEAD')
  if ($headResult.ExitCode -ne 0 -or -not [string]::IsNullOrWhiteSpace($headResult.Stderr)) {
    Stop-Terminal 'hold:source_commit_unverified' 'source_commit_unverified'
  }
  $observed = $headResult.Stdout.Trim()
  if ($observed -cnotmatch '^[0-9a-f]{40}$' -or $observed -cne $ExpectedCommit) {
    Stop-Terminal 'hold:source_commit_mismatch' 'source_commit_mismatch'
  }
  $statusResult = Invoke-NativeSeparated -FilePath $git.Source -Arguments @('-C', $RepoRoot, 'status', '--porcelain=v1', '--untracked-files=all')
  if (
    $statusResult.ExitCode -ne 0 -or
    -not [string]::IsNullOrWhiteSpace($statusResult.Stderr) -or
    -not [string]::IsNullOrWhiteSpace($statusResult.Stdout)
  ) {
    Stop-Terminal 'hold:source_worktree_dirty' 'source_worktree_dirty'
  }
  return $observed
}

function Invoke-LiveAcquisition {
  Assert-LiveInputs
  if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $runId = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ', [System.Globalization.CultureInfo]::InvariantCulture) + '-' + [guid]::NewGuid().ToString('N')
    $script:OutputRoot = Join-Path $OutputBase $runId
  }
  $preflight = Invoke-Preflight
  $observedSourceCommit = Assert-SourceCommit -RepoRoot $preflight.RepoRoot -ExpectedCommit $SourceCommit
  New-OutputRootOnce $preflight.OutputRoot
  $requestCount = 0
  [long]$totalResponseBytes = 0

  $search = Invoke-Stage -Stage 'search' -Url $SearchUrl -Accept 'application/json' -MaxBytes $MetadataMaxBytes -StageSeconds $MetadataStageSeconds -RequestCount ([ref]$requestCount) -Root $preflight.OutputRoot
  Require-Clean200 -Result $search -StageSeconds $MetadataStageSeconds
  $searchBytes = [System.IO.File]::ReadAllBytes($search.BodyPath)
  Add-StageBytes ([ref]$totalResponseBytes) $searchBytes.Length
  [void](Assert-SearchContract $searchBytes)

  $hydrate = Invoke-Stage -Stage 'hydrate' -Url $HydrateUrl -Accept 'application/json' -MaxBytes $MetadataMaxBytes -StageSeconds $MetadataStageSeconds -RequestCount ([ref]$requestCount) -Root $preflight.OutputRoot
  Require-Clean200 -Result $hydrate -StageSeconds $MetadataStageSeconds
  $hydrateBytes = [System.IO.File]::ReadAllBytes($hydrate.BodyPath)
  Add-StageBytes ([ref]$totalResponseBytes) $hydrateBytes.Length
  $hydrateValidation = Assert-HydrateContract $hydrateBytes

  $download = Invoke-Stage -Stage 'download' -Url ([string]$hydrateValidation.download_uri) -Accept '*/*' -MaxBytes ([long]$hydrateValidation.advertised_size) -StageSeconds $ArtifactStageSeconds -RequestCount ([ref]$requestCount) -Root $preflight.OutputRoot
  Require-Clean200 -Result $download -StageSeconds $ArtifactStageSeconds
  $artifactBytes = [System.IO.File]::ReadAllBytes($download.BodyPath)
  Add-StageBytes ([ref]$totalResponseBytes) $artifactBytes.Length
  $content = Assert-ArtifactContract -Bytes $artifactBytes -AdvertisedSize ([long]$hydrateValidation.advertised_size)
  if ($requestCount -ne 3) { Stop-Terminal 'hold:request_budget_incomplete' 'request_budget_incomplete' }

  $artifactSha256 = Get-Sha256Bytes $artifactBytes
  $artifactFinalizedName = 'mcs2023-germa_salient.' + $artifactSha256 + '.csv'
  $artifactPath = Join-Path $preflight.OutputRoot $artifactFinalizedName
  $stages = [pscustomobject]@{
    Search = New-StageRecord $search
    Hydrate = New-StageRecord $hydrate
    Download = New-StageRecord $download
  }
  $observedSourceCommit = Assert-SourceCommit -RepoRoot $preflight.RepoRoot -ExpectedCommit $observedSourceCommit
  $record = New-AcquisitionRecord -Stages $stages -ObservedDownloadUri ([string]$hydrateValidation.download_uri) -ArtifactFinalizedName $artifactFinalizedName -ArtifactSha256 $artifactSha256 -ArtifactBytes $artifactBytes.Length -ContentContract $content -OwnerToken $AuthorizingOwnerToken -ReviewerValue $Reviewer -SourceCommitValue $observedSourceCommit -Runtime $preflight
  [void](Assert-RecordSchema $record)

  Write-BytesCreateOnce -Path $artifactPath -Bytes $artifactBytes
  $delivered = Get-BodyRecord $artifactPath
  if ($delivered.Bytes -ne $artifactBytes.Length -or $delivered.Sha256 -cne $artifactSha256) {
    Stop-Terminal 'hold:artifact_persist_failed' 'artifact_persist_failed'
  }
  $recordPath = Join-Path $preflight.OutputRoot 'acquisition-record.json'
  Write-Utf8CreateOnce -Path $recordPath -Text ($record | ConvertTo-Json -Depth 10)
  return [ordered]@{
    terminal = 'acquired'
    request_count = $requestCount
    run_root = $preflight.OutputRoot
    artifact = $artifactPath
    acquisition_record = $recordPath
    artifact_sha256 = $artifactSha256
    artifact_bytes = [long]$artifactBytes.Length
    source_commit = $observedSourceCommit
  }
}

try {
  if ($ValidateOnly) {
    $result = Invoke-ValidateOnly
  } else {
    $result = Invoke-LiveAcquisition
  }
  Write-Output ($result | ConvertTo-Json -Depth 10 -Compress)
  exit 0
} catch {
  $terminal = Get-ExceptionTerminal $_.Exception
  $code = Get-ExceptionCode $_.Exception
  Write-Output ('terminal=' + $terminal)
  Write-Output ('code=' + $code)
  exit 2
}
