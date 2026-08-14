#Requires -Version 5.1

<#
Repo-custody ScienceBase exact-chain characterization instrument.

The live mode performs at most three GETs: search, hydrate, and the exact
hydrate-derived download. The fixture mode is local-only: it performs the
pinned curl identity check but cannot issue a curl request. Neither mode
invokes Project6, creates or consumes a GO, or authorizes W5, readiness, or a
live run.
#>

[CmdletBinding(DefaultParameterSetName = 'Fixture')]
param(
  [Parameter(Mandatory = $true)]
  [string]$OutputRoot,

  [Parameter(Mandatory = $true, ParameterSetName = 'Live')]
  [switch]$Live,

  [Parameter(Mandatory = $true, ParameterSetName = 'Fixture')]
  [switch]$LocalFixtureDryRun,

  [Parameter(ParameterSetName = 'Fixture')]
  [ValidateSet('Characterized', 'MeasurementOnly', 'ArtifactMarkup', 'DuplicateSearchJson', 'NonJsonWhitespace', 'CaseDistinctJson', 'ItemsObject', 'ItemsMixed', 'FilesObject', 'FilesMixed', 'OutputCollision', 'ConnectBound', 'LocationRejected')]
  [string]$FixtureScenario = 'Characterized'
)

Set-StrictMode -Version 5.1
$ErrorActionPreference = 'Stop'

$Notice = 'This record is a non-authorizing characterization. It is not W5, not owner readiness, and not live-run authorization.'
$CurlPath = 'C:\Windows\System32\curl.exe'
$CurlSha256 = '73D24149FF289AFC49EC41F08918EF9FAA727D39AD993E929757DC2DDAFAB805'
$CurlBytes = 818512L
$CurlVersionFirstLine = 'curl 8.21.0 (Windows) libcurl/8.21.0 Schannel zlib/1.3.2 WinIDN WinLDAP'
$ReferenceProbeSha256 = '4acd6c4b6b5c09f31d8d4198c642ab796612e8f84b0afc0f6057a4eb55d4d855'
$ReferenceCarrierName = 'Project6_ScienceBase_NRC_APS_External_Investigation_REAUDIT_FINAL_20260812.zip'
$ReferenceCarrierSha256 = 'fc0d4d84c8b64f2b61485d096a4cd0e8b234d12c23febdd8cd070c6f32beba78'
$ReferenceEntryName = 'project6_external_investigation_20260812_reaudit_final/sciencebase_exact_chain_probe.ps1'
$Query = 'Mineral Commodity Summaries 2023 GERMANIUM'
$ExpectedItemId = '63d1a3c6d34e06fef15006be'
$ExpectedFileName = 'mcs2023-germa_salient.csv'
$MetadataMaxBytes = 64MB
$ArtifactMaxBytes = 64MB
$SessionMaxBytes = 512MB
$ConnectTimeoutSeconds = 10
$MetadataStageSeconds = 30
$ArtifactStageSeconds = 30
$MaximumRequests = 3

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

