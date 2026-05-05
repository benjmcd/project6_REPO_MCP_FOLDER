# Layer 3 Synthesis Authority Boundary

Status: docs/proof guardrail after local multi-audit synthesis.

This file is intentionally scoped. It is not an exhaustive Layer 3 index, not a manifest refresh, and not an implementation freeze. It records the authority boundary future agents must apply before using mockups, Codesight output, progress prose, or stale audit conclusions as implementation truth.

## Current Authority Snapshot

- Local branch head when this note was first written: `86d420643152fc8c5b99be0f5dce4ebdbb6d5ee9`.
- Live source and tests outrank this document.
- `C:\Users\benny\Downloads\synthesis.txt` accepted that Layer 3 is real and bounded, but rejected treating mockups, Codesight summaries, progress manifests, or rendered UI presence as complete runtime proof.
- Authentication/security work remains deferred by explicit operator instruction; this note does not reopen that lane.

## Live-Boundary Evidence

- `backend/app/services/layer3_source_boundary.py` owns `SUPPORTED_SOURCE_CLASSES == ("dataset_version", "aps_content_document")`.
- The same source-boundary service owns `UNSUPPORTED_SOURCE_CLASSES == ("rag_vector_index", "arbitrary_local_directory", "broad_file_upload", "web_connector", "unbounded_runtime_db")`.
- `123_SOURCE_EXPANSION_FREEZE.md` freezes the source boundary as `supported_source_classes_only`; it does not admit source upload, local directory ingestion, broad file upload, web connector source retrieval, RAG/vector retrieval, or unbounded runtime DB sources.
- `backend/app/services/layer3_workbench.py` consumes those source-boundary constants/helpers for bootstrap, preflight, source preview, and source/material candidate id parsing.
- `backend/app/services/layer3_workbench.py` reports `single_aps_doc_qualitative_execution` as `True`, while `broad_qualitative_execution`, `hybrid_execution`, and `rag_vector_retrieval` feature flags remain `False`.
- `backend/app/services/layer3_state_action_contract.py` records exact bounded capabilities in `STATE_ACTION_ADMITTED_CAPABILITIES`, including `single_aps_doc_qualitative_execution`, `internal_dispatch_record_only`, and `package_supersession_preview_only`, and keeps `broad_qualitative_execution`, `hybrid_execution`, `rag_vector_retrieval`, `provider_public_url`, `connector_destination_dispatch`, `package_mutation_reconstruction`, `frontend_only_durable_state`, `hidden_llm_planning`, and `auth_security_hardening` in `STATE_ACTION_DEFERRED_CAPABILITIES` with `admitted: False`.
- `backend/tests/test_layer3_workbench.py` and `backend/tests/test_layer3_api.py` assert key deferred capabilities remain unadmitted and do not become action ids.
- `backend/tests/test_layer3_page.py` proves frontend session recovery markers exist, including server revalidation and Gate B draft restoration markers. That is not proof of full mockup activation.

## Mockup Boundary

The mockup files under `next_milestone_plans/layer3-mockups/` are target-state design/specification artifacts. They may guide later freeze writing, but they do not admit:

- broad execution;
- broad qualitative or hybrid execution outside the admitted single APS-document qualitative pass;
- RAG/vector/semantic retrieval;
- broad local upload or directory source expansion;
- provider/public URL support;
- connector/destination dispatch;
- package mutation or reconstruction beyond exact read-only `package_supersession_preview_only`;
- hidden LLM planning;
- frontend-only durable state;
- full mockup activation.

Any one of those capabilities needs a later narrow freeze, live source owner, route/API contract, negative proof, and acceptance proof before implementation.

## Codesight Boundary

The `.codesight` files in this worktree are generated navigation aids. In this worktree they are local sidecars, not tracked source authority.

Do not treat Codesight route tags such as `[auth]` as proof of in-app authentication or authorization. Treat them as extracted/dependency labels only unless live source code and tests prove the boundary.

Do not treat Codesight route response summaries as exact current DTO truth. Read `backend/app/api/layer3.py`, `backend/app/services/layer3_workbench.py`, service modules, and tests before making route or schema claims.

