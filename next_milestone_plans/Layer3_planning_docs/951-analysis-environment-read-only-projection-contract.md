# Layer 3 Analysis Environment Read-Only Projection Contract

Status: current-main synced activation-readiness projection contract.

Current-main authority before this branch: `project6-origin/main` at `fd0c5df1 Add Sublayer 3C projection contract (#1575)`.

Current-main sync: PR `#1576` merged as `2bbb1976 Add Analysis Environment projection contract (#1576)`.

## Selected Slice

`analysis_environment_read_only_live_projection_contract`

This slice closes the next Analysis Environment/mockup projection gap after the Sublayer 3C execution-lanes contract. It promotes the existing `.analysis-environment-projection` rendered reader into the server-owned mockup activation-readiness contract. The journey remains `read_only`; it does not admit execution start, analysis-run mutation, package construction, connector/provider dispatch, frontend-only durable authority, runtime request widening, or full mockup program activation.

## Server Authority

The projection is grounded in:

- `layer3.analysis_environment_projection.v1`
- `read_only_session_summary_analysis_environment_plane_projection`
- `State.sessionSummary.analysis_environment_projection`
- `State.sessionSummary.sublayer_visualization`
- `State.planPreview`
- `State.planApproval`
- `State.executionSelection`
- `State.executionStart`
- `State.resultStatus`
- `State.resultReview`
- `.analysis-environment-projection`

The rendered surface is read-only and must not include `button`, `input`, `select`, `textarea`, or `a[href]` controls inside the Analysis Environment projection panels.

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
- Headless Chromium proof for activation-readiness dashboard plus Analysis Environment rendered projection.
- Headed Chromium proof for the same rendered path.
- JSON manifest validation.
- `python ./tools/l3-progress-check.py`.

## Next Posture

Record the bounded trial-usable checkpoint before adding any Analysis Environment interactivity or attempting full mockup activation.
