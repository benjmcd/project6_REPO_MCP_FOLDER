# Layer 3 SEC XBRL production release decision gate

## Scope

This pass adds a validate-only gate for the controlled production release
decision that follows production-admission review readiness.

The gate does not execute a release. It proves that a release decision package is
coherently bound to the current admission basis and that release governance is
present before any separate deployment switch could be considered.

## Required release evidence

The release decision must prove:

- release decision recorded;
- release owner declared;
- admission basis bound;
- target release scope declared;
- rollback plan bound;
- monitoring plan bound;
- runbook acknowledged;
- targeted validation bound;
- default-off until a separate deploy switch;
- operator reauthorization required;
- post-release observation required.

The release decision must also prove the negative invariants:

- auto-release is not enabled;
- the gate does not execute release;
- runtime defaults are not enabled;
- API route and rendered UI are not enabled by the gate;
- value reveal is not performed;
- source acquisition is not performed;
- Arelle is not invoked;
- network is not performed;
- production database state is not touched;
- production readiness is not claimed.

## Admission binding

The gate requires:

- `status=layer3_sec_xbrl_production_admission_review_ready`;
- `production_admission_review_ready=true`;
- `production_admission_admitted=false`;
- a valid `admission_basis_hash`;
- the release decision's `admission_basis_hash` to match the current admission
  basis.

This prevents the project from treating admission review readiness as a release
action and prevents stale release decisions from floating across admission
basis changes.

## Activation relationship

A separate controlled release activation gate must bind to this gate's
`production_release_decision_basis_hash` before any deploy-switch preflight can
be considered ready. Release decision review readiness is necessary but not
sufficient for activation.

## Operational relationship

The runbook gate now requires `production_release_rollback`.

The targeted-validation gate now requires
`production_release_decision_gate_tests`.

The targeted-validation gate also requires
`controlled_release_activation_gate_tests`.

## Non-claims

Even when ready, this gate keeps:

- `production_release_executed=false`;
- `release_executed_by_gate=false`;
- `runtime_default_enabled=false`;
- `api_route_enabled=false`;
- `rendered_ui_enabled=false`;
- `value_reveal_performed=false`;
- `production_database_touched=false`;
- `production_readiness_claimed=false`.

## API projection

`POST /api/v1/layer3/sec-xbrl/production-release/decision/status` exposes this
gate as a read-only operator status projection. The route returns the gate
report and marks only the status API route as enabled. It does not execute
release, enable runtime defaults, enable SEC XBRL API/UI behavior, perform value
reveal, or touch production database state.
