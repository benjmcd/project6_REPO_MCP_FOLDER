# MVVLC Milestone Roadmap Notes

## Milestone sequence

### M0 — Program decision
- Hybrid multi-variant program adopted.
- Frozen baseline.
- Three experimental worktree tracks.
- One bounded in-repo selector seam.
- Baseline-only integration first.
- Later admission of one approved experimental variant at a time.

### M1 — Control freeze
- PDF visual-lane only.
- Exact seam / selector boundary frozen.
- Activation + isolation policy frozen.
- Validation packet and blocker packet defined.

### M2 — Bounded live-repo verification
- Pack considered aligned enough to proceed.
- No blocker-level architecture issue proven.
- Main unresolved issue is localized.
- `visual_lane_mode` is planning-frozen but not implemented.

### M3 — Current implementation pass
- Implement baseline-preserving integrated selector bootstrap.
- Create `visual_lane_mode` path:
  - normalization
  - forwarding
  - defaulting
  - first seam consumption
- Keep baseline default.
- Keep non-baseline behavior unavailable in normal runtime.

### M4 — Acceptance gate
- No public behavior drift.
- No artifact/report/review/runtime drift.
- Baseline discovery / persistence / DB behavior unchanged.
- Execute targeted validation and performance checks.

### M5 — Integrated experimental work
- Only after bootstrap is proven.
- Separate approaches stop being only worktree-side experiments.
- Candidate variants can be integrated one at a time.
- Still bounded to the frozen seam.

### M6 — Admission / promotion
- Explicit baseline comparison.
- Explicit approval.
- No simultaneous baseline + A + B + C integrated rollout.
- Further widening requires later planning.

## Key threshold

The earliest justified point for working on separate integrated ingestion/processing approaches is **after M3 is implemented and M4 passes**.
