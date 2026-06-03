# 1339 SEC XBRL operator UI controls gate

Target: `sec_xbrl_operator_ui_controls_gate_v1`.

This slice defines a validate-only gate for future operator UI controls. It does
not render a UI, add a route, or enable value reveal. It defines what the UI must
prove before the production-admission gate can treat UI readiness as satisfied.

## Required UI behavior

The eventual UI must:

- depend on a ready operator API contract;
- fetch data only through the admitted API;
- display only server-owned redacted authority handles;
- use redacted labels and hash/count/state status;
- keep operator decision controls separate from value reveal;
- hide value reveal controls in the review UI;
- visibly block unsafe controls;
- expose accessible labels for admitted controls.

The UI must not:

- render raw values;
- render raw authority references;
- render local paths;
- reconstruct authority client-side;
- enable source acquisition;
- enable Arelle invocation;
- enable value reveal in the review UI;
- enable runtime default toggles.

## Required blocked controls

The gate requires the future UI contract to explicitly block:

- `reveal_values`;
- `refresh_from_sec_source`;
- `invoke_arelle`;
- `change_runtime_default`;
- `edit_statement_packet`.

## Current boundary

The service `layer3_sec_xbrl_operator_ui_controls_gate.py` can report
`sec_xbrl_operator_ui_controls_ready` as a contract signal, but it still reports:

- `rendered_ui_enabled=false`;
- `api_route_enabled=false`;
- `value_reveal_performed=false`;
- `production_database_touched=false`;
- `production_readiness_claimed=false`.

This keeps UI contract readiness separate from actual UI implementation. The
next UI slice must render controls against the admitted API only after the API
route exists and has its own rollback/auth/idempotency evidence.
