# Layer 3 Mockup PDF-Location Panel Refinement

Status: current-branch PDF-location panel and slide-selector refinement proof for the mockup visual-diff harness.

```yaml
selected_refinement_mode: pdf_location_panel_structure_and_slide_selector_refinement
entry_proof: 278_MOCKUP_THRESHOLD_TIGHTENING.md
base_branch: main
implementation_branch: codex/l3-mockup-pixel-refinement-2
live_behavior_change: false
runtime_behavior_change: false
rendered_ui_behavior_change: true
```

This pass continues `continue_bounded_mockup_pixel_refinement_against_visual_diff_metrics` without admitting new runtime authority. It makes the existing `#mockup-pdf-location-card` static theme projection closer to `next_milestone_plans/layer3-mockups/frames/pdf-location.png` by rendering the card as a five-region board: PDF-location callout, natural-language intent card, four evidence sheets, server PDF-location projection card, and a three-card insight stack.

It also fixes selector precision for the three query/spec slide frames. `slide_1_projection`, `slide_general_projection`, and `slide_usecase_projection` now map to `#mockup-fixture-scenario` because those source frames depict natural-language query/manual-specification setup, not the whole user-flow/PDF-location board. `pdf_location_projection` remains mapped to `#mockup-pdf-location-card`.

Measured changes:

- Previous `pdf_location_projection` selector envelope: `normalizedMeanDelta: 0.272669`, `highDeltaRatio: 0.299356`.
- Refined `pdf_location_projection` panel envelope: `normalizedMeanDelta: 0.221211`, `highDeltaRatio: 0.312841`.
- Previous post-panel `slide_usecase_projection` whole-board envelope: `normalizedMeanDelta: 0.248228`, `highDeltaRatio: 0.313485`.
- Refined `slide_usecase_projection` fixture-selector envelope: `normalizedMeanDelta: 0.216169`, `highDeltaRatio: 0.116944`.
- Current worst mean frame: `userflow_overview_2_projection` at `normalizedMeanDelta: 0.253353`, `highDeltaRatio: 0.300960`.
- Current worst high-delta frame: `pdf_location_projection` at `normalizedMeanDelta: 0.221211`, `highDeltaRatio: 0.312841`.

The historical enforced visual-diff limits for this pass were:

- `normalizedMeanDeltaMax: 0.26`
- `highDeltaRatioMax: 0.32`
- `compareWidth: 360`
- `compareHeight: 220`

This pass improves structural parity and selector specificity, but it does not claim full pixel-perfect parity. Future visual work may continue bounded pixel refinement against the same repo-local frame manifest and visual-diff metrics.

This pass does not add backend API/model/migration/service behavior, source runtime, connector/destination dispatch, package mutation, qualitative/hybrid/RAG runtime, full durable mockup activation, auth/security widening, or browser-owned durable authority.
