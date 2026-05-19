# 853 - Internal Webhook Connector Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `server_configured_internal_webhook_destination_dispatch`.

Sync doc: `853_INTERNAL_WEBHOOK_CONNECTOR_RUNTIME_CURRENT_MAIN_SYNC.md`.

Governing freeze doc: `852_INTERNAL_WEBHOOK_CONNECTOR_FREEZE.md`.

Runtime PR: `#1462`.

Runtime branch: `codex/l3-internal-webhook-runtime`.

Runtime branch commit: `d42be534`.

Runtime merge commit: `08ca4ba3cc0a855eb4c75063b279dec5958d0b60`.

Sync branch: `codex/l3-internal-webhook-runtime-sync`.

Synced result: `current_main_synced_internal_webhook_connector_runtime_implementation`.

Runtime behavior introduced by implementation PR: `true`.

Runtime behavior introduced by this sync: `false`.

## Current-Main Evidence

Current main now includes the exact real connector/destination slice selected by doc `852_INTERNAL_WEBHOOK_CONNECTOR_FREEZE.md`.

The live target remains:

- target identity: `server_configured_internal_webhook_destination`;
- target class: `real_connector_invocation`;
- dispatch mode: `server_configured_allowlisted_internal_webhook_post`;
- destination address model: `server_configured_allowlisted_url`;
- credential model: `no_credentials`;
- operator surface: `read_only_status_only`.

Current main includes the owner service:

- `backend/app/services/layer3_internal_webhook_connector.py`.

Current main includes the API surfaces:

- `POST /api/v1/layer3/handoff/export/internal-webhook/dispatch`;
- `GET /api/v1/layer3/handoff/export/internal-webhook/status/{internal_webhook_dispatch_receipt_id}`.

Current main includes durable receipt/audit state:

- `L3InternalWebhookDispatchReceipt`;
- `L3InternalWebhookDispatchAuditEvent`;
- migration `0035_layer3_internal_webhook_connector.py`.

The implementation sends exactly one redacted handoff/export delivery envelope to one server-configured allowlisted internal webhook URL after package-review submit, handoff/export prepare, export/download readiness, and server-owned local outbox receipt authority are verified.

## Merge Gate

PR `#1462` merged on 2026-05-19 at merge commit `08ca4ba3cc0a855eb4c75063b279dec5958d0b60`.

PR `#1462` checks before merge:

- `backend-layer3-api`: `SUCCESS`, `3m21s`;
- `test`: `SUCCESS`, `3m41s`;
- comments: `0`;
- reviews: `0`;
- latestReviews: `0`;
- reviewThreads totalCount: `0`;
- unresolved reviewThreads totalCount: `0`;
- merge state before merge: `CLEAN`.

## Non-Admission Boundary

This current-main sync introduces no additional runtime behavior. It records current-main adoption of the already-merged server-configured internal webhook connector runtime only.

Still not admitted:

- arbitrary connector dispatch;
- arbitrary destination URLs;
- operator-supplied destination URLs;
- public URLs;
- provider-private signed URLs;
- provider-public URLs;
- cloud object-store writes;
- OAuth/provider credentials;
- stored provider credentials;
- `ConnectorRun`;
- `ConnectorRunTarget`;
- package mutation;
- package payload rewrite;
- raw package byte delivery;
- source expansion;
- vector/RAG widening;
- TabPFN runtime;
- NRC RAG runtime;
- optional-tool Gate C/pass-entry admission;
- rendered write/submit controls; and
- broad auth/security behavior.

## Validation

Runtime PR branch-local validation:

- `python -m py_compile .\backend\app\services\layer3_internal_webhook_connector.py .\backend\app\api\layer3.py .\backend\app\models\models.py .\backend\app\core\config.py` - `PASS`;
- `python -m py_compile .\backend\alembic\versions\0035_layer3_internal_webhook_connector.py` - `PASS`;
- `python -m pytest .\backend\tests\test_layer3_api.py -q -k "internal_webhook or provider_private_signed_url_openapi_prepare_status_schema"` - `PASS`;
- `python .\tools\l3-progress-check.py` - `PASS`;
- `python .\tools\l3-target-selection-validate.py --expect frozen` - `PASS`;
- `python .\tools\l3-fixture-validate.py --expect pending` - `PASS`;
- `python .\tools\l3-fixture-validate.py .\next_milestone_plans\Layer3_planning_docs\851_FIXTURE_CHECKPOINT.md --expect checkpoint` - `PASS`;
- `git diff --check` - `PASS` with CRLF normalization warnings only.

Current-main sync validation:

- `python .\tools\l3-progress-check.py` - `PASS`;
- `python .\tools\l3-target-selection-validate.py --expect frozen` - `PASS`;
- `python .\tools\l3-fixture-validate.py --expect pending` - `PASS`;
- `python .\tools\l3-fixture-validate.py .\next_milestone_plans\Layer3_planning_docs\851_FIXTURE_CHECKPOINT.md --expect checkpoint` - `PASS`;
- `python -m pytest .\backend\tests\test_layer3_api.py -q -k "internal_webhook or provider_private_signed_url_openapi_prepare_status_schema"` - `PASS`, `3 passed`, `186 deselected`.

## Next Posture

The server-configured internal webhook connector runtime is current-main synced.

Do not continue connector/destination repetition unless current-main evidence shows a concrete unresolved defect, check failure, review item, or named downstream operator-flow blocker.

The next exact current-main posture is `select_next_major_layer3_end_to_end_gap_from_current_main_evidence`.
