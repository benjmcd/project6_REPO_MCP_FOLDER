from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest


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
    return next(block for block in blocks if "Python binding gate call 2 of 6" in block)


def _ordinary_preflight_block() -> str:
    text = READINESS.read_text(encoding="utf-8")
    blocks = re.findall(r"```powershell\n(.*?)\n```", text, flags=re.DOTALL)
    return next(block for block in blocks if "Python binding gate call 1 of 6" in block)


def _live_block() -> str:
    text = READINESS.read_text(encoding="utf-8")
    blocks = re.findall(r"```powershell\n(.*?)\n```", text, flags=re.DOTALL)
    return next(block for block in blocks if "Python binding gate call 5 of 6" in block)


def _closeout_block() -> str:
    text = READINESS.read_text(encoding="utf-8")
    blocks = re.findall(r"```powershell\n(.*?)\n```", text, flags=re.DOTALL)
    return next(block for block in blocks if "Python binding gate call 6 of 6" in block)


def _custody_helper_block() -> str:
    text = READINESS.read_text(encoding="utf-8")
    blocks = re.findall(r"```powershell\n(.*?)\n```", text, flags=re.DOTALL)
    return next(block for block in blocks if "# R3 atomic custody helper" in block)


def _disposition_helper_block() -> str:
    text = READINESS.read_text(encoding="utf-8")
    blocks = re.findall(r"```powershell\n(.*?)\n```", text, flags=re.DOTALL)
    return next(block for block in blocks if "# R3 Attempt-4 disposition helper" in block)


def _w5_block() -> str:
    text = READINESS.read_text(encoding="utf-8")
    blocks = re.findall(r"```powershell\n(.*?)\n```", text, flags=re.DOTALL)
    return next(block for block in blocks if "$ExactSearchUrl" in block)


def test_documented_preparation_initializes_store_and_envelope_before_prepare() -> None:
    elevated = _elevated_preparation_block()
    rehydration = _preparation_block()

    store = elevated.index("& $Py $InitializeTool @ReservationInitializerArgs")
    envelope = elevated.index("& $Py $InitializeTool @AuthorityInitializerArgs")
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
    assert "$ConnectorRunId = [string]$Phase1bRecord[0].ConnectorRunId" in block


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


def test_readiness_uses_separate_attempt_families_and_frozen_python_binding() -> None:
    text = READINESS.read_text(encoding="utf-8")

    for token in (
        "C:\\owner-controlled\\project6-attempt-4",
        "C:\\owner-controlled\\project6-attempt-5",
        "C:\\owner-controlled\\project6-attempt-4\\sciencebase-campaign",
        "C:\\owner-controlled\\project6-attempt-5\\sciencebase-campaign",
        "C:\\owner-controlled\\project6-bindings-4",
        "C:\\owner-controlled\\project6-bindings-5",
        "C:\\owner-controlled\\project6-w5obs-4",
        "C:\\owner-controlled\\project6-w5obs-5",
        "C:\\p6-sciencebase-worker-4",
        "C:\\p6-sciencebase-worker-5",
        "python-3.12.10-embed-amd64.zip",
        "$Py = [string]$PythonBinding.ambient_interpreter",
        "$AmbientInterpreterSha256 -cne $WorkerInterpreterSha256",
        "Attempt 5 remains absent until separately authorized",
        "git cat-file blob",
        "worker_source_copy_failed",
        "explicitly treats any stderr as `worker_source_copy_failed`, even when Git exits 0",
        "8 worker files",
        "2>$null",
        "$ErrorActionPreference = 'Stop'",
        "NativeCommandError",
        "verify locally before the sitting",
        "stderr-silent `git` on PATH is a hard prerequisite",
        "$RetainedAttempt3InterpreterBytes = 103704",
        "$RetainedAttempt3InterpreterSha256 = '737a7e3b71e3578f8432acc7dd88c452e593622c544bc13da4789d69c63da5ae'",
        "RETAINED_ATTEMPT3_WORKER_SHA256=",
    ):
        assert token in text
    assert "C:\\ProgramData\\Project6\\sciencebase-worker" not in text
    assert "Get-Command python.exe" not in text
    assert "$Py = (& py" not in text
    assert "py -3.12" not in text
    assert "py -V:PythonCore/3.12" not in text
    assert "$PythonLauncherTag" not in text
    assert "-PythonVersion" not in text
    assert (
        "$RetainedWorkerSha256 -cne [string]$PythonBinding.expected_worker_sha256"
        not in text
    )


