# Layer 3 SEC XBRL controlled release status API

## Scope

This pass adds read-only operator status projections for the controlled release
decision and controlled release activation preflight gates.

## Routes

- `POST /api/v1/layer3/sec-xbrl/production-release/decision/status`
- `POST /api/v1/layer3/sec-xbrl/controlled-release/activation/status`

Both routes accept redacted hash/count/state evidence packages and return gate
reports. They do not persist receipts, record auth bindings, mutate workflow
state, execute release, execute activation, expose a deploy switch, perform
value reveal, or touch production database state.

## Purpose

The release decision and activation preflight gates are useful only if operators
can inspect their current status. These routes make that evidence visible
without collapsing the distinction between:

- production admission review readiness;
- production release decision review readiness;
- controlled activation preflight readiness;
- actual release or activation execution.

## Non-claims

The status routes keep:

- `runtime_default_enabled=false`;
- `api_route_enabled=false`;
- `rendered_ui_enabled=false`;
- `value_reveal_performed=false`;
- `production_database_touched=false`;
- `production_readiness_claimed=false`.

## Validation relationship

The targeted-validation gate now requires
`controlled_release_status_api_tests` before validation readiness can be claimed.
