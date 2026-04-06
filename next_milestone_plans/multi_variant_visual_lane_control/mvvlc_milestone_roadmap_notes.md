# MVVLC Milestone Roadmap Notes

## Milestone sequence

### M0 - Program decision (achieved / previous)
- Hybrid multi-variant program adopted.
- Frozen baseline.
- Three experimental worktree tracks.
- One bounded in-repo selector seam.
- Baseline-only integration first.
- Later admission of one approved experimental variant at a time.

### M1 - Control freeze (achieved / previous)
- PDF visual-lane only.
- Exact seam / selector boundary frozen.
- Activation + isolation policy frozen.
- Validation packet and blocker packet defined.

### M2 - Bounded live-repo verification (achieved / previous)
- Pack considered aligned enough to proceed.
- No blocker-level architecture issue proven.
- Main unresolved issue was localized.
- `visual_lane_mode` was planning-frozen and later implemented in M3.

### M3 - Baseline selector bootstrap (achieved / previous)
- Implemented baseline-preserving integrated selector bootstrap.
- Created the `visual_lane_mode` path:
  - normalization
  - forwarding
  - defaulting
  - first seam consumption
- Kept baseline as the default.
- Kept non-baseline behavior unavailable in normal runtime.

### M4 - Acceptance gate (achieved / previous)
- No public behavior drift was accepted.
- No artifact/report/review/runtime drift was accepted under the frozen T1-T8 gate.
- Baseline discovery / persistence / DB behavior remained unchanged.
- Targeted validation and local performance checks were executed and recorded.

### M5 - Next implementation lane
- Freeze and implement controlled experiment runtime-root coexistence.
- Freeze and implement baseline-facing visibility controls for experiment runs.
- Produce the exact review/report/export field-sensitivity and no-drift map needed for approve-as-is execution.
- Integrate candidate later-scope behavior one bounded step at a time.
- Stay bounded to the frozen seam and preserve accepted M3/M4 baseline behavior.

### M6 - Admission / promotion
- Explicit baseline comparison.
- Explicit approval.
- No simultaneous baseline + A + B + C integrated rollout.
- Further widening requires later planning.

## Key threshold

The earliest justified point for working on separate integrated ingestion/processing approaches has now been reached.

The remaining prerequisite for an approve-as-is M5 lane is not another M3/M4 closure pass.
It is an explicit post-M4 approval packet and scoped freeze for experiment coexistence and visibility work (`05E`).
