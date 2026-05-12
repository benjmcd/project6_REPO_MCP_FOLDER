# Layer 3 Mockup Visual Diff Harness

Status: current-branch visual-diff harness implementation proof for the mockup workbench theme.

```yaml
selected_proof_mode: repo_local_mockup_frame_visual_diff_acceptance
entry_freeze: 275_MOCKUP_VISUAL_DIFF_FREEZE.md
base_branch: main
implementation_branch: codex/l3-mockup-visual-diff-harness
live_behavior_change: false
runtime_behavior_change: false
rendered_ui_behavior_change: false
metrics_attachment: layer3-mockup-visual-diff-metrics.json
```

This pass implements the first deterministic visual-delta harness for `layer3_mockup_workbench_theme`. It does not claim pixel-perfect parity. It proves that repo-local mockup frames can be decoded, mapped to rendered selectors, screenshot in the browser, normalized through the same canvas comparison path, and reported as per-frame visual-delta metrics.

The harness lives in `e2e/layer3-workbench.spec.js` and uses `MOCKUP_VISUAL_DIFF_LIMITS` with browser canvas comparison instead of adding a new image-diff dependency. The repo-local frame authority remains `next_milestone_plans/layer3-mockups/frames/manifest.json`.

## Implemented proof surface

- `frameDataUrl(frame)` reads each repo-local frame from the manifest.
- `compareMockupFrameImages(...)` decodes the reference and rendered screenshots in browser canvas, scales both to the deterministic comparison size, and reports `normalizedMeanDelta` and `highDeltaRatio`.
- `Layer 3 mockup workbench visual diff harness compares repo-local frames` opens `/review/layer3`, selects `layer3_mockup_workbench_theme`, screenshots every manifest selector, compares all eight repo-local frames, and attaches `layer3-mockup-visual-diff-metrics.json`.
- The test keeps the existing no-request-widening guard for source materialization, package mutation, connector dispatch, provider-private URL preparation, and execution start.

## Scope and claim boundary

The current thresholds are calibration thresholds for a working deterministic harness. They are intentionally not a pixel-perfect threshold. A later pixel-refinement pass may tighten `MOCKUP_VISUAL_DIFF_LIMITS` only after the rendered theme is deliberately adjusted toward the repo-local frames.

This pass does not add backend API/model/migration/service behavior change, source runtime, connector/destination dispatch, package mutation, broad qualitative/hybrid/RAG runtime, full durable mockup activation, auth/security widening, or browser-owned durable authority.
