"""Ordering law for the worker-bundle ACL hardening pass.

The provisioner strips inheritance and rewrites the DACL of the provisioning
root, the bundle root, and every bundle descendant.  Applying a protected,
inheritance-free DACL to an ancestor before its descendants have their own
explicit DACLs removes the inherited access the still-unsecured descendants
depend on, so the very next ``Get-Acl``/``icacls`` on a child fails with
"Access is denied" and the run aborts at ``worker_bundle_acl_failed``.

These tests pin the inverse ordering law -- every target is processed strictly
before any of its ancestors -- by evaluating the *production* materialization
text against a synthetic tree.  No ACL is mutated and no elevation is needed.
"""

import os
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

# The materialization region is bounded by two anchors that exist both before
# and after the fix, so the extraction is not tuned to the repaired text.
_PRIVILEGE_ANCHOR = "\nEnable-RestorePrivilege\n"
_APPLY_ANCHOR = "\nforeach ($target in $aclTargets) {"

_BUNDLE_ENTRIES = (
    "worker-bundle.json",
    "tools/dual_live_run.py",
    "backend/app/__init__.py",
    "backend/app/services/dual_live_worker_bundle.py",
)


def _materialization(source: str) -> str:
    """Return the production text that builds ``$aclTargets``."""

    start = source.index(_PRIVILEGE_ANCHOR) + len(_PRIVILEGE_ANCHOR)
    return source[start : source.index(_APPLY_ANCHOR, start)]


def _is_strict_ancestor(candidate: str, descendant: str) -> bool:
    parent = os.path.normcase(candidate.rstrip("\\")) + "\\"
    child = os.path.normcase(descendant.rstrip("\\"))
    return child.startswith(parent)


def _build_tree(root: Path) -> tuple[Path, Path, set[str]]:
    provisioning = root / "provisioning"
    bundle_root = provisioning / "sha256-deadbeef"
    expected = {str(provisioning), str(bundle_root)}
    for relative in _BUNDLE_ENTRIES:
        target = bundle_root.joinpath(*relative.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("payload\n", encoding="ascii")
        current = target
        while current != bundle_root:
            expected.add(str(current))
            current = current.parent
    return provisioning, bundle_root, expected


def _evaluate_order(source: str, root: Path) -> list[str]:
    provisioning, bundle_root, _ = _build_tree(root)
    harness = root / "materialize.ps1"
    harness.write_text(
        "Set-StrictMode -Version Latest\n"
        "$ErrorActionPreference = 'Stop'\n"
        f"$provisioning = '{provisioning}'\n"
        f"$bundleRoot = '{bundle_root}'\n"
        f"{_materialization(source)}\n"
        "foreach ($target in $aclTargets) { Write-Output $target }\n",
        encoding="ascii",
    )
    result = subprocess.run(
        [
            str(WINDOWS_POWERSHELL),
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(harness),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


@pytest.mark.skipif(os.name != "nt", reason="requires Windows PowerShell 5.1")
def test_worker_bundle_acl_targets_are_ordered_descendant_before_ancestor() -> None:
    source = PROVISIONER.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix=f"p6-acl-order-{uuid.uuid4().hex}-") as raw:
        root = Path(raw)
        targets = _evaluate_order(source, root)
        provisioning, bundle_root, expected = _build_tree(root)

    assert targets, "materialization produced no ACL targets"
    assert len(targets) == len(set(targets)), "ACL targets contain duplicates"
    # Completeness: the repair must not narrow the hardened surface.
    assert set(targets) == expected

    for index, ancestor in enumerate(targets):
        for descendant in targets[index + 1 :]:
            assert not _is_strict_ancestor(ancestor, descendant), (
                f"{ancestor} is processed before its descendant {descendant}; "
                "parent-first stripping removes the inherited access the "
                "unsecured descendant still needs"
            )

    # The two roots are the last things hardened, provisioning root last of all.
    assert targets[-1] == str(provisioning)
    assert targets[-2] == str(bundle_root)


def test_worker_bundle_acl_targets_are_materialized_before_any_mutation() -> None:
    """The whole target list must be captured before the first ACL change."""

    materialization = _materialization(PROVISIONER.read_text(encoding="utf-8"))

    assert "$aclTargets =" in materialization
    for mutation in ("Set-Acl", "icacls.exe", "SetOwner"):
        assert mutation not in materialization, (
            f"{mutation} runs while the target list is still being built; "
            "enumeration must complete before any descriptor is rewritten"
        )