def test_retained_attempt3_uses_full_production_validator_plus_direct_hash() -> None:
    block = _ordinary_preflight_block()

    binding = block.index("$env:PROJECT6_B0_BUNDLE_BINDING = $Attempt3WorkerBinding")
    validator = block.index(
        "& $Py -m pytest .\\tests\\test_dual_live_worker_bundle.py::"
        "test_windows_probe_validates_preprovisioned_fixture -q"
    )
    restore = block.index(
        "$env:PROJECT6_B0_BUNDLE_BINDING = $PriorAttempt3BundleBinding",
        validator,
    )
    direct_hash = block.index("RETAINED_ATTEMPT3_WORKER_SHA256=", restore)
    assert binding < validator < restore < direct_hash
    assert "$RetainedExpectedAcl" not in block
    assert "$RetainedManifestSha256" not in block


def test_w6_pre_secures_campaign_root_before_worker_and_initializers() -> None:
    block = _elevated_preparation_block()
    helper = _custody_helper_block()

    parent = block.index("New-CustodyDirectoryOnce -Path $CustodyParent")
    campaign = block.index("New-CustodyDirectoryOnce -Path $CanonicalRoot")
    binding = block.index("New-CustodyDirectoryOnce -Path $BindingParent")
    verify = block.index("Assert-CustodyDirectory -Path $CanonicalRoot")
    worker = block.index("provision-dual-live-worker.ps1")
    initialize = block.index("& $Py $InitializeTool @ReservationInitializerArgs")
    assert parent < campaign < binding < verify < worker < initialize
    for token in (
        "CreateDirectoryW",
        "SECURITY_ATTRIBUTES",
        "ERROR_ALREADY_EXISTS",
        "D:P(A;OICI;FA;;;",
        "D:P(A;;FA;;;",
        "(A;;FA;;;SY)",
    ):
        assert token in block or token in helper


def test_w6_pre_keeps_binding_parent_outside_campaign_root() -> None:
    block = _elevated_preparation_block()
    text = READINESS.read_text(encoding="utf-8")
    assert "$CustodyParent = 'C:\\owner-controlled\\project6-attempt-4'" in block
    assert "$CanonicalRoot = Join-Path $CustodyParent 'sciencebase-campaign'" in block
    assert "$BindingParent = 'C:\\owner-controlled\\project6-bindings-4'" in block
    assert "Bindings, W5 scratch, and worker roots remain outside both custody families." in text


def test_elevated_preparation_stops_before_non_elevated_rehydration() -> None:
    elevated = _elevated_preparation_block()
    rehydration = _preparation_block()

    assert elevated != rehydration
    assert "--emit-owner-go-template" not in elevated
    assert "--emit-owner-go-template" in rehydration
    assert "provision-dual-live-profile.ps1" not in rehydration
    assert "provision-dual-live-worker.ps1" not in rehydration
    assert "$InitializeTool" not in rehydration
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
    assert '"PHASE1_RECORD=" + ($Phase1Record | ConvertTo-Json -Compress -Depth 4)' in elevated
    assert "| Format-List" not in elevated


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


