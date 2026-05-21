# 949 - Sublayers 3A/3B Read-Only Projection Contract

## Status

Status: branch-local activation-readiness projection contract for `sublayers_3a_3b_read_only_live_projection_contract`.

Predecessor contract: `948-pdf-location-read-only-projection-contract.md`.

Current main authority: `project6-origin/main` at `9243d966319cc38eb9adfa7e112b473ef4bdf66b` (`9243d966 Add PDF location projection contract`).

Implementation branch: `codex/l3-sublayers-ab-projection-contract`.

Selected projection slice: `sublayers_3a_3b_read_only_live_projection_contract`.

## Scope

This slice makes the existing Sublayers 3A/3B mockup journey explicit as a read-only live projection contract. It does not promote Sublayers 3A/3B to an interactive edit or drilldown journey.

The contract is grounded in:

- `State.sessionSummary.sublayer_visualization`;
- `State.materialPreview`;
- `State.gateB`;
- `State.gateC`;
- `layer3.sublayer_visualization_state.v1`;
- `#mockup-sublayers-ab-projection`.

## Non-Admission Boundary

This slice does not admit raw local file path exposure, provider or object-store URL exposure, provider-private URL projection, output payload or diagnostics references, runtime request widening, frontend-only durable authority, route/model/migration changes, connector/provider writes, or full mockup program activation.

## Verification

Targeted verification for this branch must prove:

- the activation-readiness bootstrap contract exposes `sublayers_3a_3b_read_only_live_projection_contract`;
- the `sublayers_3a_3b` journey remains `read_only`;
- the rendered activation-readiness dashboard shows the Sublayers 3A/3B projection contract;
- the existing Sublayers 3A/3B projection continues to render available and unavailable server state without controls, links, local storage authority, API requests, or forbidden URL/file/path leakage.

## Next Posture

After this branch is merged and synced to current main, select Sublayer 3C execution lanes as the next read-only projection contract unless current-main evidence identifies a narrower still-uncontracted projection gap.