## Post-Synthesis Proof Recheck

- `backend/tests/test_layer3_api.py::test_layer3_api_external_export_download_deliver_fails_closed_when_bundle_artifact_missing` is the scoped live proof for the synthesis `CL36` missing-artifact recheck on the same-origin external export/download delivery path.
- The proof moves the prepared APS bundle artifact inside the isolated pytest temp tree, then verifies delivery returns a structured `409` `external_export_download_delivery_source_artifact_unavailable` error.
- The proof verifies no new `AnalysisArtifact`, `AnalysisRun`, `ConnectorRun`, `L3OutputPackage`, `L3PassRun`, or `L3ReconciliationRecord` rows are created, recorded readiness state is unchanged, and no `download_url`, `public_url`, `signed_url`, or `connector_run_id` headers are emitted.
- Scope limit: this is delivery-path fail-closed proof only. It does not implement artifact cleanup, artifact reconstruction, provider/public URLs, connector dispatch, package mutation/reconstruction, source widening, or full mockup activation.
- `backend/tests/test_layer3_model_exports.py` is the scoped live proof for the synthesis `CL11` model-discoverability gap. The `L3*` SQLAlchemy models are re-exported from `app.models`; this is import-surface cleanup only and does not change model definitions, schema, migrations, persistence behavior, routes, or runtime state.
- `backend/tests/test_layer3_plan_revision_state.py` is the scoped live proof for the no-behavior-change `CL08` service-extraction follow-up around plan-revision state. `backend/app/services/layer3_plan_revision_state.py` owns the revision-control schema id, supported decisions, decision-to-terminal-state mapping, record builder, and session parser. This extraction does not admit revision recovery, approved-plan supersession, execution, result/package/handoff behavior, source widening, connector dispatch, or package mutation/reconstruction.
- `backend/tests/test_layer3_api.py::test_layer3_api_session_summary_fails_closed_on_manifest_mismatch` is the scoped live proof for a `CL10` service-boundary hardening step. The server now rejects a session whose recorded `selection_manifest_id` diverges from the server-owned manifest row. This is not a database migration, does not add the circular `L3Session.selection_manifest_id` foreign key, and does not alter the normal `commit_selection(...)` happy path.
- `backend/tests/test_layer3_api.py::test_layer3_api_json_or_error_call_sites_return_workbench_error_envelope` is the scoped live proof for the synthesis `CL19` API error-boundary recheck. It forces each `_json_or_error` route call-site to raise a `Layer3WorkbenchError` and verifies the API returns the structured `layer3.workbench_error.v1` envelope. This is route-boundary proof only; it does not claim every possible non-`Layer3WorkbenchError` exception is converted.
- `backend/tests/test_layer3_package_entry.py::test_gated_package_entry_emits_canonical_user_and_review_packages` now proves the `CL34` canonicalization boundary for package payloads: package rows hash the exact pretty-text JSON bytes persisted on disk, and those payload hashes are intentionally distinct from compact stable hashes. This is an invariant proof, not a package mutation/reconstruction feature.
- `backend/tests/test_layer3_source_boundary.py` is the scoped live proof for the no-behavior-change source-boundary extraction. `backend/app/services/layer3_source_boundary.py` owns the admitted source classes, deferred unsupported source classes, and source/material candidate id parsing. This extraction does not admit RAG/vector retrieval, broad upload, local directory ingestion, web connector sources, runtime DB widening, connector dispatch, package mutation/reconstruction, or full mockup activation.
- `backend/tests/test_layer3_signed_reference_state.py` is the scoped live proof for the synthesis `CL17`/`CL18` signed-reference lifecycle and concurrency gap. `backend/app/services/layer3_signed_reference_state.py` now consumes same-origin signed-reference tokens through an atomic conditional update, and the test proves sanitized durable generation, single-use replay rejection, revocation rejection, expiry rejection, and concurrent no-double-delivery behavior. This does not add a revocation API, provider/public URLs, connector/destination dispatch, package mutation/reconstruction, broad delivery, source widening, auth/security hardening, or full mockup activation.
- `backend/tests/test_layer3_api.py::test_layer3_api_plan_preview_rejects_extra_fields_before_service_mutation` is the scoped live proof for a narrow `CL06` plan-preview DTO boundary hardening step. `Layer3PlanPreviewRequest` rejects extra execution/package/handoff/source-widening fields before the plan-preview service can run, while preserving the existing missing-session service error path. This does not change plan materialization, execution, package, handoff, source, mockup, or auth/security behavior.
- `backend/tests/test_layer3_api.py::test_layer3_api_source_preview_rejects_extra_fields_before_service_execution` is the scoped live proof for a narrow `CL06` source-preview DTO boundary hardening step. `Layer3SourcePreviewRequest` rejects extra source-widening fields before the source-preview service can run, while preserving the admitted `dataset_version` and `aps_content_document` source classes. This does not admit broad upload, local directory ingestion, RAG/vector sources, web connector sources, runtime DB widening, connector dispatch, package mutation/reconstruction, provider/public URLs, mockup activation, or auth/security behavior.
- `backend/tests/test_layer3_api.py::test_layer3_api_material_preview_rejects_extra_fields_before_service_execution` is the scoped live proof for a narrow `CL06` material-preview DTO boundary hardening step. `Layer3MaterialPreviewRequest` rejects extra source-widening fields before the material-preview service can run, while preserving the admitted material preview fields and nested `query_basis` authority context. This does not admit broad upload, local directory ingestion, RAG/vector sources, web connector sources, runtime DB widening, connector dispatch, package mutation/reconstruction, provider/public URLs, mockup activation, or auth/security behavior.
- `backend/tests/test_layer3_session_entry.py::test_layer3_session_entry_migration_defines_status_check_constraint` is the scoped live proof that `backend/alembic/versions/0012_layer3_session_entry.py` carries the same `ck_l3_session_status` vocabulary boundary as the model metadata. This session-status migration constraint alignment does not add a new migration, alter session lifecycle behavior, add recovery/supersession, or broaden execution, source, package, connector, mockup, or auth/security behavior.

