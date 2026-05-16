# 626 - Server-Configured External Local Export Directory Freeze

## Status

Status: implementation-entry freeze for `server_configured_external_local_export_directory`.

Doc: `626_SERVER_CONFIGURED_EXTERNAL_LOCAL_EXPORT_DIRECTORY_FREEZE.md`.

Current-main checkpoint before freeze: `173cb84553eb1841c7b317879adcd151afafee2b`.

Prior decision intake: `623_NEXT_EXTERNAL_SURFACE_DECISION_INTAKE.md`.

Prior objective audit: `625_LAYER3_OBJECTIVE_COMPLETION_AUDIT_AFTER_NEXT_EXTERNAL_SURFACE_INTAKE_SYNC.md`.

Runtime status before implementation: `selected_next_external_surface_frozen_runtime_not_implemented`.

Implementation-entry allowed next: true, but only after this freeze is merged, synced to current main, and still admits the exact tranche defined here.

Live behavior change in this pass: false.

## Operator-Filled Decision Record

```yaml
next_surface_identity: server_configured_external_local_export_directory
next_surface_owner: Bennet / project operator
next_surface_class: server_configured_external_destination_write
operator_purpose: after Layer 3 completes source intake, Data Structuring & Processing, package/review, handoff/export, local outbox write, and provider-private preparation where applicable, write the finalized outbox artifact and manifest to a controlled local filesystem export directory outside app-owned staging for manual review, preservation, or downstream consumption
authority_source: external export/download readiness + connector-local durable receipt + server-owned local outbox write receipt + provider-private local-outbox handoff receipt where applicable
artifact_family: finalized outbox artifact + outbox manifest derived from server-owned package/export/handoff authority
credential_model: no_credentials
destination_address_model: server_configured_target_only
side_effect_boundary: write exactly one finalized Layer 3 outbox artifact and one outbox manifest to one server-configured local filesystem export directory outside app-owned staging; no caller-supplied path, network egress, connector invocation, connector-run creation, provider-public delivery, package mutation, source expansion, RAG/vector, auth/security broadening, full mockup activation, or frontend-durable authority
idempotency_contract: same client_request_id plus same authority/export/outbox/provider-private basis returns same receipt/status; same client_request_id plus different basis fails closed; same authority basis plus different client_request_id returns existing status rather than duplicate external export output; same export-directory deterministic target plus same bytes returns existing receipt/status; same target plus different bytes fails closed
failure_lifecycle: fail closed on stale authority, wrong session/pass/artifact/basis, missing export/download readiness, missing connector-local receipt, missing server-owned local outbox write receipt, missing required provider-private handoff receipt where applicable, tampered hash/size, target mismatch, export directory unavailable, path escape, timeout, partial write, conflicting existing output, unsupported credential/provider state, caller-supplied path/URL, or any forbidden adjacent surface
receipt_audit_contract: durable receipt id, session/pass/package/export refs, connector-local receipt ref, local outbox write receipt ref, provider-private handoff receipt ref where applicable, artifact/manifest refs with hash/size, target identity/class, redacted server-configured destination label, status/history, created/updated timestamps, idempotency key, redacted failure code, and audit history; never expose raw local paths
exposure_security_posture: private/internal only; no public URL; no provider-public delivery/use; no raw token; no credential storage; no external network egress; no public/indexable artifact exposure; no user-provided arbitrary path or URL
operator_surface: write_submit_control_plus_read_only_status_history_no_path_editing
proof_architecture: API proof over isolated runtime state plus headed/headless E2E proof if rendered write/status behavior changes; negative tests for stale authority, wrong artifact, duplicate-key conflict, same-key different-basis conflict, no ConnectorRun or ConnectorRunTarget creation, no real external connector invocation, no credential use, no provider-public delivery/use, no package mutation, no source expansion, no RAG/vector behavior, no broad auth/security change, and no arbitrary destination path
selection_complete: true
implementation_entry_freeze_written: true
```

## Layer 3 Placement

