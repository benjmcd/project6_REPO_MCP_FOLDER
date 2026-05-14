# 326 - Source Intake External Export Download Rendered Controls Boundary Freeze

Status: planning/control freeze for `source_intake_external_export_download_rendered_controls_boundary`.

Branch: `codex/l3-source-intake-delivery-controls-freeze`
Current-main predecessor commit: `ac3a776d6ce7cdfdac7a0d4ac82d9959951a3350`
Predecessor implementation: `325_SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_BOUNDARY.md`
Owner UI absence surface: `backend/app/review_ui/static/claude.html`
Future implementation owner UI: `backend/app/review_ui/static/layer3.js`
Future implementation rendered shell: `backend/app/review_ui/static/layer3.html`
Owner service: `backend/app/services/layer3_workbench.py`
Historical rendered freeze boundary: before doc 327, source-intake external export/download delivery controls were not rendered; current-main live rendered behavior is governed by the later implementation proof.

## Canonical source of truth

The canonical source of truth for any future rendered source-intake delivery controls is the server-owned delivery capability admitted by `external_export_download_deliver` after doc 325, backed by source-intake prepare/readiness state and the APS evidence-bundle handoff package. The delivery schema is `layer3.source_intake_external_export_download_delivery.v1`, and the required prepare/readiness schema is `layer3.source_intake_external_export_download_prepare.v1`.

Rendered controls must project server-owned readiness and delivery authority only. The browser must not invent delivery eligibility, local path authority, provider/public URL authority, signed-reference authority, connector/destination state, package mutation state, source-expansion state, or RAG/vector state.

## Frozen next code-bearing action

The next code-bearing action is `implement_source_intake_external_export_download_rendered_controls_boundary` only.

That implementation may add source-intake rendered controls only if they use the already-admitted server-side delivery path and preserve these boundaries:

- no source-intake delivery control is enabled without server readiness and delivery authority
- no provider/public/signed URL controls are introduced
- no connector or destination dispatch controls are introduced
- no local file or local directory authority is introduced
- no package mutation or reconstruction control is introduced
- no RAG/vector or broad qualitative control is introduced
- no route/model/migration/auth/security behavior is changed

## Required future proofs

- `source_intake_delivery_controls_project_server_authority_only`
- `source_intake_delivery_control_uses_existing_same_origin_delivery_path`
- `source_intake_delivery_control_requires_external_export_download_prepared_state`
- `source_intake_delivery_control_preserves_source_intake_identity`
- `provider_public_private_url_controls_remain_blocked`
- `signed_reference_controls_remain_blocked`
- `connector_destination_controls_remain_blocked`
- `package_mutation_controls_remain_blocked`
- `source_expansion_controls_remain_blocked`
- `rag_vector_controls_remain_blocked`
- `existing_associated_cohort_single_aps_qualitative_aps_and_source_intake_delivery_unchanged`

## Explicit non-goals

- provider public/private URL behavior
- signed-reference generation or use
- connector dispatch or destination selection
- package mutation, copying, reconstruction, amendment, or supersession
- source expansion, generic upload, local file selection, or local directory ingestion
- source adapter registry expansion
- RAG/vector retrieval or hybrid qualitative analysis
- backend route changes
- model or migration changes
- auth/security behavior changes
- broad qualitative execution
- full mockup activation

## Stop condition for this freeze

This freeze is complete when the planning doc, progress board, progress manifest, proof manifest, and checker all agree that rendered source-intake external export/download delivery controls are selected as the next exact boundary and that this branch admits no rendered UI or runtime behavior.
