# 327 - Source Intake External Export Download Rendered Controls Boundary

Status: branch-local implementation for `source_intake_external_export_download_rendered_controls_boundary`.

Branch: `codex/l3-source-intake-rendered-delivery-controls`
Current-main predecessor commit: `f17d9e2e9a6e1dacfbb86552dd94b6b9af447634`
Freeze predecessor: `326_SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_RENDERED_CONTROLS_BOUNDARY_FREEZE.md`
Owner UI: `backend/app/review_ui/static/layer3.js`
Rendered shell: `backend/app/review_ui/static/layer3.html`
Targeted test: `backend/tests/test_layer3_page.py`

## Implemented boundary

The rendered Layer 3 workbench now treats source-intake external export/download delivery as an explicit rendered family instead of relying on a generic non-associated/non-qualitative fallback.

Implemented UI markers:

- `SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID = 'layer3.source_intake_external_export_download_prepare.v1'`
- `SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID = 'layer3.source_intake_external_export_download_delivery.v1'`
- `isSourceIntakeExternalExportDownloadState`
- `sourceIntakeDeliveryUiState`
- `source_intake_external_export_download_delivery_ui_ready`
- `deliveryUiStateAdmitted`

## Server authority projection

The rendered control may enable source-intake same-origin delivery only when the server-returned prepare/readiness state is complete:

- schema id is `layer3.source_intake_external_export_download_prepare.v1`
- readiness state is `external_export_download_prepared`
- `external_export_download_record_ref` is present
- `export_download_descriptor_ref` is present
- `source_intake_record_id` is present
- `candidate_id` is present
- `aps_bundle_ref` is present
- `source_artifact_hash` is present

The actual delivery still uses the existing same-origin attachment path, `submitAttachmentForm('/handoff/export/download/deliver', externalExportDownloadDeliveryPayload())`, and posts `operator_decision: 'deliver_external_export_download'` plus `delivery_mode: 'same_origin_artifact_stream'`.

## Scope locks preserved

This branch admits no backend runtime behavior, route, model, migration, auth/security behavior, package mutation, source expansion, connector/destination dispatch, provider public/private URL behavior, RAG/vector behavior, broad qualitative behavior, or full mockup activation.

The rendered logic explicitly blocks these adjacent controls for source-intake delivery:

- signed-reference generation/use remains blocked by `!isSourceIntakeExternalExportDownloadState(external)`
- provider-private signed URL prepare/status/revoke remains blocked by `!isSourceIntakeExternalExportDownloadState(external)`
- unknown non-associated/non-qualitative external-export families no longer get implicit delivery UI admission
- the pre-existing APS evidence-bundle delivery path remains admitted only when the prepare record is explicitly an `aps_evidence_bundle_download_reference` over `aps.evidence_bundle.v2`

## Validation

- `python -m pytest .\backend\tests\test_layer3_page.py` -> `3 passed, 3 warnings`
- `npx playwright test e2e/layer3-handoff.spec.js --project=chromium` -> `3 passed`
- `python .\tools\l3-progress-check.py` -> `Layer 3 progress state check: PASS`
- `git diff --check` -> clean except expected CRLF normalization warnings

## Next required decision

After this branch lands, the source-intake external export/download rendered delivery chain is implemented through same-origin delivery. The next required action is a current-main proof/control sync, then a separate named freeze for whichever deferred lane is selected next. Do not begin provider/public URL, connector/destination dispatch, package mutation, source expansion, RAG/vector, full mockup, or auth/security work without a new explicit freeze.
