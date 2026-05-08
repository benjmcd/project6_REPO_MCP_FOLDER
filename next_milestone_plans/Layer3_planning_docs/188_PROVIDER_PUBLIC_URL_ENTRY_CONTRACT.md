# Provider/Public URL Entry Contract

Status: planning/control contract paired with `187_PROVIDER_PUBLIC_URL_ENTRY_FREEZE.md`.

This contract defines the exact requirements for moving beyond the deferred `provider_public_url_entry_freeze` decision. It admits no provider/public URL runtime, route, DTO, service behavior, model, migration, provider adapter, provider config, rendered UI control, test behavior, connector dispatch, package mutation, source expansion, RAG/vector retrieval, full mockup activation, hidden LLM planning, or auth/security behavior change.

Docs `110_PROVIDER_URL_FREEZE.md` and `111_PROVIDER_URL_CONTRACT.md` remain historical provider/public URL governance. Docs `184_POST_745_DOWNSTREAM_EXPANSION_FREEZE.md` and `185_POST_745_DOWNSTREAM_EXPANSION_CONTRACT.md` remain the broader post-signed-reference roadmap. This contract is the narrower post-PR #748 entry-decision layer.

## Authority Order

1. live `project6-origin/main` source, tests, models, migrations, routes, service code, and checker behavior;
2. rendered signed-reference proof in `e2e/layer3-workbench.spec.js`;
3. docs `181`, `182`, and `183` for rendered signed-reference freeze, contract, and proof;
4. docs `184` and `185` for post-745 downstream expansion ordering;
5. docs `110` and `111` for older provider/public URL governance;
6. this contract and `187_PROVIDER_PUBLIC_URL_ENTRY_FREEZE.md`;
7. the external V6 assurance pack only as non-authoritative reference context.

Planning prose, browser state, copied URLs, provider console observations, local fixture state, or prior PR titles are not sufficient authority for runtime implementation.

## Entry Decision Contract

The current entry decision is:

```yaml
entry_decision: deferred
selected_mode: null
runtime_status: not_implemented
receipt_family: no_receipt_planning_only
```

The decision may change only in a later freeze if all of these are repo-confirmed:

- concrete named use case proving same-origin attachment delivery and same-origin signed references are insufficient;
- selected artifact family;
- provider/storage authority;
- exposure classification;
- access authority;
- TTL, expiry, replay, and revocation contract;
- audit and receipt contract;
- provider configuration and secret posture;
- leak-control posture;
- stale-authority failure plan;
- test architecture using fake provider or contract double by default;
- no-cross-mode privilege escalation proof.

## Allowed Future Modes

A later runtime freeze must choose exactly one of:

- `provider_private_signed_url`;
- `provider_public_url`;
- `public_proxy_url`.

The selected mode must be represented unambiguously in any future request/response schema. A same-origin signed reference must not be renamed or represented as a provider/public URL.

## Request Contract For Later Runtime

A future provider/public URL request must be server-authority based. It may include or derive server-side:

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
- artifact ref, hash, and size authority;
- signed-reference authority only if the future freeze explicitly uses it as a prerequisite;
- selected provider/public URL mode;
- fresh idempotency key or `client_request_id`.

The request must not accept:

- client-supplied `download_url`, `public_url`, `provider_url`, `signed_url`, or `signed_delivery_url`;
- provider credentials, bearer tokens, bucket names, object keys, ACLs, CORS policy, cache policy, or namespace from the browser;
- local file paths, local upload payloads, local-directory paths, arbitrary path input, or source expansion fields;
- connector ids, destination ids, connector-run ids, destination-write flags, or generic dispatch flags;
- package payload bytes, package mutation fields, replacement fields, supersession fields, retry/rerun/recovery/cancel fields, RAG/vector fields, broad qualitative fields, hidden LLM fields, auth/security fields, or full mockup activation fields.

## Response Contract For Later Runtime

A future response may expose only response-safe metadata admitted by the later runtime freeze:

- selected mode;
- URL or proxy route only if explicitly admitted;
- expiry or TTL;
- artifact ref/hash/size basis;
- response-safe display label;
- revocation/audit status if implemented;
- disabled downstream flags only if response-safe and not a dispatch receipt.

The response must not expose provider credentials, raw provider signatures beyond the intended URL, local filesystem paths, raw object paths when `public_proxy_url` is selected, connector targets, destination ids, package payload bytes, source expansion state, qualitative output, auth internals, or provider URL fields on existing same-origin delivery or signed-reference routes.