def test_r3_has_exactly_six_gates_and_five_governed_python_tool_calls() -> None:
    text = READINESS.read_text(encoding="utf-8")

    for call in range(1, 7):
        assert text.count(f"Python binding gate call {call} of 6") == 1
    assert text.count("Python binding gate call ") == 6
    assert text.count("status -cne 'PYTHON_BINDING_OK'") == 6
    assert text.count("$Py = [string]$PythonBinding.ambient_interpreter") == 6

    for call in range(1, 6):
        assert text.count(f"Governed Python tool call {call} of 5") == 1
    assert text.count("Governed Python tool call ") == 5
    assert text.count("& $Py $InitializeTool") == 2
    assert text.count("& $Py $RunTool") == 2
    assert text.count("-Mode LiveRuntime -CurrentRoot $CanonicalRoot -Py $Py -PyArgumentList $LiveArgs") == 1
    assert ".\\project6.ps1 -Action" not in text


def test_r3_guards_each_action_and_fixes_phase_dispositions() -> None:
    text = READINESS.read_text(encoding="utf-8")
    preflight = _ordinary_preflight_block()
    elevated = _elevated_preparation_block()
    phase1b = _preparation_block()
    live = _live_block()
    closeout = _closeout_block()

    assert "-Mode NonRuntime -Action" in preflight
    assert "-Mode NonRuntime -Action" in elevated
    assert "-Mode NonRuntime -Action" in phase1b
    assert "-Mode LiveRuntime -CurrentRoot $CanonicalRoot -Py $Py -PyArgumentList $LiveArgs" in live
    assert "-Action" not in live
    assert "-Mode NonRuntime -Action" in closeout

    for token in (
        "calls 1-2 are `PRE-SITTING HOLD`",
        "call 3 is `PRE-BEGIN HOLD`",
        "call 4 is terminal `ATTEMPT HOLD`",
        "call 5 is terminal `SIGNED-AUTHORITY HOLD`",
        "call 6 is `POST-LIVE CLOSEOUT HOLD`",
    ):
        assert token in text


def test_call4_guard_contains_only_the_explicit_pytest_and_w5_auxiliary_allowlist() -> None:
    block = _preparation_block()

    gate = block.index("Python binding gate call 4 of 6")
    bundle_env = block.index("$env:PROJECT6_B0_BUNDLE_BINDING = $WorkerBinding")
    fixture = block.index(
        "& $Py -m pytest .\\tests\\test_dual_live_worker_bundle.py::"
        "test_windows_probe_validates_preprovisioned_fixture -q"
    )
    rehearsal = block.index(
        "& $Py -m pytest .\\tests\\test_sciencebase_no_signature_rehearsal.py -q -s"
    )
    w5 = block.index("Invoke-W5Observation -Py $Py")
    template = block.index("& $Py $RunTool @TemplateArgs")
    restore = block.index(
        "$env:PROJECT6_B0_BUNDLE_BINDING = $PriorBundleBinding", template
    )
    assert gate < bundle_env < fixture < rehearsal < w5 < template < restore
    assert "py -3.12" not in block
    assert "project6.ps1" not in block


def test_atomic_custody_stage_sets_and_post_provision_broker_acl_proof_are_explicit() -> None:
    text = READINESS.read_text(encoding="utf-8")
    block = _elevated_preparation_block()

    for token in (
        "$ExpectedOwnerSid = '<OWNER-FILL frozen owner SID>'",
        "WindowsIdentity]::GetCurrent().User.Value",
        "New-CustodyDirectoryOnce -Path $CustodyParent",
        "New-CustodyDirectoryOnce -Path $CanonicalRoot",
        "New-CustodyDirectoryOnce -Path $BindingParent",
        "Assert-ExactChildSet -Path $CustodyParent -Expected @('sciencebase-campaign')",
        "Assert-ExactChildSet -Path $CanonicalRoot -Expected @()",
        "Assert-ExactChildSet -Path $BindingParent -Expected @()",
        "Assert-ExactChildSet -Path $BindingParent -Expected @($ProfileLeaf)",
        "Assert-ExactChildSet -Path $BindingParent -Expected @($ProfileLeaf, $WorkerLeaf)",
        "[string]$Profile.broker_sid -cne $CurrentSid",
        "[string]$Worker.broker_sid -cne $CurrentSid",
        "$ObservedWorkerAces.Count -ne 6",
        "$SeenWorkerSids.Count -ne 6",
        "0x001200A9",
        "terminal ATTEMPT HOLD",
    ):
        assert token in block or token in text
    assert "rerunning the step is idempotent" not in text
    assert "ERROR_ALREADY_EXISTS" in _custody_helper_block()


