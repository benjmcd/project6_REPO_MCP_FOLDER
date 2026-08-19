"""Elevated end-to-end proof of the worker-bundle ACL hardening routine.

This exercises the *production* ACL text lifted verbatim out of
``scripts/provision-dual-live-worker.ps1`` -- the expectation table, the
bottom-up materialization, the apply loop, and the final descriptor
verification -- against a throwaway GUID-named tree on fixed local NTFS.

Why it needs elevation: the routine sets the owner to Local Service
(``S-1-5-19``), which requires ``SeRestorePrivilege``.  Without elevation the
test SKIPS; it never silently passes.

Separately measured behaviour of the pre-repair parent (a10626bf), obtained by
driving that script's own apply loop, not by anything below: the target list
there is ``[provisioning root, bundle root, descendants...]``, so the
provisioning root is hardened first.  Effect of that single first iteration on
an otherwise identical tree: the provisioning root becomes protected with its
six explicit ACEs, but because none of those ACEs is inheritable, the resulting
re-propagation strips every inherited ACE from the still-unsecured children --
the bundle root drops from seven inherited ACEs to an *empty* DACL, and every
object beneath it becomes unreadable ("Access is denied").  The loop's next
iteration then transfers the bundle root's ownership away to ``S-1-5-19``,
surrendering the implicit owner rights that were the last way in, and its
``icacls`` call fails, aborting at ``worker_bundle_acl_failed``.  That is
exactly where W6-PRE attempt 2 died.

This module cannot reproduce that measurement, because it cannot run against
the parent at all: the parent carries no expectation table and no post-loop
descriptor verification, so ``_ROUTINE_START``
(``$expectedAcl = [ordered]@{}``) is absent from its text and ``_acl_routine``
raises ``ValueError: substring not found`` while assembling the harness --
before any PowerShell process is launched, and therefore long before the
bundle-root op or any descriptor assertion below.

Bottom-up ordering removes the exposure: each descendant already carries its
own protected DACL before its ancestor is touched, so the ancestor's
re-propagation has nothing left to strip.

What is asserted below is the descriptor's *content*, keyed by principal, not
its DACL order.  Windows canonicalizes explicit-ACE order when a descriptor is
written, so the stored sequence is not something a provisioner establishes; see
``_EXPECTED_ACES``.
"""

import ctypes
import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PROVISIONER = ROOT / "scripts" / "provision-dual-live-worker.ps1"
WINDOWS_POWERSHELL = Path(
    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
)

_SYSTEM_SID = "S-1-5-18"
_ADMINISTRATORS_SID = "S-1-5-32-544"
_OWNER_SID = "S-1-5-19"
_PROVISIONER_SID = "S-1-5-20"
# AppContainer-shaped stand-ins for the profile-bound principals.  The routine
# is SID-agnostic; only distinctness and grant shape matter to the contract.
_BROKER_SID = (
    "S-1-15-2-3624051433-2125758914-1423191267-1740899205-1073925389"
    "-3782572162-737981194"
)
_PACKAGE_SID = (
    "S-1-15-2-1861897761-1695161497-2927542615-642690995-327840285"
    "-2659745135-2630312742"
)

_CONTROL_MASK = 0x001F01FF
_RX_MASK = 0x001200A9
# Keyed by principal.  The insertion order below is the icacls argument order the
# provisioner grants in; it is NOT the order Windows stores.  Windows
# canonicalizes explicit-ACE order when a descriptor is written -- measured as
# ascending SID, and identical whether the DACL is written by one icacls call,
# one per principal, in reverse argument order, or by .NET Set-Acl -- so DACL
# position is not a property the provisioner can establish and is not asserted.
_EXPECTED_ACES = {
    _SYSTEM_SID: _CONTROL_MASK,
    _ADMINISTRATORS_SID: _CONTROL_MASK,
    _OWNER_SID: _CONTROL_MASK,
    _PROVISIONER_SID: _CONTROL_MASK,
    _BROKER_SID: _RX_MASK,
    _PACKAGE_SID: _RX_MASK,
}

# Nothing disposable may ever be created inside a ceremony or evidence path.
_FORBIDDEN_ROOTS = (
    r"C:\owner-controlled",
    r"C:\ProgramData\Project6",
    r"C:\p6-sciencebase-worker",
    str(ROOT),
)

_PRIVILEGE_START = "function Enable-RestorePrivilege {"
_PRIVILEGE_END = "[Project6WorkerProvisionerPrivilege]::Enable()\n}\n"
_ROUTINE_START = "$expectedAcl = [ordered]@{}"
_ROUTINE_END = "\n$binding = [ordered]@{"


