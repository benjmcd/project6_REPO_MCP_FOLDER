[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PythonArchive,
    [Parameter(Mandatory = $true)][string]$ProfileBinding,
    [Parameter(Mandatory = $true)][string]$ProvisioningRoot,
    [Parameter(Mandatory = $true)][string]$OutputBinding,
    [Parameter(Mandatory = $true)][string]$CampaignRoot,
    [Parameter(Mandatory = $true)][string]$AmbientInterpreterRoot,
    [Parameter(Mandatory = $true)][string]$RepositoryRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$PythonVersion = '3.12.6'
$PythonArchitecture = 'amd64'
$PythonArchiveName = 'python-3.12.6-embed-amd64.zip'
$PythonArchiveSha256 = 'a86a2e28870967745d255cc597d1e4d19ae79e65e927cdc324baa0256202231c'
$OwnerSid = 'S-1-5-19'
$ProvisionerSid = 'S-1-5-20'
$SystemSid = 'S-1-5-18'
$AdministratorsSid = 'S-1-5-32-544'
$WorkerFiles = @(
    'tools/dual_live_run.py',
    'backend/app/__init__.py',
    'backend/app/services/__init__.py',
    'backend/app/services/connector_egress_contract.py',
    'backend/app/services/dual_live_effect_guard.py',
    'backend/app/services/dual_live_sciencebase_producer.py',
    'backend/app/services/dual_live_worker_bundle.py',
    'backend/app/services/dual_live_windows_boundary.py'
)

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
    if (-not $item.PSIsContainer -or $item.FullName -ne [IO.Path]::GetFullPath($Path)) { throw $Code }
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw $Code }
    if ([IO.DriveInfo]::new($item.PSDrive.Root).DriveType -ne [IO.DriveType]::Fixed) { throw $Code }
    return $item.FullName
}

function Resolve-ExactFile([string]$Path, [string]$Code) {
    if (-not (Test-FullyQualifiedLocalPath $Path)) { throw $Code }
    $item = Get-Item -LiteralPath $Path -Force
    if ($item.PSIsContainer -or $item.FullName -ne [IO.Path]::GetFullPath($Path)) { throw $Code }
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw $Code }
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
    return $full
}

