# Provider Private Signed URL Rendered UI Freeze

Status: planning/control implementation-entry freeze for `provider_private_signed_url_rendered_ui_freeze`.

This document follows `243_PROVIDER_PRIVATE_SIGNED_URL_USE_MODEL_CLOSEOUT.md` and `244_PROVIDER_PRIVATE_SIGNED_URL_USE_MODEL_CONTRACT.md`. It admits the next implementation only as a rendered `/review/layer3` UI slice over already-live provider-private prepare/status/revoke backend APIs.

## Decision

```yaml
selected_planning_mode: provider_private_signed_url_rendered_ui_freeze
entry_decision: rendered_ui_entry_frozen_runtime_blocked
selected_runtime_family: provider_public_url_runtime
selected_runtime_mode: provider_private_signed_url
selected_use_model: no_use_api_external_provider_consumption
named_use_case_selected: external_downstream_recipient_private_artifact_delivery
allowed_next_runtime_slice: rendered_prepare_status_revoke_controls_only
prepare_status_runtime: prepare_status_backend_api_only_implemented
revoke_runtime: revoke_backend_api_only_implemented
use_route_status: closed_not_implemented
backend_api_change_allowed: false
model_or_migration_change_allowed: false
implementation_entry_allowed_next: true
```

## Allowed next implementation

The next implementation may add only rendered controls and Playwright proof that:

- prepare a provider-private signed URL receipt over existing external export/download authority;
- inspect provider-private signed URL status by receipt id;
- revoke a provider-private signed URL receipt;
- show only redacted provider-private state;
- keep `use` absent and unavailable;
- prove the flow in headless and headed Chromium across `system`, `light`, `dark`, and `workbench`.

## Required UI authority

The UI must derive request fields from existing server-authoritative state already present in the rendered external export/download path. It must not ask the browser/operator for raw provider-private tokens, provider credentials, provider URLs, local paths, connector destinations, package mutation instructions, or source expansion details.

The rendered state must preserve these contracts:

- receipt id comes from the prepare response;
- status lookup uses the prepared receipt id;
- revoke uses the prepared receipt id plus explicit operator decision;
- response display redacts provider-private URL/token material;
- disabled/unavailable state explains that provider-private `use` is closed for this lane.

## Required tests

The implementation PR must include:

- focused Playwright proof on the canonical raw-mixed rendered external export/download path;
- request payload allowlist assertions for prepare and revoke;
- status-after-prepare and status-after-revoke assertions;
- absence assertion for provider-private `use` controls and route calls;
- forbidden-control assertions for connector/destination, package mutation/reconstruction, and source expansion;
- headed and headless Chromium runs;
- live-theme coverage for `system`, `light`, `dark`, and `workbench`.

## Forbidden changes

This freeze admits no:

- backend route, DTO, service, model, or migration change;
- `POST /api/v1/layer3/handoff/export/download/provider-private-signed-url/use` route;
- raw provider-private token exposure;
- raw token durable persistence;
- real provider network/object-store behavior;
- provider/public URL runtime;
- public proxy URL runtime;
- connector/destination dispatch;
- package mutation/reconstruction;
- source expansion;
- same-origin delivery or signed-reference semantic change;
- broad qualitative/hybrid/RAG/vector runtime;
- hidden LLM planning;
- full mockup activation;
- auth/security behavior change;
- frontend-only durable authority.

## Stop condition

Stop before implementation if the UI requires a provider-private `use` route, raw token input, provider credentials, provider network calls, new backend fields, new source classes, connector/destination selection, package mutation, same-origin delivery changes, same-origin signed-reference changes, auth/security changes, or Claude live-theme admission.
