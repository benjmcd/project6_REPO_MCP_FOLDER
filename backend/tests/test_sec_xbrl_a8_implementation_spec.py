from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOC_DIR = ROOT / "next_milestone_plans" / "Layer3_planning_docs"
SPEC_DOC = DOC_DIR / "a8-implementation-spec.md"
GATE_DOC = DOC_DIR / "a8-readiness-gate.md"
PROGRESS_BOARD = ROOT / "next_milestone_plans" / "layer3_progress_board.md"
PROGRESS_MANIFEST = ROOT / "next_milestone_plans" / "layer3_progress_manifest.json"
PROOF_MANIFEST = (
    ROOT / "next_milestone_plans" / "layer3_workbench_proof_manifest.json"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _squash_whitespace(text: str) -> str:
    return " ".join(text.split())


def test_a8_implementation_spec_maps_all_gate_items_to_code_tests_and_rollback() -> None:
    text = _read(SPEC_DOC)

    gate_items = [
        "### Gate 1 - Live authority and posture are refreshed and pinned",
        "### Gate 2 - Durable value-store design is owner-approved",
        "### Gate 3 - Storage hygiene is implemented before retained values can be written",
        "### Gate 4 - Reveal request binding is explicit and server-owned",
        "### Gate 5 - Audit/status redaction preserves identity and operational secrecy",
        "### Gate 6 - Verification is complete before owner authorization",
        "### Gate 7 - Tier-2 governance is satisfied for runtime implementation",
    ]
    missing = [item for item in gate_items if item not in text]
    assert missing == []

    for item in gate_items:
        section = text.split(item, 1)[1].split("### Gate ", 1)[0]
        assert "Future code changes:" in section, item
        assert "Tests:" in section, item
        assert "Rollback:" in section, item


def test_a8_implementation_spec_covers_required_owner_authorization_surfaces() -> None:
    text = _squash_whitespace(_read(SPEC_DOC))
    required = [
        "Status: owner-authorizable Tier-2 implementation specification only.",
        "No flag is flipped in this PR.",
        "backend/app/services/layer3_sec_xbrl_sidecar.py:825-829",
        "backend/app/services/layer3_sec_xbrl_sidecar.py:1129-1161",
        "backend/app/services/layer3_sec_xbrl_sidecar.py:1341-1353",
        "backend/app/services/layer3_sec_edgar_arelle_value_reveal.py",
        "backend/app/api/layer3/sec_xbrl.py:778-953",
        "backend/app/api/layer3/source_sec_edgar.py:531-566",
        "backend/app/services/layer3_sec_xbrl_value_reveal_authority.py:70-258",
        "backend/app/services/layer3_sec_xbrl_controlled_value_reveal_submit.py:98-204",
        "backend/app/services/layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.py:710-812",
        "a8-lifecycle-design.md",
        "PR `#2406`",
        "owner-approved A8 durable value-retention design authority",
        "Recommended path: keep the filesystem-backed internal value store",
        "Recommendation: keep sidecar-mode material-bridge CSV redacted",
        "LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED",
        "LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED",
        "LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED",
    ]

    missing = [marker for marker in required if marker not in text]
    assert missing == []


def test_a8_retention_policy_backdoor_is_in_spec_and_gate() -> None:
    combined = _squash_whitespace(_read(SPEC_DOC) + "\n" + _read(GATE_DOC))
    required = [
        "tied_to_sidecar_receipt_lifecycle",
        "sec_xbrl_public_financial_value_retention_v1",
        "no value-store deletion path",
        "Tier-2 Implementation Guard Addendum",
        "rollback must not remove retained public SEC financial values",
    ]

    missing = [marker for marker in required if marker not in combined]
    assert missing == []


def test_a8_implementation_spec_remains_planning_only_and_excludes_forbidden_surfaces() -> None:
    text = _squash_whitespace(_read(SPEC_DOC))
    required_non_admissions = [
        "does not implement runtime behavior",
        "flip flags",
        "change defaults",
        "add schema or migrations",
        "change value reveal behavior",
        "change redaction posture",
        "touch A7 proof surfaces",
        "generate runtime artifacts",
        "No live SEC egress changes.",
        "No Arelle execution or Arelle network behavior changes.",
        "No A7 proof-surface changes.",
        "No nonlocal delivery, export, or provider delivery behavior.",
        "No workflow or GitHub Actions changes.",
        "No progress board, progress manifest, or proof manifest changes beyond Tier-1 ledger reconciliation for PR `#2409`.",
        "Temp roots are test fixtures only.",
        "Durable runtime roots must remain off-repo, off-OneDrive/cloud-sync, non-static, non-git, and not Downloads-like.",
    ]

    missing = [marker for marker in required_non_admissions if marker not in text]
    assert missing == []


def test_a8_implementation_spec_ledger_reconciliation_is_manifested() -> None:
    board = _squash_whitespace(_read(PROGRESS_BOARD))
    progress_manifest = json.loads(_read(PROGRESS_MANIFEST))
    proof_manifest = json.loads(_read(PROOF_MANIFEST))

    board_markers = [
        "SEC EDGAR Arelle Fact-Authority Proof + A8 Value-Retention Design",
        "A8 Durable Value Retention Implementation Spec Preclearance",
        "PR `#2407`",
        "PR `#2406`",
        "PR `#2408`",
        "PR `#2409`",
        "ledger metadata so the manifests and board reflect the #2406/#2407/#2408 A7/A8 frontier plus the #2409 implementation-spec tranche",
    ]
    missing_board = [marker for marker in board_markers if marker not in board]
    assert missing_board == []

    progress_tracking = progress_manifest["sec_xbrl_a8_implementation_spec_tracking"]
    assert progress_tracking["design_authority_doc"].endswith(
        "a8-lifecycle-design.md"
    )
    assert progress_tracking["design_authority_pr"] == "#2406"
    assert progress_tracking["prior_arelle_ci_proof_pr"] == "#2407"
    assert progress_tracking["prior_board_reconciliation_pr"] == "#2408"
    assert progress_tracking["pr"] == "#2409"
    assert progress_tracking["ledger_reconciliation_only"] is True
    assert progress_tracking["temp_roots_fixture_only"] is True
    assert progress_tracking["runtime_behavior_changed_by_tracking"] is False
    assert progress_tracking["schema_model_migration_changed_by_tracking"] is False

    proof = proof_manifest["sec_xbrl_a8_implementation_spec_proof"]
    assert proof["design_authority_pr"] == "#2406"
    assert proof["prior_arelle_ci_proof_pr"] == "#2407"
    assert proof["prior_board_reconciliation_pr"] == "#2408"
    assert proof["pr"] == "#2409"
    assert proof["negative_authority_flags"]["runtime_behavior_change"] is False
    assert proof["negative_authority_flags"]["a7_proof_surface_change"] is False
