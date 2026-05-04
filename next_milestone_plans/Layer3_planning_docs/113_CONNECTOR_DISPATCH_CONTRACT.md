# Layer 3 Connector Dispatch Contract

## Status

Current-main planning/control contract paired with `112_CONNECTOR_DISPATCH_FREEZE.md`.

This contract defines the minimum admissibility rules for any future connector, destination, or generic downstream dispatch lane. It does not allocate a live route, connector invocation, destination write, connector-run lifecycle, rendered control, provider/public URL, schema/model/migration change, package mutation, qualitative execution, queue behavior, or runtime snapshot write.

## Authority Order

Use this order before auditing or extending connector/destination dispatch behavior:

1. current `project6-origin/main` source and tests;
2. PR `#466` for associated-cohort APS evidence-bundle owner-service dispatch;
3. PR `#479`, PR `#483`, and PR `#487` for readiness, same-origin delivery, and rendered delivery gate authority;
4. PR `#499`, PR `#514`, and PR `#520` for same-origin signed-reference generation/use, rendered controls, and durable backing state;
5. PR `#522` for parser/bridge/provenance residual hardening only;
6. docs `110`/`111` for provider/public URL governance;
7. `112_CONNECTOR_DISPATCH_FREEZE.md` and this contract for connector/destination dispatch governance;
8. actual connector/destination configuration and deployment policy, when a future lane names one.

Browser state, copied links, request-local tokens, provider console observations, destination-console observations, connector-run history outside repo authority, and operator notes are never sufficient authority for enabling connector/destination dispatch behavior.

## Contract Vocabulary

Reserved labels:

- `connector_dispatch_not_admitted`;
- `destination_selection_blocked`;
- `generic_downstream_dispatch_blocked`;
- `internal_dispatch_record_only_candidate`;
- `single_named_connector_dispatch_candidate`;
- `single_named_destination_dispatch_candidate`;
- `connector_dispatch_ready`;
- `connector_dispatch_recorded`;
- `connector_dispatch_failed`.

These labels are not live states by themselves. They may be used only by a later implementation freeze or progress/control sync to classify the next connector/destination lane.

## Dispatch Mode Contract

The first implementation lane must choose exactly one mode:

- `internal_dispatch_record_only`: a server-side control-plane receipt of an operator-approved dispatch intent, without external connector invocation or destination writes.
- `single_named_connector_dispatch`: a server-side invocation of exactly one named connector family, using repo-confirmed connector-run lifecycle authority.
- `single_named_destination_dispatch`: a server-side send/write to exactly one named destination family, using repo-confirmed destination id and credential authority.

The chosen mode must be represented in request/response state. The response must not ambiguously call owner-service APS evidence-bundle handoff, same-origin delivery, same-origin signed-reference generation, or provider/public URL governance a connector dispatch.

## Request Contract

A future connector/destination dispatch request must be server-authority based and must include, or derive server-side from existing state:

- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- selected-pass associated-cohort method and source authority;
- result-review approval record;
- package-review approval and package ids/hashes;
- handoff/export prepare record;
- APS handoff dispatch record;
- external export/download readiness record;
- same-origin delivery authority;
- same-origin signed-reference and durable token/receipt/audit basis when the future lane depends on PR `#520` state;
- selected dispatch mode;
- server-confirmed connector key or destination id, if the selected mode needs one;
- fresh `client_request_id`.

The request must not accept:

- client-supplied connector secrets, destination secrets, credentials, URLs, raw provider paths, local paths, object keys, bucket names, ACLs, or policy documents;
- client-supplied `connector_run_id`, `destination_id`, `connector_key`, or `dispatch_mode` unless the future freeze defines a server-side allowlist and validates the supplied value against it;
- client-supplied `download_url`, `public_url`, `provider_url`, `signed_url`, or `signed_delivery_url`;
- package payload bytes, package mutation fields, source expansion fields, runtime write flags, retry/rerun/recovery/cancel fields, or qualitative execution flags unless separately admitted.

