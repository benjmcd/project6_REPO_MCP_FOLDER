# Layer 3 Mockup Visual Diff Freeze

Status: planning/control freeze for pixel-faithful mockup visual parity proof.

```yaml
selected_proof_mode: repo_local_mockup_frame_visual_diff_acceptance
base_branch: main
implementation_branch: codex/l3-mockup-visual-diff-freeze
live_behavior_change: false
runtime_behavior_change: false
rendered_ui_behavior_change: false
next_allowed_action: implement_repo_local_mockup_visual_diff_harness
frame_manifest_authority: next_milestone_plans/layer3-mockups/frames/manifest.json
```

This freeze names the next visual-proof slice for the dedicated `layer3_mockup_workbench_theme`. The current mockup theme has rendered frame projection and a server-backed PDF-location projection, but it must not be called pixel-perfect until a repo-local visual-diff harness compares rendered theme surfaces against the repo-local mockup frame authority.

The source of truth for frame identity, dimensions, and rendered selector mapping is `next_milestone_plans/layer3-mockups/frames/manifest.json`, not the original Downloads directory. The Downloads paths remain provenance only.

## Required next harness behavior

- launch the existing `/review/layer3` mockup theme in headed and headless Chromium;
- select `layer3_mockup_workbench_theme` without adding backend API/model/migration/service behavior change;
- capture the already-mapped rendered surfaces for user-flow/PDF-location, Sublayer 3A/3B, and Sublayer 3C;
- compare those captures against repo-local mockup frame authority through a deterministic tolerance policy;
- write test artifacts only through the existing test-artifact mechanism, not repo-tracked generated screenshots unless a later freeze explicitly admits baselines;
- keep static explanatory text and known non-functional text boxes out of functional-runtime claims;
- fail closed when a frame manifest entry is missing, a rendered selector is missing, a screenshot is empty, or headed/headless coverage is absent.

## Required acceptance dimensions

- `frame_manifest_authority`: every compared frame must come from `next_milestone_plans/layer3-mockups/frames/manifest.json`.
- `selector_authority`: every rendered surface must use the frame manifest's `rendered_projection.selector`.
- `browser_matrix`: headed and headless Chromium must both run or the proof is incomplete.
- `viewport_matrix`: desktop and 390 px responsive no-horizontal-overflow proof must remain covered.
- `failure_policy`: missing frame, missing selector, empty screenshot, image decode failure, and over-tolerance visual delta must fail the proof.
- `scope_policy`: the harness must not seed runtime state, mutate data, add a new API call, widen backend behavior, or treat browser storage as durable authority.

## Explicit non-goals

- no backend API/model/migration/service behavior change;
- no new source runtime or source breadth expansion;
- no connector/destination dispatch;
- no package mutation or package reconstruction;
- no broad qualitative/hybrid/RAG runtime;
- no full durable mockup activation;
- no auth/security widening;
- no claim that current rendered theme is pixel-perfect before the visual-diff harness exists and passes.

## Review-debt settlement authority clarifications

- The frame manifest remains authoritative for frame identity, source path, repository path, checksum, size, and `rendered_projection`; raw width/height dimensions are image-decode observations captured by the harness, not standalone manifest fields.
- Shared rendered selectors are allowed only when each frame has a distinct `rendered_projection` capture record. The harness must record per-frame capture state by projection id so different frames mapped to the same selector cannot collapse into a single undifferentiated screenshot.
- `rendered_ui_behavior_change` remains `false` for this freeze; the freeze defines the proof contract and does not alter rendered UI behavior by itself.