@pytest.mark.skipif(os.name != "nt", reason="requires Windows PowerShell 5.1 ACL semantics")
def test_documented_atomic_custody_helper_executes_without_create_then_harden(
    tmp_path: Path,
) -> None:
    text = READINESS.read_text(encoding="utf-8")
    assert "# R3 atomic custody helper" in text
    helper = _custody_helper_block()
    for forbidden in ("New-Item", "Set-Acl", "[IO.Directory]::CreateDirectory"):
        assert forbidden not in helper

    proof = helper + r'''
$ExpectedOwnerSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$Base = [IO.Path]::GetFullPath($env:P6_CUSTODY_TEST_ROOT)
$Parent = Join-Path $Base 'attempt-4'
$Campaign = Join-Path $Parent 'sciencebase-campaign'
$Binding = Join-Path $Base 'bindings-4'
$ParentSddl = "O:$ExpectedOwnerSid" + "D:P(A;OICI;FA;;;$ExpectedOwnerSid)(A;OICI;FA;;;SY)"
$CampaignSddl = "O:$ExpectedOwnerSid" + "D:P(A;;FA;;;$ExpectedOwnerSid)(A;;FA;;;SY)"

New-CustodyDirectoryOnce -Path $Parent -Sddl $ParentSddl
New-CustodyDirectoryOnce -Path $Campaign -Sddl $CampaignSddl
New-CustodyDirectoryOnce -Path $Binding -Sddl $ParentSddl
Assert-CustodyDirectory -Path $Parent -Inheritable $true
Assert-CustodyDirectory -Path $Campaign -Inheritable $false
Assert-CustodyDirectory -Path $Binding -Inheritable $true
Assert-ExactChildSet -Path $Parent -Expected @('sciencebase-campaign')
Assert-ExactChildSet -Path $Campaign -Expected @()
Assert-ExactChildSet -Path $Binding -Expected @()

$ProfileLeaf = 'sciencebase-profile-test.json'
$WorkerLeaf = 'sciencebase-worker-test.json'
[IO.File]::WriteAllBytes((Join-Path $Binding $ProfileLeaf), [byte[]]@(1))
Assert-ExactChildSet -Path $Binding -Expected @($ProfileLeaf)
[IO.File]::WriteAllBytes((Join-Path $Binding $WorkerLeaf), [byte[]]@(2))
Assert-ExactChildSet -Path $Binding -Expected @($ProfileLeaf, $WorkerLeaf)

$CallbackEntered = $false
try {
  New-CustodyDirectoryOnce -Path $Parent -Sddl $ParentSddl
  $CallbackEntered = $true
  throw 'collision did not fail closed'
} catch {
  if ($_.Exception.Message -notlike '*already exists*') { throw }
}
if ($CallbackEntered) { throw 'callback entered after existing-path collision' }
'ATOMIC_CUSTODY_PROOF_OK'
'''
    test_env = os.environ.copy()
    test_env["P6_CUSTODY_TEST_ROOT"] = str(tmp_path)
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            proof,
        ],
        check=False,
        capture_output=True,
        env=test_env,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ATOMIC_CUSTODY_PROOF_OK" in result.stdout


