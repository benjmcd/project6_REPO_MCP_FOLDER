[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProfileMoniker,
    [Parameter(Mandatory = $true)][string]$OutputBinding
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Test-FullyQualifiedLocalPath([string]$Path) {
    try {
        $root = [IO.Path]::GetPathRoot($Path)
        $full = [IO.Path]::GetFullPath($Path)
        return $root -match '\A[A-Za-z]:\\\z' -and
            [string]::Equals($full, $Path, [StringComparison]::OrdinalIgnoreCase)
    }
    catch { return $false }
}

function Resolve-ExactDirectory([string]$Path, [string]$Code) {
    if (-not (Test-FullyQualifiedLocalPath $Path)) { throw $Code }
    $item = Get-Item -LiteralPath $Path -Force
    if (-not $item.PSIsContainer -or $item.FullName -ne [IO.Path]::GetFullPath($Path)) {
        throw $Code
    }
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw $Code }
    if ([IO.DriveInfo]::new($item.PSDrive.Root).DriveType -ne [IO.DriveType]::Fixed) {
        throw $Code
    }
    return $item.FullName
}

function Assert-StableDirectoryAncestors([string]$Path, [string]$Code) {
    $full = [IO.Path]::GetFullPath($Path)
    $volumeRoot = [IO.Path]::GetPathRoot($full)
    $current = $full
    while ($true) {
        $item = Get-Item -LiteralPath $current -Force
        if (-not $item.PSIsContainer -or
            ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or
            -not [string]::Equals([IO.Path]::GetPathRoot($item.FullName), $volumeRoot, [StringComparison]::OrdinalIgnoreCase)) {
            throw $Code
        }
        if ([string]::Equals($item.FullName.TrimEnd('\'), $volumeRoot.TrimEnd('\'), [StringComparison]::OrdinalIgnoreCase)) {
            break
        }
        $parent = Split-Path -Parent $item.FullName
        if ([string]::IsNullOrWhiteSpace($parent) -or [string]::Equals($parent, $current, [StringComparison]::OrdinalIgnoreCase)) {
            throw $Code
        }
        $current = $parent
    }
}

function Convert-SidToText([IntPtr]$Sid) {
    $text = [IntPtr]::Zero
    if (-not [Project6ProfileProvisioner]::ConvertSidToStringSid($Sid, [ref]$text)) {
        throw 'worker_profile_sid_invalid'
    }
    try { return [Runtime.InteropServices.Marshal]::PtrToStringUni($text) }
    finally { [void][Project6ProfileProvisioner]::LocalFree($text) }
}

function Write-CreateOnce([string]$Path, [byte[]]$Bytes) {
    try {
        $stream = [IO.File]::Open($Path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        try {
            $stream.Write($Bytes, 0, $Bytes.Length)
            $stream.Flush($true)
        }
        finally { $stream.Dispose() }
    }
    catch { throw 'worker_profile_binding_write_failed' }
}

function ConvertTo-CanonicalUtf8([Collections.IDictionary]$Document) {
    $json = $Document | ConvertTo-Json -Compress
    $encoding = [Text.UTF8Encoding]::new($false, $true)
    return $encoding.GetBytes($json)
}

function Assert-BindingObservation([string]$Path, [Collections.IDictionary]$Expected) {
    try {
        $bytes = [IO.File]::ReadAllBytes($Path)
        if ($bytes.Length -eq 0 -or $bytes.Length -gt 65536) {
            throw 'worker_profile_binding_observation_failed'
        }
        $encoding = [Text.UTF8Encoding]::new($false, $true)
        $observed = $encoding.GetString($bytes) | ConvertFrom-Json
        $expectedFields = @($Expected.Keys)
        $observedFields = @($observed.PSObject.Properties.Name)
        [Array]::Sort($expectedFields, [StringComparer]::Ordinal)
        [Array]::Sort($observedFields, [StringComparer]::Ordinal)
        if ([string]::Join("`n", $expectedFields) -ne [string]::Join("`n", $observedFields)) {
            throw 'worker_profile_binding_observation_failed'
        }
        foreach ($field in $expectedFields) {
            if (-not [string]::Equals([string]$observed.$field, [string]$Expected[$field], [StringComparison]::Ordinal)) {
                throw 'worker_profile_binding_observation_failed'
            }
        }
    }
    catch { throw 'worker_profile_binding_observation_failed' }
}

if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw 'worker_profile_provisioner_windows_required'
}
$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'worker_profile_provisioner_elevation_required'
}
if ($ProfileMoniker -notmatch '\A[A-Za-z0-9][A-Za-z0-9._-]{0,63}\z') {
    throw 'worker_profile_moniker_invalid'
}
if (-not (Test-FullyQualifiedLocalPath $OutputBinding) -or (Test-Path -LiteralPath $OutputBinding)) {
    throw 'worker_profile_binding_invalid'
}
$outputParent = Resolve-ExactDirectory (Split-Path -Parent $OutputBinding) 'worker_profile_binding_parent_invalid'
Assert-StableDirectoryAncestors $outputParent 'worker_profile_binding_parent_invalid'

Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class Project6ProfileProvisioner {
  [DllImport("userenv.dll", CharSet=CharSet.Unicode)] public static extern int CreateAppContainerProfile(string name, string display, string description, IntPtr capabilities, uint count, out IntPtr sid);
  [DllImport("userenv.dll", CharSet=CharSet.Unicode)] public static extern int DeriveAppContainerSidFromAppContainerName(string name, out IntPtr sid);
  [DllImport("userenv.dll", CharSet=CharSet.Unicode)] public static extern int GetAppContainerFolderPath(string sid, out IntPtr path);
  [DllImport("advapi32.dll", CharSet=CharSet.Unicode, SetLastError=true)] public static extern bool ConvertSidToStringSid(IntPtr sid, out IntPtr text);
  [DllImport("advapi32.dll")] public static extern IntPtr FreeSid(IntPtr sid);
  [DllImport("kernel32.dll")] public static extern IntPtr LocalFree(IntPtr value);
  [DllImport("ole32.dll")] public static extern void CoTaskMemFree(IntPtr value);
}
'@

$brokerIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$brokerSid = $brokerIdentity.User.Value
$brokerProfileRoot = Resolve-ExactDirectory ([Environment]::GetFolderPath([Environment+SpecialFolder]::UserProfile)) 'worker_broker_profile_invalid'
$userDataRoot = Resolve-ExactDirectory (Join-Path $brokerProfileRoot 'AppData\Local') 'worker_user_data_invalid'

$createdSid = [IntPtr]::Zero
$created = [Project6ProfileProvisioner]::CreateAppContainerProfile(
    $ProfileMoniker, $ProfileMoniker, $ProfileMoniker, [IntPtr]::Zero, 0, [ref]$createdSid
)
if ($created -ne 0 -or $createdSid -eq [IntPtr]::Zero) {
    throw 'worker_profile_create_failed'
}
try {
    $createdPackageSid = Convert-SidToText $createdSid
    $derivedSid = [IntPtr]::Zero
    $derived = [Project6ProfileProvisioner]::DeriveAppContainerSidFromAppContainerName($ProfileMoniker, [ref]$derivedSid)
    if ($derived -ne 0 -or $derivedSid -eq [IntPtr]::Zero) {
        throw 'worker_profile_derive_failed'
    }
    try { $derivedPackageSid = Convert-SidToText $derivedSid }
    finally { [void][Project6ProfileProvisioner]::FreeSid($derivedSid) }
    if ($derivedPackageSid -ne $createdPackageSid) { throw 'worker_profile_sid_mismatch' }

    $profilePath = [IntPtr]::Zero
    $folder = [Project6ProfileProvisioner]::GetAppContainerFolderPath($createdPackageSid, [ref]$profilePath)
    if ($folder -ne 0 -or $profilePath -eq [IntPtr]::Zero) {
        throw 'worker_profile_root_invalid'
    }
    try { $profileRootText = [Runtime.InteropServices.Marshal]::PtrToStringUni($profilePath) }
    finally { [Project6ProfileProvisioner]::CoTaskMemFree($profilePath) }
    $appContainerProfileRoot = Resolve-ExactDirectory $profileRootText 'worker_profile_root_invalid'

    $binding = [ordered]@{
        appcontainer_profile_root = $appContainerProfileRoot
        broker_profile_root = $brokerProfileRoot
        broker_sid = $brokerSid
        package_sid = $createdPackageSid
        profile_moniker = $ProfileMoniker
        user_data_root = $userDataRoot
    }
    $bindingBytes = ConvertTo-CanonicalUtf8 $binding
    Write-CreateOnce ([IO.Path]::GetFullPath($OutputBinding)) $bindingBytes
    Assert-BindingObservation ([IO.Path]::GetFullPath($OutputBinding)) $binding
}
finally { [void][Project6ProfileProvisioner]::FreeSid($createdSid) }

Write-Output "WORKER_PROFILE_BINDING: $([IO.Path]::GetFullPath($OutputBinding))"
