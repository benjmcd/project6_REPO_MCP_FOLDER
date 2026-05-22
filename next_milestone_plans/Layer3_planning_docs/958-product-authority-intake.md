# 958 - Product Authority Intake After Bounded Trial Evidence

## Status

Status: no-runtime product-authority intake checkpoint after the current-main bounded trial evidence refresh.

Doc: `958-product-authority-intake.md`.

Current-main authority before this branch: `project6-origin/main` at `8a0a3027 Record Layer 3 runbook evidence refresh (#1583)`.

Predecessor closure sync: `957-trial-readiness-sync.md`.

Decision: do not select a new implementation slice from this checkpoint alone. The next implementation pass requires a named product-authority answer, a concrete failed proof/remediation target, or a product objective outside blanket full mockup activation.

Runtime behavior introduced by this checkpoint: `false`.

Rendered behavior introduced by this checkpoint: `false`.

Backend behavior introduced by this checkpoint: `false`.

Route/API/DTO/model/migration/service behavior introduced by this checkpoint: `false`.

Executable test behavior introduced by this checkpoint: `false`.

Implementation-entry allowed by this checkpoint alone: `false`.

Full mockup program activation selected now: `false`.

Frontend-only durable authority selected now: `false`.

## Current-Main Basis

Current main now proves and records the bounded operator runbook evidence in `957-trial-readiness-sync.md`.

Current main also preserves these classifications from `backend/app/services/layer3_mockup_activation_readiness.py::build_mockup_activation_readiness`:

- `query_source_setup`: `interactive_live`;
- `output_review_package_handoff`: `interactive_live`;
- `pdf_location`: `read_only`;
- `sublayers_3a_3b`: `read_only`;
- `sublayer_3c_execution_lanes`: `read_only`;
- `analysis_environment_projection`: `read_only`;
- `full_mockup_program`: `blocked`.

Because the bounded trial evidence is current-main recorded and no failed check, rendered proof, open PR, or review-thread blocker remains, the next useful work is a product-authority decision, not speculative runtime implementation.

## Required Product Authority Answer

Before a new implementation pass, one of these authority answers must be current-main recorded:

1. Full mockup activation is selected as the next phase.
2. One named read-only journey is selected for a journey-specific interactive authority freeze.
3. One named already-live journey is selected for a bounded extension of existing server-owned controls.
4. A separate product objective outside blanket full mockup activation is selected.
5. No new product phase is selected; the bounded trial checkpoint remains the stop state.

If the answer is absent or ambiguous, stop at this checkpoint.

## Decision Matrix

| Product answer | Next admissible pass | Required proof before implementation |
| --- | --- | --- |
| Full mockup activation | Governed full-activation freeze only | product decision, rollback/disable authority, journey ownership, full proof matrix, no frontend-only durable authority by default |
| PDF location interaction | Single-journey freeze for `pdf_location` | server-owned route/API contract, rendered-control boundary, rollback, headed/headless proof, no raw path/file exposure |
| Sublayers 3A/3B interaction | Single-journey freeze for `sublayers_3a_3b` | server-owned edit/drilldown authority, projection-to-control boundary, rollback, headed/headless proof |
| Sublayer 3C execution-lane interaction | Single-journey freeze for `sublayer_3c_execution_lanes` | server-owned lane-control authority, no hidden execution widening, rollback, headed/headless proof |
| Analysis Environment interaction | Single-journey freeze for `analysis_environment_projection` | server-owned interaction contract, no frontend durable state, no hidden model/provider execution, rollback, headed/headless proof |
| Existing query/source setup extension | Extension freeze for `query_source_setup` | explicit route/API delta, no broad source/RAG/provider expansion, rollback, headed/headless proof |
| Existing output/package/handoff extension | Extension freeze for `output_review_package_handoff` | explicit route/API delta, payload/provider/credential redaction proof, rollback, headed/headless proof |
| Separate product objective | Objective-specific freeze | canonical source of truth, exact admitted scope, rollback/no-go/proof boundaries |
| No phase selected | Stop state | no implementation; continue preserving bounded trial evidence |

## Default Rejections

Reject these by default unless a later product-authority record explicitly admits them with rollback and proof:

- frontend-only durable authority;
- browser storage as authority;
- full mockup activation by inference;
- raw provider URL, provider token, local path, file bytes, object ref, output payload ref, diagnostics ref, destination credential, signed URL, or public URL exposure;
- unapproved connector/provider writes;
- route/API/DTO/model/migration/service widening outside the named decision;
- broad source-family, model-provider, RAG, vector, or hidden LLM planning expansion;
- read-only projection controls without a named server-owned route/API contract.

## Stop Conditions

Stop before implementation if:

- the product-authority answer is missing, ambiguous, or names more than one next implementation target;
- the selected journey is not classified as live, read-only, intentionally excluded, or blocked in current-main evidence;
- full mockup activation is requested without a governed activation freeze and rollback plan;
- frontend-only durable authority is required;
- rollback cannot return to the bounded trial state recorded by `957-trial-readiness-sync.md`;
- headed and headless proof requirements are not accepted for the selected journey;
- `python ./tools/l3-progress-check.py` cannot prove the current bounded trial state.

## Next Posture

Next exact posture: `await_product_authority_for_named_layer3_next_phase_or_stop_at_bounded_trial_checkpoint`.

