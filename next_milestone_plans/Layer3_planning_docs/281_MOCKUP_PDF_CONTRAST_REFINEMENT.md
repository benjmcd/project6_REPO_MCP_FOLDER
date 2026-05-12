# Layer 3 Mockup PDF-Location Contrast Refinement

Status: current-branch PDF-location contrast refinement proof for the mockup visual-diff harness.

```yaml
selected_refinement_mode: pdf_location_contrast_palette_refinement
entry_proof: 280_MOCKUP_OVERVIEW_SELECTOR_REFINEMENT.md
base_branch: main
implementation_branch: codex/l3-mockup-pdf-contrast-refinement
live_behavior_change: false
runtime_behavior_change: false
rendered_ui_behavior_change: true
```

This pass continues `continue_bounded_mockup_pixel_refinement_against_visual_diff_metrics` without admitting new runtime authority. It refines only the `#mockup-pdf-location-card` palette by moving the static board and card colors toward the repo-local mid-gray `pdf-location.png` frame while preserving the existing five-region structure, selectors, server PDF-location projection placeholder, and fail-closed runtime boundaries.

Measured changes:

- Previous `pdf_location_projection`: `normalizedMeanDelta: 0.221211`, `highDeltaRatio: 0.312841`.
- Refined `pdf_location_projection`: `normalizedMeanDelta: 0.190949`, `highDeltaRatio: 0.300808`.
- Current worst mean frame: `slide_usecase_projection` at `normalizedMeanDelta: 0.216169`, `highDeltaRatio: 0.116944`.
- Current worst high-delta frame: `pdf_location_projection` at `normalizedMeanDelta: 0.190949`, `highDeltaRatio: 0.300808`.

The enforced visual-diff limits are now:

- `normalizedMeanDeltaMax: 0.22`
- `highDeltaRatioMax: 0.31`
- `compareWidth: 360`
- `compareHeight: 220`

This pass improves contrast parity and tightens both visual-diff thresholds, but it does not claim full pixel-perfect parity. Future visual work may continue bounded pixel refinement against the same repo-local frame manifest and visual-diff metrics.

This pass does not add backend API/model/migration/service behavior, source runtime, connector/destination dispatch, package mutation, qualitative/hybrid/RAG runtime, full durable mockup activation, auth/security widening, or browser-owned durable authority.