@pytest.mark.skipif(os.name != "nt", reason="requires Windows PowerShell 5.1 parser")
def test_all_documented_powershell_blocks_parse_under_ps51() -> None:
    text = READINESS.read_text(encoding="utf-8")
    blocks = re.findall(r"```powershell\n(.*?)\n```", text, flags=re.DOTALL)
    parser = r'''
$Tokens = $null
$Errors = $null
[Management.Automation.Language.Parser]::ParseInput(
  [Console]::In.ReadToEnd(),
  [ref]$Tokens,
  [ref]$Errors
) | Out-Null
if ($Errors.Count -ne 0) {
  $Errors | ForEach-Object { [Console]::Error.WriteLine($_.Message) }
  exit 1
}
'''
    assert blocks
    for index, block in enumerate(blocks, start=1):
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                parser,
            ],
            check=False,
            capture_output=True,
            input=block,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"PowerShell block {index}: {result.stderr}"


def test_programdata_owner_and_attempt4_disposition_record_are_narrow() -> None:
    text = READINESS.read_text(encoding="utf-8")

    for token in (
        "Reservation and authority initializers do not touch `C:\\ProgramData\\Project6\\Authority`",
        "`OneUseLiveGoConsumer` first reaches it during GO consumption through `SpentMarkerStore`",
        "securely creates missing managed directories",
        "`SpentMarkerStore.claim_exact` byte-for-byte unchanged",
        "existing ABSENT/secure-create-new behavior",
        "attempt = 4",
        "phase_flags = $PhaseFlags",
        "disposition = $AttemptDisposition",
        "source_head = $SourceCommit",
        "exactly one four-field Attempt-4 disposition line",
    ):
        assert token in text
    assert "provisioner remains the sole worker-root and ProgramData ACL mechanism" not in text
    assert "Attempt-5 activation" in text
    assert "remains separately owner-gated and absent" in text


def test_attempt4_disposition_is_branch_complete_and_verified_after_guard_release() -> None:
    text = READINESS.read_text(encoding="utf-8")
    phase1b = _preparation_block()
    live = _live_block()
    closeout = _closeout_block()

    for token in (
        "$ElevatedState = [pscustomobject]@{ CustodyBegun = $false; Phase1Begun = $false }",
        "$ElevatedState.CustodyBegun = $true",
        "$ElevatedState.Phase1Begun = $true",
        "ATTEMPT4_TERMINAL_HANDOFF=",
        "Complete-Attempt4Disposition $EarlyDisposition",
        "Signing declined or failed; the unsigned/signed bytes are preserved.",
        "Complete-Attempt4Disposition 'ATTEMPT HOLD'",
    ):
        assert token in text

    call4 = phase1b.index("& $FamilyGuard -Mode NonRuntime -Action")
    call4_returned = phase1b.index("$Phase1bGuardReturned = $true")
    call4_complete = phase1b.index("Complete-Attempt4Disposition 'ATTEMPT HOLD'")
    assert call4 < call4_returned < call4_complete

    for token in (
        "Get-Attempt4DurableLiveDisposition",
        "sciencebase_attempt_family_active",
        "sciencebase_attempt_family_guard_indeterminate",
        "sciencebase_attempt_family_guard_release_failed",
        "$PhaseFlags.signed_live_returned = $true",
    ):
        assert token in live or token in _disposition_helper_block()
    assert "Complete-Attempt4Disposition $DurableDisposition" in live

    release_known = closeout.index("$CloseoutGuardReturned = $true")
    verified = closeout.index("Complete-Attempt4Disposition 'VERIFIED'")
    assert closeout.index("& $FamilyGuard -Mode NonRuntime -Action") < release_known < verified
    assert closeout.index("$PhaseFlags.closeout_verified = $true") < release_known
    assert "Complete-Attempt4Disposition 'POST-LIVE CLOSEOUT HOLD'" in closeout


