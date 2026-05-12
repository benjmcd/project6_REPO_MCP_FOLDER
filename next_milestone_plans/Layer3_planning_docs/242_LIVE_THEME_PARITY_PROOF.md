# Layer 3 Live Theme Parity Proof

Status: test-only proof for `live_theme_parity_proof`.

This document records the bounded live-theme parity proof admitted by `236_THEME_E2E_MATRIX.md`, `237_THEME_ENTRY_FREEZE.md`, and `238_LAYER3_THEME_TO_FULL_PIPELINE_SYNTHESIS.md`. It adds no runtime behavior.

## Authority boundary

```yaml
route: /review/layer3
status: live
theme_set:
  - system
  - light
  - dark
  - workbench
claude_status: excluded_prototype_only
implementation_branch: codex/l3-theme-parity-proof
live_behavior_change: false
production_backend_change: false
production_ui_change: false
model_or_migration_change: false
```

The live source of truth is the existing `/review/layer3` route and its server-authoritative Layer 3 API flow. The Claude route remains a static prototype and is not included in this proof.

## Implemented proof

The proof updates `e2e/layer3-workbench.spec.js` only. It adds a reusable `LIVE_LAYER3_THEMES` list and `expectLiveThemeParityCheckpoint` helper, then applies that helper to the canonical rendered signed-reference path:

```text
Layer 3 workbench drives raw mixed rendered external export download signed reference
```

The checkpoint coverage is:

- `materialized-source-selection` with `#source-fieldset` as the active visible surface;
- `signed-reference-delivered` with `#external-export-download-signed-reference-panel` as the active visible surface.

At each checkpoint, the helper switches through `system`, `light`, `dark`, and `workbench`, verifies the selector and `html[data-theme-preference]`, verifies the checkpoint-specific visible surface, verifies stable live workbench surfaces remain present, verifies non-admitted provider/private connector/package-mutation controls remain absent, and restores the entry theme before the next flow step.

Restoring the entry theme is part of the proof contract. It prevents theme parity observation from changing the existing workflow's visible-step semantics.

## Validation

The proof was run in both browser modes required by the theme entry freeze:

```text
npx playwright test e2e/layer3-workbench.spec.js --grep "external export download signed reference" --project=chromium
npx playwright test e2e/layer3-workbench.spec.js --grep "external export download signed reference" --project=chromium --headed
```

Both targeted runs passed for the same canonical rendered signed-reference path.

## What this proves

- The existing live `/review/layer3` route can traverse the maximum currently supported rendered raw-mixed path through same-origin signed-reference delivery while live theme preferences are switched at stable checkpoints.
- Theme selection remains presentation-only for this path; the existing request-shape assertions in the canonical test continue to govern payload shape.
- The live theme set for this proof is exactly `system`, `light`, `dark`, and `workbench`.
- Claude is intentionally excluded because it remains prototype-only until a separate admission freeze exists.
- The proof is reusable because the theme list and checkpoint helper are separated from source setup and API progression.

## What this does not prove

- It does not admit Claude as a live theme.
- It does not prove every possible viewport, page, or future route.
- It does not add rendered provider-private signed URL controls.
- It does not implement provider-private signed URL `use`.
- It does not add backend routes, DTOs, services, models, migrations, provider network writes, provider/public URLs, connector/destination dispatch, source expansion, package mutation/reconstruction, broad qualitative/hybrid/RAG runtime, hidden LLM planning, full mockup activation, auth/security behavior, or frontend-only durable authority.

## Future matrix work

Future theme work should expand the same helper or an equivalent parameterized matrix across additional admitted page/theme rows. It should not copy scenario scripts or make a theme-specific runtime branch. If a future row requires new runtime behavior, it needs a separate implementation-entry freeze before code changes.

## Stop condition

Stop before implementation if parity work requires Claude runtime admission, backend/API behavior changes, source-family expansion, provider-private rendered controls, public/proxy URL behavior, connector/destination delivery, package mutation, auth/security changes, or using browser/local-storage state as durable authority.
