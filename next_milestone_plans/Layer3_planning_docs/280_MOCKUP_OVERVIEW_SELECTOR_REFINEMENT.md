# Layer 3 Mockup Overview Selector Refinement

Status: current-branch overview-frame selector refinement proof for the mockup visual-diff harness.

```yaml
selected_refinement_mode: overview_frame_selector_refinement_to_theme_shell
entry_proof: 279_MOCKUP_PDF_LOCATION_PANEL_REFINEMENT.md
base_branch: main
implementation_branch: codex/l3-mockup-overview-selector-refinement
live_behavior_change: false
runtime_behavior_change: false
rendered_ui_behavior_change: false
```

This pass continues `continue_bounded_mockup_pixel_refinement_against_visual_diff_metrics` without changing rendered UI or runtime behavior. It refines the repo-local frame manifest so the two overview montage frames map to `#mockup-theme-shell` instead of `#mockup-userflow-board`.

The selector change is justified because `userflow_overview_1_projection` and `userflow_overview_2_projection` depict full-workbench overview/montage flows, while `#mockup-userflow-board` is only the user-flow/PDF-location sub-board. The full mockup workbench shell is the narrower correct existing selector for those overview frames.

Measured changes:

- `userflow_overview_1_projection` before: `#mockup-userflow-board`, `normalizedMeanDelta: 0.248685`, `highDeltaRatio: 0.301755`.
- `userflow_overview_1_projection` after: `#mockup-theme-shell`, `normalizedMeanDelta: 0.138044`, `highDeltaRatio: 0.113333`.
- `userflow_overview_2_projection` before: `#mockup-userflow-board`, `normalizedMeanDelta: 0.253353`, `highDeltaRatio: 0.300960`.
- `userflow_overview_2_projection` after: `#mockup-theme-shell`, `normalizedMeanDelta: 0.129707`, `highDeltaRatio: 0.118220`.
- Current measured worst frame: `pdf_location_projection` at `normalizedMeanDelta: 0.221211`, `highDeltaRatio: 0.312841`.

The enforced visual-diff limits are now:

- `normalizedMeanDeltaMax: 0.22`
- `highDeltaRatioMax: 0.31`
- `compareWidth: 360`
- `compareHeight: 220`

This pass improves selector specificity and tightens the mean-delta envelope, but it does not claim full pixel-perfect parity. Future visual work may continue bounded pixel refinement against the same repo-local frame manifest and visual-diff metrics.

This pass does not add backend API/model/migration/service behavior, source runtime, connector/destination dispatch, package mutation, qualitative/hybrid/RAG runtime, full durable mockup activation, auth/security widening, or browser-owned durable authority.