@pytest.mark.skipif(os.name != "nt", reason="requires Windows PowerShell 5.1 transcript semantics")
def test_attempt4_disposition_helper_executes_once_and_fails_closed(
    tmp_path: Path,
) -> None:
    helper = _disposition_helper_block()
    proof = helper + r'''
$NonElevatedTranscript = [IO.Path]::GetFullPath($env:P6_DISPOSITION_TRANSCRIPT)
$SourceCommit = '0123456789abcdef0123456789abcdef01234567'
$PhaseFlags = [ordered]@{
  phase1_rehydrated = $true
  template_created = $true
  signed_live_returned = $false
  closeout_verified = $false
}
$AttemptState = [pscustomobject]@{
  DispositionWritten = $false
  TranscriptStarted = $false
}
Complete-Attempt4Disposition 'ATTEMPT HOLD' | Out-Host
$DuplicateFailed = $false
try { Complete-Attempt4Disposition 'VERIFIED' } catch {
  if ($_.Exception.Message -ceq 'Attempt-4 disposition already written.') {
    $DuplicateFailed = $true
  } else { throw }
}
if (-not $DuplicateFailed) { throw 'duplicate disposition did not fail closed' }
$Raw = [IO.File]::ReadAllText($NonElevatedTranscript)
$Lines = @($Raw -split "`r?`n" | Where-Object { $_ -like '{"attempt":4,*' })
if ($Lines.Count -ne 1) { throw "expected exactly one disposition line, found $($Lines.Count)" }
$Record = $Lines[0] | ConvertFrom-Json
if (
  @($Record.psobject.Properties.Name).Count -ne 4 -or
  [int]$Record.attempt -ne 4 -or
  [string]$Record.disposition -cne 'ATTEMPT HOLD' -or
  [string]$Record.source_head -cne $SourceCommit
) { throw 'disposition record shape mismatch' }
'ATTEMPT4_DISPOSITION_PROOF_OK'
'''
    test_env = os.environ.copy()
    test_env["P6_DISPOSITION_TRANSCRIPT"] = str(tmp_path / "attempt4.txt")
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            proof,
        ],
        check=False,
        capture_output=True,
        env=test_env,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ATTEMPT4_DISPOSITION_PROOF_OK" in result.stdout


