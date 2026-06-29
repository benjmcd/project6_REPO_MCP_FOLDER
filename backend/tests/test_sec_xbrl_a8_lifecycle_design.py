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


def test_a8_retention_design_covers_required_readiness_topics() -> None:
    text = _read(DESIGN_DOC)
    required_sections = [
        "## Retention State Machine",
        "## Durable Value Store Model",
        "## Redaction Boundary",
        "## Request Binding And Controlled Reveal",
        "## Provenance Integrity And Idempotency",
        "## H6 Boundary",
        "## Conditional Future Source-Class Caveat",
        "## Modularity Non-Fragility Scalability",
        "## Acceptance Coverage Map",
    ]
    required_states = [
        "resolved_redacted_authority",
        "retention_preflight_passed",
        "values_retained_durable",
        "reveal_requested",
        "values_displayed_controlled",
        "retention_replayed",
        "retention_blocked",
    ]
    coverage_markers = [
        "B1 durable value-store retention model",
        "B2 identity/secret/path/token redaction",
        "B3 storage hygiene",
        "B4 provenance/integrity",
        "B5 reveal request binding",
        "B6 idempotency",
        "B7 conditional future non-public-source caveat",
        "B8 modularity/non-fragility/scalability",
    ]

    missing = [
        marker
        for marker in [*required_sections, *required_states, *coverage_markers]
        if marker not in text
    ]
    assert missing == []


def test_a8_readiness_gate_has_checkable_retention_criteria() -> None:
    text = _read(GATE_DOC)

    missing_items = [f"{item}." for item in range(1, 8) if f"{item}. " not in text]
    assert missing_items == []
    assert text.count("Acceptance criterion:") == 7
    assert text.count("Evidence required:") == 7
    assert text.count("Fails closed when:") == 7
    assert "M-A8-RETENTION-REDESIGN" in text
    assert "c96ea5154dd13a0724d74f8979bb28651d667cb8" in text


def test_a8_docs_preserve_retention_and_identity_redaction_boundary() -> None:
    combined = _squash_whitespace(_read(DESIGN_DOC) + "\n" + _read(GATE_DOC))
    required_boundaries = [
        "SEC EDGAR XBRL financial values are public government disclosures",
        "Public financial values are retained durably as product data.",
        "A8 redaction is about identity and operational authority, not public financial values in the retained store.",
        "Retained: public SEC EDGAR financial values",
        "explicit operator confirmation is a hard requirement for any operator-visible display/submit",
        "No value-reveal implementation or enablement.",
        "No internal value-store flag default change.",
        "No A7 proof-surface modification.",
        "This document changes no runtime behavior and authorizes no reveal.",
    ]

    missing = [boundary for boundary in required_boundaries if boundary not in combined]
    assert missing == []


def test_a8_docs_remove_old_destruction_lifecycle_terms() -> None:
    combined = (_read(DESIGN_DOC) + "\n" + _read(GATE_DOC)).lower()
    forbidden_terms = [
        "crypto_erase",
        "overwrite_unlink",
        "secure-erasure",
        "secure erasure",
        "erasure backend",
        "erase_pending",
        "securely_erased",
        "erasure_blocked",
        "tombstone",
        "value-destruction requirement",
        "quarantine_only",
        "valuerevealrawstore",
    ]

    present = [term for term in forbidden_terms if term in combined]
    assert present == []


def test_a8_docs_keep_h6_outside_retention_model() -> None:
    combined = _squash_whitespace(_read(DESIGN_DOC) + "\n" + _read(GATE_DOC))
    required_h6_boundaries = [
        "H6 remains outside A8.",
        "A8 retention must not call H6, upgrade H6, or describe H6 as part of the retained public-value store.",
        "No H6 dependency or upgrade.",
    ]

    missing = [boundary for boundary in required_h6_boundaries if boundary not in combined]
    assert missing == []
