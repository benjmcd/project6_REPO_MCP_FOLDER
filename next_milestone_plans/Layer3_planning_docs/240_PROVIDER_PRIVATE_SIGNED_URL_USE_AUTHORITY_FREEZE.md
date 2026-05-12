# Provider Private Signed URL Use Authority Freeze

Status: current-main planning/control freeze for `provider_private_signed_url_use_authority_freeze`.

This document follows `239_PROVIDER_PRIVATE_SIGNED_URL_REVOKE_API.md`. Prepare/status and revoke are now backend/API-only live. The use route remains blocked because the project has not selected a token/delivery authority model.

This pass is docs/proof/checker-only. It does not add routes, DTOs, services, models, migrations, executable backend tests, rendered UI controls, browser automation, raw token exposure, raw token durable persistence, provider credentials, provider network calls, provider object-store writes, connector/destination dispatch, package mutation/reconstruction, source expansion, RAG/vector behavior, full mockup activation, auth/security behavior, same-origin delivery changes, same-origin signed-reference changes, provider/public URL runtime, or public proxy URL runtime.

## Decision

```yaml
selected_planning_mode: provider_private_signed_url_use_authority_freeze
entry_decision: use_authority_not_selected_runtime_blocked
selected_runtime_family: provider_public_url_runtime
selected_runtime_mode: provider_private_signed_url
named_use_case_selected: external_downstream_recipient_private_artifact_delivery
prepare_status_runtime: prepare_status_backend_api_only_implemented
revoke_runtime: revoke_backend_api_only_implemented
use_route_status: blocked_no_token_delivery_model
rendered_ui_change: false
provider_network_or_object_store_write: false
same_origin_delivery_semantics_changed: false
same_origin_signed_reference_semantics_changed: false
runtime_implementation_allowed_next: false
```

## Authority finding

Current prepare/status/revoke responses expose only redacted provider-private URL/token material. Durable provider-private state stores token hash/prefix metadata rather than raw usable token material. Therefore a client-callable use route cannot be safely or coherently implemented without first selecting one token/delivery model.

## Candidate token/delivery models

```yaml
candidate_models:
  client_held_token:
    status: not_selected
    blocker: current API never exposes raw provider-private token
  server_owned_proxy_use:
    status: not_selected
    blocker: requires proxy/delivery semantics and likely raw token retention policy
  encrypted_server_retained_token:
    status: not_selected
    blocker: requires secret storage, encryption, expiry, rotation, audit, and threat model
  no_use_api_external_provider_consumption:
    status: not_selected
    blocker: current fake-provider/local runtime has no real external recipient delivery surface
```

No model is selected by this freeze. The correct next action is to choose exactly one model or explicitly close `use` as out of scope for the provider-private signed URL lane.

## Required future freeze before use

Any later use-route implementation-entry freeze must specify:

- selected token/delivery model;
- whether raw provider-private token material is ever exposed to a client;
- whether raw token material is stored, encrypted, rotated, or never retained;
- replay, expiry, revocation, idempotency, and concurrency semantics;
- stale artifact/session/receipt authority behavior;
- audit/receipt/leakage behavior;
- route/API owner and request/response contract;
- fake-provider and real-provider compatibility assumptions;
- headed/headless rendered proof requirements if UI is admitted;
- auth/security posture and secret-handling threat model.

## Negative invariants

Until a later freeze selects a token/delivery model:

- no `POST /api/v1/layer3/handoff/export/download/provider-private-signed-url/use` route;
- no raw provider-private token in API responses, logs, audit receipts, tests, screenshots, or manifests;
- no raw token durable persistence;
- no provider network/object-store behavior;
- no public/proxy URL behavior;
- no rendered provider-private controls;
- no connector/destination dispatch;
- no package/source mutation;
- no same-origin delivery or signed-reference semantic change;
- no auth/security behavior change.

## Recommended next action

```yaml
recommended_next_action: choose_or_reject_one_provider_private_signed_url_use_model
if_model_selected: write_use_route_implementation_entry_freeze
if_no_model_selected: keep_use_route_blocked_and_move_to_theme_parity_or_other_admitted_work
```
