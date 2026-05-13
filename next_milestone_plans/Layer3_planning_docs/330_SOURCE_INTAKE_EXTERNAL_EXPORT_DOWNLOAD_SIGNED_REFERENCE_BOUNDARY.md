# 330 - Source Intake External Export Download Signed Reference Boundary

Status: branch-local implementation for `source_intake_external_export_download_signed_reference_boundary`.

Implementation branch: `codex/l3-source-intake-signed-reference`
Current-main predecessor commit: `f30b501e9590c9b2f961c8390e912f1b40a85580`
Freeze predecessor: `329_SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_BOUNDARY_FREEZE.md`
Owner service: `backend/app/services/layer3_workbench.py`
Owner UI: `backend/app/review_ui/static/layer3.js`
Targeted test surface: `backend/tests/test_layer3_workbench.py`, `backend/tests/test_layer3_page.py`, `e2e/layer3-workbench.spec.js`, `e2e/layer3-handoff.spec.js`
Targeted validation result: `python -m pytest .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_page.py` passed with `25 passed`; `npx playwright test e2e/layer3-workbench.spec.js e2e/layer3-handoff.spec.js --project=chromium` passed with `34 passed`.

## Implemented boundary

This branch admits source-intake same-origin signed-reference generation and token-only use over the already admitted source-intake external export/download prepare plus same-origin delivery authority.

The implementation does not create a provider URL, public URL, connector run, destination dispatch, package mutation, source expansion, route, model, migration, auth/security behavior, RAG/vector behavior, or broad qualitative behavior. It keeps the existing same-origin signed-reference model and adds source-intake as a second explicit authority rail next to the existing associated-cohort descriptive-summary rail.

## Server authority

`backend/app/services/layer3_workbench.py` now uses `_signed_reference_required_delivery_authority` instead of the previous associated-cohort-only predicate. The admitted source-intake rail requires:

- `schema_id: layer3.source_intake_external_export_download_prepare.v1`
- `analysis_run_id: None`
- `source_intake_record_id`
- `candidate_id`
- `output_payload_hash`
- `aps_bundle_ref`
- `aps_bundle_id`
- `aps_schema_id`
- `source_artifact_hash`

Generation still calls `external_export_download_deliver` before minting a token. Use still accepts only `signed_reference_token`, replays the token payload through `external_export_download_deliver`, compares the current authority basis to the token authority, and records use through the existing durable signed-reference state/replay policy.

## Rendered controls

`backend/app/review_ui/static/layer3.js` now allows source-intake signed-reference generation once `externalExportDownloadDeliveryUiAdmitted(external)` is true. provider-private signed URL controls still retain `!isSourceIntakeExternalExportDownloadState(external)`, so this branch does not admit provider/public URL behavior.

## Proof obligations

The targeted backend test extends the existing source-intake end-to-end chain to prove:

- source-intake delivery remains `layer3.source_intake_external_export_download_delivery.v1`
- signed-reference generation returns `layer3.external_export_download_signed_reference.v1`
- server authority is `source_intake_external_export_download_signed_reference_gate`
- generated authority carries source-intake identity, output hash, artifact hash, artifact size, and no `AnalysisRun`
- token-only use returns `layer3.external_export_download_signed_reference_use.v1`
- use revalidates source-intake delivery authority and returns the existing APS evidence-bundle artifact

The targeted rendered test proves source-intake signed-reference generation is no longer UI-blocked while provider-private URL controls remain source-intake-blocked.

## Scope still blocked

Provider-private URLs, public URLs, connector/destination dispatch, package mutation/reconstruction, source expansion, local-directory authority, web connector retrieval, RAG/vector behavior, broad qualitative behavior, full mockup activation, route/model/migration changes, and auth/security behavior remain blocked behind later named freezes.

## Next boundary

After this branch is merged and current-main proof is synchronized, the next required decision is a separate named freeze. The likely downstream choices are provider/private URL rendering, connector/destination dispatch, RAG/vector retrieval, source expansion beyond bounded operator upload, or broad qualitative execution, but none should start without a new source-of-truth audit and boundary freeze.
