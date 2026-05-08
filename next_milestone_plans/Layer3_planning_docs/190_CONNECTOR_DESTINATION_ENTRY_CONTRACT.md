# Connector/Destination Dispatch Entry Contract

Status: planning/control contract paired with `189_CONNECTOR_DESTINATION_ENTRY_FREEZE.md`.

This contract defines the exact requirements for moving beyond the deferred `connector_destination_dispatch_entry_freeze` decision. It admits no new connector/destination runtime, external connector invocation, destination write, connector-run creation, generic downstream dispatch, route, DTO, service behavior, model, migration, connector adapter, destination adapter, provider/public URL runtime, rendered UI control, test behavior, package mutation, source expansion, RAG/vector retrieval, full mockup activation, hidden LLM planning, or auth/security behavior change.

Docs `112_CONNECTOR_DISPATCH_FREEZE.md` and `113_CONNECTOR_DISPATCH_CONTRACT.md` remain historical connector/destination governance. Doc `121_CONNECTOR_DISPATCH_ENTRY_FREEZE.md` remains authority for the already-live `internal_dispatch_record_only` runtime. Docs `184` through `188` remain the broader post-signed-reference and provider/public URL governance chain. This contract is the narrower post-PR #749 external connector/destination entry-decision layer.

## Authority Order

1. live `project6-origin/main` source, tests, models, migrations, routes, service code, and checker behavior;
2. `121_CONNECTOR_DISPATCH_ENTRY_FREEZE.md` and `backend/app/services/layer3_connector_dispatch_entry.py` for the already-admitted `internal_dispatch_record_only` runtime;
3. rendered signed-reference proof in `e2e/layer3-workbench.spec.js`;
4. docs `181`, `182`, and `183` for rendered signed-reference freeze, contract, and proof;
5. docs `184` and `185` for post-745 downstream expansion ordering;
6. docs `187` and `188` for deferred provider/public URL entry decision;
7. this contract and `189_CONNECTOR_DESTINATION_ENTRY_FREEZE.md`.

Planning prose, browser state, copied URLs, provider or destination console observations, connector-run history outside repo authority, local fixture state, or prior PR titles are not sufficient authority for runtime implementation.

## Entry Decision Contract

The current entry decision is:

```yaml
entry_decision: deferred
selected_mode: null
runtime_status: not_implemented
live_internal_record_only_status: already_admitted_by_doc_121
receipt_family: no_receipt_planning_only
```

The decision may change only in a later freeze if all of these are repo-confirmed:

- concrete named downstream use case proving same-origin delivery, same-origin signed references, provider/public URL governance, and existing internal record-only behavior are insufficient;
- selected artifact family;
- selected connector or destination family;
- connector/destination authority and configuration;
- credential and access authority;
- lifecycle, retry, cancel, timeout, and idempotency contract;
- stale-authority failure plan;
- audit and receipt contract;
- leak-control posture;
- fake connector/destination test architecture by default;
- no-cross-mode privilege escalation proof.

## Allowed Future Modes

A later runtime freeze must choose exactly one of:

- `single_named_connector_dispatch`;
- `single_named_destination_dispatch`;
- `internal_dispatch_record_only_extension`.

The selected mode must be represented unambiguously in any future request/response schema. Existing `internal_dispatch_record_only`, APS handoff dispatch, same-origin attachment delivery, same-origin signed-reference delivery, and deferred provider/public URL governance must not be renamed or represented as external connector/destination dispatch.

## Request Contract For Later Runtime

A future connector/destination request must be server-authority based. It may include or derive server-side:

- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- selected source authority;
- result-review authority;
- package-review submit authority;
- package construction authority;
- handoff/export prepare authority;
- APS handoff dispatch authority;
- external export/download prepare authority;
- same-origin delivery authority if used;
- signed-reference authority only if the future freeze explicitly uses it as a prerequisite;
- internal dispatch record authority only if the future freeze explicitly uses it as a prerequisite;
- artifact ref, hash, and size authority;
- selected connector/destination mode;
- fresh idempotency key or `client_request_id`.

The request must not accept:

- connector credentials, destination credentials, provider credentials, bearer tokens, secrets, raw connector targets, raw destination URLs, bucket names, object keys, ACLs, or policy documents from the browser;
- client-supplied `connector_key`, `destination_id`, `connector_run_id`, or `dispatch_mode` unless a later freeze defines a server-side allowlist and validates the supplied value against it;
- client-supplied `download_url`, `public_url`, `provider_url`, `signed_url`, or `signed_delivery_url`;
- local file paths, local upload payloads, local-directory paths, arbitrary path input, or source expansion fields;
- package payload bytes, package mutation fields, replacement fields, supersession fields, retry/rerun/recovery/cancel fields, RAG/vector fields, broad qualitative fields, hidden LLM fields, auth/security fields, or full mockup activation fields.

## Response Contract For Later Runtime

A future response may expose only response-safe metadata admitted by the later runtime freeze:

- selected mode;
- server-confirmed connector or destination display label;
- lifecycle state;
- receipt id or audit ref;
- artifact ref/hash/size basis;
- idempotency key status;
- operator-visible next actions;
- failure code and response-safe failure reason.

The response must not expose connector credentials, destination credentials, provider credentials, raw bearer tokens, raw signatures, local filesystem paths, raw storage object paths, raw connector targets, raw destination URLs, package payload bytes, source expansion state, qualitative output, auth internals, or connector/destination fields on existing same-origin delivery, signed-reference, provider/public URL governance, or internal record-only responses unless a later compatibility freeze admits it.

