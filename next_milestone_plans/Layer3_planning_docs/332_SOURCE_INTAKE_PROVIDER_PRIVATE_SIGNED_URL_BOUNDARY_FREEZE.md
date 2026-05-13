# 332 - Source Intake Provider Private Signed URL Boundary Freeze

Status: current-main planning/control freeze for `source_intake_provider_private_signed_url_boundary`.

Planning branch: `codex/l3-source-intake-postmerge-sync-922`
Current-main predecessor commit: `d4df0c4892303a3fd05fd1c6a87edeaf880682cf`
Sync predecessor: `331_SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_CURRENT_MAIN_SYNC.md`
Runtime predecessors: `323_SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_BOUNDARY.md`, `325_SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_BOUNDARY.md`, `330_SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_BOUNDARY.md`
Owner service: `backend/app/services/layer3_workbench.py`
Owner UI: `backend/app/review_ui/static/layer3.js`
Targeted future test surface: `backend/tests/test_layer3_workbench.py`, `backend/tests/test_layer3_page.py`, `e2e/layer3-workbench.spec.js`, `e2e/layer3-handoff.spec.js`

## Selected boundary

The next exact server-authoritative boundary is source-intake provider-private signed URL prepare/status/revoke over the current-main source-intake external export/download prepare, same-origin delivery, and token-only same-origin signed-reference authority.

This is intentionally narrower than public URLs, connector/destination dispatch, object-store provider writes beyond the existing provider-private URL contract, package mutation, source expansion, and RAG/vector retrieval.

## Current failure boundary

Source-intake provider-private signed URL behavior remains blocked in rendered controls by `!isSourceIntakeExternalExportDownloadState(external)` in the provider-private signed URL controls.

The future implementation must verify the backend provider-private signed URL admission boundary before editing. If backend provider-private endpoints also reject source-intake authority, the implementation must add an explicit source-intake rail there. If backend already admits the authority through server-side validation, the implementation must only remove the rendered block after proving the server owns the authority. Either way, the next implementation must not use frontend-only durable authority.

For planning/control purposes, the current failure boundary is `source_intake_provider_private_signed_url_not_admitted`.

## Future admitted semantics

The next code-bearing slice may only admit this path:

- request contract: existing provider-private signed URL prepare/status/revoke contracts
- required source-intake prepare schema: `layer3.source_intake_external_export_download_prepare.v1`
- required source-intake delivery schema: `layer3.source_intake_external_export_download_delivery.v1`
- required signed-reference server authority: `source_intake_external_export_download_signed_reference_gate`
- required signed-reference use mode: token-only same-origin signed-reference authority
- required source-intake identity: `source_intake_record_id`, `candidate_id`, `output_payload_hash`
- required APS artifact identity: `aps_bundle_ref`, `aps_bundle_id`, `aps_schema_id`, `source_artifact_hash`, `source_artifact_size_bytes`
- required provider behavior: provider-private signed URL prepare/status/revoke only
- rendered behavior: provider-private signed URL controls may enable only after complete source-intake server authority

## Required future proofs

The implementation PR must prove:

- source-intake provider-private signed URL prepare succeeds only after complete source-intake external export/download and signed-reference authority
- status and revoke remain bounded to the durable provider-private URL receipt/state contract
- source-intake identity and APS artifact identity are preserved
- no `AnalysisRun` is required or created
- source-intake same-origin delivery and same-origin signed-reference behavior remain unchanged
- provider public URL behavior remains blocked
- connector/destination dispatch remains blocked
- package mutation/reconstruction remains blocked
- source expansion, local-directory authority, web connector retrieval, and RAG/vector behavior remain blocked
- broad qualitative, full mockup, route/model/migration/auth/security behavior remain blocked unless a proven blocker forces a narrower freeze
- rendered controls expose no connector/destination controls and no public URL controls

## Scope explicitly not admitted

This freeze admits no runtime behavior by itself. It does not implement public URLs, connector/destination dispatch, package mutation/reconstruction, source expansion, local directory authority, web connector retrieval, RAG/vector retrieval, broad qualitative execution, full mockup activation, route/model/migration changes, auth/security behavior, or frontend-only durable authority.

## Next action

The next code-bearing action is `implement_source_intake_provider_private_signed_url_boundary` only. Start with a live source-of-truth audit of the provider-private backend admission helper and rendered provider-private signed URL controls before editing.