function Assert-Outside([string]$Candidate, [string[]]$Forbidden) {
    $candidatePrefix = $Candidate.TrimEnd('\') + '\'
    foreach ($path in $Forbidden) {
        $forbiddenPrefix = $path.TrimEnd('\') + '\'
        if ($candidatePrefix.StartsWith($forbiddenPrefix, [StringComparison]::OrdinalIgnoreCase) -or
            $forbiddenPrefix.StartsWith($candidatePrefix, [StringComparison]::OrdinalIgnoreCase)) {
            throw 'worker_provisioning_root_forbidden'
        }
    }
}

function Write-CreateOnce([string]$Path, [byte[]]$Bytes, [string]$Code) {
    try {
        $stream = [IO.File]::Open($Path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        try {
            $stream.Write($Bytes, 0, $Bytes.Length)
            $stream.Flush($true)
        }
        finally { $stream.Dispose() }
    }
    catch { throw $Code }
}

function Write-GitBlobCreateOnce([string]$Repository, [string]$Object, [string]$Path) {
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = 'git.exe'
    $start.Arguments = "-C `"$Repository`" cat-file blob `"$Object`""
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $start
    try {
        if (-not $process.Start()) { throw 'worker_source_copy_failed' }
        $stream = [IO.File]::Open($Path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        try { $process.StandardOutput.BaseStream.CopyTo($stream) }
        finally { $stream.Dispose() }
        $errorText = $process.StandardError.ReadToEnd()
        $process.WaitForExit()
        if ($process.ExitCode -ne 0 -or -not [string]::IsNullOrEmpty($errorText)) {
            throw 'worker_source_copy_failed'
        }
    }
    catch { throw 'worker_source_copy_failed' }
    finally { $process.Dispose() }
}

function Get-RelativeWorkerPath([string]$Root, [string]$Path) {
    $rootUri = [Uri]::new($Root.TrimEnd('\') + '\')
    $pathUri = [Uri]::new($Path)
    $relative = [Uri]::UnescapeDataString($rootUri.MakeRelativeUri($pathUri).ToString())
    if ($relative.StartsWith('../') -or [Uri]::IsWellFormedUriString($relative, [UriKind]::Absolute)) {
        throw 'worker_inventory_path_invalid'
    }
    return $relative.Replace('\', '/')
}

function Get-Sha256Hex([byte[]]$Bytes) {
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($algorithm.ComputeHash($Bytes))).Replace('-', '').ToLowerInvariant() }
    finally { $algorithm.Dispose() }
}

function Enable-RestorePrivilege {
    Add-Type @'
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
public static class Project6WorkerProvisionerPrivilege {
  [StructLayout(LayoutKind.Sequential)] struct LUID { public uint LowPart; public int HighPart; }
  [StructLayout(LayoutKind.Sequential)] struct LUID_AND_ATTRIBUTES { public LUID Luid; public uint Attributes; }
  [StructLayout(LayoutKind.Sequential)] struct TOKEN_PRIVILEGES { public uint Count; public LUID_AND_ATTRIBUTES Privilege; }
  [DllImport("advapi32.dll", SetLastError=true)] static extern bool OpenProcessToken(IntPtr process, uint access, out IntPtr token);
  [DllImport("advapi32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern bool LookupPrivilegeValue(string system, string name, out LUID luid);
  [DllImport("advapi32.dll", SetLastError=true)] static extern bool AdjustTokenPrivileges(IntPtr token, bool disableAll, ref TOKEN_PRIVILEGES state, uint length, IntPtr previous, IntPtr required);
  [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
  public static void Enable() {
    IntPtr token;
    if (!OpenProcessToken(Process.GetCurrentProcess().Handle, 0x28, out token)) throw new InvalidOperationException("restore privilege token open failed");
    try {
      LUID luid;
      if (!LookupPrivilegeValue(null, "SeRestorePrivilege", out luid)) throw new InvalidOperationException("restore privilege lookup failed");
      TOKEN_PRIVILEGES state = new TOKEN_PRIVILEGES { Count = 1, Privilege = new LUID_AND_ATTRIBUTES { Luid = luid, Attributes = 2 } };
      Marshal.GetLastWin32Error();
      if (!AdjustTokenPrivileges(token, false, ref state, 0, IntPtr.Zero, IntPtr.Zero) || Marshal.GetLastWin32Error() != 0) throw new InvalidOperationException("restore privilege enable failed");
    }
    finally { CloseHandle(token); }
  }
}
'@
    [Project6WorkerProvisionerPrivilege]::Enable()
}

if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'worker_provisioner_windows_required' }
$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'worker_provisioner_elevation_required'
}

$repo = Resolve-ExactDirectory $RepositoryRoot 'worker_repository_invalid'
$archive = Resolve-ExactFile $PythonArchive 'worker_python_archive_invalid'
$profilePath = Resolve-ExactFile $ProfileBinding 'worker_profile_binding_invalid'
$campaign = Resolve-ExactDirectory $CampaignRoot 'worker_campaign_root_invalid'
$ambient = Resolve-ExactDirectory $AmbientInterpreterRoot 'worker_ambient_interpreter_invalid'
if ([IO.Path]::GetFileName($archive) -ne $PythonArchiveName -or
    (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $PythonArchiveSha256) {
    throw 'worker_python_archive_mismatch'
}

$profile = Get-Content -Raw -LiteralPath $profilePath | ConvertFrom-Json
$expectedProfileFields = @('appcontainer_profile_root', 'broker_profile_root', 'broker_sid', 'package_sid', 'profile_moniker', 'user_data_root')
$observedProfileFields = @($profile.PSObject.Properties.Name)
[Array]::Sort($expectedProfileFields, [StringComparer]::Ordinal)
[Array]::Sort($observedProfileFields, [StringComparer]::Ordinal)
if ([string]::Join("`n", $observedProfileFields) -ne [string]::Join("`n", $expectedProfileFields)) {
    throw 'worker_profile_binding_invalid'
}
if ($profile.profile_moniker -notmatch '\A[A-Za-z0-9][A-Za-z0-9._-]{0,63}\z' -or
    $profile.package_sid -notmatch '\AS-1-[0-9-]+\z' -or $profile.broker_sid -notmatch '\AS-1-[0-9-]+\z') {
    throw 'worker_profile_binding_invalid'
}
$appProfile = Resolve-ExactDirectory $profile.appcontainer_profile_root 'worker_profile_binding_invalid'
$brokerProfile = Resolve-ExactDirectory $profile.broker_profile_root 'worker_profile_binding_invalid'
$userData = Resolve-ExactDirectory $profile.user_data_root 'worker_profile_binding_invalid'
if (-not $userData.StartsWith($brokerProfile.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'worker_profile_binding_invalid'
}

$provisioningParent = Split-Path -Parent ([IO.Path]::GetFullPath($ProvisioningRoot))
$provisioningParent = Resolve-ExactDirectory $provisioningParent 'worker_provisioning_parent_invalid'
$provisioningParent = Assert-StableDirectoryAncestors $provisioningParent 'worker_provisioning_parent_invalid'
$provisioning = [IO.Path]::GetFullPath($ProvisioningRoot)
if (Test-Path -LiteralPath $provisioning) { throw 'worker_provisioning_root_exists' }
Assert-Outside $provisioning @($repo, $campaign, $ambient, $appProfile, $brokerProfile, $userData)
if (-not (Test-FullyQualifiedLocalPath $OutputBinding) -or (Test-Path -LiteralPath $OutputBinding)) {
    throw 'worker_output_binding_invalid'
}
$outputParent = Resolve-ExactDirectory (Split-Path -Parent ([IO.Path]::GetFullPath($OutputBinding))) 'worker_output_binding_parent_invalid'
$outputParent = Assert-StableDirectoryAncestors $outputParent 'worker_output_binding_parent_invalid'
Assert-Outside $outputParent @($repo, $campaign, $appProfile)

# git rev-parse HEAD is the sole source identity for this local closure.
$sourceCommit = (& git -C $repo rev-parse HEAD 2>$null).Trim()
if ($LASTEXITCODE -ne 0 -or $sourceCommit -notmatch '\A[0-9a-f]{40}\z') { throw 'worker_source_commit_invalid' }
$sourceStatus = @(& git -C $repo status --porcelain=v1 --untracked-files=all 2>$null)
if ($LASTEXITCODE -ne 0 -or $sourceStatus.Count -ne 0) { throw 'worker_source_not_clean' }
foreach ($relative in $WorkerFiles) {
    $source = Join-Path $repo $relative
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw 'worker_source_file_missing' }
}

New-Item -ItemType Directory -Path $provisioning | Out-Null
$stage = Join-Path $provisioning ("stage-" + [Guid]::NewGuid().ToString('N'))
Expand-Archive -LiteralPath $archive -DestinationPath $stage
Get-ChildItem -LiteralPath $stage -Recurse -Force -File | Unblock-File
foreach ($relative in $WorkerFiles) {
    $destination = Join-Path $stage $relative
    New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
    Write-GitBlobCreateOnce $repo "$sourceCommit`:$relative" $destination
    Unblock-File -LiteralPath $destination
}

$observedCommit = (& git -C $repo rev-parse HEAD 2>$null).Trim()
$observedStatus = @(& git -C $repo status --porcelain=v1 --untracked-files=all 2>$null)
if ($LASTEXITCODE -ne 0 -or $observedCommit -ne $sourceCommit -or $observedStatus.Count -ne 0) {
    throw 'worker_source_identity_drift'
}

$relativeFiles = @(Get-ChildItem -LiteralPath $stage -Recurse -File | ForEach-Object {
    Get-RelativeWorkerPath $stage $_.FullName
})
[Array]::Sort($relativeFiles, [StringComparer]::Ordinal)
$files = @()
foreach ($relative in $relativeFiles) {
    $file = Get-Item -LiteralPath (Join-Path $stage $relative)
    $files += [ordered]@{
        path = $relative
        sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        size = $file.Length
    }
}
$manifest = [ordered]@{
    architecture = $PythonArchitecture
    entrypoint = 'tools/dual_live_run.py'
    files = $files
    interpreter = 'python.exe'
    principals = [ordered]@{
        broker = $profile.broker_sid
        owner = $OwnerSid
        package = $profile.package_sid
        provisioner = $ProvisionerSid
    }
    profile_moniker = $profile.profile_moniker
    python_version = $PythonVersion
    schema_version = 'project6.worker-bundle.v1'
    source_commit = $sourceCommit
}
$manifestBytes = [Text.Encoding]::ASCII.GetBytes(($manifest | ConvertTo-Json -Compress -Depth 8))
$manifestDigest = Get-Sha256Hex $manifestBytes
Write-CreateOnce (Join-Path $stage 'worker-bundle.json') $manifestBytes 'worker_manifest_write_failed'
$bundleRoot = Join-Path $provisioning "sha256-$manifestDigest"
if (Test-Path -LiteralPath $bundleRoot) { throw 'worker_bundle_exists' }
Move-Item -LiteralPath $stage -Destination $bundleRoot

Enable-RestorePrivilege
$aclTargets = @($provisioning, $bundleRoot) + @(Get-ChildItem -LiteralPath $bundleRoot -Recurse -Force | ForEach-Object FullName)
foreach ($target in $aclTargets) {
    $acl = Get-Acl -LiteralPath $target
    $acl.SetOwner([Security.Principal.SecurityIdentifier]::new($OwnerSid))
    Set-Acl -LiteralPath $target -AclObject $acl
    & icacls.exe $target /inheritance:r /grant:r "*$SystemSid`:(F)" "*$AdministratorsSid`:(F)" "*$OwnerSid`:(F)" "*$ProvisionerSid`:(F)" "*$($profile.broker_sid)`:(RX)" "*$($profile.package_sid)`:(RX)" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'worker_bundle_acl_failed' }
}

$binding = [ordered]@{
    root = $bundleRoot
    provisioning_root = $provisioning
    profile_moniker = $profile.profile_moniker
    manifest_digest = "sha256:$manifestDigest"
    source_commit = $sourceCommit
    entrypoint = 'tools/dual_live_run.py'
    interpreter = 'python.exe'
    python_version = $PythonVersion
    architecture = $PythonArchitecture
    package_sid = $profile.package_sid
    owner_sid = $OwnerSid
    provisioner_sid = $ProvisionerSid
    broker_sid = $profile.broker_sid
    ambient_interpreter_root = $ambient
    repository_root = $repo
    campaign_root = $campaign
    appcontainer_profile_root = $appProfile
    broker_profile_root = $brokerProfile
    user_data_root = $userData
}
$bindingBytes = [Text.Encoding]::ASCII.GetBytes(($binding | ConvertTo-Json -Compress))
Write-CreateOnce ([IO.Path]::GetFullPath($OutputBinding)) $bindingBytes 'worker_binding_write_failed'
Write-Output "WORKER_BUNDLE_ROOT: $bundleRoot"
Write-Output "WORKER_MANIFEST_SHA256: sha256:$manifestDigest"
Write-Output "WORKER_BINDING: $([IO.Path]::GetFullPath($OutputBinding))"
