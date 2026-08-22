[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$Mode,

    [Parameter(Mandatory = $false)]
    [scriptblock]$Action,

    [Parameter(Mandatory = $false)]
    [string]$CurrentRoot,

    [Parameter(Mandatory = $false)]
    [string]$Py,

    [Parameter(Mandatory = $false)]
    [AllowEmptyCollection()]
    [string[]]$PyArgumentList = @()
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

$FamilyGuardIndeterminate = 'sciencebase_attempt_family_guard_indeterminate'
$FamilyGuardActive = 'sciencebase_attempt_family_active'
$FamilyGuardReleaseFailed = 'sciencebase_attempt_family_guard_release_failed'
$CampaignId = 'sciencebase-live-v2'
$FamilyRoots = [string[]]@(
    'C:\owner-controlled\project6\sciencebase-campaign'
    'C:\owner-controlled\project6-attempt-4\sciencebase-campaign'
    'C:\owner-controlled\project6-attempt-5\sciencebase-campaign'
)

function Throw-FamilyGuardHold {
    param([Parameter(Mandatory = $true)][string]$Code)

    throw [InvalidOperationException]::new($Code)
}

try {
    if ($null -eq ('Project6DualLiveFamilyGuard.FamilyGuardNative' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;

namespace Project6DualLiveFamilyGuard
{
    public sealed class NativeCallResult
    {
        public NativeCallResult(IntPtr handle, int error, bool success)
        {
            Handle = handle;
            Error = error;
            Success = success;
        }

        public IntPtr Handle { get; private set; }
        public int Error { get; private set; }
        public bool Success { get; private set; }
    }

    internal static class NativeMethods
    {
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        internal static extern IntPtr CreateMutexW(
            IntPtr lpMutexAttributes,
            [MarshalAs(UnmanagedType.Bool)] bool bInitialOwner,
            string lpName);

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        internal static extern IntPtr OpenMutexW(
            uint dwDesiredAccess,
            [MarshalAs(UnmanagedType.Bool)] bool bInheritHandle,
            string lpName);

        [DllImport("kernel32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        internal static extern bool CloseHandle(IntPtr handle);

        [DllImport("kernel32.dll")]
        internal static extern void SetLastError(int error);
    }

    public static class FamilyGuardNative
    {
        private const uint SYNCHRONIZE = 0x00100000;

        public static void SetThreadLastError(int error)
        {
            NativeMethods.SetLastError(error);
        }

        public static NativeCallResult CreateMutex(string name)
        {
            NativeMethods.SetLastError(0);
            IntPtr handle = NativeMethods.CreateMutexW(IntPtr.Zero, false, name);
            int error = Marshal.GetLastWin32Error();
            return new NativeCallResult(handle, error, handle != IntPtr.Zero);
        }

        public static NativeCallResult OpenMutex(string name)
        {
            NativeMethods.SetLastError(0);
            IntPtr handle = NativeMethods.OpenMutexW(SYNCHRONIZE, false, name);
            int error = Marshal.GetLastWin32Error();
            return new NativeCallResult(handle, error, handle != IntPtr.Zero);
        }

        public static NativeCallResult Close(IntPtr handle)
        {
            NativeMethods.SetLastError(0);
            bool success = NativeMethods.CloseHandle(handle);
            int error = Marshal.GetLastWin32Error();
            return new NativeCallResult(IntPtr.Zero, error, success);
        }
    }

    public sealed class FamilyGuardLease
    {
        private readonly List<IntPtr> handles = new List<IntPtr>();

        public void Add(IntPtr handle)
        {
            if (handle == IntPtr.Zero)
            {
                throw new ArgumentException("handle");
            }
            handles.Add(handle);
        }

        public IntPtr[] TakeReverse()
        {
            IntPtr[] result = handles.ToArray();
            handles.Clear();
            Array.Reverse(result);
            return result;
        }
    }
}
'@
    }
} catch {
    Throw-FamilyGuardHold -Code $FamilyGuardIndeterminate
}

function Get-NormalizedFamilyRoot {
    param([Parameter(Mandatory = $true)][string]$Root)

    if ([string]::IsNullOrWhiteSpace($Root) -or -not [IO.Path]::IsPathRooted($Root)) {
        Throw-FamilyGuardHold -Code $FamilyGuardIndeterminate
    }
    try {
        $normalized = [IO.Path]::GetFullPath($Root).Replace('/', '\').ToLowerInvariant()
    } catch {
        Throw-FamilyGuardHold -Code $FamilyGuardIndeterminate
    }
    if ([string]::IsNullOrWhiteSpace($normalized)) {
        Throw-FamilyGuardHold -Code $FamilyGuardIndeterminate
    }
    return $normalized
}

function Get-FamilyMutexName {
    param([Parameter(Mandatory = $true)][string]$Root)

    $normalized = Get-NormalizedFamilyRoot -Root $Root
    $payload = [Text.Encoding]::UTF8.GetBytes($normalized + [char]0 + $CampaignId)
    $sha256 = [Security.Cryptography.SHA256]::Create()
    try {
        $hash = $sha256.ComputeHash($payload)
    } finally {
        $sha256.Dispose()
    }
    $digest = [BitConverter]::ToString($hash).Replace('-', '').ToLowerInvariant()
    return "Local\Project6DualLive-$digest"
}

function Get-FamilyGuardTable {
    if ($FamilyRoots.Count -ne 3) {
        Throw-FamilyGuardHold -Code $FamilyGuardIndeterminate
    }

    $normalizedRoots = New-Object 'System.Collections.Generic.HashSet[string]' (
        [StringComparer]::OrdinalIgnoreCase
    )
    $names = New-Object 'System.Collections.Generic.HashSet[string]' (
        [StringComparer]::Ordinal
    )
    $table = @()
    foreach ($root in $FamilyRoots) {
        $normalized = Get-NormalizedFamilyRoot -Root $root
        $name = Get-FamilyMutexName -Root $root
        if (
            -not $normalizedRoots.Add($normalized) -or
            [string]::IsNullOrWhiteSpace($name) -or
            -not $name.StartsWith('Local\Project6DualLive-', [StringComparison]::Ordinal) -or
            -not $names.Add($name)
        ) {
            Throw-FamilyGuardHold -Code $FamilyGuardIndeterminate
        }
        $table += [pscustomobject][ordered]@{
            Root = $normalized
            Name = $name
        }
    }
    if ($table.Count -ne 3 -or $names.Count -ne 3) {
        Throw-FamilyGuardHold -Code $FamilyGuardIndeterminate
    }
    return $table
}

function Close-FamilyGuardHandle {
    param([Parameter(Mandatory = $true)][IntPtr]$Handle)

    try {
        $result = [Project6DualLiveFamilyGuard.FamilyGuardNative]::Close($Handle)
    } catch {
        Throw-FamilyGuardHold -Code $FamilyGuardReleaseFailed
    }
    if (-not $result.Success) {
        Throw-FamilyGuardHold -Code $FamilyGuardReleaseFailed
    }
}

function Close-FamilyGuardLease {
    param(
        [Parameter(Mandatory = $true)]
        [Project6DualLiveFamilyGuard.FamilyGuardLease]$Lease
    )

    $releaseFailed = $false
    try {
        try {
            $handles = $Lease.TakeReverse()
        } catch {
            $handles = @()
            $releaseFailed = $true
        }
        foreach ($handle in $handles) {
            try {
                $result = [Project6DualLiveFamilyGuard.FamilyGuardNative]::Close($handle)
                if (-not $result.Success) {
                    $releaseFailed = $true
                }
            } catch {
                $releaseFailed = $true
            }
        }
    } finally {
        [GC]::KeepAlive($Lease)
    }
    if ($releaseFailed) {
        Throw-FamilyGuardHold -Code $FamilyGuardReleaseFailed
    }
}

function Add-FamilyGuardMutex {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)]
        [Project6DualLiveFamilyGuard.FamilyGuardLease]$Lease
    )

    try {
        $result = [Project6DualLiveFamilyGuard.FamilyGuardNative]::CreateMutex($Name)
    } catch {
        Throw-FamilyGuardHold -Code $FamilyGuardIndeterminate
    }
    if ($result.Handle -eq [IntPtr]::Zero) {
        Throw-FamilyGuardHold -Code $FamilyGuardIndeterminate
    }
    if ($result.Error -eq 183) {
        Close-FamilyGuardHandle -Handle $result.Handle
        Throw-FamilyGuardHold -Code $FamilyGuardActive
    }
    if ($result.Error -ne 0) {
        Close-FamilyGuardHandle -Handle $result.Handle
        Throw-FamilyGuardHold -Code $FamilyGuardIndeterminate
    }
    try {
        $Lease.Add($result.Handle)
    } catch {
        Close-FamilyGuardHandle -Handle $result.Handle
        Throw-FamilyGuardHold -Code $FamilyGuardIndeterminate
    }
}

function Assert-CurrentFamilyMutexAbsent {
    param([Parameter(Mandatory = $true)][string]$Name)

    try {
        $result = [Project6DualLiveFamilyGuard.FamilyGuardNative]::OpenMutex($Name)
    } catch {
        Throw-FamilyGuardHold -Code $FamilyGuardIndeterminate
    }
    if ($result.Handle -ne [IntPtr]::Zero) {
        Close-FamilyGuardHandle -Handle $result.Handle
        Throw-FamilyGuardHold -Code $FamilyGuardActive
    }
    if ($result.Error -ne 2) {
        Throw-FamilyGuardHold -Code $FamilyGuardIndeterminate
    }
}

if ($Mode -cne 'NonRuntime' -and $Mode -cne 'LiveRuntime') {
    Throw-FamilyGuardHold -Code $FamilyGuardIndeterminate
}

if ($Mode -ceq 'NonRuntime') {
    if (
        -not $PSBoundParameters.ContainsKey('Action') -or
        $null -eq $Action -or
        $PSBoundParameters.ContainsKey('CurrentRoot') -or
        $PSBoundParameters.ContainsKey('Py') -or
        $PSBoundParameters.ContainsKey('PyArgumentList')
    ) {
        Throw-FamilyGuardHold -Code $FamilyGuardIndeterminate
    }
} else {
    if (
        $PSBoundParameters.ContainsKey('Action') -or
        -not $PSBoundParameters.ContainsKey('CurrentRoot') -or
        -not $PSBoundParameters.ContainsKey('Py') -or
        [string]::IsNullOrWhiteSpace($CurrentRoot) -or
        [string]::IsNullOrWhiteSpace($Py) -or
        -not [IO.Path]::IsPathRooted($Py) -or
        $null -eq $PyArgumentList -or
        @($PyArgumentList | Where-Object { $null -eq $_ }).Count -ne 0
    ) {
        Throw-FamilyGuardHold -Code $FamilyGuardIndeterminate
    }
    try {
        $fullPy = [IO.Path]::GetFullPath($Py)
    } catch {
        Throw-FamilyGuardHold -Code $FamilyGuardIndeterminate
    }
    if (-not [StringComparer]::OrdinalIgnoreCase.Equals($fullPy, $Py)) {
        Throw-FamilyGuardHold -Code $FamilyGuardIndeterminate
    }
}

try {
    $familyTable = @(Get-FamilyGuardTable)
} catch {
    if ($_.Exception.Message -ceq $FamilyGuardIndeterminate) {
        throw
    }
    Throw-FamilyGuardHold -Code $FamilyGuardIndeterminate
}

$currentIndex = -1
if ($Mode -ceq 'LiveRuntime') {
    $normalizedCurrent = Get-NormalizedFamilyRoot -Root $CurrentRoot
    foreach ($candidate in 1, 2) {
        if ([StringComparer]::OrdinalIgnoreCase.Equals(
            $normalizedCurrent,
            $familyTable[$candidate].Root
        )) {
            $currentIndex = $candidate
            break
        }
    }
    if ($currentIndex -lt 1) {
        Throw-FamilyGuardHold -Code $FamilyGuardIndeterminate
    }
}

$lease = [Project6DualLiveFamilyGuard.FamilyGuardLease]::new()
$callbackExitCode = $null
try {
    for ($index = 0; $index -lt $familyTable.Count; $index++) {
        if ($index -ne $currentIndex) {
            Add-FamilyGuardMutex -Name $familyTable[$index].Name -Lease $lease
        }
    }

    if ($Mode -ceq 'NonRuntime') {
        & $Action
    } else {
        Assert-CurrentFamilyMutexAbsent -Name $familyTable[$currentIndex].Name
        & $Py @PyArgumentList
        $callbackExitCode = $LASTEXITCODE
    }
} finally {
    Close-FamilyGuardLease -Lease $lease
}

if ($Mode -ceq 'LiveRuntime') {
    exit $callbackExitCode
}
