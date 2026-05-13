# 323 - Source Intake External Export Download Boundary

Status: branch-local implementation for `source_intake_external_export_download_boundary`.

Branch: `codex/l3-source-intake-export-download`
Freeze predecessor: `322_SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_BOUNDARY_FREEZE.md`
Owner service: `backend/app/services/layer3_workbench.py`
Response helper: `backend/app/services/layer3_external_export_response.py`
Targeted proof: `backend/tests/test_layer3_workbench.py::test_execution_start_runs_source_intake_selected_pass_without_analysis_run`

## Canonical source of truth

The canonical source of truth is the durable server-owned source-intake APS handoff dispatch chain:

- `layer3.source_intake_aps_handoff_dispatch.v1`
- `layer3.source_intake_handoff_export_prepare.v1`
- `layer3.source_intake_package_review_submit.v1`
- `layer3.source_intake_package_construction_commit.v1`
- `layer3.source_intake_execution_output.v1`

The boundary admits source-intake external export/download prepare/readiness only when `external_export_download_prepare` can prove that the supplied request matches durable source-intake dispatch authority, durable handoff/export prepare authority, durable package-review submit authority, package construction state, source package refs/hashes, APS bundle package identity, and source-intake identity.

## Implemented behavior

`external_export_download_prepare` now admits the source-intake APS handoff dispatch path and returns schema `layer3.source_intake_external_export_download_prepare.v1` for the bounded readiness state.

The implementation preserves `source_intake_record_id`, `candidate_id`, `output_payload_ref`, `output_payload_hash`, `package_review_submit_schema_id`, package refs/hashes, APS handoff record refs, APS output package identity, and APS bundle identity. It rejects source-intake requests that provide `analysis_run_id` or whose upstream source-intake authority does not match durable server state with `source_intake_external_export_download_prepare_not_admitted`.

The no-validator prepare path derives artifact hash and size from the recorded APS handoff package when no existing readiness record exists. It does not treat caller-supplied bundle hash or local/browser state as authority.

## Proofs

- `source_intake_aps_handoff_dispatch_can_prepare_external_export_download`
- `source_intake_external_export_download_identity_is_deterministic_and_server_derived`
- `source_intake_identity_preserved_in_external_export_download_state`
- `aps_handoff_dispatch_record_ref_matches_durable_dispatch_state`
- `handoff_export_prepare_record_ref_matches_durable_prepare_state`
- `package_review_submit_record_ref_matches_durable_submit_state`
- `source_package_payload_refs_and_hashes_match_durable_package_state`
- `aps_evidence_bundle_payload_ref_and_hash_match_durable_dispatch_package`
- `no_analysis_run_required_or_created`
- `no_source_package_rows_or_payloads_mutated`
- `duplicate_or_conflicting_external_export_download_requests_fail_closed_or_replay_idempotently`
- `mismatched_dispatch_record_ref_fails_closed`
- `connector_destination_dispatch_remains_blocked`
- `provider_public_private_url_remains_blocked`

## Validation

Targeted validation passed:

```powershell
python -m pytest .\backend\tests\test_layer3_workbench.py
```

Result: `22 passed`.

## Non-goals and blocked scope

This branch does not implement actual delivery, rendered UI controls, connector or destination dispatch, provider public/private URLs, signed-reference behavior, RAG/vector retrieval, route changes, model changes, migration changes, auth/security behavior, package mutation or reconstruction, source expansion, local path or local directory authority, generic upload, broad qualitative behavior, or full mockup behavior.

## Next boundary

The next required decision is `source_intake_external_export_download_delivery_boundary_freeze` if source-intake same-origin delivery should be admitted after this prepare/readiness state. Until that freeze exists and is implemented, this branch should be treated as prepare/readiness only.
