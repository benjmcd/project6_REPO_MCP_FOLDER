# Layer 3 Mockup Fixture Slide Refinement

Status: current-branch query/spec fixture slide refinement proof for the mockup visual-diff harness.

```yaml
selected_refinement_mode: fixture_query_spec_slide_structure_refinement
entry_proof: 281_MOCKUP_PDF_CONTRAST_REFINEMENT.md
base_branch: main
implementation_branch: codex/l3-mockup-fixture-slide-refinement
live_behavior_change: false
runtime_behavior_change: false
rendered_ui_behavior_change: true
```

This pass continues `continue_bounded_mockup_pixel_refinement_against_visual_diff_metrics` without admitting new runtime authority. It reshapes `#mockup-fixture-scenario` from a compact three-column strip into a vertical natural-language query/manual-specification fixture with a disabled chip grid, matching the repo-local query/spec slide frames more closely while preserving fail-closed unavailable controls.

Measured changes:

- Previous `slide_usecase_projection`: `normalizedMeanDelta: 0.216169`, `highDeltaRatio: 0.116944`.
- Refined `slide_usecase_projection`: `normalizedMeanDelta: 0.072746`, `highDeltaRatio: 0.072854`.
- Refined `slide_1_projection`: `normalizedMeanDelta: 0.113501`, `highDeltaRatio: 0.041301`.
- Refined `slide_general_projection`: `normalizedMeanDelta: 0.113376`, `highDeltaRatio: 0.038939`.
- Current measured worst frame: `pdf_location_projection` at `normalizedMeanDelta: 0.191193`, `highDeltaRatio: 0.301313`.

The enforced visual-diff limits are now:

- `normalizedMeanDeltaMax: 0.19`
- `highDeltaRatioMax: 0.305`
- `compareWidth: 360`
- `compareHeight: 220`

This pass improves query/spec slide parity and tightens the mean-delta envelope, but it does not claim full pixel-perfect parity. Future visual work may continue bounded pixel refinement against the same repo-local frame manifest and visual-diff metrics.

This pass does not add backend API/model/migration/service behavior, source runtime, connector/destination dispatch, package mutation, qualitative/hybrid/RAG runtime, full durable mockup activation, auth/security widening, or browser-owned durable authority.
