# 740 - Corrected Artifact Active Authority External Local Export Evaluation

## Status

Status: branch-local proof for `corrected_artifact_active_authority_external_local_export`.

Doc: `740_CORRECTED_ARTIFACT_ACTIVE_AUTHORITY_EXTERNAL_LOCAL_EXPORT_EVALUATION.md`.

Predecessor current-main sync doc: `739_CORRECTED_ARTIFACT_ACTIVE_AUTHORITY_LOCAL_OUTBOX_PROVIDER_PRIVATE_HANDOFF_EVALUATION_CURRENT_MAIN_SYNC.md`.

Evaluation branch: `codex/l3-corrected-external-local-export`.

Current-main checkpoint before evaluation: `d85d5ad7602a22cea7d52edd678612274d7fab73`.

Selected downstream reader path: `external_local_export`.

Selected route: `POST /api/v1/layer3/handoff/connector/local-outbox/external-local-export/write`.

Selected service authority: `backend/app/services/layer3_external_local_export.py`.

Durable receipt authority: `L3ExternalLocalExportReceipt`.

Durable audit authority: `L3ExternalLocalExportAuditEvent`.

Evaluation result: `corrected_artifact_active_authority_external_local_export_proven`.

Runtime behavior change in this pass: `false`.

Test/proof behavior change in this pass: `true`.

Current-main proof already present: `false`.

## Canonical Authority

The canonical implementation source for this reader is `backend/app/services/layer3_external_local_export.py`.

The canonical API entrypoint is `POST /api/v1/layer3/handoff/connector/local-outbox/external-local-export/write` in `backend/app/api/layer3.py`.

The reader consumes recorded `local_outbox_provider_private_handoff`, `server_owned_local_outbox_write`, `server_owned_local_outbox_target`, `connector_local_destination_receipt`, `connector_dispatch_record`, and `external_export_download_prepare` authority. It validates the server-owned local outbox artifact and manifest bytes, writes only to the server-configured external local export directory, records durable external local export receipt/audit state, and returns only redacted `external-local-export://` refs.

## Branch-Local Proof

This pass extends `backend/tests/test_layer3_api.py::test_layer3_api_connector_local_destination_receipt_applies_corrected_artifact_active_authority` so the corrected-artifact activation chain reaches external local export after local-outbox provider-private handoff.

The proof drives:

- package correction and replacement activation;
- handoff export prepare;
- APS handoff dispatch;
- external export/download prepare and same-origin delivery;
- connector dispatch record;
- connector-local destination receipt;
- server-owned local outbox fake target;
- server-owned local outbox write;
- local-outbox provider-private handoff prepare/status; and
- external local export write/status.

The external local export proof verifies:

- `server_owned_local_outbox_write_receipt_id` and `provider_private_handoff_receipt_id` match the corrected active-authority chain;
- `external_artifact_hash`, `external_artifact_size_bytes`, `source_outbox_artifact_hash`, and `source_outbox_artifact_size_bytes` match the server-owned local outbox write response;
- durable `L3ExternalLocalExportReceipt.authority_snapshot_json` carries both `provider_private_handoff_authority_basis_hash` and `server_owned_local_outbox_write_authority_basis_hash`;
- external local export status returns `external_local_export_written`;
- written artifact bytes match the corrected active readiness artifact;
- response, status, and session-summary surfaces expose no raw storage path, configured export path, or source artifact ref;
- source `L3OutputPackage` rows remain unchanged;
- no `ConnectorRun`, `ConnectorRunTarget`, or `L3ProviderPrivateSignedUrlReceipt` rows are created;
- no real connector invocation, credentials, network egress, provider-public delivery, raw public URL, raw token, package mutation, source expansion, RAG/vector behavior, qualitative-hybrid runtime, auth/security behavior, full mockup activation, frontend-durable authority, or generic downstream dispatch is enabled; and
- duplicate write requests replay as `already_recorded`.

Observed validation:

```powershell
python -m pytest .\backend\tests\test_layer3_api.py::test_layer3_api_connector_local_destination_receipt_applies_corrected_artifact_active_authority -q
```

Result observed in this branch: `1 passed`.

## Still Blocked

This pass admits no service runtime behavior change, provider-public delivery/use, provider-private signed URL generation/use, raw token exposure, raw provider object key exposure, real provider network write, real provider object store write, real connector invocation, `ConnectorRun` creation, `ConnectorRunTarget` creation, arbitrary external destination write, credentials, package payload rewrite, source `L3OutputPackage` mutation, downstream invalidation, handoff/export rerun, external export/download prepare rerun beyond delivery revalidation, source expansion, RAG/vector behavior, qualitative-hybrid runtime, rendered controls, auth/security behavior, full mockup activation, frontend-durable authority, caller-supplied paths/URLs, browser-supplied refs/hashes/bytes, raw local path exposure, or hidden LLM planning.

## Next Posture

The next exact posture after merge is `await_current_main_sync_for_corrected_artifact_active_authority_external_local_export_evaluation`.

After current-main sync, the next exact posture should pivot out of same-family package/export active-authority proof loops to `select_source_expansion_ingestion_named_source_family_after_corrected_artifact_external_local_export_sync` unless current-main evidence identifies a concrete unresolved defect or another named downstream reader.
