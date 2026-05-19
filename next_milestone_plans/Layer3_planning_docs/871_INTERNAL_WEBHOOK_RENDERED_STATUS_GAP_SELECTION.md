# 871 - Internal Webhook Rendered Status Gap Selection

## Status

Status: no-runtime current-main selection control for `server_configured_internal_webhook_rendered_read_only_status_projection`.

Selection doc: `871_INTERNAL_WEBHOOK_RENDERED_STATUS_GAP_SELECTION.md`.

Predecessor current-main sync doc: `853_INTERNAL_WEBHOOK_CONNECTOR_RUNTIME_CURRENT_MAIN_SYNC.md`.

Predecessor optional-tool revalidation doc: `870_OPTIONAL_TOOL_AUTHORITY_REVALIDATION_SELECTION.md`.

Current-main checkpoint before this selection: `4e6eb6e8b119f0b787fa7e3ddf5a1b3a0a794ad3`.

Selected gap: `server_configured_internal_webhook_rendered_read_only_status_projection`.

Runtime behavior introduced by this selection: `false`.

Rendered behavior introduced by this selection: `false`.

Implementation-entry allowed next: `false`.

## Current-Main Evidence

Current main already contains the server-configured internal webhook connector runtime selected by doc `852_INTERNAL_WEBHOOK_CONNECTOR_FREEZE.md` and synced by doc `853_INTERNAL_WEBHOOK_CONNECTOR_RUNTIME_CURRENT_MAIN_SYNC.md`.

Canonical backend dispatch/status authority is:

- `backend/app/services/layer3_internal_webhook_connector.py`;
- `POST /api/v1/layer3/handoff/export/internal-webhook/dispatch`;
- `GET /api/v1/layer3/handoff/export/internal-webhook/status/{internal_webhook_dispatch_receipt_id}`;
- `L3InternalWebhookDispatchReceipt`; and
- `L3InternalWebhookDispatchAuditEvent`.

Current main also has rendered read-only status surfaces for adjacent downstream handoff states in `backend/app/review_ui/static/layer3.js`, including:

- `State.sessionSummary.connector_local_destination_receipt`;
- `State.sessionSummary.server_owned_local_outbox_target`;
- `State.sessionSummary.server_owned_local_outbox_write`;
- `State.sessionSummary.local_outbox_provider_private_handoff`; and
- `State.sessionSummary.external_local_export`.

The current `backend/app/services/layer3_workbench.py::session_summary` response includes those adjacent read-only status projections, but it does not yet expose `State.sessionSummary.internal_webhook_dispatch` for the rendered workbench to inspect.

## Selection Result

The next non-optional-tool Layer 3 end-to-end gap is the missing rendered read-only operator projection for the already-current-main server-configured internal webhook dispatch/status authority.

The future target must remain read-only and status-only. It may project durable internal webhook dispatch status/history into `GET /api/v1/layer3/session/{session_id}` and render it in `/review/layer3`, but only after a separate freeze names the exact API/session-summary field, response authority, UI panel, fail-closed state, and headed/headless proof requirements.

This selection does not admit a dispatch button, submit control, destination picker, retry/rerun control, generic connector control, URL field, credential field, provider integration, or browser-storage authority.

## Non-Admission Boundary

This selection admits no runtime behavior, rendered behavior, route/API/DTO/model/migration/service behavior change, internal webhook dispatch rerun, new dispatch endpoint, connector run creation, connector run target creation, arbitrary connector dispatch, arbitrary destination URL, operator-supplied URL, public URL, provider-private signed URL, provider-public URL, cloud object-store write, OAuth/provider credential, stored provider credential, package mutation, package payload rewrite, raw package byte delivery, source expansion, vector/RAG widening, TabPFN runtime, NRC RAG runtime, optional-tool Gate C/pass-entry admission, broad auth/security behavior, rendered write/submit control, public exposure, browser-storage authority, or frontend-only durable authority.

## Required Future Authority

A future freeze may proceed only if it preserves:

- canonical backend authority from `layer3_internal_webhook_connector.py` and durable receipt/audit rows;
- read-only session-summary projection authority for `internal_webhook_dispatch`;
- rendered `/review/layer3` inspection only over `State.sessionSummary.internal_webhook_dispatch`;
- fail-closed display when no internal webhook receipt exists;
- redaction of raw destination URL, tokens, headers, local paths, package payloads, package bytes, public URLs, signed URLs, provider object keys, browser storage, and auth internals; and
- headed plus headless Chromium proof if rendered behavior is implemented.

The future freeze must keep dispatch invocation and rendered write/submit controls outside the rendered status projection.

## Validation Basis

Required validation for this selection:

- `python .\tools\l3-progress-check.py`;
- `python .\tools\l3-fixture-validate.py --expect pending`;
- `python .\tools\l3-fixture-validate.py .\next_milestone_plans\Layer3_planning_docs\851_FIXTURE_CHECKPOINT.md --expect checkpoint`;
- `python .\tools\l3-target-selection-validate.py --expect frozen`;
- `python -m py_compile .\tools\l3-progress-check.py .\tools\l3-fixture-validate.py`;
- JSON validation for `layer3_progress_manifest.json` and `layer3_workbench_proof_manifest.json`; and
- `git diff --check`.

No runtime, API, or browser test is required for this selection because it changes no runtime behavior, route, dependency, session-summary field, or rendered UI behavior.

## Next Posture

The next exact posture is `freeze_internal_webhook_rendered_read_only_status_projection_before_runtime`.

Do not implement internal webhook rendered status behavior until that freeze is current-main selected, review-cleared, and checker-backed.