function Get-Sha256Bytes {
  param([Parameter(Mandatory = $true)][AllowEmptyCollection()][byte[]]$Bytes)
  $sha = [System.Security.Cryptography.SHA256]::Create()
  try {
    return ([System.BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-', '').ToLowerInvariant()
  } finally {
    $sha.Dispose()
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
  param([Parameter(Mandatory = $true)][byte[]]$Bytes)
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

function Get-MetricValue {
  param([string]$Text, [string]$Name)
  $match = [regex]::Match($Text, ('(?m)^' + [regex]::Escape($Name) + '=(.*)$'))
  if (-not $match.Success) { return $null }
  return $match.Groups[1].Value.Trim()
}

function Get-LastHeaderValue {
  param([string]$Text, [string]$Name)
  $matches = [regex]::Matches(
    $Text,
    ('(?im)^' + [regex]::Escape($Name) + '\s*:\s*([^\r\n]*?)\r?$')
  )
  if ($matches.Count -eq 0) { return $null }
  return $matches[$matches.Count - 1].Groups[1].Value.Trim()
}

function Get-FixtureArtifactBytes {
  param([string]$Scenario)
  $encoding = New-Object System.Text.UTF8Encoding($false, $true)
  if ($Scenario -ceq 'MeasurementOnly') {
    return $encoding.GetBytes("only_column`r`n")
  }
  if ($Scenario -ceq 'ArtifactMarkup') {
    return $encoding.GetBytes('<html>fixture rejection</html>')
  }
  return $encoding.GetBytes("Year,Commodity,Value`r`n2023,Germanium,42`r`n2024,Germanium`r`n")
}

function Get-LocalFixtureResult {
  param([string]$Stage, [string]$Scenario)
  $encoding = New-Object System.Text.UTF8Encoding($false, $true)
  $artifactBytes = Get-FixtureArtifactBytes $Scenario
  $downloadUri = 'https://www.sciencebase.gov/catalog/file/get/63d1a3c6d34e06fef15006be/mcs2023-germa_salient.csv'
  if ($Stage -ceq 'search' -and $Scenario -ceq 'ConnectBound') {
    return [pscustomobject]@{
      BodyBytes = [byte[]]@()
      HeaderBytes = [byte[]]@()
      ExitCode = 28
      Metrics = "HTTP_CODE=000`nTIME_CONNECT=0.000000`nTIME_TOTAL=10.000000`nSIZE_DOWNLOAD=0`nURL_EFFECTIVE="
      Stderr = 'fixture connect bound'
    }
  }
  if ($Stage -ceq 'search' -and $Scenario -ceq 'LocationRejected') {
    return [pscustomobject]@{
      BodyBytes = $encoding.GetBytes('{}')
      HeaderBytes = $encoding.GetBytes("HTTP/1.1 302 Found`r`nLocation: https://www.sciencebase.gov/other`r`n`r`n")
      ExitCode = 0
      Metrics = "HTTP_CODE=302`nTIME_CONNECT=0.001000`nTIME_TOTAL=0.002000`nSIZE_DOWNLOAD=2`nURL_EFFECTIVE=https://www.sciencebase.gov/catalog/items"
      Stderr = ''
    }
  }
  if ($Stage -ceq 'search') {
    $json = if ($Scenario -ceq 'DuplicateSearchJson') {
      '{"items":[{"id":"63d1a3c6d34e06fef15006be","meta":{"x":1,"\u0078":2}}]}'
    } elseif ($Scenario -ceq 'NonJsonWhitespace') {
      '{"items":' + [char]0x00A0 + '[{"id":"63d1a3c6d34e06fef15006be"}]}'
    } elseif ($Scenario -ceq 'CaseDistinctJson') {
      '{"items":[{"id":"63d1a3c6d34e06fef15006be"}],"x":1,"X":2}'
    } elseif ($Scenario -ceq 'ItemsObject') {
      '{"items":{"id":"63d1a3c6d34e06fef15006be"}}'
    } elseif ($Scenario -ceq 'ItemsMixed') {
      '{"items":[{"id":"63d1a3c6d34e06fef15006be"},7]}'
    } else {
      '{"items":[{"id":"63d1a3c6d34e06fef15006be"}]}'
    }
    return [pscustomobject]@{
      BodyBytes = $encoding.GetBytes($json)
      HeaderBytes = $encoding.GetBytes("HTTP/1.1 200 OK`r`nContent-Type: application/json`r`nSet-Cookie: fixture=secret`r`n`r`n")
      ExitCode = 0
      Metrics = "HTTP_CODE=200`nTIME_CONNECT=0.001000`nTIME_TOTAL=0.002000`nSIZE_DOWNLOAD=$($encoding.GetByteCount($json))`nURL_EFFECTIVE=https://www.sciencebase.gov/catalog/items"
      Stderr = ''
    }
  }
  if ($Stage -ceq 'hydrate') {
    $fileJson = '{"name":"' + $ExpectedFileName + '","downloadUri":"' + $downloadUri + '","url":"' + $downloadUri + '","size":' + $artifactBytes.Length + '}'
    $filesJson = if ($Scenario -ceq 'FilesObject') {
      $fileJson
    } elseif ($Scenario -ceq 'FilesMixed') {
      '[' + $fileJson + ',7]'
    } else {
      '[' + $fileJson + ']'
    }
    $json = '{"id":"' + $ExpectedItemId + '","files":' + $filesJson + '}'
    return [pscustomobject]@{
      BodyBytes = $encoding.GetBytes($json)
      HeaderBytes = $encoding.GetBytes("HTTP/1.1 200 OK`r`nContent-Type: application/json`r`n`r`n")
      ExitCode = 0
      Metrics = "HTTP_CODE=200`nTIME_CONNECT=0.001000`nTIME_TOTAL=0.002000`nSIZE_DOWNLOAD=$($encoding.GetByteCount($json))`nURL_EFFECTIVE=https://www.sciencebase.gov/catalog/item/$ExpectedItemId"
      Stderr = ''
    }
  }
  $artifactContentType = if ($Scenario -ceq 'ArtifactMarkup') { 'text/html; charset=utf-8' } else { 'text/csv; charset=utf-8' }
  return [pscustomobject]@{
    BodyBytes = $artifactBytes
    HeaderBytes = $encoding.GetBytes("HTTP/1.1 200 OK`r`nContent-Type: $artifactContentType`r`n`r`n")
    ExitCode = 0
    Metrics = "HTTP_CODE=200`nTIME_CONNECT=0.001000`nTIME_TOTAL=0.002000`nSIZE_DOWNLOAD=$($artifactBytes.Length)`nURL_EFFECTIVE=$downloadUri"
    Stderr = ''
  }
}

function Invoke-Stage {
  param(
    [string]$Stage,
    [string]$Url,
    [string]$Accept,
    [long]$MaxBytes,
    [int]$StageSeconds,
    [ref]$RequestCount,
    [string]$Root
  )
  $RequestCount.Value += 1
  if ($RequestCount.Value -gt $MaximumRequests) {
    Stop-Terminal 'hold:request_budget_exceeded' 'request_budget_exceeded'
  }
  $token = [guid]::NewGuid().ToString('N')
  $stageRoot = Join-Path $Root ("{0}-{1}" -f $Stage, $token)
  try {
    [void](New-Item -ItemType Directory -Path $stageRoot -ErrorAction Stop)
  } catch {
    if (Test-Path -LiteralPath $stageRoot) {
      Stop-Terminal 'hold:output_collision' 'output_collision'
    }
    throw
  }
  $bodyPath = Join-Path $stageRoot 'body.part'
  $headerPath = Join-Path $stageRoot 'headers.part'
  $metricsPath = Join-Path $stageRoot 'metrics.txt'
  $stderrPath = Join-Path $stageRoot 'stderr.txt'
  if ($LocalFixtureDryRun) {
    $fixture = Get-LocalFixtureResult -Stage $Stage -Scenario $FixtureScenario
    if ($Stage -ceq 'search' -and $FixtureScenario -ceq 'OutputCollision') {
      Write-Utf8CreateOnce -Path $bodyPath -Text 'fixture-original'
    }
    Write-BytesCreateOnce -Path $bodyPath -Bytes $fixture.BodyBytes
    Write-BytesCreateOnce -Path $headerPath -Bytes $fixture.HeaderBytes
    Write-Utf8CreateOnce -Path $metricsPath -Text $fixture.Metrics
    Write-Utf8CreateOnce -Path $stderrPath -Text $fixture.Stderr
    $exitCode = [int]$fixture.ExitCode
    $metricsText = [string]$fixture.Metrics
  } else {
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
    $native = Invoke-NativeSeparated -FilePath $CurlPath -Arguments $curlArgs
    $exitCode = [int]$native.ExitCode
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
    if (-not (Test-Path -LiteralPath $bodyPath -PathType Leaf)) {
      Write-BytesCreateOnce -Path $bodyPath -Bytes ([byte[]]@())
    }
  }
  $headers = Redact-HeaderDump -Path $headerPath
  $statusText = Get-MetricValue -Text $metricsText -Name 'HTTP_CODE'
  $status = if ($statusText -match '^\d{3}$') { [int]$statusText } else { 0 }
  return [pscustomobject]@{
    Stage = $Stage
    RequestOrdinal = $RequestCount.Value
    Url = $Url
    ExitCode = $exitCode
    HttpStatus = $status
    MetricsText = $metricsText
    BodyPath = $bodyPath
    HeaderPath = $headerPath
    HeaderText = $headers.Text
    HeaderSha256 = $headers.Sha256
    CookieHeadersObserved = $headers.CookieHeadersObserved
    MetricsPath = $metricsPath
    StderrPath = $stderrPath
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
  $body = [System.IO.File]::ReadAllBytes($Result.BodyPath)
  return [ordered]@{
    non_authorizing_notice = $Notice
    stage = $Result.Stage
    request_ordinal = $Result.RequestOrdinal
    url = $Result.Url
    curl_exit = $Result.ExitCode
    http_status = $Result.HttpStatus
    body_bytes = [long]$body.Length
    body_sha256 = Get-Sha256Bytes $body
    header_sha256_after_redaction = $Result.HeaderSha256
    cookie_headers_observed = $Result.CookieHeadersObserved
    content_type = Get-LastHeaderValue -Text $Result.HeaderText -Name 'Content-Type'
    metrics = [ordered]@{
      time_connect = Get-MetricValue -Text $Result.MetricsText -Name 'TIME_CONNECT'
      time_total = Get-MetricValue -Text $Result.MetricsText -Name 'TIME_TOTAL'
      size_download = Get-MetricValue -Text $Result.MetricsText -Name 'SIZE_DOWNLOAD'
      url_effective = Get-MetricValue -Text $Result.MetricsText -Name 'URL_EFFECTIVE'
    }
  }
}

function Move-FileCreateOnce {
  param([string]$Source, [string]$Destination)
  if (Test-Path -LiteralPath $Destination) {
    Stop-Terminal 'hold:output_collision' 'output_collision'
  }
  [System.IO.File]::Move($Source, $Destination)
}

function Move-RejectedArtifact {
  param([string]$BodyPath, [string]$Code, [string]$Root)
  if ([string]::IsNullOrWhiteSpace($BodyPath) -or -not (Test-Path -LiteralPath $BodyPath -PathType Leaf)) {
    return $null
  }
  $safeCode = ([regex]::Replace($Code, '[^A-Za-z0-9_]+', '_')).Trim('_')
  if ([string]::IsNullOrWhiteSpace($safeCode)) { $safeCode = 'unknown' }
  $destination = Join-Path $Root ($ExpectedFileName + '.rejected.' + $safeCode)
  Move-FileCreateOnce -Source $BodyPath -Destination $destination
  return $destination
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
    $parsed.Fragment.Length -ne 0
  ) {
    Stop-Terminal 'hold:downloadUri_authority_rejected' 'downloadUri_authority_rejected'
  }
}

$preflight = $null
try {
  $preflight = Invoke-Preflight
  New-OutputRootOnce $preflight.OutputRoot
} catch {
  $terminal = Get-ExceptionTerminal $_.Exception
  $code = Get-ExceptionCode $_.Exception
  Write-Output ('LOCAL_NO_NETWORK_FIXTURE=' + [string][bool]$LocalFixtureDryRun)
  Write-Output ('terminal=' + $terminal)
  Write-Output ('code=' + $code)
  exit 2
}

$OutputRoot = $preflight.OutputRoot
$requestCount = 0
$totalResponseBytes = 0L
$stageRecords = New-Object System.Collections.ArrayList
$downloadResult = $null
$acceptedArtifactPath = $null
$rejectedArtifactPath = $null
$terminal = 'hold:internal_error'
$terminalCode = 'internal_error'
$searchUrl = 'https://www.sciencebase.gov/catalog/items?q=' + [uri]::EscapeDataString($Query) + '&format=json'
$hydrateUrl = 'https://www.sciencebase.gov/catalog/item/' + [uri]::EscapeDataString($ExpectedItemId) + '?format=json'

$summary = [ordered]@{
  schema = 'project6.sciencebase_exact_chain_characterization.v1'
  non_authorizing_notice = $Notice
  mode = 'A_characterization'
  execution = if ($LocalFixtureDryRun) { 'local_no_network_fixture' } else { 'live_three_get_chain' }
  fixture_scenario = if ($LocalFixtureDryRun) { $FixtureScenario } else { $null }
  generated_at_utc = (Get-Date).ToUniversalTime().ToString('o')
  terminal = 'started'
  terminal_code = $null
  provenance = [ordered]@{
    repo_script = $MyInvocation.MyCommand.Path
    reference_carrier_name = $ReferenceCarrierName
    reference_carrier_sha256 = $ReferenceCarrierSha256
    reference_entry_name = $ReferenceEntryName
    reference_probe_entry_sha256 = $ReferenceProbeSha256
    reference_probe_was_invoked = $false
  }
  host = [ordered]@{
    powershell_version = $preflight.PowerShellVersion
    convert_from_json_rejects_duplicates = $preflight.ConvertFromJsonRejectsDuplicates
    curl = $preflight.CurlIdentity
  }
  custody = [ordered]@{
    output_root = $OutputRoot
    output_root_create_once = $true
    raw_bytes_confined_to_output_root = $true
    enumerated_repo_worktrees = @($preflight.Worktrees)
  }
  bounds = [ordered]@{
    maximum_requests = [ordered]@{ value = $MaximumRequests; class = 'D' }
    redirects = [ordered]@{ value = 0; class = 'D' }
    retries = [ordered]@{ value = 0; class = 'D' }
    proxy = [ordered]@{ value = 'disabled'; class = 'D' }
    metadata_max_bytes_per_stage = [ordered]@{ value = $MetadataMaxBytes; class = 'D' }
    artifact_max_bytes = [ordered]@{ value = $ArtifactMaxBytes; class = 'D' }
    metadata_stage_seconds = [ordered]@{ value = $MetadataStageSeconds; class = 'D' }
    artifact_stage_seconds = [ordered]@{ value = $ArtifactStageSeconds; class = 'D' }
    connect_timeout_seconds = [ordered]@{ value = $ConnectTimeoutSeconds; class = 'E' }
    session_total_bytes = [ordered]@{ value = $SessionMaxBytes; class = 'D-implicit'; first_binding_possible = $false }
    artifact_size = [ordered]@{ value = 'positive hydrate-advertised exact size'; class = 'D-by-provider' }
  }
  target = [ordered]@{
    query = $Query
    expected_item_id = $ExpectedItemId
    expected_file_name = $ExpectedFileName
    search_url = $searchUrl
    hydrate_url = $hydrateUrl
    single_unpaginated_search = $true
    forbidden_search_parameters = @('max', 'offset', 'sort')
  }
  curl_posture = @(
    '--disable', "--proto '=https'", "--noproxy '*'", '--globoff',
    '--request GET', '--max-redirs 0', 'no retries', 'no cookies',
    'no credentials', '--no-clobber', '--connect-timeout 10', '--max-time 30'
  )
  stages = $stageRecords
  search_membership = $null
  hydrate_locator = $null
  artifact = $null
  total_response_bytes = 0L
  request_count = 0
  rejected_artifact = $null
}

try {
  $queryPairs = @($searchUrl.Substring($searchUrl.IndexOf('?') + 1).Split('&'))
  if ($queryPairs.Count -ne 2 -or $queryPairs[1] -cne 'format=json') {
    Stop-Terminal 'hold:search_request_shape_invalid' 'search_request_shape_invalid'
  }
  foreach ($forbiddenName in @('max', 'offset', 'sort')) {
    if ($queryPairs | Where-Object { $_ -match ('^(?i)' + [regex]::Escape($forbiddenName) + '=') }) {
      Stop-Terminal 'hold:search_request_shape_invalid' 'search_request_shape_invalid'
    }
  }

  $search = Invoke-Stage -Stage 'search' -Url $searchUrl -Accept 'application/json' `
    -MaxBytes $MetadataMaxBytes -StageSeconds $MetadataStageSeconds `
    -RequestCount ([ref]$requestCount) -Root $OutputRoot
  [void]$stageRecords.Add((New-StageRecord $search))
  Require-Clean200 -Result $search -StageSeconds $MetadataStageSeconds
  $searchBytes = [System.IO.File]::ReadAllBytes($search.BodyPath)
  Add-StageBytes ([ref]$totalResponseBytes) $searchBytes.Length
  $searchDecoded = ConvertFrom-ArtifactBytes $searchBytes
  $searchPayload = ConvertFrom-StrictJsonObject -Text $searchDecoded.Text -Stage 'search'
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
  $MatchingItems = @($items | Where-Object {
    $id = Get-ExactProperty -Object $_ -Name 'id'
    return $id.Present -and $id.Value -is [string] -and $id.Value -ceq $ExpectedItemId
  })
  if ($MatchingItems.Count -ne 1) {
    Stop-Terminal 'hold:search_expected_item_not_unique' 'search_expected_item_not_unique'
  }
  $summary.search_membership = [ordered]@{
    non_authorizing_notice = $Notice
    exact_item_id = $ExpectedItemId
    exact_matches = $MatchingItems.Count
    returned_items = $items.Count
    single_unpaginated_response = $true
  }

  $hydrate = Invoke-Stage -Stage 'hydrate' -Url $hydrateUrl -Accept 'application/json' `
    -MaxBytes $MetadataMaxBytes -StageSeconds $MetadataStageSeconds `
    -RequestCount ([ref]$requestCount) -Root $OutputRoot
  [void]$stageRecords.Add((New-StageRecord $hydrate))
  Require-Clean200 -Result $hydrate -StageSeconds $MetadataStageSeconds
  $hydrateBytes = [System.IO.File]::ReadAllBytes($hydrate.BodyPath)
  Add-StageBytes ([ref]$totalResponseBytes) $hydrateBytes.Length
  $hydrateDecoded = ConvertFrom-ArtifactBytes $hydrateBytes
  $item = ConvertFrom-StrictJsonObject -Text $hydrateDecoded.Text -Stage 'hydration'
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
  $MatchingFiles = @($files | Where-Object {
    $name = Get-ExactProperty -Object $_ -Name 'name'
    return $name.Present -and $name.Value -is [string] -and $name.Value -ceq $ExpectedFileName
  })
  if ($MatchingFiles.Count -ne 1) {
    Stop-Terminal 'hold:hydrate_expected_file_not_unique' 'hydrate_expected_file_not_unique'
  }
  $file = $MatchingFiles[0]
  $downloadProperty = Get-ExactProperty -Object $file -Name 'downloadUri'
  $urlProperty = Get-ExactProperty -Object $file -Name 'url'
  if (-not $downloadProperty.Present -or $downloadProperty.Value -isnot [string] -or [string]::IsNullOrWhiteSpace($downloadProperty.Value)) {
    Stop-Terminal 'hold:downloadUri_missing' 'downloadUri_missing'
  }
  $downloadUri = [string]$downloadProperty.Value
  if ($urlProperty.Present -and ($urlProperty.Value -isnot [string] -or [string]$urlProperty.Value -cne $downloadUri)) {
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
  $summary.hydrate_locator = [ordered]@{
    non_authorizing_notice = $Notice
    expected_file_matches = $MatchingFiles.Count
    downloadUri = $downloadUri
    url_alias_present = $urlProperty.Present
    url_alias_equal = (-not $urlProperty.Present) -or ([string]$urlProperty.Value -ceq $downloadUri)
    authority = 'https://www.sciencebase.gov:default-port; no userinfo or fragment'
    advertised_size = $advertisedSize
  }

  $downloadResult = Invoke-Stage -Stage 'download' -Url $downloadUri -Accept '*/*' `
    -MaxBytes $advertisedSize -StageSeconds $ArtifactStageSeconds `
    -RequestCount ([ref]$requestCount) -Root $OutputRoot
  [void]$stageRecords.Add((New-StageRecord $downloadResult))
  Require-Clean200 -Result $downloadResult -StageSeconds $ArtifactStageSeconds
  $artifactBytes = [System.IO.File]::ReadAllBytes($downloadResult.BodyPath)
  Add-StageBytes ([ref]$totalResponseBytes) $artifactBytes.Length
  if ($artifactBytes.Length -ne $advertisedSize) {
    Stop-Terminal 'hold:artifact_size_mismatch' 'artifact_size_mismatch'
  }
  $decoded = ConvertFrom-ArtifactBytes $artifactBytes
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
  $csv = Measure-Csv $decoded.Text
  $artifactSha256 = Get-Sha256Bytes $artifactBytes
  $acceptedName = ([System.IO.Path]::GetFileNameWithoutExtension($ExpectedFileName) + '.' + $artifactSha256 + [System.IO.Path]::GetExtension($ExpectedFileName))
  $acceptedCandidate = Join-Path $OutputRoot $acceptedName
  Move-FileCreateOnce -Source $downloadResult.BodyPath -Destination $acceptedCandidate
  $acceptedArtifactPath = $acceptedCandidate
  $utf8 = New-Object System.Text.UTF8Encoding($false, $true)
  $headerSha256 = Get-Sha256Bytes $utf8.GetBytes($csv.HeaderRaw)
  $summary.artifact = [ordered]@{
    non_authorizing_notice = $Notice
    file_name = $ExpectedFileName
    finalized_name = $acceptedName
    bytes = [long]$artifactBytes.Length
    sha256 = $artifactSha256
    encoding = $decoded.Encoding
    bom = $decoded.Bom
    content_type = Get-LastHeaderValue -Text $downloadResult.HeaderText -Name 'Content-Type'
    verbatim_header_line = $csv.HeaderRaw
    header_sha256_utf8_no_bom = $headerSha256
    column_count = $csv.ColumnCount
    column_names = @($csv.ColumnNames)
    data_row_count = $csv.DataRowCount
    uniform_row_width = $csv.UniformRowWidth
    minimum_field_count = $csv.MinimumFieldCount
    maximum_field_count = $csv.MaximumFieldCount
    has_at_least_one_data_row = $csv.HasAtLeastOneDataRow
    has_at_least_two_columns = $csv.HasAtLeastTwoColumns
  }
  $terminal = 'characterized'
  $terminalCode = 'characterized'
} catch {
  $terminal = Get-ExceptionTerminal $_.Exception
  $terminalCode = Get-ExceptionCode $_.Exception
  if ($null -ne $downloadResult -and $null -eq $acceptedArtifactPath) {
    try {
      $rejectedArtifactPath = Move-RejectedArtifact -BodyPath $downloadResult.BodyPath -Code $terminalCode -Root $OutputRoot
    } catch {
      $terminal = 'hold:quarantine_failed'
      $terminalCode = 'quarantine_failed'
    }
  }
}

if (
  $terminal -cne 'characterized' -and
  $terminal -notmatch '^hold:[A-Za-z0-9_]+$' -and
  $terminal -cne 'EXPERIMENT_BOUND_EXCEEDED:connect'
) {
  $terminal = 'hold:terminal_vocabulary_invalid'
  $terminalCode = 'terminal_vocabulary_invalid'
}
$summary.terminal = $terminal
$summary.terminal_code = $terminalCode
$summary.total_response_bytes = $totalResponseBytes
$summary.request_count = $requestCount
$summary.rejected_artifact = if ($null -ne $rejectedArtifactPath) { Split-Path -Leaf $rejectedArtifactPath } else { $null }
$recordPath = Join-Path $OutputRoot 'characterization.json'
Write-Utf8CreateOnce -Path $recordPath -Text ($summary | ConvertTo-Json -Depth 50)

Write-Output ('LOCAL_NO_NETWORK_FIXTURE=' + [string][bool]$LocalFixtureDryRun)
if ($LocalFixtureDryRun) { Write-Output ('fixture_scenario=' + $FixtureScenario) }
Write-Output ('terminal=' + $terminal)
Write-Output ('request_count=' + $requestCount)
Write-Output ('record=' + $recordPath)
if ($null -ne $acceptedArtifactPath) { Write-Output ('artifact=' + $acceptedArtifactPath) }
if ($null -ne $rejectedArtifactPath) { Write-Output ('rejected_artifact=' + $rejectedArtifactPath) }
if ($terminal -cne 'characterized') { exit 2 }
