from __future__ import annotations

from pathlib import Path, PureWindowsPath
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
READINESS = REPO_ROOT / "next_milestone_plans" / "sciencebase-live-readiness.md"
PILOT_RUNBOOK = REPO_ROOT / "SCIENCEBASE_PILOT_RUNBOOK.md"


def _preparation_block() -> str:
    text = READINESS.read_text(encoding="utf-8")
    blocks = re.findall(r"```powershell\n(.*?)\n```", text, flags=re.DOTALL)
    return next(block for block in blocks if "$PreparedRuntimeArgs" in block)


def _elevated_preparation_block() -> str:
    text = READINESS.read_text(encoding="utf-8")
    blocks = re.findall(r"```powershell\n(.*?)\n```", text, flags=re.DOTALL)
    return next(block for block in blocks if "initialize-dual-live -- reservation-store" in block)


def _w5_block() -> str:
    text = READINESS.read_text(encoding="utf-8")
    blocks = re.findall(r"```powershell\n(.*?)\n```", text, flags=re.DOTALL)
    return next(block for block in blocks if "$ExactSearchUrl" in block)


def test_documented_preparation_initializes_store_and_envelope_before_prepare() -> None:
    elevated = _elevated_preparation_block()
    rehydration = _preparation_block()

    store = elevated.index("-Action initialize-dual-live -- reservation-store")
    envelope = elevated.index("-Action initialize-dual-live -- authority-envelope")
    digest = elevated.index("$AuthorityEnvelopeDigest =")
    assert store < envelope < digest
    assert "$PreparedRuntimeArgs =" in rehydration
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
        "re-authenticates the GO nor measures containment."
    ) in text
    assert "`boundary_assurance=owner_waived_unproven`" in text
    assert "R5 remains OPEN; this is disclosure, not control." in text


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
        "$MatchingItems.Count -ne 1",
        "$SearchMembership -cne $BaselineSearchMembership",
        "$Hydrate.files",
        "$Hydrate.id -cne $ExactItemId",
        "$ExactFileName",
        "$MatchingFiles.Count -ne 1",
        ".downloadUri",
        ".url",
        "$DerivedDownloadUrl",
        "$DerivedDownloadUrl -cne $BaselineDownloadUrl",
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


def test_w5_download_applies_production_content_contract_before_recording() -> None:
    block = _w5_block()

    download = block.index("$DownloadRecord = Invoke-W5Stage")
    contract = block.index("pathlib.Path(sys.argv[1]).read_bytes()")
    failure = block.index("W5 download content contract HOLD")
    record = block.index("$ObservationRecords.Add($SearchRecord)")
    assert download < contract < failure < record
    for token in (
        "not t or t.startswith(('<','{','['))",
        "len(lines)>=2",
        "lines[0]==header",
        "all(line.count(',')+1==13 for line in lines[1:])",
    ):
        assert token in block


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
        "fresh single-segment worker root, worker binding, profile binding, and moniker",
        "at most five owner-budgeted elevated W6-PRE attempts",
        "W7 and template emission are non-elevated",
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


def test_w6_pre_secures_campaign_root_before_worker_and_initializers() -> None:
    block = _elevated_preparation_block()

    create = block.index("$CampaignRootSecurity.SetSecurityDescriptorSddlForm")
    verify = block.index("backend.secure(handle) != (True, True, True)")
    worker = block.index("provision-dual-live-worker.ps1")
    initialize = block.index("initialize-dual-live -- reservation-store")
    assert create < verify < worker < initialize
    for token in ("D:P(A;;FA;;;", "(A;;FA;;;SY)", "open_existing_directory"):
        assert token in block