The external Project 2a references are advisory only. For this freeze, Layer 3 maps to the Data Structuring & Processing block, and this selected surface is a controlled export/write boundary for finalized Layer 3 structured outputs.

This freeze does not admit downstream qualitative-hybrid analysis, package mutation/reconstruction, source expansion/ingestion, RAG/vector indexing, provider-public delivery/use, real connector invocation, credentials, broad auth/security work, full mockup activation, or frontend-durable authority. Those remain separate future surfaces/actions that must each be selected, frozen, implemented, and proven independently.

## Canonical Authority Order

1. Live `project6-origin/main` source code, tests, models, migrations, API routes, service implementations, and checker behavior.
2. `623_NEXT_EXTERNAL_SURFACE_DECISION_INTAKE.md` as the operator-filled selected next-surface record.
3. Existing connector-local receipt, server-owned local outbox write, and local-outbox provider-private handoff runtime authority.
4. This freeze document.
5. Future implementation evidence only after this freeze is merged and synced into current main.

Planning prose, diagrams, PDFs, HTML exports, SVGs, brainstorm notes, and session logs are not runtime authority unless later reconciled against source and tests.

## Owner Seam And Route Boundary

The implementation owner service seam is `backend/app/services/layer3_external_local_export.py`.

The admitted route namespace is:

```yaml
write: POST /api/v1/layer3/handoff/connector/local-outbox/external-local-export/write
status: GET /api/v1/layer3/handoff/connector/local-outbox/external-local-export/status/{external_local_export_receipt_id}
```

The route and service may be wired through `backend/app/api/layer3.py` only for this selected external local export surface. No generic destination router, generic connector runtime, connector-run target, provider-public route, source-expansion route, package mutation route, RAG/vector route, or auth/security route is admitted.

## Server Configuration Authority

The destination address model is server-configured target only. The implementation may add a backend setting in `backend/app/core/config.py`, such as `LAYER3_EXTERNAL_LOCAL_EXPORT_DIR`, and must derive the actual filesystem destination exclusively from that setting.

The configured destination must resolve outside `settings.storage_dir` and outside the app-owned `layer3-outbox` staging root. The service must fail closed if the setting is missing, empty, relative when an absolute path is required by the implementation, points inside app-owned staging, points to an unsafe root, cannot be created or written, or resolves through a path escape.

The request contract must not accept any local path, destination path, URL, bucket, object key, provider target, connector target, credential, token, or caller-edited destination label.

Responses, status projections, audit rows, logs, and rendered UI must not expose raw local filesystem paths. They may expose only redacted labels such as `server_configured_external_local_export_directory` and redacted refs such as `external-local-export://<receipt_id>/artifact.json`.

## Admitted First Runtime Tranche

After this freeze is merged and synced, the next implementation pass may add only:

- service `backend/app/services/layer3_external_local_export.py`;
- route/model wiring in `backend/app/api/layer3.py`;
- config setting in `backend/app/core/config.py` for one server-configured external local export directory;
- durable receipt table `l3_external_local_export_receipt`;
- durable audit table `l3_external_local_export_audit_event`;
- one Alembic migration for those tables;
- read-only session summary/status/history projection for external local export receipts;
- optional rendered write submit control plus read-only status/history, with no path editing and no raw path display;
- targeted API/backend tests for the exact authority, idempotency, failure, redaction, and disabled-side-effect contract; and
- headed/headless E2E proof if rendered write/status behavior changes.

No package mutation/reconstruction, source expansion/ingestion, RAG/vector behavior, qualitative-hybrid analysis runtime, provider-public delivery/use, real connector invocation, `ConnectorRun` or `ConnectorRunTarget` creation, credentials, network egress, generic destination dispatch, broad auth/security behavior, full mockup activation, or frontend-durable authority is admitted.

## Request Contract

The write request may accept only:

- `client_request_id`;
- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `reconciliation_record_id`;
- `connector_dispatch_record_ref`;
- `connector_local_destination_receipt_id`;
- `server_owned_local_outbox_target_receipt_id`;
- `server_owned_local_outbox_write_receipt_id`;
- `provider_private_handoff_receipt_id` when provider-private handoff is applicable;
- `external_export_download_record_ref`;
- `target_identity`;
- `dispatch_mode`;
- `operator_decision`; and
- optional `decision_notes`.

