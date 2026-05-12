# Layer 3 Mockup Threshold Tightening

Status: current-branch visual-diff threshold-tightening proof for the mockup workbench theme.

```yaml
selected_refinement_mode: visual_diff_threshold_tightening_to_observed_envelope
entry_proof: 277_MOCKUP_PIXEL_REFINEMENT.md
base_branch: main
implementation_branch: codex/l3-mockup-pixel-threshold-tighten
live_behavior_change: false
runtime_behavior_change: false
rendered_ui_behavior_change: false
```

This pass tightens the visual-diff harness envelope after the PDF-location selector precision pass. The measured post-refinement worst frame is `pdf_location_projection` at `normalizedMeanDelta: 0.272669` and `highDeltaRatio: 0.299356`.

The enforced limits are now:

- `normalizedMeanDeltaMax: 0.26`
- `highDeltaRatioMax: 0.32`
- `compareWidth: 360`
- `compareHeight: 220`

These limits are intentionally close to the current observed envelope, but this pass does not claim full pixel-perfect parity. Future visual work may continue bounded pixel refinement against the same repo-local frame manifest and visual-diff metrics.

This pass does not add backend API/model/migration/service behavior, source runtime, connector/destination dispatch, package mutation, qualitative/hybrid/RAG runtime, full durable mockup activation, auth/security widening, or browser-owned durable authority.
