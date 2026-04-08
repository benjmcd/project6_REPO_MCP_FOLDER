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

### M6B - Admission / promotion (merged on `main`)
- `03AA` freezes the exact controlled-admission / promotion mechanism.
- `05H` freezes the exact owner boundary, widening rules, validation packet, and fail-closed stop conditions.
- `05K` now provides the exact record shape that must be filled before direct-admission code begins.
- `05L` now freezes the exact approved Candidate A target record derived from `05K`.
- The approved first non-`baseline` selector value is `candidate_a_page_evidence_v1`.
- `05M` records the achieved direct-admission implementation and local validation for the lane that later merged.
- `05N` records the merged-main closure and the next-scope handoff.
- No simultaneous baseline + A + B + C integrated rollout.

### Post-M6B planning freeze (achieved / current)
- `03AC` freezes the exact post-admission/defaulting scope and decision boundary.
- `05O` freezes the exact planning packet for later defaulting/defer/retain-default decision work.
- No default-promotion code is implied.
- No Candidate B/C admission, OCR/media widening, policy retuning, or new dependency work is implied.

### Post-M6B current-horizon decision (achieved / current)
- `05P` freezes the explicit current-horizon decision to retain `baseline` as the default.
- Candidate A remains admitted but non-default.
- Candidate B/C remain non-admitted.
- No default-promotion target-definition lane opens from this decision.

### Post-M6B retained-default merged-main closure (achieved / current)
- `05Q` records that the retained-default state from `05P` is now merged-main authority.
- The primary MVVLC path is now in a stable hold state rather than waiting on another immediate decision lane.
- Any future non-`baseline` default still requires an explicit amendment to `00D` plus a later exact target-definition lane.

## Current roadmap position

- M3 is complete for the baseline-only selector/bootstrap path.
- M4 is complete for that same baseline-only path.
- M5 coexistence / visibility barrier is implemented and recorded on merged `main`.
- M6A standalone PageEvidence workbench implementation is complete on merged `main`.
- M6B exact Candidate A target-definition is now complete in `05L`.
- M6B direct admission of the one approved Candidate A value is now merged on `main`.
- The exact post-admission/defaulting planning boundary is now frozen in `03AC` + `05O`.
- The current-horizon retain-`baseline` decision is now merged-main authority through `05P` + `05Q`.
- No further primary MVVLC implementation, promotion, or decision lane is justified by default from the current merged-main state.

## Key threshold

The earliest justified point for later-scope experiment construction has now been reached because M3 is implemented, M4 has passed, the M5 barrier lane is closed on merged `main`, and the standalone M6A workbench now exists.

Merged `main` now contains the bounded direct-admission closure state:
- implement only the one approved selector value within the frozen `03AA` + `05H` packet
- prove the required no-drift validation bundles and `06I`
- record any justified widening explicitly instead of inferring it

Bounded residuals that do not block the current retained-default merged-main posture remain:
- repo-native Python acceptance-path enforcement
- Tier 2 performance sample breadth
- broader non-audited duplicate/generated surfaces
- any future program-decision amendment, default-promotion target-definition, or additional-candidate scope beyond the retained-default decision
