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

### M5 - Coexistence / visibility barrier (achieved / previous)
- `03Y` standalone field-sensitivity map is now frozen.
- `05F` exact execution packet boundary is now frozen.
- `03Z` exact runtime-root coexistence plus baseline-facing visibility mechanism is now frozen and implemented.
- `05G` records the achieved owner set, validation results, `06I` rerun, and no-drift judgment for the bounded M5 barrier lane.
- Baseline-facing review/catalog/API/report/export surfaces now hide experiment-marked runs by explicit design on merged `main`.
- Upstream admission of approved non-baseline run creation remains later-scope and is not implied by this barrier lane.

### M6A - Candidate A workbench (achieved / previous)
- `03AB` froze the dedicated PageEvidence / Option 2 workbench boundary.
- `05I` froze the exact owner boundary, location strategy, validation packet, and fail-closed stop conditions for the workbench lane.
- `05J` records the implemented standalone PageEvidence service, runner, validation bundle, and no-drift judgment.
- Candidate A remains pre-admission.
- The workbench now produces isolated evidence and tuning outputs without widening integrated runtime behavior.

### M6B - Admission / promotion (planning packet frozen; next, after target naming)
- `03AA` freezes the exact controlled-admission / promotion mechanism.
- `05H` freezes the exact owner boundary, widening rules, validation packet, and fail-closed stop conditions.
- No specific non-baseline selector value is approved by default.
- Exactly one approved non-baseline value must be named explicitly before direct integrated-admission code begins.
- No simultaneous baseline + A + B + C integrated rollout.

## Current roadmap position

- M3 is complete for the baseline-only selector/bootstrap path.
- M4 is complete for that same baseline-only path.
- M5 coexistence / visibility barrier is implemented and recorded on merged `main`.
- M6A standalone PageEvidence workbench implementation is complete in the current clean lane.
- The immediate next work is exact M6B Candidate A target-definition and later direct admission under the already-frozen packet.
- Direct M6B admission remains separately fail-closed until one exact approved target is explicitly named.

## Key threshold

The earliest justified point for later-scope experiment construction has now been reached because M3 is implemented, M4 has passed, the M5 barrier lane is closed on merged `main`, and the standalone M6A workbench now exists.

The remaining prerequisite before starting direct later-scope admission work is:
- name one exact approved non-baseline selector value explicitly
- then record explicit approval and baseline-comparison evidence for that one value
- then implement within the frozen `03AA` + `05H` packet or record any justified widening explicitly

Bounded residuals that do not block M6 planning remain:
- repo-native Python acceptance-path enforcement
- Tier 2 performance sample breadth
- broader non-audited duplicate/generated surfaces
