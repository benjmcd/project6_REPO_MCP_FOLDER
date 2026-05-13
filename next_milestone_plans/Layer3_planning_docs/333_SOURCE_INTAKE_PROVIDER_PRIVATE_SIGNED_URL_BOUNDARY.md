# Source Intake Provider Private Signed URL Boundary

Status: branch-local implementation for `source_intake_provider_private_signed_url_boundary`.

This pass admits the narrow provider-private signed URL prepare/status/revoke path for source-intake external export/download readiness only after server-side same-origin signed-reference use has produced a durable receipt. The canonical source of truth is the existing provider-private signed URL service plus the source-intake external export/download prepare authority recorded by `backend/app/services/layer3_workbench.py`.

## Implemented authority chain

- implementation_branch: `codex/l3-source-intake-provider-private-url`
- selected_runtime_family: `source_breadth_runtime`
- selected_runtime_mode: `source_intake_provider_private_signed_url_boundary`
- freeze_predecessor: `source_intake_provider_private_signed_url_boundary_freeze`
- freeze_doc: `332_SOURCE_INTAKE_PROVIDER_PRIVATE_SIGNED_URL_BOUNDARY_FREEZE.md`
- governing_service: `backend/app/services/layer3_provider_private_signed_url.py`
- rendered_authority_projection: `backend/app/review_ui/static/layer3.js`
- source_prepare_schema_id: `layer3.source_intake_external_export_download_prepare.v1`
- provider_prepare_schema_id: `layer3.provider_private_signed_url.prepare.v1`
- provider_status_schema_id: `layer3.provider_private_signed_url.status.v1`
- provider_revoke_schema_id: `layer3.provider_private_signed_url.revoke.v1`

## Server-side admission rule

For readiness rows whose schema is `layer3.source_intake_external_export_download_prepare.v1`, `provider_private_signed_url_prepare` now requires `signed_reference_receipt_id` and resolves it through durable `L3SignedReferenceReceipt` and `L3SignedReferenceToken` state. The token must be in `used` state with `use_count >= 1`, and the token authority snapshot must match the same session, reconciliation record, source artifact hash/size, external export/download refs, source-intake record id, candidate id, and output payload hash.

The rule deliberately rejects raw signed-reference tokens at provider-private prepare time. The only provider-private bridge from source-intake signed-reference behavior is a server durable receipt id produced by same-origin signed-reference use.

## Rendered controls

The rendered workbench provider-private prepare gate no longer blocks source-intake readiness solely by source family. It requires `State.externalExportDownloadSignedReferenceUse`, reads `x-layer3-signed-reference-receipt-id` from signed-reference use, and sends `signed_reference_receipt_id` in the provider-private prepare payload.

## Preserved exclusions

- Provider public URL behavior remains blocked.
- Connector/destination dispatch remains blocked.
- Package mutation or reconstruction remains blocked.
- Source expansion, local-directory authority, web connector retrieval, and RAG/vector behavior remain blocked.
- Broad qualitative behavior and full mockup activation remain blocked.
- Route, model, migration, and auth/security behavior remain unchanged.
- Frontend-only durable authority remains blocked because provider-private prepare is revalidated against backend receipt/token authority.

## Validation posture

- targeted_validation_status: `branch_local_implemented_targeted_tests_passed`
- required_backend_tests: `python -m pytest .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_page.py`
- required_api_test: `python -m pytest .\backend\tests\test_layer3_api.py`
- required_rendered_e2e: `npx playwright test e2e/layer3-workbench.spec.js e2e/layer3-handoff.spec.js --project=chromium`
- required_progress_check: `python .\tools\l3-progress-check.py`

## Next boundary

After this branch is reviewed, tested, merged, and current-main synchronized, the next action should be a docs/control sync that records the PR merge proof and freezes the next downstream source-intake boundary. That next boundary must be selected from current-main evidence, not inferred from this branch-local implementation alone.
