"""Front-door truth guard (lane L23).

The README opening status note silently rotted for ~3 months (a 2026-03-25
phase-closure note led the file long after it stopped being the current
posture). These guards keep the front door honest: it must lead with the
current support posture, must not present a dated historical phase note as the
headline, and must name the selected local expert RC3 profile without upgrading
that selection into a production-ready, live SEC, or nonlocal claim.
"""
from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"
LOCAL_EXPERT_SUPPORT = (
    Path(__file__).resolve().parents[1] / "docs" / "support-matrix-local-expert.md"
)


def _text() -> str:
    return README.read_text(encoding="utf-8")


def test_readme_leads_with_current_status_before_any_dated_phase_note():
    text = _text()
    assert "Current status" in text, "README lost its current-status lead"
    current_idx = text.index("Current status")
    # Any dated historical phase note (e.g. the 2026-03-25 NRC APS note) must be
    # demoted below the current-status lead, never presented as the headline.
    dated_idx = text.find("2026-03-25")
    assert dated_idx == -1 or dated_idx > current_idx, (
        "a dated historical phase note precedes the current-status lead"
    )


def test_readme_states_honest_selected_local_profile():
    text = _text()
    assert "not a production-ready claim" in text, (
        "README dropped its not-production-ready honesty"
    )
    assert "selected RC3 profile" in text
    assert "base=local_expert" in text
    assert 'overlays=["public_connectors","sec_xbrl_offline"]' in text
    assert "Public connector support is bounded to operator-workflow + local-deployment" in text
    assert "SEC-XBRL value-bearing support is simulation/offline-replay only" in text
    assert "already-acquired operator-supplied evidence" in text
    assert "Bounded SEC-XBRL live source-artifact acquisition is present but remains explicit-default-off" in text
    assert "keyed connectors" in text
    assert "HA" in text
    assert "No release profile is selected yet" not in text


def test_local_expert_doc_names_canonical_operator_journey():
    text = LOCAL_EXPERT_SUPPORT.read_text(encoding="utf-8")
    assert "selected RC3 profile" in text
    assert 'overlays=["public_connectors","sec_xbrl_offline"]' in text
    assert "SEC live network egress | `experimental_default_off`" in text
    assert "default-on SEC live network" in text
    assert "canonical local_expert operator journey" in text
    assert "config/support_matrix.yaml" in text
    assert "method_aware_analytics_vertical" in text
    for phrase in [
        "CSV upload",
        "variable profiling",
        "transform recommend/apply",
        "annotation",
        "cross_correlation",
        "decomposition",
        "structural_break",
        "content_hash",
        "source_row_count",
        "dropped_row_count",
        "GET /api/v1/analysis-runs/{id}",
        "unsupported_method",
    ]:
        assert phrase in text
