# 399 - Layer 3 Connector Destination Authority Discovery Freeze

## Status

Status: planning/control freeze for `connector_destination_dispatch_authority_discovery`; no runtime connector or destination behavior admitted.

This freeze follows current-main doc `398_LAYER3_END_TO_END_GOVERNANCE_LIFECYCLE_READ_ONLY_DASHBOARD_CURRENT_MAIN_SYNC.md`, merged by PR `#994` at merge commit `329f784ef842a9d9b6b842a068b49f80aef26d31`.

This governing artifact is `399_LAYER3_CONNECTOR_DESTINATION_AUTHORITY_DISCOVERY_FREEZE.md`.

The selected exact named Layer 3 product/use-case requirement is `operator_reviews_connector_destination_dispatch_authority_gap_without_external_invocation`.

The selected freeze mode is `connector_destination_dispatch_authority_discovery`.

## Selection Basis

Current main now has read-only lifecycle dashboards for package, downstream access, and the end-to-end governance lifecycle. Those dashboards continue to show connector/destination as blocked.

Current main also has an admitted internal connector dispatch record substrate, but it is not external dispatch:

- `backend/app/services/layer3_connector_dispatch_entry.py` defines `CONNECTOR_DISPATCH_RECORD_MODE = "internal_dispatch_record_only"`.
- `backend/app/services/layer3_connector_dispatch_entry.py` forbids `connector_key`, `connector_run_id`, `connector_secret`, `destination_id`, `destination_secret`, `destination_url`, provider URL fields, package mutation fields, source expansion fields, RAG fields, retry/rerun fields, and hidden LLM fields in the record request.
- `backend/app/services/layer3_connector_dispatch_entry.py` returns `external_connector_invocation_enabled: False`, `destination_write_enabled: False`, and `connector_run_created: False`.
- `backend/app/services/layer3_state_action_contract.py` describes `internal_dispatch_record_only` as a response-safe internal connector dispatch intent record with no external connector invocation or destination write.
- `backend/app/services/layer3_state_model_contract.py` allows only `inspect_internal_connector_dispatch_record` after `connector_dispatch_recorded` and keeps `external_connector_invocation`, `destination_write`, and `connector_run_creation` forbidden.
- `backend/app/review_ui/static/layer3.js` shows connector invocation, destination write, and connector/destination dispatch as disabled or blocked labels only.
- `backend/tests/test_layer3_api.py` asserts `/api/v1/layer3/handoff/connector/record` request/response shape as record-only and checks `connector_key` plus provider URL fields remain known but non-admitted.
- Doc `385_LAYER3_RUNTIME_FREEZE_SEQUENCE_COMPLETION_AUDIT_AFTER_PROVIDER_PUBLIC_NO_RUNTIME.md` records that connector/destination remains blocked because no named connector or destination target is present.

Therefore the next safe milestone is not connector runtime implementation. The next safe milestone is a discovery freeze that makes the missing connector/destination authority explicit before any later runtime contract.

## Canonical Authority

The next discovery pass must treat these files as current authority:

- `backend/app/services/layer3_connector_dispatch_entry.py`
- `backend/app/services/layer3_state_action_contract.py`
- `backend/app/services/layer3_state_model_contract.py`
- `backend/app/services/layer3_readiness_contract.py`
- `backend/app/api/layer3.py`
- `backend/app/review_ui/static/layer3.js`
- `backend/tests/test_layer3_api.py`
- `next_milestone_plans/Layer3_planning_docs/385_LAYER3_RUNTIME_FREEZE_SEQUENCE_COMPLETION_AUDIT_AFTER_PROVIDER_PUBLIC_NO_RUNTIME.md`
- `next_milestone_plans/Layer3_planning_docs/398_LAYER3_END_TO_END_GOVERNANCE_LIFECYCLE_READ_ONLY_DASHBOARD_CURRENT_MAIN_SYNC.md`

## Required Discovery

The immediate next pass is `conduct_connector_destination_dispatch_authority_discovery`.

That pass must answer, from source evidence only:

- whether any exact named connector key is selected for Layer 3 runtime dispatch;
- whether any exact named destination target is selected;
- whether destination writes are allowed at all or remain blocked;
- whether the existing `internal_dispatch_record_only` substrate is sufficient as a predecessor to runtime dispatch or only as an inspection/intent record;
- what owner service would control runtime dispatch if later admitted;
- what route, request DTO, response DTO, model, migration, idempotency key, replay policy, audit event, and failure modes would be required before any runtime dispatch;
- what credential, secret, tenant/session-owner, auth/security, and leak-control policy would be required;
- what negative tests must prove malformed, stale, cross-session, duplicate, unauthorized, missing-destination, missing-credential, failed-connector, failed-destination, retry, rerun, and partial-side-effect cases fail closed;
- whether rendered controls are needed, and if so which read-only or action controls are admissible;
- whether headed/headless browser proof is required for any rendered surface.

If the discovery cannot identify a named connector, named destination, owner service, credential/security model, and fail-closed side-effect policy, it must stop as `no_runtime_now_connector_destination_named_target_absent`.

## Non-Admission Boundary

This freeze admits no runtime behavior, no external connector invocation, no destination write, no connector-run creation, no generic downstream dispatch, no rendered connector action control, no provider-public delivery/use, no raw public URL display/use, no package mutation, no source expansion, no RAG/vector behavior, no auth/security behavior change, no model or migration change, and no frontend-only durable authority.

The existing `/api/v1/layer3/handoff/connector/record` surface remains internal record-only.

No closed or blocked deferred lane is reopened by implication.

## Next Required Action

The next required action after this freeze merges is `current_main_sync_connector_destination_authority_discovery_freeze_after_merge`.
