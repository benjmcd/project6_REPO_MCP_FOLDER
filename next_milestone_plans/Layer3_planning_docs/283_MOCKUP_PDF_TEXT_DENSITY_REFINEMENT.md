# Layer 3 Mockup PDF-Location Text-Density Refinement

Status: current-branch PDF-location text-density refinement proof for the mockup visual-diff harness.

```yaml
selected_refinement_mode: pdf_location_text_density_and_disabled_chip_refinement
entry_proof: 282_MOCKUP_FIXTURE_SLIDE_REFINEMENT.md
base_branch: main
implementation_branch: codex/l3-mockup-pdf-layout-refinement
live_behavior_change: false
runtime_behavior_change: false
rendered_ui_behavior_change: true
```

This pass continues `continue_bounded_mockup_pixel_refinement_against_visual_diff_metrics` without admitting new runtime authority. It adjusts only `#mockup-pdf-location-card` text density and the read-only disabled chip presentation so the PDF-location panel has less dense dark text mass and no dark placeholder patch inside the gray server-projection card.

Measured changes:

- Previous `pdf_location_projection`: `normalizedMeanDelta: 0.191193`, `highDeltaRatio: 0.301313`.
- Refined `pdf_location_projection`: `normalizedMeanDelta: 0.188340`, `highDeltaRatio: 0.298573`.
- Current measured worst frame: `pdf_location_projection` at `normalizedMeanDelta: 0.188340`, `highDeltaRatio: 0.298573`.

The enforced visual-diff limits are now:

- `normalizedMeanDeltaMax: 0.19`
- `highDeltaRatioMax: 0.305`
- `compareWidth: 360`
- `compareHeight: 220`

This pass improves PDF-location text-density parity and tightens both visual-diff thresholds, but it does not claim full pixel-perfect parity. Future visual work may continue bounded pixel refinement against the same repo-local frame manifest and visual-diff metrics.

This pass does not add backend API/model/migration/service behavior, source runtime, connector/destination dispatch, package mutation, qualitative/hybrid/RAG runtime, full durable mockup activation, auth/security widening, or browser-owned durable authority.