## Supported Next-Action Boundary

The synthesis-supported direction after the already-landed proof/state/refactor slices is:

- continue narrow state/proof/refactor hardening;
- correct stale labels that could cause future overclaims;
- preserve fail-closed deferred capability markers;
- defer broad feature activation until a separate freeze and proof plan admit exactly one lane.

This note blocks broad activation from mockup, progress, or Codesight evidence alone.

## Merged-Main Verification Recheck

- Current merged-main authority after PR #535: `project6-origin/main` at `7d07477a`.
- This recheck is current-main proof for the bounded PR #535 merge. It does not claim any deferred broad capability beyond the admitted Layer 3 surfaces listed here.
- `python -m pytest $files -q`, where `$files` is the local `backend/tests/test_layer3*.py` set, passed with `264 passed, 4 warnings`.
- `python .\tools\l3-progress-check.py` passed with `Layer 3 progress state check: PASS`.
- `npx playwright test layer3-workbench.spec.js --project=chromium` passed with `12 passed`.
- `npx playwright test layer3-workbench.spec.js --project=chromium --headed` passed with `12 passed`.
- PR #535 checks passed before merge: `backend-layer3-api` and `test`.
- Post-merge `main` workflow for `7d07477a` passed both `backend-layer3-api` and `test`.
- The remaining local working-tree noise during post-merge audit was limited to out-of-scope local sidecars and `.omc/state/*`.

This recheck validates the merged current-main bounded state/action, session-status migration constraint alignment, frontend recovery, service-extraction, DTO/error-boundary including the plan-preview, source-preview, and material-preview DTO boundaries, package-hash, same-origin signed-reference service proof, single APS-document qualitative execution, and fail-closed proof posture. It does not implement or newly admit generic connector/destination dispatch, package mutation/reconstruction beyond exact read-only `package_supersession_preview_only`, broad source/upload expansion, broad qualitative/hybrid/RAG execution, provider/public URLs, full mockup activation, or authentication/security hardening. Existing bounded APS owner-service dispatch, package construction/submit, same-origin delivery, same-origin signed-reference behavior, and single APS-document qualitative execution must not be relabeled as those broader deferred categories.
