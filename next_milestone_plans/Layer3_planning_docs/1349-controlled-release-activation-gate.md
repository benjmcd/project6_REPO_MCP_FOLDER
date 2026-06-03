# Layer 3 SEC XBRL controlled release activation gate

## Scope

This pass adds a validate-only preflight gate for the deploy-switch boundary
after production release decision review readiness.

The gate does not activate production. It proves that activation preconditions
are explicit and bound to the current production release decision basis before
any separate deploy switch could be considered.

## Required activation evidence

The activation preflight must prove:

- production release decision basis bound;
- deploy-switch owner declared;
- activation window declared;
- feature-flag plan declared;
- runtime-default toggle plan declared;
- API-route enablement plan declared;
- rendered-UI enablement plan declared;
- rollback switch declared;
- monitoring observation window declared;
- post-activation validation declared;
- emergency stop declared;
- change record recorded.

The activation preflight must also prove the negative invariants:

- activation is not executed by the gate;
- auto-activation is not enabled;
- runtime defaults are not enabled;
- API route is not enabled;
- rendered UI is not enabled;
- value reveal is not performed;
- source acquisition is not performed;
- Arelle is not invoked;
- network is not performed;
- production database state is not touched;
- production readiness is not claimed;
- stale release decisions are not accepted.

## Release-decision binding

The gate requires:

- `status=sec_xbrl_production_release_decision_gate_review_ready`;
- `production_release_decision_review_ready=true`;
- `production_release_executed=false`;
- a valid `production_release_decision_basis_hash`;
- the activation spec's `production_release_decision_basis_hash` to match the
  current release decision basis.

This prevents stale activation plans from floating across release decision basis
changes.

## Validation relationship

The targeted-validation gate now requires
`controlled_release_activation_gate_tests`.

## Non-claims

Even when preflight-ready, this gate keeps:

- `controlled_release_activation_executed=false`;
- `production_release_executed=false`;
- `activation_executed_by_gate=false`;
- `runtime_default_enabled=false`;
- `api_route_enabled=false`;
- `rendered_ui_enabled=false`;
- `value_reveal_performed=false`;
- `production_database_touched=false`;
- `production_readiness_claimed=false`.

## API projection

`POST /api/v1/layer3/sec-xbrl/controlled-release/activation/status` exposes this
gate as a read-only operator status projection. The route returns the activation
preflight report and marks only the status API route as enabled. It does not
execute activation, expose a deploy switch, enable runtime defaults, enable SEC
XBRL API/UI behavior, perform value reveal, or touch production database state.
