# 1338 SEC XBRL operator API contract gate

Target: `sec_xbrl_operator_api_contract_gate_v1`.

This slice freezes the validate-only contract gate for the operator API. It now
tracks the implemented open-route contract without enabling API behavior by
default. It defines the minimum contract evidence required before the route can
be considered production-admission review evidence.

## Contract requirements

The future operator API must:

- declare the operator-review workflow open route;
- keep the open route disabled by default;
- accept only server-owned redacted authority handles;
- require a server-owned authority resolver;
- require the atomic evidence-to-review service;
- require auth binding;
- keep workflow creation and auth binding under a caller-owned commit boundary;
- require idempotency;
- require rollback on binding or persistence failure;
- expose status as hash/count/state only.

The future operator API must not:

- accept raw operator paths;
- accept raw CompanyFacts payloads;
- accept raw storage payloads;
- return raw values;
- reconstruct authority client-side;
- acquire SEC sources;
- invoke Arelle;
- admit value reveal in the same route.

## Current implementation

The service `layer3_sec_xbrl_operator_api_contract_gate.py` returns
`sec_xbrl_operator_api_contract_ready` only when:

- offline evidence proof capability is ready;
- proof source and result hashes are present;
- atomic persistence is proven;
- every positive contract flag is true;
- every negative contract flag is false;
- request fields are limited to the open-route public contract:
  `client_request_id`, `open_mode`, `operator_decision`, `period_limit`,
  `proof_source_report_hash`, and `operator_review_authority_handle`.

`proof_result_hash` remains proof authority evidence. It is not admitted as a
caller request field on the open route.

Even when ready, the gate keeps:

- `api_route_enabled=false`;
- `operator_review_open_api_route_enabled=false`;
- `rendered_ui_enabled=false`;
- `value_reveal_performed=false`;
- `production_database_touched=false`;
- `production_readiness_claimed=false`.

## Sequencing

This gate should feed the production-admission gate as
`operator_api_contract`. It is not sufficient for production admission by
itself. The current route implementation still requires targeted validation,
server-owned authority resolver wiring, UI controls, controlled value reveal,
rollback/monitoring, runbooks, and real multi-filing evidence authority before
production admission can be backed by current evidence.
