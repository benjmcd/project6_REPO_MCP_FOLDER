# 959 - Source-Directory Provider-Private Redacted Lifecycle

## Status

Status: implementation/proof checkpoint for the first source-directory provider-private redacted prepare/status/use/revoke lifecycle slice after `958-product-authority-intake.md`.

Current-main authority before this branch: `project6-origin/main` at `51b069d6 Validate Layer 3 product authority intake`.

Selected product-authority answer: existing `output_review_package_handoff` extension plus separate provider-private/redacted delivery lifecycle objective for one exact artifact family.

Selected artifact family: `source_directory_hybrid_context_packet_qualitative_analysis` external export/download package artifact, specifically the source-directory handoff/export download package reference selected by package kind and payload hash.

Runtime behavior introduced by this checkpoint: `true`.

Rendered behavior introduced by this checkpoint: `true`.

Generic provider-private signed URL use route introduced: `false`.

Provider-public URL, public proxy, provider object write/copy/mutation, connector dispatch, credential exposure, frontend durable authority, source expansion, RAG/vector/model runtime, and full mockup activation introduced: `false`.

## Implemented Scope

This slice adds source-directory-specific server-owned status/use/revoke routes around the existing source-directory prepare route:

```yaml
routes:
  prepare:
    method: POST
    path: /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/provider-private-signed-url/prepare
  status:
    method: POST
    path: /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/provider-private-signed-url/status
  use:
    method: POST
    path: /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/provider-private-signed-url/use
  revoke:
    method: POST
    path: /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/provider-private-signed-url/revoke
owner_services:
  - backend/app/services/layer3_source_directory_hybrid_analysis.py
  - backend/app/services/layer3_provider_private_signed_url_state.py
rendered_surface:
  - backend/app/review_ui/static/layer3.html
  - backend/app/review_ui/static/layer3.js
focused_tests:
  - backend/tests/test_layer3_source_directory_vector_retrieval.py::test_source_directory_hybrid_context_packet_provider_private_to_public_redacted_use
  - e2e/layer3-workbench.spec.js::Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path
```

The lifecycle routes do not accept or return raw provider-private token material. Each source-directory-specific status/use/revoke action revalidates the current source-directory external export/download delivery authority and checks that it still matches the durable provider-private receipt authority. Use records a single-use durable `use` audit event, and revoke records durable revocation/audit state.

The existing generic route remains absent:

```yaml
blocked_route: POST /api/v1/layer3/handoff/export/download/provider-private-signed-url/use
```

## Contract

The source-directory status/use request is intentionally scoped to the current delivery authority plus:

- `provider_signed_url_receipt_id`;
- `operator_decision: inspect_source_directory_hybrid_provider_private_signed_url_status` or `use_source_directory_hybrid_provider_private_signed_url`;
- `delivery_mode: provider_private_signed_url`;
- optional `decision_notes`.

The source-directory revoke request adds:

- `idempotency_key`;
- `revoked_by`;
- `revocation_reason`;
- `operator_decision: revoke_source_directory_hybrid_provider_private_signed_url`.

The response reports:

- durable provider-private receipt id and state;
- status/use/revoke lifecycle status;
- `delivery_use_decision: allowed` and `delivery_use_mode: server_owned_redacted_provider_private_use` for use responses;
- `revocation_recorded` and `revocation_idempotency_key` for revoke responses;
- redacted provider URL marker only;
- TTL/expiry projection;
- use count and replay policy;
- durable audit receipt;
- source artifact hash and size;
- explicit negative authority flags.

The response does not expose raw provider URL, raw provider-private token, provider credentials, provider object identity, raw local path, package payload bytes, connector destination, public URL, or public proxy URL.

## Failure Behavior

The lifecycle routes fail closed for:

- missing receipt;
- stale source-directory delivery authority or package payload hash mismatch;
- revoked receipt;
- expired receipt;
- single-use replay;
- forbidden raw token, raw URL, credential, provider, connector, package mutation, source expansion, or frontend durable authority fields.

Accepted use records a durable `use` audit event with `reason_code: server_owned_redacted_use_accepted`.

Accepted revoke records durable revocation/audit state through the provider-private receipt state authority.

Rejected durable-state use attempts record bounded rejection audit events where durable state has been reached.

## Rendered Proof

The rendered workbench now exposes source-directory-specific status/use/revoke routing for the provider-private controls. `#provider-private-signed-url-use` remains disabled until the source-directory provider-private receipt is prepared and the current source-directory delivery authority is available.

For generic provider-private receipts, the use path remains `closed_not_implemented`, and generic status/revoke behavior remains unchanged.

For the selected source-directory artifact family, the controls call only the source-directory-specific status/use/revoke routes and render redacted server-owned lifecycle state. They do not activate generic external-provider consumption.

## Verification

Focused verification run on this branch:

```powershell
python -m pytest backend/tests/test_layer3_api.py::test_layer3_api_provider_private_signed_url_openapi_prepare_status_schema backend/tests/test_layer3_api.py::test_layer3_api_provider_private_signed_url_revoke_success_idempotency_and_fail_closed backend/tests/test_layer3_source_directory_vector_retrieval.py::test_source_directory_hybrid_context_packet_provider_private_to_public_redacted_use -q
node --check .\backend\app\review_ui\static\layer3.js
python .\tools\l3-progress-check.py
npx playwright test e2e/layer3-workbench.spec.js -g "Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path" --project=chromium
npx playwright test e2e/layer3-workbench.spec.js -g "Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path" --project=chromium --headed
```

## Remaining Work

This is the first provider-private redacted lifecycle slice for one exact artifact family, not the completed long-term delivery program. Current-main follow-up through `961-provider-private-sync.md` records that package replacement/supersession and hybrid rendered stale/replay/revoked proof have since landed.

Remaining passes:

- any further provider-private artifact family only through a separate freeze;
- bounded operator runbook recheck when a full readiness refresh is needed;
- broader artifact-family expansion only after a separate freeze;
- real provider, public URL, proxy, connector, RAG/vector/model runtime, auth/security, and full mockup activation only after separate authority freezes.
