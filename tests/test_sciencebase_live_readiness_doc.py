from __future__ import annotations

from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
READINESS = REPO_ROOT / "next_milestone_plans" / "sciencebase-live-readiness.md"
PILOT_RUNBOOK = REPO_ROOT / "SCIENCEBASE_PILOT_RUNBOOK.md"


def _preparation_block() -> str:
    text = READINESS.read_text(encoding="utf-8")
    blocks = re.findall(r"```powershell\n(.*?)\n```", text, flags=re.DOTALL)
    return next(block for block in blocks if "$PreparedRuntimeArgs" in block)


def _w5_block() -> str:
    text = READINESS.read_text(encoding="utf-8")
    blocks = re.findall(r"```powershell\n(.*?)\n```", text, flags=re.DOTALL)
    return next(block for block in blocks if "$ExactSearchUrl" in block)


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
        "--query",
        "--expected-item-id",
        "--expected-file-name",
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


def test_w5_validates_exact_sciencebase_authority_before_direct_curl() -> None:
    block = _w5_block()

    validation = block.index("foreach ($Stage in $StageUrls)")
    attempts = block.index("foreach ($Attempt in 1..3)")
    assert validation < attempts
    for token in (
        "[uri]::TryCreate",
        "$ParsedUrl.Scheme -cne 'https'",
        "$ParsedUrl.DnsSafeHost -ine 'www.sciencebase.gov'",
        "-not $ParsedUrl.IsDefaultPort",
        "$ParsedUrl.Port -ne 443",
        "$ParsedUrl.UserInfo.Length -ne 0",
        "$RawUrl.Contains('@')",
        "$ParsedUrl.Fragment.Length -ne 0",
        "curl.exe --disable",
        "--proto '=https'",
        "--noproxy '*'",
        "--globoff",
        "--max-redirs 0",
    ):
        assert token in block


def test_closeout_discloses_local_consistency_and_containment_limit() -> None:
    text = READINESS.read_text(encoding="utf-8")

    assert (
        "`--verify-closeout` checks internal consistency; it neither "
        "re-authenticates the GO nor measures containment. R5 remains OPEN; "
        "this is disclosure, not control."
    ) in text


def test_w5_uses_saved_exact_chain_bytes_and_runtime_membership() -> None:
    block = _w5_block()

    for token in (
        "$SearchBody",
        "$SearchHeaders",
        "$HydrateBody",
        "$HydrateHeaders",
        "$DownloadBody",
        "$DownloadHeaders",
        "Assert-NoDuplicateJsonKeys",
        "$Search.items",
        "$ExactItemId",
        "$Hydrate.files",
        "$Hydrate.id -cne $ExactItemId",
        "$ExactFileName",
        ".downloadUri",
        ".url",
        "$DerivedDownloadUrl",
        "$ExactDownloadUrl -cne $DerivedDownloadUrl",
        "$BaselineSearchMembership",
        "$BaselineDownloadUrl",
    ):
        assert token in block
    assert "--output NUL" not in block
    assert "--dump-header -" not in block
    assert "max=" not in block
    assert "offset=" not in block
    assert "sort=" not in block
    assert "@($Hydrate.files).Count -ne 1" not in block
    required_inputs = block[block.index("if (@(") : block.index("$StageUrls = @(")]
    assert "$ExactDownloadUrl" not in required_inputs
    initial_stages = block[
        block.index("$StageUrls = @(") : block.index("function Test-PathInside")
    ]
    assert "$ExactDownloadUrl" not in initial_stages
    derive = block.index("$DerivedDownloadUrl =")
    download = block.index("Invoke-W5Stage $Attempt 'download' $DerivedDownloadUrl")
    assert derive < download


def test_w5_records_cleans_and_invalidates_observation_set() -> None:
    block = _w5_block()

    for token in (
        "$ScienceBaseInactivitySeconds = 30",
        "$ConnectTimeoutSeconds = $ScienceBaseInactivitySeconds",
        "$MaxTimeSeconds = $ExactChainStageCount * $ScienceBaseInactivitySeconds",
        "--connect-timeout $ConnectTimeoutSeconds",
        "--max-time $MaxTimeSeconds",
        "BodySha256",
        "BodyBytes",
        "HttpStatus",
        "DerivedDownloadUri",
        "$ObservationSetValid = $false",
        "$ObservationRecords.Clear()",
        "three fresh complete attempts in the same sitting",
        "finally",
        "Remove-Item -LiteralPath $RawPath -Force",
        "$ConvertFromJsonRejectsDuplicates",
    ):
        assert token in block


def test_readiness_uses_single_segment_fresh_attempt_topology_and_exact_py312_interpreter() -> None:
    text = READINESS.read_text(encoding="utf-8")

    for token in (
        "$WorkerProvisioningRoot = 'C:\\p6-sciencebase-worker'",
        "$Py = (& py -3.12 -c \"import sys; print(sys.executable)\").Trim()",
        "$AmbientInterpreterRoot = Split-Path -Parent $Py",
        "$AmbientInterpreterSha256 -cne $WorkerInterpreterSha256",
        "fresh single-segment root, worker binding, profile binding, and moniker",
        "at most five owner-budgeted elevated W6-PRE attempts",
        "W7 is non-elevated",
        "git cat-file blob",
        "worker_source_copy_failed",
        "explicitly treats any stderr as `worker_source_copy_failed`, even when Git exits 0",
        "8 worker files",
        "2>$null",
        "$ErrorActionPreference = 'Stop'",
        "NativeCommandError",
        "verify locally before the sitting",
        "stderr-silent `git` on PATH is a hard prerequisite",
    ):
        assert token in text
    assert "C:\\ProgramData\\Project6\\sciencebase-worker" not in text
    assert "Get-Command python.exe" not in text


def test_readiness_requires_exact_clean_reviewed_source_and_owner_fill_ids() -> None:
    text = READINESS.read_text(encoding="utf-8")
    block = _preparation_block()

    assert "`codex/sb-live-impl`" in text
    assert "$ExpectedSourceCommit = '<OWNER-FILL reviewed head>'" in block
    assert "git branch --show-current" in block
    assert "git status --porcelain=v1 --untracked-files=all" in block
    assert "git rev-parse HEAD" in block
    for token in (
        "$BranchExit = $LASTEXITCODE",
        "$StatusExit = $LASTEXITCODE",
        "$CommitExit = $LASTEXITCODE",
        "$BranchExit -ne 0",
        "$StatusExit -ne 0",
        "$CommitExit -ne 0",
    ):
        assert token in block
    assert "$SourceCommit -cne $ExpectedSourceCommit" in block
    assert block.count("<OWNER-FILL fresh UUID>") == 2
    assert "$ConnectorRunId -like '<OWNER-FILL*'" in block
    assert "$GoId -like '<OWNER-FILL*'" in block


def test_pilot_runbook_disambiguates_without_supersession() -> None:
    text = PILOT_RUNBOOK.read_text(encoding="utf-8")

    assert "in-process public connector API pilot" in text
    assert "signed-GO readiness procedure" in text
    assert "next_milestone_plans/sciencebase-live-readiness.md" in text
    assert "Neither document supersedes the other." in text