def _posture_report(where: str, aces: list[dict]) -> str:
    """Classify every observed ACE, so a failure names the offending field.

    Rendered eagerly and passed as the assertion message: an elevated run is
    expensive and one-shot, so a failure must not come back as a bare
    ``assert False`` that needs another elevated run to interpret.
    """

    lines = [f"{where}: observed {len(aces)} explicit ACE(s)"]
    for index, ace in enumerate(aces):
        expected_mask = _EXPECTED_ACES.get(ace["sid"])
        if expected_mask is None:
            verdict = "UNEXPECTED PRINCIPAL"
        elif (
            ace["kind"] == "Allow"
            and ace["mask"] == expected_mask
            and ace["inherited"] is False
            and ace["inheritance"] == "None"
            and ace["propagation"] == "None"
        ):
            verdict = "ok"
        else:
            verdict = (
                f"mask={ace['mask']:#010x} (expected {expected_mask:#010x}) "
                f"kind={ace['kind']} inherited={ace['inherited']} "
                f"inheritance={ace['inheritance']} propagation={ace['propagation']}"
            )
        lines.append(f"  [{index}] {ace['sid']} -> {verdict}")
    missing = sorted(set(_EXPECTED_ACES) - {ace["sid"] for ace in aces})
    if missing:
        lines.append(f"  missing principals: {missing}")
    return "\n".join(lines)


def _privilege_function(source: str) -> str:
    start = source.index(_PRIVILEGE_START)
    end = source.index(_PRIVILEGE_END, start) + len(_PRIVILEGE_END)
    return source[start:end]


def _acl_routine(source: str) -> str:
    """The production ACL routine, verbatim -- not a reimplementation."""

    start = source.index(_ROUTINE_START)
    return source[start : source.index(_ROUTINE_END, start)]


def _is_elevated() -> bool:
    if os.name != "nt":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):  # pragma: no cover - non-Windows guard
        return False


def _is_fixed_local_ntfs(path: Path) -> bool:
    drive = os.path.splitdrive(str(path))[0] + "\\"
    if ctypes.windll.kernel32.GetDriveTypeW(drive) != 3:  # DRIVE_FIXED
        return False
    name = ctypes.create_unicode_buffer(261)
    filesystem = ctypes.create_unicode_buffer(261)
    ok = ctypes.windll.kernel32.GetVolumeInformationW(
        drive, name, 261, None, None, None, filesystem, 261
    )
    return bool(ok) and filesystem.value.upper() == "NTFS"


def _harness(provisioning: Path, bundle_root: Path, report: Path) -> str:
    source = PROVISIONER.read_text(encoding="utf-8")
    return (
        "Set-StrictMode -Version Latest\n"
        "$ErrorActionPreference = 'Stop'\n"
        f"{_privilege_function(source)}"
        f"$SystemSid = '{_SYSTEM_SID}'\n"
        f"$AdministratorsSid = '{_ADMINISTRATORS_SID}'\n"
        f"$OwnerSid = '{_OWNER_SID}'\n"
        f"$ProvisionerSid = '{_PROVISIONER_SID}'\n"
        "$profile = [pscustomobject]@{ broker_sid = '"
        f"{_BROKER_SID}'; package_sid = '{_PACKAGE_SID}' " + "}\n"
        f"$provisioning = '{provisioning}'\n"
        f"$bundleRoot = '{bundle_root}'\n"
        f"{_acl_routine(source)}\n"
        "$report = @()\n"
        "foreach ($target in $aclTargets) {\n"
        "  $a = Get-Acl -LiteralPath $target\n"
        "  $aces = @(@($a.GetAccessRules($true, $false, "
        "[Security.Principal.SecurityIdentifier])) | ForEach-Object {\n"
        "    [ordered]@{ sid = $_.IdentityReference.Value; "
        "mask = [int]$_.FileSystemRights; kind = \"$($_.AccessControlType)\"; "
        "inherited = [bool]$_.IsInherited; "
        "inheritance = \"$($_.InheritanceFlags)\"; "
        "propagation = \"$($_.PropagationFlags)\" }\n"
        "  })\n"
        "  $report += ,([ordered]@{ path = $target; "
        "owner = $a.GetOwner([Security.Principal.SecurityIdentifier]).Value; "
        "protected = [bool]$a.AreAccessRulesProtected; "
        "inheritedCount = @($a.GetAccessRules($false, $true, "
        "[Security.Principal.SecurityIdentifier])).Count; aces = $aces })\n"
        "}\n"
        f"Set-Content -LiteralPath '{report}' -Encoding utf8 -Value "
        "(ConvertTo-Json -Depth 6 -InputObject @($report))\n"
        "Write-Output 'ACL_ROUTINE_OK'\n"
    )


