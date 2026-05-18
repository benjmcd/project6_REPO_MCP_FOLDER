# 738 - Corrected Artifact Active Authority Local Outbox Provider-Private Handoff Evaluation

## Status

Status: branch-local proof for `corrected_artifact_active_authority_local_outbox_provider_private_handoff`.

Doc: `738_CORRECTED_ARTIFACT_ACTIVE_AUTHORITY_LOCAL_OUTBOX_PROVIDER_PRIVATE_HANDOFF_EVALUATION.md`.

Predecessor current-main sync doc: `737_CORRECTED_ARTIFACT_ACTIVE_AUTHORITY_SERVER_OWNED_LOCAL_OUTBOX_WRITE_EVALUATION_CURRENT_MAIN_SYNC.md`.

Evaluation branch: `codex/l3-corrected-provider-private-handoff`.

Current-main checkpoint before evaluation: `881e8965698229c12e092de8c21a89fd94a9db4c`.

Selected downstream reader path: `local_outbox_provider_private_handoff`.

Selected route: `POST /api/v1/layer3/handoff/connector/local-outbox/provider-private/prepare`.

Selected service authority: `backend/app/services/layer3_local_outbox_provider_private_handoff.py`.

Durable receipt authority: `L3LocalOutboxProviderPrivateHandoffReceipt`.

Durable audit authority: `L3LocalOutboxProviderPrivateHandoffAuditEvent`.

Evaluation result: `corrected_artifact_active_authority_local_outbox_provider_private_handoff_proven`.

Runtime behavior change in this pass: `false`.

Test/proof behavior change in this pass: `true`.

Current-main proof already present: `false`.

## Canonical Authority

The canonical implementation source for this reader is `backend/app/services/layer3_local_outbox_provider_private_handoff.py`.

The canonical API entrypoint is `POST /api/v1/layer3/handoff/connector/local-outbox/provider-private/prepare` in `backend/app/api/layer3.py`.

The reader consumes recorded `server_owned_local_outbox_write`, `server_owned_local_outbox_target`, `connector_local_destination_receipt`, `connector_dispatch_record`, and `external_export_download_prepare` authority. It validates the derived server-owned local outbox artifact and manifest refs, records durable provider-private handoff receipt/audit state, and returns only redacted provider-private and `storage://server-owned-local-outbox/...` authority.

## Branch-Local Proof

This pass extends `backend/tests/test_layer3_api.py::test_layer3_api_connector_local_destination_receipt_applies_corrected_artifact_active_authority` so the corrected-artifact activation chain reaches provider-private local-outbox handoff after server-owned local outbox write.

The proof drives:

- package correction and replacement activation;
- handoff export prepare;
- APS handoff dispatch;
- external export/download prepare and same-origin delivery;
- connector dispatch record;
- connector-local destination receipt;
- server-owned local outbox fake target;
- server-owned local outbox write; and
- local-outbox provider-private handoff prepare/status.

The provider-private handoff proof verifies:

- `server_owned_local_outbox_write_receipt_id`, `server_owned_local_outbox_target_receipt_id`, and `connector_local_destination_receipt_id` match the corrected active-authority chain;
- `source_artifact_hash` and `source_artifact_size_bytes` match the corrected active readiness artifact;
- `outbox_artifact_hash`, `outbox_artifact_size_bytes`, `outbox_artifact_ref`, and `outbox_manifest_ref` match the server-owned local outbox write response;
- durable `L3LocalOutboxProviderPrivateHandoffReceipt.authority_snapshot_json` carries `server_owned_local_outbox_write_authority_basis_hash`;
- provider-private status returns `local_outbox_provider_private_handoff_prepared`;
- raw provider token, raw signature, raw source artifact ref, and raw local storage path are not exposed;
- source `L3OutputPackage` rows remain unchanged;
- no `ConnectorRun`, `ConnectorRunTarget`, or `L3ProviderPrivateSignedUrlReceipt` rows are created;
- no external provider network write, object store write, external destination write, credentials, provider-public delivery, package mutation, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, or frontend-durable authority is enabled; and
- duplicate prepare requests replay as `already_recorded`.

Observed validation:

```powershell
python -m pytest .\backend\tests\test_layer3_api.py::test_layer3_api_connector_local_destination_receipt_applies_corrected_artifact_active_authority -q
```

Result observed in this branch: `1 passed`.

## Still Blocked

This pass admits no service runtime behavior change, external local export adoption, provider-public delivery/use, provider-private signed URL generation/use, raw token exposure, raw provider object key exposure, real provider network write, real provider object store write, real connector invocation, `ConnectorRun` creation, `ConnectorRunTarget` creation, arbitrary external destination write, credentials, package payload rewrite, source `L3OutputPackage` mutation, downstream invalidation, handoff/export rerun, external export/download prepare rerun beyond delivery revalidation, source expansion, RAG/vector behavior, rendered controls, auth/security behavior, full mockup activation, frontend-durable authority, caller-supplied paths/URLs, browser-supplied refs/hashes/bytes, raw local path exposure, or hidden LLM planning.

## Next Posture

The next exact posture after merge is `await_current_main_sync_for_corrected_artifact_active_authority_local_outbox_provider_private_handoff_evaluation`.

After current-main sync, the next exact posture should be `select_next_downstream_active_package_authority_reader_after_corrected_artifact_local_outbox_provider_private_handoff_sync`.
