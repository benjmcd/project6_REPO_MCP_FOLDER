# 872 - Internal Webhook Rendered Status Freeze

## Status

Status: no-runtime implementation-entry freeze for `server_configured_internal_webhook_rendered_read_only_status_projection`.

Freeze doc: `872_INTERNAL_WEBHOOK_RENDERED_STATUS_FREEZE.md`.

Predecessor gap-selection doc: `871_INTERNAL_WEBHOOK_RENDERED_STATUS_GAP_SELECTION.md`.

Current-main checkpoint before this freeze: `df811aa9f9e8263ed8b233d5f530b82267be7b93`.

Selected implementation action: `implement_internal_webhook_rendered_read_only_status_projection`.

Runtime behavior introduced by this freeze: `false`.

Rendered behavior introduced by this freeze: `false`.

Implementation-entry allowed next: true only after current-main sync for this freeze, and only for the read-only internal webhook status projection named here.

## Canonical Source Of Truth

The canonical source of truth for the future rendered projection is durable internal webhook dispatch receipt/audit authority, exposed read-only through existing Layer 3 session-summary authority.

The backend authority remains:

- owner service: `backend/app/services/layer3_internal_webhook_connector.py`;
- durable receipt model: `L3InternalWebhookDispatchReceipt`;
- durable audit model: `L3InternalWebhookDispatchAuditEvent`;
- dispatch endpoint already current-main synced: `POST /api/v1/layer3/handoff/export/internal-webhook/dispatch`;
- status endpoint already current-main synced: `GET /api/v1/layer3/handoff/export/internal-webhook/status/{internal_webhook_dispatch_receipt_id}`;
- future session-summary field: `internal_webhook_dispatch: dict[str, Any]`;
- future response authority: `State.sessionSummary.internal_webhook_dispatch`;
- future projection mode: `read_only_session_summary_projection`.

The implementation may read durable internal webhook receipt/audit state and existing session-summary state. It must not treat browser state, localStorage, DOM labels, CSS state, operator notes, hidden form fields, or mockup copy as authority.

## Exact Session-Summary Surface

The only admitted backend/session-summary change for the later implementation is adding `internal_webhook_dispatch: dict[str, Any]` to the existing `GET /api/v1/layer3/session/{session_id}` response path.

The field may expose only response-safe status facts:

- schema id;
- availability / blocked reason;
- internal webhook dispatch state;
- internal webhook dispatch receipt id;
- target identity;
- target class;
- dispatch mode;
- redacted destination display name;
- package ref and package kind;
- package artifact hash and size;
- server-owned local outbox write receipt id;
- connector local destination receipt id;
- external export/download record ref;
- idempotency policy summary;
- redacted response summary;
- failure code;
- audit event count;
- receipt/audit history with redacted fields only; and
- downstream unavailable / forbidden authority flags.

The field must fail closed when no internal webhook dispatch receipt exists for the session, when durable receipt/audit authority is stale or ambiguous, or when redaction cannot be proven.

## Exact Rendered Surface

The only admitted rendered surface for the later implementation is the existing `/review/layer3` page in `backend/app/review_ui/static/layer3.js`, with any required style-only support in `backend/app/review_ui/static/layer3.css` and bounded static assertions in `backend/tests/test_layer3_page.py`.

The future rendered implementation is limited to:

- `State.sessionSummary.internal_webhook_dispatch` as the response holder;
- a read-only helper, tentatively `internalWebhookDispatchStatusState()`;
- a state-name helper, tentatively `internalWebhookDispatchStateName()`;
- a read-only panel renderer, tentatively `renderInternalWebhookDispatchStatusPanel()`;
- a static HTML panel container, tentatively `internal-webhook-dispatch-panel`;
- existing session refresh authority through `refreshSessionSummary()`.

The rendered panel may display only response-safe fields from `State.sessionSummary.internal_webhook_dispatch`. It must not add a dispatch button, submit control, URL input, destination selector, credential input, retry/rerun control, generic connector control, operation dock step, or browser-persisted authority.

## Fail-Closed And Redaction Policy

If `State.sessionSummary.internal_webhook_dispatch` is absent, not an object, has an unexpected schema id, reports unavailable state, lacks durable receipt/audit basis, or reports a redaction/failure state, the UI must render a read-only blocked/unknown status.

The future implementation must not seed session summary, generate fake receipts, infer dispatch state from DOM state, backfill from localStorage, call the dispatch endpoint, or read raw destination URL/token/header/local path/package bytes into the browser.

Responses, rendered text, tests, logs, screenshots, and proof manifests must not expose raw destination URL, raw token, raw secret header, raw local path, raw package payload, raw package bytes, public URLs, signed URLs, provider object keys, browser storage, or auth internals.

## Non-Admission Boundary

This freeze admits no runtime behavior and no rendered behavior now.

Still blocked:

- implementation before current-main sync for this freeze;
- new dispatch endpoint, dispatch rerun, retry/rerun behavior, queue behavior, cancel behavior, or background worker behavior;
- rendered dispatch button, submit control, URL input, destination selector, credential input, generic connector control, or operation dock step;
- arbitrary connector dispatch, arbitrary destination URLs, operator-supplied URLs, public URLs, provider-private signed URLs, provider-public URLs, cloud object-store writes, OAuth/provider credentials, stored provider credentials, or external internet target selection;
- `ConnectorRun`, `ConnectorRunTarget`, package mutation, package payload rewrite, raw package byte delivery, source expansion, vector/RAG widening, TabPFN runtime, NRC RAG runtime, optional-tool Gate C/pass-entry admission, broad auth/security behavior, public exposure, browser-storage authority, or frontend-only durable authority.

## Proof Obligations

The later implementation proof must include:

- `node --check .\backend\app\review_ui\static\layer3.js`;
- targeted static/page tests proving the rendered reader is bounded in `backend/tests/test_layer3_page.py`;
- targeted backend/API tests proving `internal_webhook_dispatch` session-summary projection is read-only, redacted, and fail-closed;
- proof that no new dispatch endpoint, retry/rerun behavior, destination selector, provider URL behavior, credential behavior, `ConnectorRun`, `ConnectorRunTarget`, package mutation, source expansion, vector/RAG, optional-tool, frontend-only durable authority, or broad auth/security behavior was added;
- headed Chromium proof for the affected `/review/layer3` status panel;
- headless Chromium proof for the same panel;
- desktop and mobile no-overlap/no-horizontal-overflow checks for the affected status panel;
- `python .\tools\l3-progress-check.py`;
- `python .\tools\l3-target-selection-validate.py --expect frozen`;
- pending/checkpoint fixture validation.

## Next Posture

The next exact posture is `current_main_sync_internal_webhook_rendered_status_freeze_then_implementation`.

After that sync, the only admitted implementation action is `implement_internal_webhook_rendered_read_only_status_projection`.