Connector/destination authority must be generated or confirmed by the server only.

## Response Contract

A future response may expose only response-safe connector/destination metadata admitted by the implementation freeze:

- dispatch mode;
- server-confirmed connector family or destination display label;
- lifecycle state;
- receipt id;
- artifact ref/hash/size basis;
- idempotency key status;
- operator-visible next actions;
- failure code and response-safe failure reason.

The response must not expose:

- connector credentials, destination credentials, provider credentials, raw bearer tokens, or signed credential material;
- local filesystem paths;
- raw storage object paths;
- package payload bytes or mutable package content;
- raw connector targets or destination ids unless the future freeze explicitly defines them as response-safe;
- qualitative execution output;
- schema/runtime/source mutation details.

Existing same-origin delivery, same-origin signed-reference, durable signed-reference, and provider/public URL governance responses must remain valid and must not start emitting connector/destination dispatch fields unless the request uses the future admitted connector/destination endpoint or mode.

## Lifecycle Contract

The future lane must define one connector/destination lifecycle before implementation:

- `dispatch_requested`;
- `dispatch_recorded`;
- `dispatch_submitted`;
- `dispatch_succeeded`;
- `dispatch_failed`;
- `dispatch_cancelled`;
- `dispatch_expired`.

The chosen lifecycle must include:

- which states are terminal;
- who can submit, cancel, or retry;
- idempotency key behavior;
- audit event shape;
- stale authority behavior;
- connector/destination failure behavior;
- timeout behavior;
- cleanup and retention expectations.

If retry, cancel, recovery, or queue behavior cannot be made deterministic, the first implementation must use `internal_dispatch_record_only` or another narrower mode rather than silently enabling external dispatch.

## Security Contract

The future lane must fail closed for:

- missing connector/destination configuration;
- missing dispatch authority;
- stale selected-pass/package/handoff/readiness/delivery authority;
- stale artifact hash/size;
- expired or revoked durable signed-reference state when used as a prerequisite;
- connector or destination errors;
- malformed request fields;
- connector/destination leakage into non-admitted responses.

Connector credentials, destination credentials, provider credentials, raw bearer tokens, raw provider signatures, local paths, and package payload bytes must not be logged, persisted in audit payloads, or returned in error bodies.

## Test Contract

Minimum future proof:

- focused backend/API tests for disabled-by-default connector/destination dispatch;
- missing connector/destination configuration fail-closed tests;
- forbidden client connector/destination/provider/URL/package/source fields tests;
- exact authority binding tests across session, plan, pass, package, handoff/export, APS dispatch, readiness, delivery, artifact ref/hash/size, signed-reference, and durable state where applicable;
- idempotency, duplicate request, stale authority, wrong artifact, wrong session, wrong destination, malformed request, connector failure, destination failure, timeout, and cancellation tests;
- no connector/destination/generic dispatch leakage on existing APS handoff, delivery, same-origin signed-reference, durable signed-reference, and provider/public URL governance paths;
- no provider/public URL generation, package mutation, schema/runtime/source widening, qualitative execution, or full mockup side effects;
- headed and headless browser proof if any rendered connector/destination control is admitted.

## Implementation Stop Conditions

Stop and return to planning if implementation would require:

- supporting multiple dispatch modes in one PR;
- invoking an unnamed connector or destination;
- accepting connector/destination ids directly from the browser without a server allowlist;
- adding provider/public URL behavior as a side effect;
- adding retry/cancel/recovery/queue behavior without a specified lifecycle;
- adding schema/model/migration changes outside a named dispatch/audit/receipt contract;
- mutating package payloads or APS evidence-bundle artifact bytes;
- introducing qualitative/hybrid/RAG/vector execution;
- changing PR `#466`, PR `#479`, PR `#483`, PR `#487`, PR `#499`, PR `#514`, or PR `#520` behavior without a compatibility freeze.