def test_w6_pre_keeps_binding_parent_outside_campaign_root() -> None:
    block = _elevated_preparation_block()
    text = READINESS.read_text(encoding="utf-8")
    campaign_match = re.search(r"^\$CanonicalRoot = '([^']+)'$", block, flags=re.MULTILINE)
    binding_match = re.search(r"^\$BindingParent = '([^']+)'$", block, flags=re.MULTILINE)

    assert campaign_match is not None
    assert binding_match is not None
    campaign_parts = tuple(part.casefold() for part in PureWindowsPath(campaign_match.group(1)).parts)
    binding_parts = tuple(part.casefold() for part in PureWindowsPath(binding_match.group(1)).parts)

    assert campaign_parts[: len(binding_parts)] != binding_parts
    assert binding_parts[: len(campaign_parts)] != campaign_parts
    assert (
        "output-binding parent under `C:\\owner-controlled\\project6-bindings` and the dedicated "
        "campaign root under `C:\\owner-controlled\\project6`"
    ) in text

    # Retries past the first take an attempt-scoped binding parent so retained
    # failed-attempt binding state is never reused; it must satisfy the same
    # containment rule as the base parent and must not collide with it.
    scoped_match = re.search(r'^  \$BindingParent = "([^"]+)"$', block, flags=re.MULTILINE)
    assert scoped_match is not None
    assert (
        "$BindingParent = 'C:\\owner-controlled\\project6-bindings'\n"
        "if ($W6PreAttempt -gt 1) {\n"
        '  $BindingParent = "C:\\owner-controlled\\project6-bindings-$W6PreAttempt"\n'
        "}\n"
    ) in block
    scoped_parts = tuple(
        part.casefold()
        for part in PureWindowsPath(scoped_match.group(1).replace("$W6PreAttempt", "3")).parts
    )

    assert campaign_parts[: len(scoped_parts)] != scoped_parts
    assert scoped_parts[: len(campaign_parts)] != campaign_parts
    assert scoped_parts != binding_parts
    assert binding_parts[: len(scoped_parts)] != scoped_parts
    assert scoped_parts[: len(binding_parts)] != binding_parts
    assert "attempt-scoped binding parent" in text


def test_elevated_preparation_stops_before_non_elevated_rehydration() -> None:
    elevated = _elevated_preparation_block()
    rehydration = _preparation_block()

    assert elevated != rehydration
    assert "--emit-owner-go-template" not in elevated
    assert "--emit-owner-go-template" in rehydration
    assert "provision-dual-live-profile.ps1" not in rehydration
    assert "provision-dual-live-worker.ps1" not in rehydration
    assert "initialize-dual-live" not in rehydration
    for token in (
        "$ConnectorRunId = '<PHASE-1-RECORD connector run UUID>'",
        "$AttemptNonce = '<PHASE-1-RECORD attempt nonce>'",
        "$ProfileMoniker = '<PHASE-1-RECORD profile moniker>'",
        "$ProfileBinding = '<PHASE-1-RECORD profile binding path>'",
        "$WorkerBinding = '<PHASE-1-RECORD worker binding path>'",
        "$WorkerBundleRoot = '<PHASE-1-RECORD worker bundle root>'",
        "$WorkerProvisioningRoot = '<PHASE-1-RECORD worker provisioning root>'",
        "$AuthorityEnvelope = '<PHASE-1-RECORD authority envelope path>'",
        "$AuthorityEnvelopeDigest = '<PHASE-1-RECORD authority envelope digest>'",
        "$InterpreterIdentity = '<PHASE-1-RECORD interpreter identity>'",
        "$AmbientInterpreterRoot = '<PHASE-1-RECORD ambient interpreter root>'",
        "$PreparedRuntimeArgs = @(",
    ):
        assert token in rehydration
    assert "B2 authorization label:" in rehydration
    assert "B2 grant label:" in rehydration


def test_readiness_requires_exact_clean_reviewed_source_and_owner_fill_ids() -> None:
    text = READINESS.read_text(encoding="utf-8")
    elevated = _elevated_preparation_block()
    rehydration = _preparation_block()

    assert "`codex/sb-live-impl`" in text
    assert "$ExpectedSourceCommit = '<OWNER-FILL reviewed head>'" in elevated
    assert "$ExpectedSourceCommit = '<PHASE-1-RECORD source commit>'" in rehydration
    for block in (elevated, rehydration):
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
    assert elevated.count("<OWNER-FILL fresh UUID>") == 1
    assert rehydration.count("<OWNER-FILL fresh UUID>") == 1
    assert "$ConnectorRunId -like '<OWNER-FILL*'" in elevated
    assert "$GoId -like '<OWNER-FILL*'" in rehydration


def test_pilot_runbook_disambiguates_without_supersession() -> None:
    text = PILOT_RUNBOOK.read_text(encoding="utf-8")

    assert "in-process public connector API pilot" in text
    assert "signed-GO readiness procedure" in text
    assert "next_milestone_plans/sciencebase-live-readiness.md" in text
    assert "Neither document supersedes the other." in text
