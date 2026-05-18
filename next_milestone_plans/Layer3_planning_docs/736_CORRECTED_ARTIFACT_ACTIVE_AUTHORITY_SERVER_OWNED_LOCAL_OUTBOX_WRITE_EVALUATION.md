# 736 - Corrected Artifact Active Authority Server Owned Local Outbox Write Evaluation

## Status

Status: branch-local proof for `corrected_artifact_active_authority_server_owned_local_outbox_write`.

Doc: `736_CORRECTED_ARTIFACT_ACTIVE_AUTHORITY_SERVER_OWNED_LOCAL_OUTBOX_WRITE_EVALUATION.md`.

Predecessor current-main sync doc: `735_CORRECTED_ARTIFACT_ACTIVE_AUTHORITY_SERVER_OWNED_LOCAL_OUTBOX_FAKE_TARGET_EVALUATION_CURRENT_MAIN_SYNC.md`.

Evaluation branch: `codex/l3-corrected-outbox-write`.

Current-main checkpoint before evaluation: `fdb0e94d14a791548f104a739276c597320c4682`.

Selected downstream reader path: `server_owned_local_outbox_write`.

Selected route: `POST /api/v1/layer3/handoff/connector/local-outbox/write`.

Selected service authority: `backend/app/services/layer3_server_owned_local_outbox_write.py`.

Evaluation result: `corrected_artifact_active_authority_server_owned_local_outbox_write_proven`.

Runtime behavior change in this pass: `false`.

Test/proof behavior change in this pass: `false`.

Current-main proof already present: `true`.

## Canonical Authority

The canonical implementation source for this reader is `backend/app/services/layer3_server_owned_local_outbox_write.py`.

The canonical API entrypoint is `POST /api/v1/layer3/handoff/connector/local-outbox/write` in `backend/app/api/layer3.py`.

The durable write/status authority remains `L3ServerOwnedLocalOutboxWriteReceipt`.

The reader consumes recorded `server_owned_local_outbox_target`, `connector_local_destination_receipt`, `connector_dispatch_record`, and `external_export_download_prepare` authority. It validates the APS bundle artifact through `load_persisted_bundle_artifact`, writes only under the server-owned storage-derived local outbox root, and returns only redacted `storage://server-owned-local-outbox/...` refs.

## Current-Main Proof

Current main already contains the direct corrected-artifact API regression proving this reader in `backend/tests/test_layer3_api.py::test_layer3_api_connector_local_destination_receipt_applies_corrected_artifact_active_authority`.

The proof drives the corrected-artifact chain through:

- package correction and replacement activation;
- handoff export prepare;
- APS handoff dispatch;
- external export/download prepare;
- same-origin external export/download delivery;
- connector dispatch record;
- connector-local destination receipt;
- server-owned local outbox fake target; and
- server-owned local outbox write.

The write proof verifies:

- `accepted_artifact_hash` and `accepted_artifact_size_bytes` match the corrected active readiness source artifact;
- the response uses `artifact://server-owned-local-outbox-source-redacted`;
- `outbox_artifact_ref` and `outbox_manifest_ref` are redacted `storage://server-owned-local-outbox/...` refs;
- the written outbox artifact bytes match the corrected delivered APS bundle bytes;
- the written artifact hash matches `external_export_download_prepare.source_artifact_hash`;
- the manifest uses the redacted accepted artifact ref;
- `L3ServerOwnedLocalOutboxWriteReceipt.authority_snapshot_json` carries `connector_local_destination_receipt_authority_basis_hash`;
- source `L3OutputPackage` rows remain unchanged;
- no `ConnectorRun` or `ConnectorRunTarget` rows are created;
- no external destination write, real connector invocation, credentials, provider-public delivery, package mutation, source expansion, or RAG/vector behavior is enabled; and
- duplicate write requests replay as `already_recorded`.

Observed validation:

```powershell
python -m pytest .\backend\tests\test_layer3_api.py::test_layer3_api_connector_local_destination_receipt_applies_corrected_artifact_active_authority -q
```

Result observed before this control record: `1 passed`.

## Scope Boundary

This pass records the already-present current-main proof for the server-owned local outbox write reader. It does not introduce service runtime behavior.

The existing regression also contains downstream provider-private handoff and external local export assertions. Those assertions are not admitted by this document as the selected reader for this pass. Provider-private handoff adoption and external local export adoption still require their own exact selection, proof/control record, current-main sync, and checker coverage before broader activation claims.

## Still Blocked

This pass admits no new service runtime behavior, connector invocation, connector-run creation, connector target creation, real destination write beyond the selected server-owned local outbox write, arbitrary external destination write, credentials, external network egress, provider-public delivery/use, raw public URL exposure, signed URL generation, provider-private signed URL generation, provider-private handoff adoption, external local export adoption, package payload rewrite, source `L3OutputPackage` mutation, downstream invalidation, handoff/export rerun, external export/download prepare rerun beyond delivery revalidation, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, rendered controls, auth/security behavior, frontend-durable authority, caller-supplied paths/URLs, browser-supplied refs/hashes/bytes, raw local path exposure, or hidden LLM planning.

## Next Posture

The next exact posture after merge is `await_current_main_sync_for_corrected_artifact_active_authority_server_owned_local_outbox_write_evaluation`.

After current-main sync, the next exact posture should be `select_next_downstream_active_package_authority_reader_after_corrected_artifact_server_owned_local_outbox_write_sync`.