## Provider Object Non-Contract

Provider/public URL work is not provider object materialization. It must not write, copy, mutate, publish, delete, revoke, or change ACLs on provider objects unless a separate provider object materialization freeze and contract admit that behavior.

## Signed-Reference Compatibility Contract

Provider/public URL work must preserve same-origin signed-reference generation, durable backing state, secret requirements, single-use semantics, replay denial, token-only use, and rendered proof behavior unless a later compatibility freeze admits a replacement.

Disallowed cross-mode upgrades:

- signed reference to provider URL upgrade;
- expired signed reference creating a provider URL;
- failed same-origin delivery creating a provider URL;
- stale package review creating a provider URL;
- stale artifact hash creating a provider URL;
- provider URL enabling connector dispatch.

## Security And Access Contract

A later runtime freeze must fail closed for:

- missing provider configuration;
- missing signing or ACL authority;
- missing access authority;
- stale session, plan, pass, result review, package review, package construction, package submit, handoff/export, APS dispatch, external export/download prepare, artifact ref, artifact hash, artifact size, or signed-reference prerequisite;
- wrong session, wrong package, wrong artifact, wrong provider mode, wrong idempotency key, malformed request, forbidden field, provider failure, expired URL, revoked URL, or replay outside the selected policy.

Provider credentials, full bearer URLs, raw tokens, raw signatures, raw provider object keys, and local paths must not appear in logs, error bodies, screenshots, traces, audit payloads, or response fields unless a later freeze names a safe redaction policy.

## Browser And UI Contract

This entry freeze adds no rendered UI control. If a later freeze admits rendered provider/public URL controls, it must:

- preserve `light` for status, preview, and review inspection;
- preserve `dark` for execution and package construction surfaces;
- preserve `workbench` for package submit, handoff/export, APS handoff, external export/download, signed-reference, and downstream operation-dock flows;
- prove headed and headless Chromium consistency;
- prove no target-state mockup control appears as live durable authority;
- define cache-control, referrer-policy, content-disposition, CORS, CSP, URL display, and redaction behavior where applicable.

## Test Contract For Later Runtime

Runtime implementation remains blocked until a later freeze names tests for:

- disabled-by-default behavior;
- missing provider configuration fail-closed behavior;
- fake provider adapter or contract double;
- provider error simulation;
- forbidden URL/provider/connector/destination/package/source/RAG/auth/mockup fields;
- exact authority binding;
- stale authority failure cases;
- TTL, expiry, replay, and revocation behavior;
- no URL/token leakage in logs, error bodies, traces, screenshots, existing same-origin responses, or proof manifests;
- no connector dispatch, destination write, package mutation, source expansion, RAG/vector retrieval, full mockup activation, hidden LLM, auth/security behavior change, or frontend-only durable authority;
- headed and headless rendered proof if UI changes are admitted.

Real provider credentials are forbidden in CI by default.

## Checker Contract

`tools/l3-progress-check.py` should verify structural guardrails only:

- docs `187` and `188` exist and are referenced;
- entry decision is `deferred`;
- selected mode is null;
- runtime status is `not_implemented`;
- evidence ledger exists and unverified provider authority forces deferral;
- exposure model exists and unknown values force deferral;
- capability isolation matrix exists and all runtime flags remain false;
- negative invariants are present;
- docs do not claim provider/public URL runtime is live;
- docs do not conflate same-origin signed references with provider/public URLs;
- docs do not admit connector dispatch, destination writes, package mutation, source expansion, RAG/vector retrieval, auth/security changes, full mockup activation, provider object writes/copies, or provider ACL changes.

The checker must not pretend to validate real provider configuration, object-store authority, ACL state, TTL implementation, revocation behavior, provider credentials, CORS, CSP, or actual provider network behavior in this planning-only pass.

## Stop Conditions

Stop and return to planning if a future implementation proposal tries to:

- implement more than one provider/public URL mode;
- emit provider URL fields on existing same-origin attachment or signed-reference routes;
- accept provider credentials or provider namespace from the client;
- use public ACLs without a security/public exposure freeze;
- create connector runs, destination writes, or generic dispatch records;
- mutate packages, rewrite package payloads, or supersede packages;
- expand source classes, local upload, local-directory ingestion, web retrieval, RAG/vector retrieval, or broad qualitative execution;
- add rendered controls without a rendered implementation-entry freeze and headed/headless proof;
- alter auth/security behavior without an auth/security freeze.
