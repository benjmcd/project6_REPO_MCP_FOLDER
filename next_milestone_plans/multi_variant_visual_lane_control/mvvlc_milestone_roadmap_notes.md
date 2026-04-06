# MVVLC Milestone Roadmap Notes

## Status note

This roadmap is a high-level orientation artifact.
If it conflicts with `00F`, `05E`, `05F`, `06E`, `03Y`, `03Z`, or `README_INDEX`, those stronger docs govern.

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
- `visual_lane_mode` planning freeze completed and was later implemented in M3.

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
- T1-T8 acceptance gate passed for the baseline-only bootstrap path.
- Local `06I` performance gate was executed and recorded.
- No accepted public/artifact/review/runtime drift was introduced on the merged baseline path.
- Baseline discovery / persistence / DB behavior remained unchanged.

### M5 - Current implementation milestone
- `03Y` standalone field-sensitivity map is now frozen.
- `05F` exact execution packet boundary is now frozen.
- `03Z` exact runtime-root coexistence plus baseline-facing visibility mechanism is now frozen.
- The next work is bounded implementation of that frozen barrier inside the `05F` owner boundary.
- Baseline-facing review/catalog/API/report/export surfaces must hide experiment-marked runs by explicit design.
- Upstream admission of approved non-baseline run creation remains later-scope and is not implied by this barrier lane.

### M6 - Admission / promotion (later future)
- Explicit baseline comparison.
- Explicit approval before admission.
- No simultaneous baseline + A + B + C integrated rollout.
- Further widening requires later planning.

## Current roadmap position

- M3 is complete for the baseline-only selector/bootstrap path.
- M4 is complete for that same baseline-only path.
- We are now at the start of bounded M5 implementation.
- The immediate work is executing the frozen `03Z` mechanism inside `05F`, not more mechanism-discovery or another M3/M4 closure pass.

## Key threshold

The earliest justified point for separate integrated ingestion/processing work has now been reached in principle because M3 is implemented and M4 has passed.

The remaining prerequisite for an approve-as-is M5 lane is:
- implementation of the frozen `03Z` coexistence / visibility mechanism
- passing validation for the `05F` owner and blocker bundles
- explicit no-drift proof for baseline review/runtime/report/export/diagnostics surfaces
- a refreshed `06I` result if the touched surfaces justify rerunning it

Bounded residuals that do not block M5 prep remain:
- repo-native Python acceptance-path enforcement
- Tier 2 performance sample breadth
- broader non-audited duplicate/generated surfaces