The admitted target identity is `server_configured_external_local_export_directory`.

The admitted dispatch mode is `server_configured_external_local_export_directory_write`.

The admitted operator decision is `write_server_configured_external_local_export_directory`.

The route must reject raw local paths, destination paths, destination URLs, provider URLs, public URLs, connector keys, connector payloads, connector run ids, connector run target ids, credentials, provider tokens, raw signed URLs, package mutation payloads, source expansion inputs, RAG/vector settings, prompt/model/provider settings, auth/security overrides, browser durable authority, retry, rerun, cancel, and arbitrary destination labels.

## Response And Status Contract

Write and status responses may expose only redacted server-owned fields:

- schema id/version and request id;
- status and operation state;
- session, pass, reconciliation, connector dispatch, connector-local receipt, server-owned local outbox target, server-owned local outbox write, provider-private handoff where applicable, and external export/download refs;
- `external_local_export_receipt_id`;
- target identity and dispatch mode;
- redacted server-configured destination label;
- external local export artifact ref and manifest ref using a redacted URI scheme;
- artifact and manifest hash/size;
- authority basis hash;
- idempotency/replay policy;
- audit receipt summary;
- status/history and created/updated timestamps; and
- disabled downstream lanes.

Responses and errors must not expose absolute local paths, relative caller paths, credentials, provider URLs, public URLs, raw token material, connector targets, destination URLs, package payload bytes, source contents, prompt/model data, RAG/vector internals, auth internals, browser storage state, or provider object keys.

## Lifecycle, Idempotency, And Failure Semantics

Required status vocabulary:

- `external_local_export_not_ready`;
- `external_local_export_ready`;
- `external_local_export_written`;
- `external_local_export_replay`;
- `external_local_export_conflict`;
- `external_local_export_stale_authority`;
- `external_local_export_failed`.

Required idempotency semantics:

- `client_request_id` is required and unique for the write operation;
- same `client_request_id` plus same authority basis returns the existing receipt/status;
- same `client_request_id` plus different authority basis fails closed;
- same authority basis plus different `client_request_id` returns the existing receipt/status rather than duplicate output;
- same deterministic export target plus same bytes returns the existing receipt/status;
- same deterministic export target plus different bytes fails closed; and
- retry/rerun/cancel request fields are not admitted.

Failure lifecycle must fail closed on stale authority, wrong session, wrong pass, wrong artifact, wrong connector dispatch ref, wrong connector-local receipt, wrong server-owned local outbox target, wrong server-owned local outbox write, wrong provider-private handoff where applicable, wrong external export/download ref, tampered hash/size, missing configured directory, path escape, target mismatch, timeout, partial write, unsupported credential/provider state, caller-supplied path/URL, and any forbidden adjacent surface.

Partial completion must not claim `external_local_export_written` unless both artifact and manifest bytes exist at the server-configured target and verify against expected hashes and sizes.

## Receipt And Audit Contract

The durable receipt must include:

- external local export receipt id;
- client request id;
- session id;
- analysis plan id;
- pass run id;
- reconciliation record id;
- connector dispatch record ref;
- connector-local destination receipt id;
- server-owned local outbox target receipt id;
- server-owned local outbox write receipt id;
- provider-private handoff receipt id where applicable;
- external export/download record ref;
- target identity `server_configured_external_local_export_directory`;
- dispatch mode `server_configured_external_local_export_directory_write`;
- target class `server_configured_external_destination_write`;
- redacted destination label;
- external artifact ref and manifest ref;
- artifact hash and size;
- manifest hash and size;
- authority basis hash;
- authority snapshot;
- status;
- idempotency key;
- redacted failure code where applicable;
- created timestamp; and
- updated timestamp.

The audit record must include explicit booleans showing that real connector invocation, `ConnectorRun` creation, `ConnectorRunTarget` creation, credential handling, network egress, provider-public delivery/use, raw public URL exposure, raw token exposure, package mutation/reconstruction, source expansion, RAG/vector behavior, broad auth/security behavior, full mockup activation, frontend-durable authority, and generic downstream dispatch remain disabled.