def test_r3_exhaustive_mutation_and_worktree_receipts_are_counted_and_compared() -> None:
    text = READINESS.read_text(encoding="utf-8")
    ordinary = _ordinary_preflight_block()
    elevated = _elevated_preparation_block()

    for token in (
        "$MutationVector = @(",
        "$WorktreeVector = @(",
        "C:\\owner-controlled\\project6",
        "C:\\owner-controlled\\project6-bindings-3",
        "C:\\owner-controlled\\project6-w5obs-3",
        "C:\\p6-sciencebase-worker-2",
        "C:\\p6-sciencebase-worker-3",
        "plan-of-record-sciencebase-signed-go-2026-08-12.md",
        "SITTING-RUNBOOK-2026-08-14.md",
        "Q12-EVIDENCE-POINTER-INDEX-2026-08-15.md",
        "owner-decision-sheet-sciencebase-signed-go-2026-08-12.md",
        "amendment-addendum-v1.1-sciencebase-signed-go-2026-08-12.md",
        "forward-map-signed-go-lane-2026-08-13.md",
        "HANDOFF-SESSION-CONTINUATION-2026-08-14.md",
        "AUDIT-LEDGER-2026-08-14.md",
        "session-8e8b798b-archive",
        "session-9ee3527a-adversarial-pass",
        "characterization-record-2026-08-13",
        "characterization-record-2-2026-08-14",
        "git worktree list --porcelain",
        "git status --porcelain=v1 -z --untracked-files=all",
        "git diff --binary",
        "git diff --cached --binary",
        "ReparseData",
        "VolumeIdentity",
        "FileIdentity",
        "LinkCount",
        "CreationTimeUtc",
        "LastWriteTimeUtc",
        "DaclProtected",
        "OrderedSddl",
        "SortedAceTuples",
        "MUTATION_VECTOR_COUNT=",
        "WORKTREE_VECTOR_COUNT=",
        "BEFORE_AFTER_IDENTICAL",
        "without following reparse points",
        "validate-dual-live-preservation-receipts.ps1",
        "New-DualLivePreservationReceipt",
        "PRESERVATION_RECEIPT_OK",
        "Expected='absent'",
        "AllowedChildren=@()",
        "$ExpectedAmbientInterpreter = '<OWNER-FILL frozen ambient interpreter>'",
        "$PreservationContext = & $NewPreservationBaseline",
        "& $AssertPreservationUnchanged $PreservationContext",
    ):
        assert token in text
    assert "Wildcards, category-only claims, guessed counts, unresolved profiles" in text
    for undefined_seam in (
        "Get-ReviewedWindowsHandleIdentity",
        "Get-ReviewedReparseData",
        "ConvertFrom-ReviewedWorktreePorcelain",
        "Invoke-ReviewedGitRaw",
        "Get-ReviewedUntrackedManifest",
        "New-ReviewedPreservationReceipt",
    ):
        assert undefined_seam not in text
    assert "must be landed at the exact reviewed head" not in text
    assert ordinary.index("$PreservationContext = & $NewPreservationBaseline") < ordinary.index(
        "WindowsIdentity]::GetCurrent().User.Value"
    )
    assert ordinary.index("RETAINED_ATTEMPT3_WORKER_SHA256=") < ordinary.index(
        "& $AssertPreservationUnchanged $PreservationContext"
    )
    assert elevated.index("$PreservationContext = & $NewPreservationBaseline") < elevated.index(
        "WindowsIdentity]::GetCurrent().User.Value"
    )
    assert elevated.index("& $AssertPreservationUnchanged $PreservationContext") < elevated.index(
        "New-CustodyDirectoryOnce -Path $CustodyParent"
    )


def test_r3_journal_observer_contract_reopens_design_on_observed_unsafe_posture() -> None:
    text = READINESS.read_text(encoding="utf-8")

    for token in (
        "journal_observer: Callable[[Path, Path], None] | None = None",
        "after the connector_run INSERT and before COMMIT",
        "staging_database_path.with_name(staging_database_path.name + \"-journal\")",
        "journal_observer=assert_frozen_journal_posture",
        "ordinary, non-reparse, single-link file",
        "same directory and fixed-local volume",
        "owner SID, DACL protection, ordered SDDL, and sorted ACE tuples",
        "invoked exactly once",
        "Hook exceptions propagate",
        "custody_cleanup_indeterminate",
        "protected=false",
        "extra current-logon SID RX ACE",
        "session-specific",
        "does not match the required protected owner-and-SYSTEM-only staging posture",
        "DESIGN REOPENED",
        "Attempt 4 remains HOLD",
        "ReservationStore.reserve",
        "write_sciencebase_live_event",
        "complete runtime journal lifecycle remains uncharacterized",
        "owner-gated R4",
    ):
        assert token in text
    assert "PRESENT branch" in text
    assert "no PRESENT branch" in text


def test_rehearsal_roots_are_explicitly_pending_not_falsely_receipted() -> None:
    text = READINESS.read_text(encoding="utf-8")

    for token in (
        "C5 rehearsal root population is pending",
        "owner-gated R4 journal resolution",
        "exact rehearsal custody, binding, W5, worker, and scratch roots",
        "must be added to `$MutationVector` as present recursive receipts",
        "cannot yet claim an exhaustive pre-Attempt-4 preservation baseline",
    ):
        assert token in text


def test_pilot_runbook_disambiguates_without_supersession() -> None:
    text = PILOT_RUNBOOK.read_text(encoding="utf-8")

    assert "in-process public connector API pilot" in text
    assert "signed-GO readiness procedure" in text
    assert "next_milestone_plans/sciencebase-live-readiness.md" in text
    assert "Neither document supersedes the other." in text
