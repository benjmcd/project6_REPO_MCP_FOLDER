"""Front-door truth guard (lane L23).

The README opening status note silently rotted for ~3 months (a 2026-03-25
phase-closure note led the file long after it stopped being the current
posture). These guards keep the front door honest: it must lead with the
current support posture, must not present a dated historical phase note as the
headline, and must name the selected local expert RC1 profile without upgrading
that selection into a production-ready or nonlocal claim.
"""
from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"


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
    assert "analytics-only" in text
    assert "base=local_expert" in text
    assert "overlays=none" in text
    assert "connectors are deferred to RC2" in text
    assert "No release profile is selected yet" not in text
