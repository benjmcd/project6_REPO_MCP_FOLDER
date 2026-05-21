# Layer 3 Sublayer 3C Read-Only Projection Contract

Status: branch-local activation-readiness projection contract.

Current-main authority before this branch: `project6-origin/main` at `66435b86 Add Sublayers AB projection contract (#1574)`.

## Selected Slice

`sublayer_3c_execution_lanes_read_only_live_projection_contract`

This slice promotes the existing rendered Sublayer 3C execution-lanes projection into the server-owned mockup activation-readiness contract. The journey remains `read_only`; it does not admit execution start, analysis-run mutation, package construction, connector/provider dispatch, frontend-only durable authority, runtime request widening, or full mockup program activation.

## Server Authority

The projection is grounded in:

- `layer3.analysis_environment_projection.v1`
- `read_only_session_summary_analysis_environment_execution_projection`
- `State.sessionSummary.sublayer_visualization`
- `State.sessionSummary.analysis_environment_projection`
- `State.sessionSummary.plan_preview`
- `State.sessionSummary.plan_approval`
- `State.sessionSummary.execution_selection`
- `State.sessionSummary.analysis_execution_start`
- `State.sessionSummary.execution_result_review`
- `State.planPreview`
- `State.planApproval`
- `State.executionSelection`
- `State.executionStart`
- `State.resultStatus`
- `State.resultReview`
- `#mockup-execution-lanes-projection`

The rendered surface is read-only and must not include `button`, `input`, `select`, `textarea`, or `a[href]` controls inside the 3C projection panel.

## Blocked Boundaries

- `execution_start_side_effect`
- `analysis_run_mutation`
- `raw_execution_payload_exposure`
- `output_payload_ref_exposure`
- `diagnostics_ref_exposure`
- `package_construction_or_mutation`
- `connector_provider_write`
- `provider_or_object_store_url_exposure`
- `frontend_only_durable_authority`
- `runtime_request_widening`
- `full_mockup_program_activation`

## Verification Expectations

- Python compile of the activation-readiness service.
- Focused backend service/API/static route tests.
- Headless Chromium proof for activation-readiness dashboard plus 3C rendered projection.
- Headed Chromium proof for the same rendered path.
- JSON manifest validation.
- `python ./tools/l3-progress-check.py`.

## Next Posture

After this branch is merged and synced to current main, select the next Analysis Environment/mockup projection gap before attempting any full mockup activation or new execution-lane interactivity.