## Existing Internal Record Compatibility Contract

This entry freeze must preserve the existing `internal_dispatch_record_only` runtime:

- `/api/v1/layer3/handoff/connector/record` remains the bounded internal record-only endpoint;
- `backend/app/services/layer3_connector_dispatch_entry.py` remains the owner service;
- `connector_dispatch_recorded` remains an internal control-plane receipt state;
- `external_connector_invocation_enabled`, `destination_write_enabled`, `connector_run_created`, and `provider_public_url_enabled` remain false for that response;
- no external connector invocation or destination write may be inferred from an internal record.

Any future external connector/destination runtime must either treat the internal record as independent historical authority or define an explicit compatibility rule in a later freeze.

## Connector/Destination Non-Contract

Connector/destination work is not provider/public URL generation, provider object materialization, package mutation, source ingestion, RAG/vector execution, hidden LLM planning, auth/security hardening, or full mockup activation.

The first external runtime lane must not be generic dispatch and must not support multiple connector/destination modes in one PR.

## Security And Access Contract

A later runtime freeze must fail closed for:

- missing connector/destination configuration;
- missing credential authority;
- missing operator access authority;
- stale session, plan, pass, result review, package review, package construction, package submit, handoff/export, APS dispatch, external export/download prepare, same-origin delivery, signed-reference prerequisite, internal dispatch record prerequisite, artifact ref, artifact hash, or artifact size;
- wrong session, wrong package, wrong artifact, wrong connector, wrong destination, wrong idempotency key, malformed request, forbidden field, connector failure, destination failure, timeout, cancellation, duplicate dispatch, or replay outside the selected policy.

Connector credentials, destination credentials, provider credentials, full bearer URLs, raw tokens, raw signatures, raw targets, and local paths must not appear in logs, error bodies, screenshots, traces, audit payloads, or response fields unless a later freeze names a safe redaction policy.

## Browser And UI Contract

This entry freeze adds no rendered UI control. If a later freeze admits rendered connector/destination controls, it must:

- preserve `light` for status, preview, and review inspection;
- preserve `dark` for execution and package construction surfaces;
- preserve `workbench` for package submit, handoff/export, APS handoff, external export/download, signed-reference, provider/public URL governance, and downstream operation-dock flows;
- prove headed and headless Chromium consistency;
- prove no target-state mockup control appears as live durable authority;
- define destination labels, disabled/ready/failed states, redaction behavior, and no-credential exposure behavior.

## Test Contract For Later Runtime

Runtime implementation remains blocked until a later freeze names tests for:

- disabled-by-default external connector/destination behavior;
- missing connector/destination configuration fail-closed behavior;
- fake connector or destination adapter by default;
- connector error, destination error, timeout, duplicate, retry, and cancel simulation if those behaviors are admitted;
- forbidden URL/provider/connector/destination/package/source/RAG/auth/mockup fields;
- exact authority binding;
- stale authority failure cases;
- no credential, token, target, destination, URL, or receipt leakage in logs, error bodies, traces, screenshots, existing same-origin responses, existing internal record responses, or proof manifests;
- no provider/public URL runtime, package mutation, source expansion, RAG/vector retrieval, full mockup activation, hidden LLM, auth/security behavior change, or frontend-only durable authority;
- headed and headless rendered proof if UI changes are admitted.

Real connector and destination credentials are forbidden in CI by default.

## Checker Contract

`tools/l3-progress-check.py` should verify structural guardrails only:

- docs `189` and `190` exist and are referenced;
- entry decision is `deferred`;
- selected mode is null;
- runtime status is `not_implemented`;
- the already-live internal record-only boundary is acknowledged without being expanded;
- evidence ledger exists and unverified external connector/destination authority forces deferral;
- dispatch exposure model exists and unknown values force deferral;
- capability isolation matrix exists and all new runtime flags remain false;
- negative invariants are present;
- docs do not claim external connector invocation, destination writes, connector-run creation, or generic downstream dispatch is live;
- docs do not conflate internal record-only, APS handoff dispatch, same-origin delivery, same-origin signed-reference, or provider/public URL governance with external connector/destination dispatch;
- docs do not admit provider/public URLs, provider object writes/copies, package mutation, source expansion, RAG/vector retrieval, auth/security changes, full mockup activation, or rendered controls.

The checker must not pretend to validate real connector credentials, destination credentials, connector APIs, destination APIs, retries, cancellations, queues, external network behavior, or real dispatch receipts in this planning-only pass.

## Stop Conditions

Stop and return to planning if a future implementation proposal tries to:

- implement more than one connector/destination mode;
- invoke an unnamed connector or destination;
- emit connector/destination fields on existing same-origin attachment, signed-reference, provider/public URL governance, or internal record-only routes without compatibility freeze;
- accept connector or destination credentials from the client;
- create connector runs or destination writes without lifecycle and access authority;
- add provider/public URL behavior as a side effect;
- mutate packages, rewrite package payloads, or supersede packages;
- expand source classes, local upload, local-directory ingestion, web retrieval, RAG/vector retrieval, or broad qualitative execution;
- add rendered controls without a rendered implementation-entry freeze and headed/headless proof;
- alter auth/security behavior without an auth/security freeze.
