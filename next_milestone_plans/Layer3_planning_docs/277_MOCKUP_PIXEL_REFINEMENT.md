# Layer 3 Mockup Pixel Refinement

Status: current-branch bounded pixel-refinement proof for the mockup visual-diff harness.

```yaml
selected_refinement_mode: pdf_location_frame_selector_precision_and_threshold_tightening
entry_proof: 276_MOCKUP_VISUAL_DIFF_HARNESS.md
base_branch: main
implementation_branch: codex/l3-mockup-pixel-refinement
live_behavior_change: false
runtime_behavior_change: false
rendered_ui_behavior_change: false
```

This pass tightens the repo-local visual-diff proof without claiming full pixel-perfect parity. The previous harness compared `pdf_location_projection` against the whole `#mockup-userflow-board`, which was too broad for `next_milestone_plans/layer3-mockups/frames/pdf-location.png`.

The refinement adds a stable `#mockup-pdf-location-card` selector and maps only `pdf_location_projection` to that selector in `next_milestone_plans/layer3-mockups/frames/manifest.json`. The user-flow frames remain mapped to `#mockup-userflow-board`.

## Measured proof delta

- Before selector precision, `pdf_location_projection` measured `normalizedMeanDelta: 0.289284` and `highDeltaRatio: 0.315669`.
- After selector precision, `pdf_location_projection` measured `normalizedMeanDelta: 0.272669` and `highDeltaRatio: 0.299356`.
- The harness limits were first tightened to `normalizedMeanDeltaMax: 0.30` and `highDeltaRatioMax: 0.34`, then tightened again in `278_MOCKUP_THRESHOLD_TIGHTENING.md` to `normalizedMeanDeltaMax: 0.28` and `highDeltaRatioMax: 0.31`.

## Scope boundary

This is a proof/selector precision pass only. It does not claim full pixel-perfect parity and does not add backend API/model/migration/service behavior, source runtime, connector/destination dispatch, package mutation, qualitative/hybrid/RAG runtime, full durable mockup activation, auth/security widening, or browser-owned durable authority.
