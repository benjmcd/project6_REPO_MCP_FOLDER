[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PythonArchive
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProductionLauncher = 'py.exe'
$ProductionLauncherTag = '-V:PythonCore/3.12'
$ProductionAmbientBytes = [long]104952
$ProductionAmbientSha256 = '4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a'
$ProductionArchiveName = 'python-3.12.10-embed-amd64.zip'
$ProductionArchiveBytes = [long]11133606
$ProductionArchiveSha256 = '4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3'
$ProductionArchiveMember = 'python.exe'

function Test-FullyQualifiedLocalPath([string]$Path) {
    try {
        $root = [IO.Path]::GetPathRoot($Path)
        $full = [IO.Path]::GetFullPath($Path)
        return $root -match '\A[A-Za-z]:\\\z' -and
            [string]::Equals($full, $Path, [StringComparison]::OrdinalIgnoreCase)
    }
    catch { return $false }
}

function Resolve-OrdinaryFixedFile(
    [string]$Path,
    [string]$Code,
    [scriptblock]$DriveTypeResolver = $null
) {
    try {
        if (-not (Test-FullyQualifiedLocalPath $Path)) { throw $Code }
        $full = [IO.Path]::GetFullPath($Path)
        $item = Get-Item -LiteralPath $full -Force
        if ($item.PSIsContainer -or
            -not [string]::Equals($item.FullName, $full, [StringComparison]::OrdinalIgnoreCase) -or
            ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw $Code
        }

        $volumeRoot = [IO.Path]::GetPathRoot($full)
        $driveType = if ($null -eq $DriveTypeResolver) {
            [IO.DriveInfo]::new($volumeRoot).DriveType
        } else {
            & $DriveTypeResolver $volumeRoot
        }
        if ($driveType -ne [IO.DriveType]::Fixed) { throw $Code }
        $currentPath = $item.Directory.FullName
        while ($true) {
            $current = Get-Item -LiteralPath $currentPath -Force
            if (-not $current.PSIsContainer -or
                ($current.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or
                -not [string]::Equals(
                    [IO.Path]::GetPathRoot($current.FullName),
                    $volumeRoot,
                    [StringComparison]::OrdinalIgnoreCase
                )) {
                throw $Code
            }
            if ([string]::Equals(
                    $current.FullName.TrimEnd('\'),
                    $volumeRoot.TrimEnd('\'),
                    [StringComparison]::OrdinalIgnoreCase
                )) {
                break
            }
            $parentPath = Split-Path -Parent $current.FullName
            if ([string]::IsNullOrWhiteSpace($parentPath) -or
                [string]::Equals($parentPath, $currentPath, [StringComparison]::OrdinalIgnoreCase)) {
                throw $Code
            }
            $currentPath = $parentPath
        }
        return $item
    }
    catch { throw $Code }
}

function Get-LowerSha256([IO.Stream]$Stream) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($sha.ComputeHash($Stream))).Replace('-', '').ToLowerInvariant()
    }
    finally { $sha.Dispose() }
}

function Assert-PythonBindingMatch(
    [long]$AmbientBytes,
    [string]$AmbientSha256,
    [long]$MemberBytes,
    [string]$MemberSha256
) {
    if ($MemberBytes -ne $AmbientBytes -or
        -not [string]::Equals($MemberSha256, $AmbientSha256, [StringComparison]::Ordinal)) {
        throw 'python_binding_mismatch'
    }
}

function Invoke-PythonBindingLauncher([string]$LauncherExecutable, [string]$LauncherTag) {
    $process = $null
    try {
        $start = [System.Diagnostics.ProcessStartInfo]::new()
        $start.FileName = $LauncherExecutable
        $start.Arguments = "$LauncherTag -I -S -c `"import sys; print(sys.executable)`""
        $start.UseShellExecute = $false
        $start.CreateNoWindow = $true
        $start.RedirectStandardOutput = $true
        $start.RedirectStandardError = $true

        $process = [System.Diagnostics.Process]::new()
        $process.StartInfo = $start
        if (-not $process.Start()) { throw 'python_binding_launcher_invalid' }
        $stdout = $process.StandardOutput.ReadToEnd()
        $stderr = $process.StandardError.ReadToEnd()
        $process.WaitForExit()
        if ($process.ExitCode -ne 0 -or -not [string]::IsNullOrEmpty($stderr)) {
            throw 'python_binding_launcher_invalid'
        }
        if ($stdout -notmatch '\A([^\r\n]+)(?:\r\n|\n|\r)?\z') {
            throw 'python_binding_launcher_invalid'
        }
        $candidate = $Matches[1]
        if (-not (Test-FullyQualifiedLocalPath $candidate)) {
            throw 'python_binding_launcher_invalid'
        }
        return $candidate
    }
    catch { throw 'python_binding_launcher_invalid' }
    finally {
        if ($null -ne $process) { $process.Dispose() }
    }
}

function Get-PythonBindingObservation(
    [string]$LauncherExecutable,
    [string]$LauncherTag,
    [string]$ArchivePath,
    [long]$ExpectedAmbientBytes,
    [string]$ExpectedAmbientSha256,
    [string]$ExpectedArchiveName,
    [long]$ExpectedArchiveBytes,
    [string]$ExpectedArchiveSha256,
    [string]$ExpectedArchiveMember,
    [scriptblock]$AmbientHeldProbe = $null,
    [scriptblock]$ArchiveHeldProbe = $null
) {
    $ambientPath = Invoke-PythonBindingLauncher $LauncherExecutable $LauncherTag
    $ambientItem = Resolve-OrdinaryFixedFile $ambientPath 'python_binding_ambient_invalid'
    $archiveItem = Resolve-OrdinaryFixedFile $ArchivePath 'python_binding_archive_invalid'
    if (-not [string]::Equals($archiveItem.Name, $ExpectedArchiveName, [StringComparison]::Ordinal)) {
        throw 'python_binding_archive_invalid'
    }

    $ambientStream = $null
    try {
        $ambientStream = [IO.File]::Open(
            $ambientItem.FullName,
            [IO.FileMode]::Open,
            [IO.FileAccess]::Read,
            [IO.FileShare]::Read
        )
        $ambientBytes = $ambientStream.Length
        $ambientSha256 = Get-LowerSha256 $ambientStream
        if ($null -ne $AmbientHeldProbe) {
            & $AmbientHeldProbe $ambientItem.FullName $ambientStream $null
        }
    }
    catch { throw 'python_binding_ambient_invalid' }
    finally {
        if ($null -ne $ambientStream) { $ambientStream.Dispose() }
    }
    if ($ambientBytes -ne $ExpectedAmbientBytes -or
        -not [string]::Equals($ambientSha256, $ExpectedAmbientSha256, [StringComparison]::Ordinal)) {
        throw 'python_binding_ambient_invalid'
    }

    $archiveStream = $null
    try {
        $archiveStream = [IO.File]::Open(
            $archiveItem.FullName,
            [IO.FileMode]::Open,
            [IO.FileAccess]::Read,
            [IO.FileShare]::Read
        )
        $archiveBytes = $archiveStream.Length
        $archiveSha256 = Get-LowerSha256 $archiveStream
        if ($archiveBytes -ne $ExpectedArchiveBytes -or
            -not [string]::Equals($archiveSha256, $ExpectedArchiveSha256, [StringComparison]::Ordinal)) {
            throw 'python_binding_archive_invalid'
        }
        if (-not $archiveStream.CanSeek) { throw 'python_binding_archive_invalid' }
        $archiveStream.Position = 0
    }
    catch {
        if ($null -ne $archiveStream) {
            try { $archiveStream.Dispose() } catch { }
        }
        throw 'python_binding_archive_invalid'
    }

    $zip = $null
    try {
        Add-Type -AssemblyName System.IO.Compression
        $zip = [System.IO.Compression.ZipArchive]::new(
            $archiveStream,
            [System.IO.Compression.ZipArchiveMode]::Read,
            $true
        )
        if ($null -ne $ArchiveHeldProbe) {
            & $ArchiveHeldProbe $archiveItem.FullName $archiveStream $zip
        }
        $matches = @($zip.Entries | Where-Object {
            [string]::Equals($_.FullName, $ExpectedArchiveMember, [StringComparison]::OrdinalIgnoreCase)
        })
        if ($matches.Count -ne 1 -or
            -not [string]::Equals($matches[0].FullName, $ExpectedArchiveMember, [StringComparison]::Ordinal)) {
            throw 'python_binding_archive_member_invalid'
        }
        $memberStream = $null
        try {
            $memberStream = $matches[0].Open()
            $memberBytes = $matches[0].Length
            $memberSha256 = Get-LowerSha256 $memberStream
        }
        finally {
            if ($null -ne $memberStream) { $memberStream.Dispose() }
        }
    }
    catch { throw 'python_binding_archive_member_invalid' }
    finally {
        if ($null -ne $zip) { $zip.Dispose() }
        if ($null -ne $archiveStream) { $archiveStream.Dispose() }
    }

    Assert-PythonBindingMatch $ambientBytes $ambientSha256 $memberBytes $memberSha256

    return [pscustomobject][ordered]@{
        status = 'PYTHON_BINDING_OK'
        launcher_tag = $LauncherTag
        ambient_interpreter = $ambientItem.FullName
        ambient_interpreter_root = $ambientItem.Directory.FullName
        ambient_bytes = [long]$ambientBytes
        ambient_sha256 = $ambientSha256
        archive_path = $archiveItem.FullName
        archive_bytes = [long]$archiveBytes
        archive_sha256 = $archiveSha256
        archive_member = $matches[0].FullName
        archive_member_bytes = [long]$memberBytes
        archive_member_sha256 = $memberSha256
        expected_worker_sha256 = $ambientSha256
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    Get-PythonBindingObservation `
        $ProductionLauncher `
        $ProductionLauncherTag `
        $PythonArchive `
        $ProductionAmbientBytes `
        $ProductionAmbientSha256 `
        $ProductionArchiveName `
        $ProductionArchiveBytes `
        $ProductionArchiveSha256 `
        $ProductionArchiveMember
}