def _build_tree(disposable: Path) -> tuple[Path, Path]:
    provisioning = disposable / "provisioning"
    bundle_root = provisioning / "bundle"
    deep = bundle_root / "deep"
    deep.mkdir(parents=True)
    (deep / "payload").write_text("payload\n", encoding="ascii")
    (bundle_root / "worker-bundle.json").write_text("{}\n", encoding="ascii")
    return provisioning, bundle_root


def _reclaim(disposable: Path) -> None:
    """Take the disposable root back, then remove only it.

    Recovery is strictly top-down -- the inverse of the hardening order.  If the
    routine aborted midway, descendants can be left with an emptied DACL and are
    unreachable until their ancestors are restored, so ownership is taken
    recursively first and access is regranted before anything is deleted.
    """

    for command in (
        ["takeown.exe", "/F", str(disposable), "/R", "/D", "Y"],
        [
            "icacls.exe",
            str(disposable),
            "/grant",
            f"*{_ADMINISTRATORS_SID}:(OI)(CI)F",
            "/T",
            "/C",
            "/Q",
        ],
    ):
        subprocess.run(command, check=False, capture_output=True, timeout=300)
    shutil.rmtree(disposable, ignore_errors=True)


@pytest.mark.skipif(os.name != "nt", reason="requires Windows PowerShell 5.1")
def test_elevated_acl_harness_parses_under_powershell_51() -> None:
    """The elevated harness must be syntactically valid without elevation.

    This keeps a syntax error in the production ACL routine from surfacing
    only at the owner's one-shot elevated checkpoint.
    """

    with tempfile.TemporaryDirectory(prefix="p6-acl-parse-") as raw:
        root = Path(raw)
        script = root / "harness.ps1"
        script.write_text(
            _harness(root / "provisioning", root / "provisioning" / "bundle", root / "r.json"),
            encoding="utf-8",
        )
        command = (
            "$tokens=$null;$errors=$null;"
            f"[Management.Automation.Language.Parser]::ParseFile('{script}',"
            "[ref]$tokens,[ref]$errors)|Out-Null;"
            "if($errors.Count){$errors|ForEach-Object{$_.Message};exit 1}"
        )
        result = subprocess.run(
            [str(WINDOWS_POWERSHELL), "-NoProfile", "-NonInteractive", "-Command", command],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.skipif(
    not _is_elevated(),
    reason="requires an elevated Windows shell (SeRestorePrivilege for S-1-5-19 owner)",
)
def test_production_acl_routine_hardens_a_disposable_tree() -> None:
    disposable = Path(tempfile.gettempdir()) / f"p6-acl-{uuid.uuid4().hex}"
    resolved = str(disposable)
    for forbidden in _FORBIDDEN_ROOTS:
        assert not os.path.normcase(resolved).startswith(
            os.path.normcase(forbidden.rstrip("\\")) + "\\"
        ), f"disposable root {resolved} falls inside {forbidden}"
    assert _is_fixed_local_ntfs(disposable), "disposable root must be fixed local NTFS"

    disposable.mkdir(parents=False, exist_ok=False)
    try:
        provisioning, bundle_root = _build_tree(disposable)
        report = disposable / "report.json"
        script = disposable / "harness.ps1"
        script.write_text(
            _harness(provisioning, bundle_root, report), encoding="utf-8"
        )
        result = subprocess.run(
            [
                str(WINDOWS_POWERSHELL),
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=600,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "ACL_ROUTINE_OK" in result.stdout
        observed = json.loads(report.read_text(encoding="utf-8-sig"))

        paths = [entry["path"] for entry in observed]
        assert paths[-1] == str(provisioning)
        assert paths[-2] == str(bundle_root)
        assert set(paths) == {
            str(provisioning),
            str(bundle_root),
            str(bundle_root / "deep"),
            str(bundle_root / "deep" / "payload"),
            str(bundle_root / "worker-bundle.json"),
        }

        for entry in observed:
            where = entry["path"]
            assert entry["owner"] == _OWNER_SID, where
            assert entry["protected"] is True, where
            assert entry["inheritedCount"] == 0, where
            aces = entry["aces"]
            report = _posture_report(where, aces)
            assert len(aces) == 6, report
            # Keyed by principal, never by position: DACL order is imposed by
            # Windows, not by the provisioner (see _EXPECTED_ACES above).  Every
            # content requirement is still asserted per principal below.
            observed_sids = [ace["sid"] for ace in aces]
            assert len(set(observed_sids)) == len(observed_sids), report
            assert set(observed_sids) == set(_EXPECTED_ACES), report
            for ace in aces:
                assert ace["kind"] == "Allow", report
                assert ace["mask"] == _EXPECTED_ACES[ace["sid"]], report
                assert ace["inherited"] is False, report
                assert ace["inheritance"] == "None", report
                assert ace["propagation"] == "None", report
    finally:
        _reclaim(disposable)

    assert not disposable.exists()
