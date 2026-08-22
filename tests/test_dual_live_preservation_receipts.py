from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "validate-dual-live-preservation-receipts.ps1"
WINDOWS_POWERSHELL = Path(
    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
)

pytestmark = pytest.mark.skipif(os.name != "nt", reason="requires Windows PowerShell")


def _ps_quote(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _run_powershell(command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            str(WINDOWS_POWERSHELL),
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _caught_receipt_command(
    vector_file: Path,
    repository_root: Path,
    boundary_root: Path,
) -> str:
    return "\n".join(
        (
            f". {_ps_quote(HELPER)}",
            f"$decoded = Get-Content -Raw -LiteralPath {_ps_quote(vector_file)} "
            "| ConvertFrom-Json",
            "$vector = @($decoded)",
            "try {",
            "  New-DualLivePreservationReceipt "
            "-MutationVector $vector "
            f"-RepositoryRoot {_ps_quote(repository_root)} "
            f"-BoundaryRoot @({_ps_quote(boundary_root)}) "
            "-QualifyNonDriveAgainst 'C:\\' | Out-Null",
            "  [Console]::Out.Write('unexpected_success')",
            "  exit 99",
            "} catch {",
            "  [Console]::Out.Write($_.Exception.Message)",
            "  exit 17",
            "}",
        )
    )


def _write_vector(path: Path, entries: list[dict[str, object]]) -> None:
    path.write_text(json.dumps(entries), encoding="utf-8")


def test_helper_has_the_closed_validate_only_ps51_contract() -> None:
    source = HELPER.read_text(encoding="utf-8")

    assert "function New-DualLivePreservationReceipt" in source
    for parameter in (
        "MutationVector",
        "RepositoryRoot",
        "BoundaryRoot",
        "QualifyNonDriveAgainst",
    ):
        assert f"${parameter}" in source
    for field in (
        "Status",
        "MutationCount",
        "WorktreeCount",
        "MutationVector",
        "WorktreeVector",
        "CanonicalJson",
    ):
        assert field in source
    for primitive in (
        "FILE_FLAG_OPEN_REPARSE_POINT",
        "GetFileInformationByHandle",
        "FSCTL_GET_REPARSE_POINT",
        "GetSecurityInfo",
        "--no-optional-locks",
        "--porcelain=v1",
        "--binary",
        "CopyToAsync",
    ):
        assert primitive in source
    for forbidden in (
        "Set-Content",
        "Add-Content",
        "Out-File",
        "New-Item",
        "Remove-Item",
        "Move-Item",
        "Copy-Item",
        "Invoke-WebRequest",
        "Invoke-RestMethod",
        "Start-Process",
        "Verb = 'runas'",
    ):
        assert forbidden not in source

    command = (
        "$tokens=$null;$errors=$null;"
        f"[Management.Automation.Language.Parser]::ParseFile({_ps_quote(HELPER)},"
        "[ref]$tokens,[ref]$errors)|Out-Null;"
        "if($errors.Count){$errors|ForEach-Object{$_.Message};exit 1}"
    )
    result = _run_powershell(command)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""


def test_mutation_vector_schema_fails_closed_before_git_capture(tmp_path: Path) -> None:
    present = tmp_path / "present.txt"
    present.write_bytes(b"present")
    present_directory = tmp_path / "present-directory"
    present_directory.mkdir()
    (present_directory / "known.txt").write_bytes(b"known")
    boundary = tmp_path / "boundary"
    boundary.mkdir()
    base = {
        "Class": "retained-leaf",
        "Path": str(present),
        "Expected": "present",
        "Recurse": False,
        "AllowedChildren": [],
    }
    malformed = (
        {**base, "Unexpected": True},
        {key: value for key, value in base.items() if key != "Expected"},
        {**base, "Path": "<OWNER-FILL exact path>"},
        {
            **base,
            "Path": str(tmp_path / "absent"),
            "Expected": "absent",
            "Recurse": True,
        },
        [base, {**base, "Class": "duplicate"}],
        [
            base,
            {
                **base,
                "Class": "trailing-separator-duplicate",
                "Path": str(present) + "\\",
            },
        ],
        {
            **base,
            "Class": "retained-root",
            "Path": str(present_directory),
            "AllowedChildren": "known.txt",
        },
    )
    for index, candidate in enumerate(malformed):
        entries = candidate if isinstance(candidate, list) else [candidate]
        vector_file = tmp_path / f"vector-{index}.json"
        _write_vector(vector_file, entries)

        result = _run_powershell(
            _caught_receipt_command(vector_file, tmp_path, boundary)
        )

        assert result.returncode == 17
        assert result.stdout == "preservation_vector_invalid"
        assert result.stderr == ""


def test_present_directory_rejects_every_unclassified_immediate_child(
    tmp_path: Path,
) -> None:
    retained = tmp_path / "retained"
    retained.mkdir()
    (retained / "known.txt").write_bytes(b"known")
    (retained / "unknown.txt").write_bytes(b"unknown")
    boundary = tmp_path / "boundary"
    boundary.mkdir()
    vector_file = tmp_path / "vector.json"
    _write_vector(
        vector_file,
        [
            {
                "Class": "retained-root",
                "Path": str(retained),
                "Expected": "present",
                "Recurse": True,
                "AllowedChildren": ["known.txt"],
            }
        ],
    )

    result = _run_powershell(_caught_receipt_command(vector_file, tmp_path, boundary))

    assert result.returncode == 17
    assert result.stdout == "preservation_unknown_child"
    assert result.stderr == ""


def test_native_no_follow_receipt_binds_hardlink_identity_and_external_security(
    tmp_path: Path,
) -> None:
    original = tmp_path / "original.bin"
    hardlink = tmp_path / "hardlink.bin"
    payload = b"native-handle-identity\x00\xff"
    original.write_bytes(payload)
    os.link(original, hardlink)
    command = "\n".join(
        (
            f". {_ps_quote(HELPER)}",
            f"$a = Get-DualLiveNativePathReceipt -LiteralPath {_ps_quote(original)}",
            f"$b = Get-DualLiveNativePathReceipt -LiteralPath {_ps_quote(hardlink)}",
            "[pscustomobject][ordered]@{ A=$a; B=$b } "
            "| ConvertTo-Json -Depth 20 -Compress",
        )
    )

    result = _run_powershell(command)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    observations = json.loads(result.stdout)
    expected_fields = [
        "Path",
        "Exists",
        "RootedType",
        "ReparseTag",
        "ReparseDataBase64",
        "VolumeIdentity",
        "FileIdentity",
        "LinkCount",
        "CreationTimeUtc",
        "LastWriteTimeUtc",
        "Length",
        "Sha256",
        "OwnerSid",
        "DaclProtected",
        "OrderedSddl",
        "SortedAceTuples",
    ]
    for receipt, expected_path in (
        (observations["A"], original),
        (observations["B"], hardlink),
    ):
        assert list(receipt) == expected_fields
        assert Path(receipt["Path"]) == expected_path
        assert receipt["Exists"] is True
        assert receipt["RootedType"] == "file"
        assert receipt["ReparseTag"] is None
        assert receipt["ReparseDataBase64"] is None
        assert receipt["Length"] == len(payload)
        assert receipt["Sha256"] == hashlib.sha256(payload).hexdigest()
        assert receipt["OwnerSid"].startswith("S-1-")
        assert isinstance(receipt["DaclProtected"], bool)
        assert receipt["OrderedSddl"].startswith("O:")
        assert "D:" in receipt["OrderedSddl"]
        assert receipt["SortedAceTuples"] == sorted(receipt["SortedAceTuples"])
        assert "LastAccessTimeUtc" not in receipt
        assert "Sacl" not in receipt
        assert "PrimaryGroup" not in receipt
    assert observations["A"]["VolumeIdentity"] == observations["B"]["VolumeIdentity"]
    assert observations["A"]["FileIdentity"] == observations["B"]["FileIdentity"]
    assert observations["A"]["LinkCount"] >= 2
    assert observations["B"]["LinkCount"] >= 2


def test_native_receipt_rejects_an_already_mutable_file_handle(tmp_path: Path) -> None:
    mutable = tmp_path / "mutable.bin"
    mutable.write_bytes(b"must-be-locked-while-hashing")
    command = "\n".join(
        (
            f". {_ps_quote(HELPER)}",
            "$share = [IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete",
            "$stream = [IO.File]::Open("
            f"{_ps_quote(mutable)}, [IO.FileMode]::Open, "
            "[IO.FileAccess]::ReadWrite, $share)",
            "$code = 0",
            "$message = ''",
            "try {",
            "  try {",
            "    Get-DualLiveNativePathReceipt "
            f"-LiteralPath {_ps_quote(mutable)} | Out-Null",
            "    $message = 'unexpected_success'",
            "    $code = 99",
            "  } catch {",
            "    $message = $_.Exception.Message",
            "    $code = 17",
            "  }",
            "} finally {",
            "  $stream.Dispose()",
            "}",
            "[Console]::Out.Write($message)",
            "exit $code",
        )
    )

    result = _run_powershell(command)

    assert result.returncode == 17
    assert result.stdout == "preservation_path_unreadable"
    assert result.stderr == ""


def _parse_porcelain(payload: bytes, *, caught: bool = False) -> subprocess.CompletedProcess[str]:
    body = (
        "$records = @(ConvertFrom-DualLiveWorktreePorcelainBytes "
        f"-Bytes ([Convert]::FromBase64String('{base64.b64encode(payload).decode()}')) "
        "-QualifyNonDriveAgainst 'C:\\')"
    )
    if caught:
        command = "\n".join(
            (
                f". {_ps_quote(HELPER)}",
                "try {",
                f"  {body}",
                "  [Console]::Out.Write('unexpected_success')",
                "  exit 99",
                "} catch {",
                "  [Console]::Out.Write($_.Exception.Message)",
                "  exit 17",
                "}",
            )
        )
    else:
        command = "\n".join(
            (
                f". {_ps_quote(HELPER)}",
                body,
                "$records | ConvertTo-Json -Depth 10 -Compress",
            )
        )
    return _run_powershell(command)


def test_worktree_porcelain_parser_qualifies_non_drive_roots_and_sorts_records() -> None:
    payload = (
        b"worktree C:/z/repo\0"
        + b"HEAD "
        + (b"a" * 40)
        + b"\0branch refs/heads/main\0\0"
        + b"worktree /tmp/repo\0"
        + b"HEAD "
        + (b"b" * 40)
        + b"\0detached\0locked initializing\0\0"
    )

    result = _parse_porcelain(payload)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    records = json.loads(result.stdout)
    assert [record["Path"] for record in records] == [r"C:\tmp\repo", r"C:\z\repo"]
    assert records[0] == {
        "Path": r"C:\tmp\repo",
        "Head": "b" * 40,
        "State": "detached",
        "Branch": None,
        "Locked": "initializing",
        "Prunable": None,
    }
    assert records[1]["State"] == "branch"
    assert records[1]["Branch"] == "refs/heads/main"


def test_worktree_porcelain_parser_rejects_every_malformed_or_duplicate_record() -> None:
    valid_head = b"a" * 40
    malformed = (
        b"",
        b"worktree C:/repo\0HEAD " + valid_head + b"\0detached\0",
        (
            b"worktree C:/repo\0HEAD "
            + valid_head
            + b"\0detached\0\0worktree c:/REPO\0HEAD "
            + valid_head
            + b"\0detached\0\0"
        ),
        b"worktree C:/repo\0HEAD " + valid_head + b"\0HEAD " + valid_head + b"\0detached\0\0",
        b"worktree C:/repo\0HEAD " + valid_head + b"\0mystery value\0detached\0\0",
        b"worktree C:/repo\0HEAD " + valid_head + b"\0detached\0branch refs/heads/main\0\0",
        b"worktree relative/repo\0HEAD " + valid_head + b"\0detached\0\0",
        b"worktree C:relative\0HEAD " + valid_head + b"\0detached\0\0",
        b"worktree C:/repo\0HEAD short\0detached\0\0",
        b"worktree C:/repo\0HEAD " + valid_head + b"\0\xff\0detached\0\0",
    )
    for payload in malformed:
        result = _parse_porcelain(payload, caught=True)
        assert result.returncode == 17
        assert result.stdout == "preservation_worktree_porcelain_invalid"
        assert result.stderr == ""


def _git(repository: Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git.exe", "-C", str(repository), *arguments],
        check=False,
        capture_output=True,
        timeout=30,
    )


def _initialize_dirty_repository(repository: Path) -> tuple[bytes, bytes, bytes]:
    repository.mkdir()
    assert _git(repository, "init").returncode == 0
    working_base = b"working-base\x00"
    index_base = b"index-base\x00"
    (repository / "working.bin").write_bytes(working_base)
    (repository / "index.bin").write_bytes(index_base)
    assert _git(repository, "add", "working.bin", "index.bin").returncode == 0
    commit = _git(
        repository,
        "-c",
        "user.name=Receipt Test",
        "-c",
        "user.email=receipt@example.invalid",
        "commit",
        "-m",
        "baseline",
    )
    assert commit.returncode == 0, commit.stderr.decode(errors="replace")
    working_now = b"working-now\x00\xff"
    index_now = b"index-now\x00\xfe"
    untracked = b"untracked\x00\xfd"
    (repository / "working.bin").write_bytes(working_now)
    (repository / "index.bin").write_bytes(index_now)
    assert _git(repository, "add", "index.bin").returncode == 0
    (repository / "untracked.bin").write_bytes(untracked)
    return working_now, index_now, untracked


def _capture_receipt(
    vector_file: Path,
    repository: Path,
    boundary: Path,
) -> subprocess.CompletedProcess[str]:
    command = "\n".join(
        (
            f". {_ps_quote(HELPER)}",
            f"$decoded = Get-Content -Raw -LiteralPath {_ps_quote(vector_file)} "
            "| ConvertFrom-Json",
            "$vector = @($decoded)",
            "$receipt = New-DualLivePreservationReceipt "
            "-MutationVector $vector "
            f"-RepositoryRoot {_ps_quote(repository)} "
            f"-BoundaryRoot @({_ps_quote(boundary)}) "
            "-QualifyNonDriveAgainst 'C:\\'",
            "$receipt | ConvertTo-Json -Depth 100 -Compress",
        )
    )
    return _run_powershell(command)


def test_primary_receipt_captures_raw_git_bytes_untracked_hashes_and_is_stable(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    _, _, untracked = _initialize_dirty_repository(repository)
    boundary = tmp_path / "boundary"
    boundary.mkdir()
    evidence = repository / "evidence.bin"
    evidence.write_bytes(b"evidence")
    absent = tmp_path / "absent"
    vector_file = tmp_path / "vector.json"
    _write_vector(
        vector_file,
        [
            {
                "Class": "governance-carrier",
                "Path": str(evidence),
                "Expected": "present",
                "Recurse": False,
                "AllowedChildren": [],
            },
            {
                "Class": "must-remain-absent",
                "Path": str(absent),
                "Expected": "absent",
                "Recurse": False,
                "AllowedChildren": [],
            },
        ],
    )
    index_path = repository / ".git" / "index"
    index_before = (index_path.read_bytes(), index_path.stat().st_mtime_ns)

    first = _capture_receipt(vector_file, repository, boundary)
    second = _capture_receipt(vector_file, repository, boundary)

    assert first.returncode == 0, first.stdout + first.stderr
    assert first.stderr == ""
    assert second.returncode == 0, second.stdout + second.stderr
    assert second.stderr == ""
    receipt = json.loads(first.stdout)
    repeated = json.loads(second.stdout)
    assert list(receipt) == [
        "Status",
        "MutationCount",
        "WorktreeCount",
        "MutationVector",
        "WorktreeVector",
        "CanonicalJson",
    ]
    assert receipt["Status"] == "PRESERVATION_RECEIPT_OK"
    assert receipt["MutationCount"] == 2
    assert receipt["WorktreeCount"] == 1
    assert receipt["CanonicalJson"] == repeated["CanonicalJson"]
    canonical = json.loads(receipt["CanonicalJson"])
    assert canonical == {
        key: receipt[key]
        for key in (
            "Status",
            "MutationCount",
            "WorktreeCount",
            "MutationVector",
            "WorktreeVector",
        )
    }
    assert receipt["MutationVector"][0]["Entries"][0]["Sha256"] == hashlib.sha256(
        b"evidence"
    ).hexdigest()
    assert receipt["MutationVector"][1]["Exists"] is False
    assert receipt["MutationVector"][1]["Entries"] == []

    worktree = receipt["WorktreeVector"][0]
    assert Path(worktree["Path"]) == repository
    head = _git(repository, "rev-parse", "HEAD")
    assert head.returncode == 0
    assert worktree["Head"] == head.stdout.decode().strip()
    assert worktree["State"] == "branch"
    status = base64.b64decode(worktree["StatusZBase64"])
    working_diff = base64.b64decode(worktree["WorkingDiffBase64"])
    index_diff = base64.b64decode(worktree["IndexDiffBase64"])
    assert b"\0" in status
    assert b"?? untracked.bin\0" in status
    assert b"diff --git" in working_diff and b"GIT binary patch" in working_diff
    assert b"diff --git" in index_diff and b"GIT binary patch" in index_diff
    manifest = {entry["Path"]: entry for entry in worktree["UntrackedManifest"]}
    assert list(manifest) == sorted(manifest)
    assert manifest["untracked.bin"]["RootedType"] == "file"
    assert manifest["untracked.bin"]["Length"] == len(untracked)
    assert manifest["untracked.bin"]["Sha256"] == hashlib.sha256(untracked).hexdigest()
    assert (index_path.read_bytes(), index_path.stat().st_mtime_ns) == index_before


def test_recursive_and_untracked_manifests_capture_reparse_bytes_without_traversal(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    sentinel = target / "must-not-be-followed.bin"
    sentinel.write_bytes(b"outside")
    retained = tmp_path / "retained"
    retained.mkdir()
    junction = retained / "link"
    link_result = subprocess.run(
        [
            "cmd.exe",
            "/d",
            "/c",
            "mklink",
            "/J",
            str(junction),
            str(target),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert link_result.returncode == 0, link_result.stdout + link_result.stderr
    vector_file = tmp_path / "vector.json"
    _write_vector(
        vector_file,
        [
            {
                "Class": "retained-root",
                "Path": str(retained),
                "Expected": "present",
                "Recurse": True,
                "AllowedChildren": ["link"],
            }
        ],
    )
    command = "\n".join(
        (
            f". {_ps_quote(HELPER)}",
            f"$decoded = Get-Content -Raw -LiteralPath {_ps_quote(vector_file)} "
            "| ConvertFrom-Json",
            "$vector = @(ConvertTo-DualLiveMutationVector -InputVector @($decoded))",
            "$status = [Text.Encoding]::UTF8.GetBytes('?? link' + [char]0)",
            f"$untracked = @(Get-DualLiveUntrackedManifest -WorkingTree {_ps_quote(retained)} "
            "-StatusBytes $status)",
            "[pscustomobject][ordered]@{Vector=$vector;Untracked=$untracked} "
            "| ConvertTo-Json -Depth 100 -Compress",
        )
    )

    result = _run_powershell(command)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    captured = json.loads(result.stdout)
    entries = captured["Vector"][0]["Entries"]
    assert [Path(entry["Path"]).name for entry in entries] == ["retained", "link"]
    assert all(Path(entry["Path"]) != sentinel for entry in entries)
    reparse = entries[1]
    assert reparse["RootedType"] == "directory"
    assert reparse["ReparseTag"].startswith("0x")
    assert base64.b64decode(reparse["ReparseDataBase64"])
    assert reparse["Length"] is None
    assert reparse["Sha256"] is None

    untracked = captured["Untracked"][0]
    raw_reparse = base64.b64decode(untracked["ReparseDataBase64"])
    assert untracked["Path"] == "link"
    assert untracked["RootedType"] == "directory-reparse"
    assert untracked["Length"] == len(raw_reparse)
    assert untracked["Sha256"] == hashlib.sha256(raw_reparse).hexdigest()


def test_recursive_capture_rejects_a_directory_reparse_swap(tmp_path: Path) -> None:
    retained = tmp_path / "retained"
    retained.mkdir()
    (retained / "stable.bin").write_bytes(b"original")
    displaced = tmp_path / "displaced"
    target = tmp_path / "swap-target"
    target.mkdir()
    (target / "stable.bin").write_bytes(b"replacement")
    command = "\n".join(
        (
            f". {_ps_quote(HELPER)}",
            "$script:swapped = $false",
            "function Get-ChildItem {",
            "  param([switch]$Force, [string]$LiteralPath)",
            "  $items = @(Microsoft.PowerShell.Management\\Get-ChildItem "
            "-Force -LiteralPath $LiteralPath)",
            "  if (-not $script:swapped -and "
            f"[string]::Equals($LiteralPath, {_ps_quote(retained)}, "
            "[StringComparison]::OrdinalIgnoreCase)) {",
            f"    [IO.Directory]::Move({_ps_quote(retained)}, {_ps_quote(displaced)})",
            "    & cmd.exe /d /c mklink /J "
            f"{_ps_quote(retained)} {_ps_quote(target)} | Out-Null",
            "    if ($LASTEXITCODE -ne 0) { throw 'junction swap failed' }",
            "    $script:swapped = $true",
            "  }",
            "  return $items",
            "}",
            "try {",
            "  Get-DualLiveExternalEntries "
            f"-LiteralPath {_ps_quote(retained)} -Recurse $true | Out-Null",
            "  [Console]::Out.Write('unexpected_success')",
            "  exit 99",
            "} catch {",
            "  [Console]::Out.Write($_.Exception.Message)",
            "  exit 17",
            "}",
        )
    )

    result = _run_powershell(command)

    assert result.returncode == 17
    assert result.stdout == "preservation_directory_drift"
    assert result.stderr == ""


def _boundary_check(
    candidate: Path,
    worktree: Path,
    boundaries: list[Path],
) -> subprocess.CompletedProcess[str]:
    boundary_array = "@(" + ",".join(_ps_quote(path) for path in boundaries) + ")"
    command = "\n".join(
        (
            f". {_ps_quote(HELPER)}",
            "$mutation = @([pscustomobject]@{"
            "Class='attempt-4-worker';"
            f"Path={_ps_quote(candidate)};"
            "Expected='absent'"
            "})",
            f"$worktrees = @([pscustomobject]@{{Path={_ps_quote(worktree)}}})",
            "try {",
            "  Assert-DualLiveBoundaries -MutationVector $mutation "
            f"-WorktreeVector $worktrees -BoundaryRoot {boundary_array}",
            "  [Console]::Out.Write('BOUNDARY_OK')",
            "  exit 0",
            "} catch {",
            "  [Console]::Out.Write($_.Exception.Message)",
            "  exit 17",
            "}",
        )
    )
    return _run_powershell(command)


def test_boundary_checks_reject_equal_ancestor_and_descendant_candidates(
    tmp_path: Path,
) -> None:
    worktree = tmp_path / "repo"
    boundary = tmp_path / "ceremony"
    worktree.mkdir()
    boundary.mkdir()
    unrelated = tmp_path / "candidate"
    overlaps = (
        boundary,
        boundary / "child",
        boundary.parent,
        worktree / "scratch",
    )
    for candidate in overlaps:
        result = _boundary_check(candidate, worktree, [boundary])
        assert result.returncode == 17
        assert result.stdout == "preservation_boundary_overlap"
        assert result.stderr == ""

    ambiguous = _boundary_check(
        unrelated,
        worktree,
        [tmp_path / "scratch", tmp_path / "scratch" / "nested"],
    )
    assert ambiguous.returncode == 17
    assert ambiguous.stdout == "preservation_boundary_overlap"
    assert ambiguous.stderr == ""

    disjoint = _boundary_check(unrelated, worktree, [boundary])
    assert disjoint.returncode == 0
    assert disjoint.stdout == "BOUNDARY_OK"
    assert disjoint.stderr == ""

    modeled_candidate = _boundary_check(
        tmp_path / "scratch",
        worktree,
        [boundary, tmp_path / "scratch"],
    )
    assert modeled_candidate.returncode == 0
    assert modeled_candidate.stdout == "BOUNDARY_OK"
    assert modeled_candidate.stderr == ""

    modeled_worktree_anchor = _boundary_check(
        unrelated,
        worktree,
        [boundary, worktree],
    )
    assert modeled_worktree_anchor.returncode == 0
    assert modeled_worktree_anchor.stdout == "BOUNDARY_OK"
    assert modeled_worktree_anchor.stderr == ""
