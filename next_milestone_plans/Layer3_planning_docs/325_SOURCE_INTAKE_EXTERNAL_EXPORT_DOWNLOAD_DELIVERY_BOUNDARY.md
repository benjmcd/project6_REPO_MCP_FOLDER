# 325 - Source Intake External Export Download Delivery Boundary

Status: branch-local implementation for `source_intake_external_export_download_delivery_boundary`.

Branch: `codex/l3-source-intake-download-delivery`
Freeze predecessor: `324_SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_BOUNDARY_FREEZE.md`
Owner service: `backend/app/services/layer3_workbench.py`
Response helper: `backend/app/services/layer3_external_export_response.py`
Targeted proof: `backend/tests/test_layer3_workbench.py::test_execution_start_runs_source_intake_selected_pass_without_analysis_run`

## Canonical source of truth

The canonical source of truth is the durable source-intake external export/download prepare state from `layer3.source_intake_external_export_download_prepare.v1`, revalidated through the existing server-owned delivery path against:

- `layer3.source_intake_aps_handoff_dispatch.v1`
- `layer3.source_intake_handoff_export_prepare.v1`
- `layer3.source_intake_package_review_submit.v1`
- `layer3.source_intake_package_construction_commit.v1`
- `layer3.source_intake_execution_output.v1`
- the APS evidence-bundle handoff package payload ref, id, schema, hash, and size

## Implemented behavior

`external_export_download_deliver` now admits the source-intake prepare/readiness state selected by doc 324 and returns a same-origin `ExternalExportDownloadDelivery` for the already-created APS evidence-bundle handoff package.

`backend/app/services/layer3_external_export_response.py` emits `layer3.source_intake_external_export_download_delivery.v1` in `X-Layer3-Schema-Id` when the validated readiness authority is source-intake. The delivery path reuses the existing same-origin artifact-stream contract and preserves source-intake identity in the returned authority body.

The implementation does not create `AnalysisRun`, create or mutate source packages, add routes, add models or migrations, expose provider/public/signed URLs, dispatch to connectors or destinations, add rendered UI controls, widen source families, activate RAG/vector behavior, or broaden qualitative execution.

## Proofs

- `source_intake_external_export_download_prepare_can_deliver_same_origin_artifact_stream`
- `source_intake_delivery_revalidates_prepare_readiness_state`
- `source_intake_delivery_revalidates_aps_handoff_dispatch_state`
- `source_intake_delivery_revalidates_descriptor_ref`
- `source_intake_delivery_revalidates_aps_bundle_ref_id_schema_hash_and_size`
- `source_intake_identity_preserved_in_delivery_authority`
- `no_analysis_run_required_or_created`
- `no_source_package_rows_or_payloads_mutated`
- `connector_destination_dispatch_remains_blocked`
- `provider_public_private_url_remains_blocked`
- `signed_reference_behavior_remains_blocked`
- `rendered_ui_controls_remain_blocked`

## Validation

Targeted validation passed:

```powershell
python -m pytest .\backend\tests\test_layer3_workbench.py
```

Result: `22 passed`.

## Non-goals and blocked scope

This branch does not implement rendered UI controls, connector or destination dispatch, provider public/private URLs, signed-reference behavior, RAG/vector retrieval, route changes, model changes, migration changes, auth/security behavior, package mutation or reconstruction, source expansion, local path or local directory authority, generic upload, broad qualitative behavior, or full mockup behavior.

## Next boundary

The next required decision is `source_intake_external_export_download_rendered_controls_boundary_freeze` if source-intake delivery should be surfaced through rendered controls. Until that freeze exists and is implemented, delivery remains a server-authoritative same-origin service/API capability only.
