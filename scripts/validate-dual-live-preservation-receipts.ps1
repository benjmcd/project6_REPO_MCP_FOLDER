Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

if ($null -eq ('Project6DualLivePreservation.NativePathReader' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Text;
using Microsoft.Win32.SafeHandles;

namespace Project6DualLivePreservation
{
    public sealed class NativePathData
    {
        public string RootedType { get; set; }
        public string ReparseTag { get; set; }
        public byte[] ReparseData { get; set; }
        public string VolumeIdentity { get; set; }
        public string FileIdentity { get; set; }
        public uint LinkCount { get; set; }
        public DateTime CreationTimeUtc { get; set; }
        public DateTime LastWriteTimeUtc { get; set; }
        public long? Length { get; set; }
        public string Sha256 { get; set; }
        public string OwnerSid { get; set; }
        public bool DaclProtected { get; set; }
        public string OrderedSddl { get; set; }
        public string[] SortedAceTuples { get; set; }
    }

    internal static class NativeMethods
    {
        internal const uint GENERIC_READ = 0x80000000;
        internal const uint READ_CONTROL = 0x00020000;
        internal const uint FILE_READ_ATTRIBUTES = 0x00000080;
        internal const uint FILE_SHARE_READ = 0x00000001;
        internal const uint FILE_SHARE_WRITE = 0x00000002;
        internal const uint FILE_SHARE_DELETE = 0x00000004;
        internal const uint OPEN_EXISTING = 3;
        internal const uint FILE_ATTRIBUTE_DIRECTORY = 0x00000010;
        internal const uint FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400;
        internal const uint FILE_FLAG_BACKUP_SEMANTICS = 0x02000000;
        internal const uint FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000;
        internal const uint FSCTL_GET_REPARSE_POINT = 0x000900A8;
        internal const uint OWNER_SECURITY_INFORMATION = 0x00000001;
        internal const uint DACL_SECURITY_INFORMATION = 0x00000004;
        internal const int SE_FILE_OBJECT = 1;
        internal static readonly IntPtr INVALID_HANDLE_VALUE = new IntPtr(-1);

        [StructLayout(LayoutKind.Sequential)]
        internal struct FILETIME
        {
            internal uint Low;
            internal uint High;
        }

        [StructLayout(LayoutKind.Sequential)]
        internal struct BY_HANDLE_FILE_INFORMATION
        {
            internal uint FileAttributes;
            internal FILETIME CreationTime;
            internal FILETIME LastAccessTime;
            internal FILETIME LastWriteTime;
            internal uint VolumeSerialNumber;
            internal uint FileSizeHigh;
            internal uint FileSizeLow;
            internal uint NumberOfLinks;
            internal uint FileIndexHigh;
            internal uint FileIndexLow;
        }

        [StructLayout(LayoutKind.Sequential)]
        internal struct FILE_ID_INFO
        {
            internal ulong VolumeSerialNumber;
            internal ulong FileIdLow;
            internal ulong FileIdHigh;
        }

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        internal static extern IntPtr CreateFileW(
            string fileName,
            uint desiredAccess,
            uint shareMode,
            IntPtr securityAttributes,
            uint creationDisposition,
            uint flagsAndAttributes,
            IntPtr templateFile);

        [DllImport("kernel32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        internal static extern bool GetFileInformationByHandle(
            IntPtr handle,
            out BY_HANDLE_FILE_INFORMATION information);

        [DllImport("kernel32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        internal static extern bool GetFileInformationByHandleEx(
            IntPtr handle,
            int informationClass,
            out FILE_ID_INFO information,
            uint bufferSize);

        [DllImport("kernel32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        internal static extern bool DeviceIoControl(
            IntPtr handle,
            uint controlCode,
            IntPtr inputBuffer,
            uint inputBufferSize,
            byte[] outputBuffer,
            uint outputBufferSize,
            out uint bytesReturned,
            IntPtr overlapped);

        [DllImport("advapi32.dll", SetLastError = true)]
        internal static extern uint GetSecurityInfo(
            IntPtr handle,
            int objectType,
            uint securityInformation,
            out IntPtr owner,
            out IntPtr group,
            out IntPtr dacl,
            out IntPtr sacl,
            out IntPtr securityDescriptor);

        [DllImport("advapi32.dll")]
        internal static extern uint GetSecurityDescriptorLength(IntPtr securityDescriptor);

        [DllImport("kernel32.dll", SetLastError = true)]
        internal static extern IntPtr LocalFree(IntPtr memory);

        [DllImport("kernel32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        internal static extern bool CloseHandle(IntPtr handle);
    }

    public static class NativePathReader
    {
        public static string QuoteArgument(string argument)
        {
            if (argument == null)
                throw new ArgumentNullException("argument");
            if (argument.Length != 0 && argument.IndexOfAny(new char[] { ' ', '\t', '\n', '\v', '"' }) < 0)
                return argument;
            StringBuilder result = new StringBuilder();
            result.Append('"');
            int backslashes = 0;
            foreach (char value in argument)
            {
                if (value == '\\')
                {
                    backslashes++;
                }
                else if (value == '"')
                {
                    result.Append('\\', backslashes * 2 + 1);
                    result.Append('"');
                    backslashes = 0;
                }
                else
                {
                    result.Append('\\', backslashes);
                    result.Append(value);
                    backslashes = 0;
                }
            }
            result.Append('\\', backslashes * 2);
            result.Append('"');
            return result.ToString();
        }

        private static DateTime ToUtc(NativeMethods.FILETIME value)
        {
            long fileTime = ((long)value.High << 32) | value.Low;
            return DateTime.FromFileTimeUtc(fileTime);
        }

        private static string HexHash(Stream stream)
        {
            using (SHA256 sha = SHA256.Create())
            {
                byte[] digest = sha.ComputeHash(stream);
                StringBuilder result = new StringBuilder(digest.Length * 2);
                foreach (byte value in digest)
                    result.Append(value.ToString("x2", CultureInfo.InvariantCulture));
                return result.ToString();
            }
        }

        private static bool SameFileTime(
            NativeMethods.FILETIME left,
            NativeMethods.FILETIME right)
        {
            return left.Low == right.Low && left.High == right.High;
        }

        private static bool SameBasic(
            NativeMethods.BY_HANDLE_FILE_INFORMATION left,
            NativeMethods.BY_HANDLE_FILE_INFORMATION right)
        {
            return left.FileAttributes == right.FileAttributes &&
                SameFileTime(left.CreationTime, right.CreationTime) &&
                SameFileTime(left.LastWriteTime, right.LastWriteTime) &&
                left.FileSizeHigh == right.FileSizeHigh &&
                left.FileSizeLow == right.FileSizeLow &&
                left.NumberOfLinks == right.NumberOfLinks &&
                left.VolumeSerialNumber == right.VolumeSerialNumber &&
                left.FileIndexHigh == right.FileIndexHigh &&
                left.FileIndexLow == right.FileIndexLow;
        }

        private static bool SameIdentity(
            NativeMethods.FILE_ID_INFO left,
            NativeMethods.FILE_ID_INFO right)
        {
            return left.VolumeSerialNumber == right.VolumeSerialNumber &&
                left.FileIdLow == right.FileIdLow &&
                left.FileIdHigh == right.FileIdHigh;
        }

        private static bool SameStrings(string[] left, string[] right)
        {
            if (left == null || right == null || left.Length != right.Length)
                return false;
            for (int index = 0; index < left.Length; index++)
            {
                if (!String.Equals(left[index], right[index], StringComparison.Ordinal))
                    return false;
            }
            return true;
        }

        private static byte[] ReadReparseData(IntPtr handle)
        {
            byte[] buffer = new byte[16 * 1024];
            uint returned;
            if (!NativeMethods.DeviceIoControl(
                    handle,
                    NativeMethods.FSCTL_GET_REPARSE_POINT,
                    IntPtr.Zero,
                    0,
                    buffer,
                    (uint)buffer.Length,
                    out returned,
                    IntPtr.Zero))
                throw new IOException("FSCTL_GET_REPARSE_POINT failed: " + Marshal.GetLastWin32Error());
            if (returned < 8)
                throw new IOException("Reparse data is truncated");
            byte[] result = new byte[returned];
            Buffer.BlockCopy(buffer, 0, result, 0, (int)returned);
            return result;
        }

        private static bool SameBytes(byte[] left, byte[] right)
        {
            if (left == null || right == null || left.Length != right.Length)
                return false;
            for (int index = 0; index < left.Length; index++)
            {
                if (left[index] != right[index])
                    return false;
            }
            return true;
        }

        private static string[] ReadSecurity(
            IntPtr handle,
            out string ownerSid,
            out bool daclProtected,
            out string orderedSddl)
        {
            IntPtr owner;
            IntPtr group;
            IntPtr dacl;
            IntPtr sacl;
            IntPtr descriptor;
            uint error = NativeMethods.GetSecurityInfo(
                handle,
                NativeMethods.SE_FILE_OBJECT,
                NativeMethods.OWNER_SECURITY_INFORMATION |
                    NativeMethods.DACL_SECURITY_INFORMATION,
                out owner,
                out group,
                out dacl,
                out sacl,
                out descriptor);
            if (error != 0 || descriptor == IntPtr.Zero)
                throw new IOException("GetSecurityInfo failed: " + error.ToString(CultureInfo.InvariantCulture));
            try
            {
                uint size = NativeMethods.GetSecurityDescriptorLength(descriptor);
                if (size == 0 || size > Int32.MaxValue)
                    throw new IOException("Invalid security descriptor length");
                byte[] bytes = new byte[(int)size];
                Marshal.Copy(descriptor, bytes, 0, bytes.Length);
                RawSecurityDescriptor raw = new RawSecurityDescriptor(bytes, 0);
                if (raw.Owner == null)
                    throw new IOException("Owner SID is absent");
                ownerSid = raw.Owner.Value;
                daclProtected = (raw.ControlFlags & ControlFlags.DiscretionaryAclProtected) != 0;
                orderedSddl = raw.GetSddlForm(
                    AccessControlSections.Owner | AccessControlSections.Access);

                List<string> tuples = new List<string>();
                if (raw.DiscretionaryAcl != null)
                {
                    foreach (GenericAce ace in raw.DiscretionaryAcl)
                    {
                        QualifiedAce qualified = ace as QualifiedAce;
                        string sid = qualified == null || qualified.SecurityIdentifier == null
                            ? String.Empty : qualified.SecurityIdentifier.Value;
                        int mask = qualified == null ? 0 : qualified.AccessMask;
                        string qualifier = qualified == null
                            ? ace.AceType.ToString() : qualified.AceQualifier.ToString();
                        int inheritance = 0;
                        if ((ace.AceFlags & AceFlags.ContainerInherit) != 0) inheritance |= 1;
                        if ((ace.AceFlags & AceFlags.ObjectInherit) != 0) inheritance |= 2;
                        int propagation = 0;
                        if ((ace.AceFlags & AceFlags.NoPropagateInherit) != 0) propagation |= 1;
                        if ((ace.AceFlags & AceFlags.InheritOnly) != 0) propagation |= 2;
                        tuples.Add(String.Format(
                            CultureInfo.InvariantCulture,
                            "{0}|{1}|{2}|{3}|{4}|{5}",
                            sid,
                            mask,
                            qualifier,
                            (ace.AceFlags & AceFlags.Inherited) != 0,
                            inheritance,
                            propagation));
                    }
                }
                tuples.Sort(StringComparer.Ordinal);
                return tuples.ToArray();
            }
            finally
            {
                NativeMethods.LocalFree(descriptor);
            }
        }

        private static void ValidateStable(
            IntPtr handle,
            NativeMethods.BY_HANDLE_FILE_INFORMATION basic,
            NativeMethods.FILE_ID_INFO identity,
            bool isReparse,
            byte[] reparseData,
            string ownerSid,
            bool daclProtected,
            string orderedSddl,
            string[] aceTuples)
        {
            NativeMethods.BY_HANDLE_FILE_INFORMATION basicAfter;
            if (!NativeMethods.GetFileInformationByHandle(handle, out basicAfter))
                throw new IOException("GetFileInformationByHandle revalidation failed: " + Marshal.GetLastWin32Error());
            NativeMethods.FILE_ID_INFO identityAfter;
            if (!NativeMethods.GetFileInformationByHandleEx(
                    handle, 18, out identityAfter,
                    (uint)Marshal.SizeOf(typeof(NativeMethods.FILE_ID_INFO))))
                throw new IOException("FileIdInfo revalidation failed: " + Marshal.GetLastWin32Error());

            string ownerSidAfter;
            bool daclProtectedAfter;
            string orderedSddlAfter;
            string[] aceTuplesAfter = ReadSecurity(
                handle, out ownerSidAfter, out daclProtectedAfter, out orderedSddlAfter);
            byte[] reparseDataAfter = isReparse ? ReadReparseData(handle) : null;
            if (!SameBasic(basic, basicAfter) ||
                !SameIdentity(identity, identityAfter) ||
                !String.Equals(ownerSid, ownerSidAfter, StringComparison.Ordinal) ||
                daclProtected != daclProtectedAfter ||
                !String.Equals(orderedSddl, orderedSddlAfter, StringComparison.Ordinal) ||
                !SameStrings(aceTuples, aceTuplesAfter) ||
                (isReparse && !SameBytes(reparseData, reparseDataAfter)))
                throw new IOException("Path metadata changed while reading");
        }

        public static NativePathData Read(string path)
        {
            uint initialAttributes = unchecked((uint)File.GetAttributes(path));
            bool initialDirectory = (initialAttributes & NativeMethods.FILE_ATTRIBUTE_DIRECTORY) != 0;
            bool initialReparse = (initialAttributes & NativeMethods.FILE_ATTRIBUTE_REPARSE_POINT) != 0;
            uint desiredAccess = NativeMethods.READ_CONTROL | NativeMethods.FILE_READ_ATTRIBUTES;
            if (!initialDirectory && !initialReparse)
                desiredAccess |= NativeMethods.GENERIC_READ;
            uint shareMode = initialDirectory && !initialReparse
                ? NativeMethods.FILE_SHARE_READ | NativeMethods.FILE_SHARE_WRITE
                : NativeMethods.FILE_SHARE_READ;
            IntPtr handle = NativeMethods.CreateFileW(
                path,
                desiredAccess,
                shareMode,
                IntPtr.Zero,
                NativeMethods.OPEN_EXISTING,
                NativeMethods.FILE_FLAG_BACKUP_SEMANTICS |
                    NativeMethods.FILE_FLAG_OPEN_REPARSE_POINT,
                IntPtr.Zero);
            if (handle == NativeMethods.INVALID_HANDLE_VALUE)
                throw new IOException("CreateFileW failed: " + Marshal.GetLastWin32Error());

            SafeFileHandle safeHandle = new SafeFileHandle(handle, true);
            try
            {
                NativeMethods.BY_HANDLE_FILE_INFORMATION basic;
                if (!NativeMethods.GetFileInformationByHandle(handle, out basic))
                    throw new IOException("GetFileInformationByHandle failed: " + Marshal.GetLastWin32Error());
                NativeMethods.FILE_ID_INFO identity;
                if (!NativeMethods.GetFileInformationByHandleEx(
                        handle, 18, out identity,
                        (uint)Marshal.SizeOf(typeof(NativeMethods.FILE_ID_INFO))))
                    throw new IOException("FileIdInfo failed: " + Marshal.GetLastWin32Error());

                bool isDirectory = (basic.FileAttributes & NativeMethods.FILE_ATTRIBUTE_DIRECTORY) != 0;
                bool isReparse = (basic.FileAttributes & NativeMethods.FILE_ATTRIBUTE_REPARSE_POINT) != 0;
                if (isDirectory != initialDirectory || isReparse != initialReparse)
                    throw new IOException("Path type changed while opening");

                byte[] reparseData = null;
                string reparseTag = null;
                if (isReparse)
                {
                    reparseData = ReadReparseData(handle);
                    reparseTag = "0x" + BitConverter.ToUInt32(reparseData, 0).ToString("X8", CultureInfo.InvariantCulture);
                }

                string ownerSid;
                bool daclProtected;
                string orderedSddl;
                string[] aceTuples = ReadSecurity(
                    handle, out ownerSid, out daclProtected, out orderedSddl);
                long size = ((long)basic.FileSizeHigh << 32) | basic.FileSizeLow;
                string sha256 = null;
                if (!isDirectory && !isReparse)
                {
                    using (FileStream stream = new FileStream(safeHandle, FileAccess.Read))
                    {
                        IntPtr hashHandle = handle;
                        handle = IntPtr.Zero;
                        sha256 = HexHash(stream);
                        ValidateStable(
                            hashHandle,
                            basic,
                            identity,
                            isReparse,
                            reparseData,
                            ownerSid,
                            daclProtected,
                            orderedSddl,
                            aceTuples);
                    }
                }
                else
                {
                    ValidateStable(
                        handle,
                        basic,
                        identity,
                        isReparse,
                        reparseData,
                        ownerSid,
                        daclProtected,
                        orderedSddl,
                        aceTuples);
                }

                return new NativePathData
                {
                    RootedType = isDirectory ? "directory" : "file",
                    ReparseTag = reparseTag,
                    ReparseData = reparseData,
                    VolumeIdentity = identity.VolumeSerialNumber.ToString("X16", CultureInfo.InvariantCulture),
                    FileIdentity = identity.FileIdHigh.ToString("X16", CultureInfo.InvariantCulture) +
                        identity.FileIdLow.ToString("X16", CultureInfo.InvariantCulture),
                    LinkCount = basic.NumberOfLinks,
                    CreationTimeUtc = ToUtc(basic.CreationTime),
                    LastWriteTimeUtc = ToUtc(basic.LastWriteTime),
                    Length = isDirectory || isReparse ? (long?)null : size,
                    Sha256 = sha256,
                    OwnerSid = ownerSid,
                    DaclProtected = daclProtected,
                    OrderedSddl = orderedSddl,
                    SortedAceTuples = aceTuples
                };
            }
            finally
            {
                if (handle != IntPtr.Zero)
                    safeHandle.Dispose();
            }
        }
    }
}
'@
}

function Throw-DualLivePreservationHold {
    param([Parameter(Mandatory = $true)][string]$Code)

    throw [InvalidOperationException]::new($Code)
}

function Test-DualLiveCanonicalDrivePath {
    param([Parameter(Mandatory = $true)][string]$Path)

    try {
        if ([string]::IsNullOrWhiteSpace($Path) -or $Path.Contains('<') -or $Path.Contains('>')) {
            return $false
        }
        $root = [IO.Path]::GetPathRoot($Path)
        $full = [IO.Path]::GetFullPath($Path)
        return $root -match '\A[A-Za-z]:\\\z' -and
            ($full.Length -eq $root.Length -or -not $Path.EndsWith('\')) -and
            [string]::Equals($full, $Path, [StringComparison]::OrdinalIgnoreCase)
    }
    catch { return $false }
}

function Get-DualLiveNativePathReceipt {
    param([Parameter(Mandatory = $true)][string]$LiteralPath)

    try {
        if (-not (Test-DualLiveCanonicalDrivePath $LiteralPath)) {
            throw 'invalid path'
        }
        $full = [IO.Path]::GetFullPath($LiteralPath)
        $native = [Project6DualLivePreservation.NativePathReader]::Read($full)
        [pscustomobject][ordered]@{
            Path = $full
            Exists = $true
            RootedType = $native.RootedType
            ReparseTag = $native.ReparseTag
            ReparseDataBase64 = if ($null -eq $native.ReparseData) {
                $null
            } else {
                [Convert]::ToBase64String($native.ReparseData)
            }
            VolumeIdentity = $native.VolumeIdentity
            FileIdentity = $native.FileIdentity
            LinkCount = [long]$native.LinkCount
            CreationTimeUtc = $native.CreationTimeUtc.ToString(
                'o', [Globalization.CultureInfo]::InvariantCulture
            )
            LastWriteTimeUtc = $native.LastWriteTimeUtc.ToString(
                'o', [Globalization.CultureInfo]::InvariantCulture
            )
            Length = $native.Length
            Sha256 = $native.Sha256
            OwnerSid = $native.OwnerSid
            DaclProtected = [bool]$native.DaclProtected
            OrderedSddl = $native.OrderedSddl
            SortedAceTuples = [string[]]@($native.SortedAceTuples)
        }
    }
    catch {
        Throw-DualLivePreservationHold 'preservation_path_unreadable'
    }
}

function ConvertTo-DualLiveWorktreePath {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$QualifyNonDriveAgainst
    )

    if (-not (Test-DualLiveCanonicalDrivePath $QualifyNonDriveAgainst) -or
        [IO.Path]::GetFullPath($QualifyNonDriveAgainst).TrimEnd('\') -cne
            [IO.Path]::GetPathRoot($QualifyNonDriveAgainst).TrimEnd('\')) {
        Throw-DualLivePreservationHold 'preservation_worktree_porcelain_invalid'
    }
    $candidate = $Path.Replace('/', '\')
    if ($candidate -match '\A[A-Za-z]:\\') {
        $full = [IO.Path]::GetFullPath($candidate)
    }
    elseif ($candidate.StartsWith('\') -and -not $candidate.StartsWith('\\')) {
        $full = [IO.Path]::GetFullPath(
            [IO.Path]::Combine($QualifyNonDriveAgainst, $candidate.TrimStart('\'))
        )
    }
    else {
        Throw-DualLivePreservationHold 'preservation_worktree_porcelain_invalid'
    }
    if (-not (Test-DualLiveCanonicalDrivePath $full)) {
        Throw-DualLivePreservationHold 'preservation_worktree_porcelain_invalid'
    }
    return $full
}

function ConvertFrom-DualLiveWorktreePorcelainBytes {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][byte[]]$Bytes,
        [Parameter(Mandatory = $true)][string]$QualifyNonDriveAgainst
    )

    try {
        if ($Bytes.Count -eq 0) { throw 'empty' }
        $utf8 = [Text.UTF8Encoding]::new($false, $true)
        $text = $utf8.GetString($Bytes)
        if (-not $text.EndsWith("`0`0") -or $text.EndsWith("`0`0`0")) {
            throw 'terminator'
        }
        $body = $text.Substring(0, $text.Length - 2)
        if ([string]::IsNullOrEmpty($body)) { throw 'empty' }
        $recordTexts = [Text.RegularExpressions.Regex]::Split($body, "`0`0")
        $roots = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        $records = [Collections.Generic.List[object]]::new()

        foreach ($recordText in $recordTexts) {
            if ([string]::IsNullOrEmpty($recordText)) { throw 'empty record' }
            $fields = [string[]]@($recordText.Split([char]0))
            if ($fields.Count -lt 3 -or $fields[0] -notmatch '\Aworktree (.+)\z') {
                throw 'record header'
            }
            $path = ConvertTo-DualLiveWorktreePath `
                -Path $Matches[1] `
                -QualifyNonDriveAgainst $QualifyNonDriveAgainst
            if (-not $roots.Add($path)) { throw 'duplicate root' }

            $head = $null
            $state = $null
            $branch = $null
            $locked = $null
            $prunable = $null
            $lockedSeen = $false
            $prunableSeen = $false
            for ($index = 1; $index -lt $fields.Count; $index++) {
                $field = $fields[$index]
                if ([string]::IsNullOrEmpty($field)) { throw 'empty field' }
                if ($field -match '\AHEAD ([0-9a-f]{40}|[0-9a-f]{64})\z') {
                    if ($null -ne $head) { throw 'duplicate head' }
                    $head = $Matches[1]
                }
                elseif ($field -match '\Abranch (refs/heads/[^\x00-\x20~^:?*\[\\]+)\z') {
                    if ($null -ne $state) { throw 'duplicate state' }
                    $state = 'branch'
                    $branch = $Matches[1]
                }
                elseif ($field -ceq 'detached') {
                    if ($null -ne $state) { throw 'duplicate state' }
                    $state = 'detached'
                }
                elseif ($field -match '\Alocked(?: (.*))?\z') {
                    if ($lockedSeen) { throw 'duplicate locked' }
                    $lockedSeen = $true
                    $locked = if ($Matches.Count -gt 1) { $Matches[1] } else { '' }
                }
                elseif ($field -match '\Aprunable(?: (.*))?\z') {
                    if ($prunableSeen) { throw 'duplicate prunable' }
                    $prunableSeen = $true
                    $prunable = if ($Matches.Count -gt 1) { $Matches[1] } else { '' }
                }
                else {
                    throw 'unknown field'
                }
            }
            if ($null -eq $head -or $null -eq $state) { throw 'incomplete record' }
            $records.Add([pscustomobject][ordered]@{
                Path = $path
                Head = $head
                State = $state
                Branch = $branch
                Locked = $locked
                Prunable = $prunable
            })
        }
        if ($records.Count -eq 0) { throw 'empty' }
        return @($records.ToArray() | Sort-Object -Property Path -CaseSensitive)
    }
    catch {
        Throw-DualLivePreservationHold 'preservation_worktree_porcelain_invalid'
    }
}

function Invoke-DualLiveRawProcess {
    param(
        [Parameter(Mandatory = $true)][string]$FileName,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][string[]]$ArgumentList,
        [Parameter(Mandatory = $true)][string]$FailureCode
    )

    $process = $null
    $stdout = $null
    $stderr = $null
    try {
        $start = [Diagnostics.ProcessStartInfo]::new()
        $start.FileName = $FileName
        $start.Arguments = [string]::Join(' ', [string[]]@(
            $ArgumentList | ForEach-Object {
                [Project6DualLivePreservation.NativePathReader]::QuoteArgument($_)
            }
        ))
        $start.UseShellExecute = $false
        $start.CreateNoWindow = $true
        $start.RedirectStandardOutput = $true
        $start.RedirectStandardError = $true
        foreach ($name in [string[]]@(
                'GIT_ALTERNATE_OBJECT_DIRECTORIES',
                'GIT_CONFIG_COUNT',
                'GIT_DIR',
                'GIT_EXTERNAL_DIFF',
                'GIT_INDEX_FILE',
                'GIT_OBJECT_DIRECTORY',
                'GIT_WORK_TREE'
            )) {
            $start.EnvironmentVariables.Remove($name)
        }
        foreach ($name in [string[]]@($start.EnvironmentVariables.Keys)) {
            if ($name -match '\AGIT_CONFIG_(?:KEY|VALUE)_\d+\z') {
                $start.EnvironmentVariables.Remove($name)
            }
        }
        $start.EnvironmentVariables['GIT_OPTIONAL_LOCKS'] = '0'
        $start.EnvironmentVariables['GIT_TERMINAL_PROMPT'] = '0'
        $start.EnvironmentVariables['GCM_INTERACTIVE'] = 'Never'
        $start.EnvironmentVariables['GIT_PAGER'] = 'cat'

        $process = [Diagnostics.Process]::new()
        $process.StartInfo = $start
        if (-not $process.Start()) { throw 'start failed' }
        $stdout = [IO.MemoryStream]::new()
        $stderr = [IO.MemoryStream]::new()
        $stdoutTask = $process.StandardOutput.BaseStream.CopyToAsync($stdout)
        $stderrTask = $process.StandardError.BaseStream.CopyToAsync($stderr)
        $process.WaitForExit()
        [Threading.Tasks.Task]::WaitAll(
            [Threading.Tasks.Task[]]@($stdoutTask, $stderrTask)
        )
        $stdoutBytes = $stdout.ToArray()
        $stderrBytes = $stderr.ToArray()
        if ($process.ExitCode -ne 0 -or $stderrBytes.Count -ne 0) {
            throw 'process failed'
        }
        return ,$stdoutBytes
    }
    catch {
        Throw-DualLivePreservationHold $FailureCode
    }
    finally {
        if ($null -ne $stdout) { $stdout.Dispose() }
        if ($null -ne $stderr) { $stderr.Dispose() }
        if ($null -ne $process) { $process.Dispose() }
    }
}

function Invoke-DualLiveGitRaw {
    param(
        [Parameter(Mandatory = $true)][string]$WorkingTree,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$FailureCode
    )

    $common = [string[]]@(
        '--no-optional-locks',
        '-c', 'core.fsmonitor=false',
        '-c', 'core.untrackedCache=false',
        '-c', 'diff.external=',
        '-C', $WorkingTree
    )
    [byte[]]$result = Invoke-DualLiveRawProcess `
        -FileName 'git.exe' `
        -ArgumentList ([string[]]@($common + $Arguments)) `
        -FailureCode $FailureCode
    return ,$result
}

function Get-DualLiveLowerSha256 {
    param([Parameter(Mandatory = $true)][AllowEmptyCollection()][byte[]]$Bytes)

    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-', '').ToLowerInvariant()
    }
    finally { $sha.Dispose() }
}

function Get-DualLiveUntrackedPaths {
    param([Parameter(Mandatory = $true)][AllowEmptyCollection()][byte[]]$StatusBytes)

    try {
        if ($StatusBytes.Count -eq 0) { return [string[]]@() }
        $utf8 = [Text.UTF8Encoding]::new($false, $true)
        $text = $utf8.GetString($StatusBytes)
        if (-not $text.EndsWith("`0")) { throw 'terminator' }
        $tokens = [string[]]@($text.Substring(0, $text.Length - 1).Split([char]0))
        $untracked = [Collections.Generic.List[string]]::new()
        $seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        for ($index = 0; $index -lt $tokens.Count; $index++) {
            $token = $tokens[$index]
            if ($token.Length -lt 4 -or $token[2] -ne ' ') { throw 'status field' }
            $status = $token.Substring(0, 2)
            if ($status -notmatch '\A[ MADRCUT?!]{2}\z') { throw 'status code' }
            $path = $token.Substring(3)
            if ([string]::IsNullOrEmpty($path)) { throw 'empty path' }
            if ($status -ceq '??') {
                if (-not $seen.Add($path)) { throw 'duplicate untracked' }
                $untracked.Add($path)
            }
            if ($status[0] -in @('R', 'C') -or $status[1] -in @('R', 'C')) {
                $index++
                if ($index -ge $tokens.Count -or [string]::IsNullOrEmpty($tokens[$index])) {
                    throw 'rename source'
                }
            }
        }
        return [string[]]@($untracked | Sort-Object -CaseSensitive)
    }
    catch {
        Throw-DualLivePreservationHold 'preservation_status_invalid'
    }
}

function Test-DualLivePathExistsStrict {
    param([Parameter(Mandatory = $true)][string]$LiteralPath)

    try {
        [IO.File]::GetAttributes($LiteralPath) | Out-Null
        return $true
    }
    catch [IO.FileNotFoundException] { return $false }
    catch [IO.DirectoryNotFoundException] { return $false }
    catch { Throw-DualLivePreservationHold 'preservation_path_indeterminate' }
}

function Assert-DualLiveNoReparseParent {
    param([Parameter(Mandatory = $true)][string]$LiteralPath)

    $full = [IO.Path]::GetFullPath($LiteralPath)
    $root = [IO.Path]::GetPathRoot($full)
    $relative = $full.Substring($root.Length)
    $parts = [string[]]@($relative.Split([char]'\'))
    $current = $root
    for ($index = 0; $index -lt ($parts.Count - 1); $index++) {
        if ([string]::IsNullOrEmpty($parts[$index])) { continue }
        $current = [IO.Path]::Combine($current, $parts[$index])
        if (-not (Test-DualLivePathExistsStrict $current)) { break }
        $receipt = Get-DualLiveNativePathReceipt -LiteralPath $current
        if ($null -ne $receipt.ReparseTag -or $receipt.RootedType -cne 'directory') {
            Throw-DualLivePreservationHold 'preservation_reparse_parent'
        }
    }
}

function Get-DualLiveUntrackedManifest {
    param(
        [Parameter(Mandatory = $true)][string]$WorkingTree,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][byte[]]$StatusBytes
    )

    $root = [IO.Path]::GetFullPath($WorkingTree).TrimEnd('\')
    $prefix = $root + '\'
    $manifest = [Collections.Generic.List[object]]::new()
    foreach ($gitPath in @(Get-DualLiveUntrackedPaths -StatusBytes $StatusBytes)) {
        if ($gitPath -match '\A(?:[A-Za-z]:|[/\\])' -or
            @($gitPath.Replace('\', '/').Split('/')).Where({ $_ -in @('', '.', '..') }).Count -ne 0) {
            Throw-DualLivePreservationHold 'preservation_untracked_invalid'
        }
        $full = [IO.Path]::GetFullPath(
            [IO.Path]::Combine($root, $gitPath.Replace('/', '\'))
        )
        if (-not $full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
            Throw-DualLivePreservationHold 'preservation_untracked_invalid'
        }
        Assert-DualLiveNoReparseParent -LiteralPath $full
        $native = Get-DualLiveNativePathReceipt -LiteralPath $full
        if ($native.RootedType -ceq 'directory' -and $null -eq $native.ReparseTag) {
            Throw-DualLivePreservationHold 'preservation_untracked_invalid'
        }
        $length = $native.Length
        $sha256 = $native.Sha256
        $rootedType = $native.RootedType
        if ($null -ne $native.ReparseTag) {
            $raw = [Convert]::FromBase64String($native.ReparseDataBase64)
            $length = [long]$raw.Count
            $sha256 = Get-DualLiveLowerSha256 -Bytes $raw
            $rootedType = $rootedType + '-reparse'
        }
        $manifest.Add([pscustomobject][ordered]@{
            Path = $gitPath.Replace('\', '/')
            RootedType = $rootedType
            ReparseTag = $native.ReparseTag
            ReparseDataBase64 = $native.ReparseDataBase64
            Length = $length
            Sha256 = $sha256
            VolumeIdentity = $native.VolumeIdentity
            FileIdentity = $native.FileIdentity
            LinkCount = $native.LinkCount
        })
    }
    return $manifest.ToArray()
}

function Test-DualLiveNativeReceiptEqual {
    param(
        [Parameter(Mandatory = $true)][object]$Left,
        [Parameter(Mandatory = $true)][object]$Right
    )

    $leftJson = ConvertTo-Json -InputObject $Left -Depth 20 -Compress
    $rightJson = ConvertTo-Json -InputObject $Right -Depth 20 -Compress
    return [string]::Equals($leftJson, $rightJson, [StringComparison]::Ordinal)
}

function Add-DualLiveExternalEntryTree {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()]
        [Collections.Generic.List[object]]$Entries,
        [Parameter(Mandatory = $true)][string]$LiteralPath,
        [Parameter(Mandatory = $true)][string]$RootPath,
        [Parameter(Mandatory = $true)][bool]$Recurse
    )

    Assert-DualLiveNoReparseParent -LiteralPath $LiteralPath
    $receipt = Get-DualLiveNativePathReceipt -LiteralPath $LiteralPath
    $Entries.Add($receipt) | Out-Null
    if (-not $Recurse -or $receipt.RootedType -cne 'directory') {
        return $receipt
    }
    if ($null -ne $receipt.ReparseTag) {
        if ([string]::Equals(
                $LiteralPath,
                $RootPath,
                [StringComparison]::OrdinalIgnoreCase
            )) {
            Throw-DualLivePreservationHold 'preservation_reparse_root'
        }
        return $receipt
    }

    try {
        $childrenBefore = [string[]]@(
            Get-ChildItem -Force -LiteralPath $LiteralPath |
                ForEach-Object FullName |
                Sort-Object -CaseSensitive
        )
    }
    catch {
        Throw-DualLivePreservationHold 'preservation_path_unreadable'
    }
    try {
        $afterEnumeration = Get-DualLiveNativePathReceipt -LiteralPath $LiteralPath
    }
    catch {
        Throw-DualLivePreservationHold 'preservation_directory_drift'
    }
    if (-not (Test-DualLiveNativeReceiptEqual -Left $receipt -Right $afterEnumeration)) {
        Throw-DualLivePreservationHold 'preservation_directory_drift'
    }

    foreach ($child in $childrenBefore) {
        $childReceipt = Add-DualLiveExternalEntryTree `
            -Entries $Entries `
            -LiteralPath $child `
            -RootPath $RootPath `
            -Recurse $Recurse
        try {
            Assert-DualLiveNoReparseParent -LiteralPath $child
            $childAfter = Get-DualLiveNativePathReceipt -LiteralPath $child
        }
        catch {
            Throw-DualLivePreservationHold 'preservation_directory_drift'
        }
        if (-not (Test-DualLiveNativeReceiptEqual -Left $childReceipt -Right $childAfter)) {
            Throw-DualLivePreservationHold 'preservation_directory_drift'
        }
    }

    try {
        $childrenAfter = [string[]]@(
            Get-ChildItem -Force -LiteralPath $LiteralPath |
                ForEach-Object FullName |
                Sort-Object -CaseSensitive
        )
        $finalReceipt = Get-DualLiveNativePathReceipt -LiteralPath $LiteralPath
    }
    catch {
        Throw-DualLivePreservationHold 'preservation_directory_drift'
    }
    if ([string]::Join("`n", $childrenBefore) -cne [string]::Join("`n", $childrenAfter) -or
        -not (Test-DualLiveNativeReceiptEqual -Left $receipt -Right $finalReceipt)) {
        Throw-DualLivePreservationHold 'preservation_directory_drift'
    }
    return $receipt
}

function Get-DualLiveExternalEntries {
    param(
        [Parameter(Mandatory = $true)][string]$LiteralPath,
        [Parameter(Mandatory = $true)][bool]$Recurse
    )

    $entries = [Collections.Generic.List[object]]::new()
    $null = Add-DualLiveExternalEntryTree `
        -Entries $entries `
        -LiteralPath $LiteralPath `
        -RootPath $LiteralPath `
        -Recurse $Recurse
    return $entries.ToArray()
}

function Test-DualLiveBoundaryOverlap {
    param(
        [Parameter(Mandatory = $true)][string]$Left,
        [Parameter(Mandatory = $true)][string]$Right
    )

    $leftFull = [IO.Path]::GetFullPath($Left).TrimEnd('\')
    $rightFull = [IO.Path]::GetFullPath($Right).TrimEnd('\')
    return [string]::Equals($leftFull, $rightFull, [StringComparison]::OrdinalIgnoreCase) -or
        $leftFull.StartsWith($rightFull + '\', [StringComparison]::OrdinalIgnoreCase) -or
        $rightFull.StartsWith($leftFull + '\', [StringComparison]::OrdinalIgnoreCase)
}

function Assert-DualLiveBoundaries {
    param(
        [Parameter(Mandatory = $true)][object[]]$MutationVector,
        [Parameter(Mandatory = $true)][object[]]$WorktreeVector,
        [Parameter(Mandatory = $true)][string[]]$BoundaryRoot
    )

    if ($BoundaryRoot.Count -eq 0) {
        Throw-DualLivePreservationHold 'preservation_boundary_invalid'
    }
    $sensitivePaths = [Collections.Generic.HashSet[string]]::new(
        [StringComparer]::OrdinalIgnoreCase
    )
    foreach ($entry in $MutationVector) {
        if ($entry.Expected -ceq 'absent' -or $entry.Class -match '\Aattempt-[45]-') {
            $null = $sensitivePaths.Add([IO.Path]::GetFullPath([string]$entry.Path))
        }
    }

    $worktreePaths = [Collections.Generic.HashSet[string]]::new(
        [StringComparer]::OrdinalIgnoreCase
    )
    $anchors = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($worktree in $WorktreeVector) {
        if (-not (Test-DualLiveCanonicalDrivePath ([string]$worktree.Path))) {
            Throw-DualLivePreservationHold 'preservation_boundary_invalid'
        }
        $worktreePath = [IO.Path]::GetFullPath([string]$worktree.Path)
        $null = $worktreePaths.Add($worktreePath)
        $null = $anchors.Add($worktreePath)
    }

    $seenRoots = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $candidates = [Collections.Generic.List[string]]::new()
    foreach ($root in $BoundaryRoot) {
        if (-not (Test-DualLiveCanonicalDrivePath $root)) {
            Throw-DualLivePreservationHold 'preservation_boundary_invalid'
        }
        $full = [IO.Path]::GetFullPath($root)
        if (-not $seenRoots.Add($full)) {
            Throw-DualLivePreservationHold 'preservation_boundary_invalid'
        }
        if ($worktreePaths.Contains($full)) {
            $null = $anchors.Add($full)
        }
        elseif (Test-DualLivePathExistsStrict -LiteralPath $full) {
            $null = $anchors.Add($full)
        }
        else {
            $candidates.Add($full)
        }
    }

    foreach ($candidate in $candidates) {
        foreach ($anchor in $anchors) {
            if (Test-DualLiveBoundaryOverlap -Left $candidate -Right $anchor) {
                Throw-DualLivePreservationHold 'preservation_boundary_overlap'
            }
        }
    }
    for ($leftIndex = 0; $leftIndex -lt $candidates.Count; $leftIndex++) {
        for ($rightIndex = $leftIndex + 1; $rightIndex -lt $candidates.Count; $rightIndex++) {
            if (Test-DualLiveBoundaryOverlap `
                    -Left $candidates[$leftIndex] `
                    -Right $candidates[$rightIndex]) {
                Throw-DualLivePreservationHold 'preservation_boundary_overlap'
            }
        }
    }

    foreach ($sensitivePath in $sensitivePaths) {
        foreach ($anchor in $anchors) {
            if (Test-DualLiveBoundaryOverlap -Left $sensitivePath -Right $anchor) {
                Throw-DualLivePreservationHold 'preservation_boundary_overlap'
            }
        }
        foreach ($candidate in $candidates) {
            if (-not [string]::Equals(
                    $sensitivePath,
                    $candidate,
                    [StringComparison]::OrdinalIgnoreCase
                ) -and
                (Test-DualLiveBoundaryOverlap -Left $sensitivePath -Right $candidate)) {
                Throw-DualLivePreservationHold 'preservation_boundary_overlap'
            }
        }
    }
}

function Get-DualLiveWorktreeVector {
    param(
        [Parameter(Mandatory = $true)][string]$RepositoryRoot,
        [Parameter(Mandatory = $true)][string]$QualifyNonDriveAgainst
    )

    if (-not (Test-DualLiveCanonicalDrivePath $RepositoryRoot) -or
        -not (Test-DualLivePathExistsStrict $RepositoryRoot)) {
        Throw-DualLivePreservationHold 'preservation_repository_invalid'
    }
    Assert-DualLiveNoReparseParent -LiteralPath $RepositoryRoot
    $repositoryReceipt = Get-DualLiveNativePathReceipt -LiteralPath $RepositoryRoot
    if ($repositoryReceipt.RootedType -cne 'directory' -or $null -ne $repositoryReceipt.ReparseTag) {
        Throw-DualLivePreservationHold 'preservation_repository_invalid'
    }

    [byte[]]$porcelain = Invoke-DualLiveGitRaw `
        -WorkingTree $RepositoryRoot `
        -Arguments ([string[]]@('worktree', 'list', '--porcelain', '-z')) `
        -FailureCode 'preservation_worktree_inventory_failed'
    if ($porcelain.Count -eq 0) {
        Throw-DualLivePreservationHold 'preservation_worktree_inventory_failed'
    }
    $parsed = @(ConvertFrom-DualLiveWorktreePorcelainBytes `
        -Bytes $porcelain `
        -QualifyNonDriveAgainst $QualifyNonDriveAgainst)
    $captured = [Collections.Generic.List[object]]::new()
    foreach ($record in $parsed) {
        if (-not (Test-DualLivePathExistsStrict $record.Path)) {
            Throw-DualLivePreservationHold 'preservation_worktree_capture_failed'
        }
        Assert-DualLiveNoReparseParent -LiteralPath $record.Path
        $rootReceipt = Get-DualLiveNativePathReceipt -LiteralPath $record.Path
        if ($rootReceipt.RootedType -cne 'directory' -or $null -ne $rootReceipt.ReparseTag) {
            Throw-DualLivePreservationHold 'preservation_worktree_capture_failed'
        }
        [byte[]]$status = Invoke-DualLiveGitRaw `
            -WorkingTree $record.Path `
            -Arguments ([string[]]@('status', '--porcelain=v1', '-z', '--untracked-files=all')) `
            -FailureCode 'preservation_worktree_capture_failed'
        [byte[]]$workingDiff = Invoke-DualLiveGitRaw `
            -WorkingTree $record.Path `
            -Arguments ([string[]]@('diff', '--binary', '--no-ext-diff', '--no-textconv')) `
            -FailureCode 'preservation_worktree_capture_failed'
        [byte[]]$indexDiff = Invoke-DualLiveGitRaw `
            -WorkingTree $record.Path `
            -Arguments ([string[]]@('diff', '--cached', '--binary', '--no-ext-diff', '--no-textconv')) `
            -FailureCode 'preservation_worktree_capture_failed'
        $untracked = @(Get-DualLiveUntrackedManifest `
            -WorkingTree $record.Path `
            -StatusBytes $status)
        $captured.Add([pscustomobject][ordered]@{
            Path = $record.Path
            Head = $record.Head
            State = $record.State
            Branch = $record.Branch
            Locked = $record.Locked
            Prunable = $record.Prunable
            StatusZBase64 = [Convert]::ToBase64String($status)
            WorkingDiffBase64 = [Convert]::ToBase64String($workingDiff)
            IndexDiffBase64 = [Convert]::ToBase64String($indexDiff)
            UntrackedManifest = $untracked
        })
    }
    return $captured.ToArray()
}

function ConvertTo-DualLiveMutationVector {
    param([Parameter(Mandatory = $true)][object[]]$InputVector)

    if ($InputVector.Count -eq 0) {
        Throw-DualLivePreservationHold 'preservation_vector_invalid'
    }
    $paths = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $normalized = [Collections.Generic.List[object]]::new()
    $required = [string[]]@('AllowedChildren', 'Class', 'Expected', 'Path', 'Recurse')

    foreach ($entry in $InputVector) {
        if ($null -eq $entry) {
            Throw-DualLivePreservationHold 'preservation_vector_invalid'
        }
        $names = [string[]]@($entry.PSObject.Properties.Name | Sort-Object -CaseSensitive)
        if ($names.Count -ne $required.Count -or
            [string]::Join("`n", $names) -cne [string]::Join("`n", $required)) {
            Throw-DualLivePreservationHold 'preservation_vector_invalid'
        }
        if ($entry.Class -isnot [string] -or $entry.Class -notmatch '\A[a-z0-9]+(?:-[a-z0-9]+)*\z' -or
            $entry.Path -isnot [string] -or -not (Test-DualLiveCanonicalDrivePath $entry.Path) -or
            $entry.Expected -isnot [string] -or $entry.Expected -cnotin @('present', 'absent') -or
            $entry.Recurse -isnot [bool] -or $entry.AllowedChildren -isnot [Array]) {
            Throw-DualLivePreservationHold 'preservation_vector_invalid'
        }
        $full = [IO.Path]::GetFullPath([string]$entry.Path)
        if (-not $paths.Add($full)) {
            Throw-DualLivePreservationHold 'preservation_vector_invalid'
        }

        $children = [Collections.Generic.List[string]]::new()
        $childNames = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        foreach ($child in @($entry.AllowedChildren)) {
            if ($child -isnot [string] -or [string]::IsNullOrWhiteSpace($child) -or
                $child -in @('.', '..') -or $child.IndexOfAny([char[]]'\/*?[]:') -ge 0 -or
                -not $childNames.Add($child)) {
                Throw-DualLivePreservationHold 'preservation_vector_invalid'
            }
            $children.Add($child)
        }
        $orderedChildren = [string[]]@($children | Sort-Object -CaseSensitive)

        Assert-DualLiveNoReparseParent -LiteralPath $full
        $exists = Test-DualLivePathExistsStrict $full
        $capturedEntries = @()
        if ($entry.Expected -ceq 'absent') {
            if ($entry.Recurse -or $orderedChildren.Count -ne 0) {
                Throw-DualLivePreservationHold 'preservation_vector_invalid'
            }
            if ($exists) {
                Throw-DualLivePreservationHold 'preservation_state_mismatch'
            }
        }
        else {
            if (-not $exists) {
                Throw-DualLivePreservationHold 'preservation_state_mismatch'
            }
            $rootReceipt = Get-DualLiveNativePathReceipt -LiteralPath $full
            if ($rootReceipt.RootedType -cne 'directory') {
                if ($entry.Recurse -or $orderedChildren.Count -ne 0) {
                    Throw-DualLivePreservationHold 'preservation_vector_invalid'
                }
            }
            else {
                if ($null -ne $rootReceipt.ReparseTag) {
                    if ($entry.Recurse) {
                        Throw-DualLivePreservationHold 'preservation_reparse_root'
                    }
                    if ($orderedChildren.Count -ne 0) {
                        Throw-DualLivePreservationHold 'preservation_vector_invalid'
                    }
                }
                else {
                    $actualChildren = [string[]]@(
                        Get-ChildItem -Force -LiteralPath $full |
                            ForEach-Object Name |
                            Sort-Object -CaseSensitive
                    )
                    if ([string]::Join("`n", $actualChildren) -cne
                        [string]::Join("`n", $orderedChildren)) {
                        Throw-DualLivePreservationHold 'preservation_unknown_child'
                    }
                }
            }
            $capturedEntries = @(Get-DualLiveExternalEntries `
                -LiteralPath $full `
                -Recurse ([bool]$entry.Recurse))
            if ($capturedEntries.Count -eq 0 -or
                -not (Test-DualLiveNativeReceiptEqual `
                    -Left $rootReceipt `
                    -Right $capturedEntries[0])) {
                Throw-DualLivePreservationHold 'preservation_path_drift'
            }
            try {
                $finalRootReceipt = Get-DualLiveNativePathReceipt -LiteralPath $full
            }
            catch {
                Throw-DualLivePreservationHold 'preservation_path_drift'
            }
            if (-not (Test-DualLiveNativeReceiptEqual `
                    -Left $capturedEntries[0] `
                    -Right $finalRootReceipt)) {
                Throw-DualLivePreservationHold 'preservation_path_drift'
            }
            if ($rootReceipt.RootedType -ceq 'directory' -and
                $null -eq $rootReceipt.ReparseTag) {
                try {
                    $finalChildren = [string[]]@(
                        Get-ChildItem -Force -LiteralPath $full |
                            ForEach-Object Name |
                            Sort-Object -CaseSensitive
                    )
                }
                catch {
                    Throw-DualLivePreservationHold 'preservation_path_drift'
                }
                if ([string]::Join("`n", $finalChildren) -cne
                    [string]::Join("`n", $orderedChildren)) {
                    Throw-DualLivePreservationHold 'preservation_unknown_child'
                }
            }
        }

        $normalized.Add([pscustomobject][ordered]@{
            Class = [string]$entry.Class
            Path = $full
            Expected = [string]$entry.Expected
            Recurse = [bool]$entry.Recurse
            AllowedChildren = $orderedChildren
            Exists = [bool]$exists
            Entries = $capturedEntries
        })
    }
    return $normalized.ToArray()
}

function New-DualLivePreservationReceipt {
    param(
        [Parameter(Mandatory = $true)][object[]]$MutationVector,
        [Parameter(Mandatory = $true)][string]$RepositoryRoot,
        [Parameter(Mandatory = $true)][string[]]$BoundaryRoot,
        [Parameter(Mandatory = $true)][string]$QualifyNonDriveAgainst
    )

    $normalizedMutationVector = @(
        ConvertTo-DualLiveMutationVector -InputVector $MutationVector
    )
    $capturedWorktreeVector = @(
        Get-DualLiveWorktreeVector `
            -RepositoryRoot $RepositoryRoot `
            -QualifyNonDriveAgainst $QualifyNonDriveAgainst
    )
    Assert-DualLiveBoundaries `
        -MutationVector $normalizedMutationVector `
        -WorktreeVector $capturedWorktreeVector `
        -BoundaryRoot $BoundaryRoot
    $mutationCount = [int]$normalizedMutationVector.Count
    $worktreeCount = [int]$capturedWorktreeVector.Count
    if ($mutationCount -ne @($normalizedMutationVector).Count -or
        $worktreeCount -ne @($capturedWorktreeVector).Count -or
        $mutationCount -eq 0 -or $worktreeCount -eq 0) {
        Throw-DualLivePreservationHold 'preservation_count_mismatch'
    }
    $payload = [ordered]@{
        Status = 'PRESERVATION_RECEIPT_OK'
        MutationCount = $mutationCount
        WorktreeCount = $worktreeCount
        MutationVector = $normalizedMutationVector
        WorktreeVector = $capturedWorktreeVector
    }
    [pscustomobject][ordered]@{
        Status = $payload.Status
        MutationCount = $payload.MutationCount
        WorktreeCount = $payload.WorktreeCount
        MutationVector = $payload.MutationVector
        WorktreeVector = $payload.WorktreeVector
        CanonicalJson = ($payload | ConvertTo-Json -Depth 100 -Compress)
    }
}