## Required Proof

The implementation-bearing pass must prove:

1. API write success from an existing server-owned local outbox write receipt, with provider-private handoff receipt required only where applicable.
2. Status success from the durable external local export receipt.
3. OpenAPI request/response schema for write/status.
4. Forbidden request fields fail closed, including arbitrary destination path and URL fields.
5. Same-key/same-basis replay is idempotent.
6. Same-key/different-basis conflict fails closed.
7. Same-basis/different-key returns existing receipt/status rather than duplicate output.
8. Duplicate deterministic target with same bytes returns existing receipt/status.
9. Duplicate deterministic target with different bytes fails closed.
10. Stale authority, wrong session, wrong artifact hash/size, wrong connector dispatch ref, wrong local receipt id, wrong local outbox target receipt id, wrong local outbox write receipt id, wrong provider-private handoff receipt where applicable, and wrong external export/download ref fail closed.
11. Database counts prove no `ConnectorRun` or `ConnectorRunTarget` creation.
12. Filesystem proof shows writes occur only under the server-configured external local export directory and outside app-owned staging.
13. Responses, errors, session summary, and rendered UI expose only redacted refs and no raw local paths.
14. Existing connector-local receipt, server-owned local outbox write, provider-private local-outbox handoff, package, source, RAG/vector, auth/security, and rendered UI behavior remain unchanged unless explicitly admitted here.
15. Headed and headless E2E proof runs if rendered write/status controls change.

## Non-Admission Boundary

This freeze admits no real connector invocation, no connector-run creation, no `ConnectorRunTarget` creation, no credentials, no network egress, no provider-public delivery/use, no raw public URL exposure, no raw token use, no caller-supplied destination path/URL, no package mutation/reconstruction, no source expansion/ingestion, no RAG/vector behavior, no qualitative-hybrid analysis runtime, no broad auth/security behavior, no full mockup activation, no frontend-durable authority, no generic connector framework, no generic destination dispatcher, no source adapter registry, no embedding generation, no vector index creation, no prompt/model/provider runtime, and no browser-owned target authority.

## Stop Conditions

Stop before runtime implementation if the next pass:

- selects more than `server_configured_external_local_export_directory`;
- requires external credentials, connector secrets, provider tokens, raw token exposure, public URL exposure, or network access;
- accepts operator-provided local paths, destination paths, destination URLs, provider URLs, buckets, containers, object keys, or connector targets;
- writes inside app-owned staging instead of outside it;
- cannot prove the configured destination path is server-owned and fail-closed;
- creates `ConnectorRun` or `ConnectorRunTarget` rows;
- mutates the existing server-owned local outbox artifact;
- exposes raw local filesystem paths, source artifact refs, provider URLs, signed URLs, raw token material, credentials, connector targets, destination URLs, package payload bytes, source contents, prompt/model data, RAG/vector internals, auth internals, or browser storage state;
- widens package, source, RAG/vector, provider-public, mockup, rendered UI, or auth/security behavior as a side effect; or
- cannot prove the write in isolated runtime state.

## Future End-To-End Sequence

After this selected A-surface is implemented, proven, merged, and synced, the remaining end-to-end Layer 3 path still requires separately selected and frozen surfaces for:

1. Package mutation/reconstruction, if the operator names the exact package action and mutation boundary.
2. Source expansion/ingestion, one named source family at a time.
3. RAG/vector or qualitative-hybrid analysis, only after source/index authority and output authority are defined.

The order above is directional, not automatic authority. Each future surface must have its own decision intake or equivalent selection record, implementation-entry freeze, focused implementation, targeted validation, PR review/check gate, merge, and current-main sync.

## Next Posture

The next whole-project posture is `await_current_main_sync_for_server_configured_external_local_export_directory_freeze`.

After the freeze is synced, the next exact implementation posture is `implement_server_configured_external_local_export_directory_after_freeze_sync`.
