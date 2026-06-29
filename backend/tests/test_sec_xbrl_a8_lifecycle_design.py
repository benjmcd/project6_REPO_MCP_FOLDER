from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOC_DIR = ROOT / "next_milestone_plans" / "Layer3_planning_docs"
DESIGN_DOC = DOC_DIR / "a8-lifecycle-design.md"
GATE_DOC = DOC_DIR / "a8-readiness-gate.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _squash_whitespace(text: str) -> str:
    return " ".join(text.split())


def test_a8_lifecycle_design_covers_required_readiness_topics() -> None:
    text = _read(DESIGN_DOC)
    required_sections = [
        "## Lifecycle State Machine",
        "## Redaction Posture Per State",
        "## Secure-Erasure Design",
        "## Operator Confirmation And Reveal Audit Mapping",
        "## Audit Replay And Idempotency",
        "## Isolated Storage And Containment",
        "## Failure And Abort Handling",
        "## Modularity Non-Fragility Scalability",
        "## Acceptance Coverage Map",
    ]
    required_states = [
        "resolved_redacted",
        "reveal_authority_prepared",
        "reveal_requested",
        "erasure_preflight_passed",
        "raw_at_rest_created",
        "revealed",
        "erase_pending",
        "securely_erased",
        "quarantined",
        "erasure_blocked",
        "expired",
        "aborted",
    ]
    coverage_markers = [
        "B1 state machine",
        "B2 secure erasure spec",
        "B3 redaction per state",
        "B4 operator confirmation plus reveal audit",
        "B5 audit/replay/idempotency",
        "B6 isolated storage containment",
        "B7 failure/abort handling",
        "B8 modularity/non-fragility/scalability",
    ]

    missing = [
        marker
        for marker in [*required_sections, *required_states, *coverage_markers]
        if marker not in text
    ]
    assert missing == []


def test_a8_readiness_gate_has_checkable_acceptance_criteria() -> None:
    text = _read(GATE_DOC)

    missing_items = [f"{item}." for item in range(1, 12) if f"{item}. " not in text]
    assert missing_items == []
    assert text.count("Acceptance criterion:") == 11
    assert text.count("Evidence required:") == 11
    assert text.count("Fails closed when:") == 11
    assert "M-A8-DESIGN-COMPLETE" in text
    assert "525993c721cad0e1349105f7502271c2be4ae996" in text


def test_a8_docs_preserve_design_only_non_admissions() -> None:
    combined = _squash_whitespace(_read(DESIGN_DOC) + "\n" + _read(GATE_DOC))
    required_boundaries = [
        "This document changes no runtime behavior and authorizes no reveal.",
        "No value-reveal implementation or enablement.",
        "No flag default change.",
        "No secure-erasure implementation.",
        "No schema, model, migration, durable persistence, route, rendered UI, or",
        "No Arelle run, live SEC request, taxonomy download, source acquisition, or",
        "No A7 proof-surface modification.",
        "No operator-run A7 proof promoted into committed or CI implementation truth.",
        "does not upgrade operator-run A7 proof into committed implementation truth.",
    ]

    missing = [boundary for boundary in required_boundaries if boundary not in combined]
    assert missing == []


def test_a8_docs_keep_h6_quarantine_outside_secure_erasure() -> None:
    combined = _read(DESIGN_DOC) + "\n" + _read(GATE_DOC)
    required_h6_boundaries = [
        "H6 quarantine remains a separate containment tool.",
        "`quarantine_only`: never qualifies as A8 secure erasure.",
        "A8 must not call it a secure-erasure tool.",
        "H6 movement is described as secure erasure",
        "move-only/non-erasure posture",
    ]

    missing = [boundary for boundary in required_h6_boundaries if boundary not in combined]
    assert missing == []
