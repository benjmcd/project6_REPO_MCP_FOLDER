# 329 - Source Intake External Export Download Signed Reference Boundary Freeze

Status: current-main planning/control freeze for `source_intake_external_export_download_signed_reference_boundary`.

Planning branch: `codex/l3-source-intake-postmerge-sync-920`
Current-main predecessor commit: `11185c51b1af4c68a8df9f28a1fd0bb66cf5cf32`
Sync predecessor: `328_SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_RENDERED_CONTROLS_CURRENT_MAIN_SYNC.md`
Implemented rendered-controls predecessor: `327_SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_RENDERED_CONTROLS_BOUNDARY.md`
Runtime predecessors: `323_SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_BOUNDARY.md`, `325_SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_BOUNDARY.md`
Owner service: `backend/app/services/layer3_workbench.py`
Owner UI: `backend/app/review_ui/static/layer3.js`
Targeted future test surface: `backend/tests/test_layer3_workbench.py`, `backend/tests/test_layer3_page.py`, `e2e/layer3-workbench.spec.js`, `e2e/layer3-handoff.spec.js`

## Selected boundary

The next exact server-authoritative runtime boundary is source-intake same-origin signed-reference generation/use over the already-admitted source-intake external export/download prepare and same-origin delivery state.

This is intentionally narrower than provider/public URLs and connector/destination dispatch. It keeps the delivery artifact inside the existing same-origin signed-reference model and requires server-owned token, durable signed-reference state, and delivery-authority revalidation at generation and use.

## Current repo-confirmed failure boundary

Current `backend/app/services/layer3_workbench.py` limits signed delivery references to the associated-cohort descriptive-summary authority rail:

- `external_export_download_generate_signed_reference` calls `external_export_download_deliver` and then `_signed_reference_required_cohort_authority(delivery.authority)`
- blocked scope raises `external_export_download_signed_reference_scope_not_admitted`
- `external_export_download_use_signed_reference` decodes the token, revalidates delivery through `external_export_download_deliver`, and again calls `_signed_reference_required_cohort_authority(delivery.authority)`
- rendered source-intake controls stay blocked by `!isSourceIntakeExternalExportDownloadState(external)`

Therefore the future implementation must not bypass the existing delivery validator or token-use revalidation. It must replace the associated-cohort-only authority predicate with an explicit admitted-source-intake authority branch that is at least as strict as the source-intake prepare and delivery boundaries.

## Future admitted semantics

The next code-bearing slice may admit only this path:

- request contract: existing external export/download signed-reference generation/use contracts
- required prepare schema: `layer3.source_intake_external_export_download_prepare.v1`
- required delivery schema: `layer3.source_intake_external_export_download_delivery.v1`
- required source-intake identity: `source_intake_record_id`, `candidate_id`, `output_payload_hash`
- required APS artifact identity: `aps_bundle_ref`, `aps_bundle_id`, `aps_schema_id`, `source_artifact_hash`, `source_artifact_size_bytes`
- required delivery mode: `same_origin_artifact_stream`
- future signed-reference delivery mode: `same_origin_signed_delivery_reference`
- token state: server-generated, durable signed-reference state only
- use behavior: token-only request, delivery authority revalidated at use, replay policy preserved
- UI behavior: source-intake rendered signed-reference controls may enable only after complete source-intake prepare/delivery authority

## Required future proofs

The implementation PR must prove all of these before merge:

- source-intake signed-reference generation succeeds only over durable source-intake external export/download prepare and delivery authority
- generation fails closed when source-intake identity, APS bundle identity, descriptor identity, artifact hash/size, or delivery mode mismatches
- generated token authority includes source-intake identity and artifact identity without `AnalysisRun`
- token use revalidates current source-intake delivery authority and fails closed on authority mismatch
- replay behavior remains governed by existing durable signed-reference replay policy
- existing associated-cohort signed-reference generation/use remains unchanged
- source-intake provider-private/public URL behavior remains blocked
- connector/destination dispatch remains blocked
- package mutation/reconstruction remains blocked
- source expansion, local-directory authority, web connector retrieval, and RAG/vector behavior remain blocked
- broad qualitative, full mockup, route/model/migration/auth/security behavior remain blocked unless directly required by a proven blocker
- rendered source-intake controls expose no provider/private/public URL controls and no connector/destination controls

## Scope explicitly not admitted

This freeze admits no runtime behavior by itself. It does not implement provider/public URLs, provider-private URL behavior, connector/destination dispatch, package mutation/reconstruction, source expansion, local directory authority, web connector retrieval, RAG/vector retrieval, broad qualitative execution, full mockup activation, route/model/migration changes, auth/security behavior, or frontend-only durable authority.

## Next action

The next code-bearing action is `implement_source_intake_external_export_download_signed_reference_boundary` only. If live repo evidence shows that signed-reference state cannot safely carry source-intake authority without schema/model work, stop and convert that evidence into a narrower implementation-entry freeze instead of broadening the runtime slice.
