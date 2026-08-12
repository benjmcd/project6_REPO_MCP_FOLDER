from __future__ import annotations

from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
READINESS = REPO_ROOT / "next_milestone_plans" / "sciencebase-live-readiness.md"


def _preparation_block() -> str:
    text = READINESS.read_text(encoding="utf-8")
    blocks = re.findall(r"```powershell\n(.*?)\n```", text, flags=re.DOTALL)
    return next(block for block in blocks if "$PreparedRuntimeArgs" in block)


def test_documented_preparation_initializes_store_and_envelope_before_prepare() -> None:
    block = _preparation_block()

    store = block.index("-Action initialize-dual-live -- reservation-store")
    envelope = block.index("-Action initialize-dual-live -- authority-envelope")
    digest = block.index("$AuthorityEnvelopeDigest =")
    prepare = block.index("$PreparedRuntimeArgs =")
    assert store < envelope < digest < prepare
    assert "retired:sciencebase-live-v2" in READINESS.read_text(encoding="utf-8")


def test_documented_prepared_runtime_argv_uses_only_defined_variables() -> None:
    block = _preparation_block()
    assignments = set(re.findall(r"^\$(\w+)\s*=", block, flags=re.MULTILINE))
    argv = block[block.index("$PreparedRuntimeArgs =") : block.index("\n)", block.index("$PreparedRuntimeArgs ="))]
    references = set(re.findall(r"\$(\w+)", argv)) - {"PreparedRuntimeArgs"}

    assert references <= assignments
    for flag in (
        "--authority-envelope",
        "--authority-envelope-sha256",
        "--campaign-id",
        "--canonical-root",
        "--connector-run-id",
        "--reservation-database",
        "--worker-bundle-root",
        "--worker-provisioning-root",
        "--worker-profile-moniker",
        "--worker-manifest-sha256",
        "--worker-entrypoint",
        "--worker-interpreter",
        "--worker-python-version",
        "--worker-architecture",
        "--worker-package-sid",
        "--worker-owner-sid",
        "--worker-provisioner-sid",
        "--worker-broker-sid",
        "--ambient-interpreter-root",
        "--campaign-root",
        "--appcontainer-profile-root",
        "--broker-profile-root",
        "--user-data-root",
    ):
        assert flag in argv
    assert "$WorkerProfileMoniker = $Worker.profile_moniker" in block
    assert "$WorkerProfileMoniker -ne $ProfileMoniker" in block


def test_readiness_distinguishes_retired_sentinel_from_opaque_references() -> None:
    text = READINESS.read_text(encoding="utf-8")

    assert "wrapper_start_token_ref=retired:sciencebase-live-v2" in text
    assert "two opaque authority/grant references" in text
    assert "three opaque authority/grant/token references" not in text

