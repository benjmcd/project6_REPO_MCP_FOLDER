# Layer 3 Synthesis Authority Boundary

Status: docs/proof guardrail after local multi-audit synthesis.

This file is intentionally scoped. It is not an exhaustive Layer 3 index, not a manifest refresh, and not an implementation freeze. It records the authority boundary future agents must apply before using mockups, Codesight output, progress prose, or stale audit conclusions as implementation truth.

## Current Authority Snapshot

- Local branch head when this note was written: `86d420643152fc8c5b99be0f5dce4ebdbb6d5ee9`.
- Live source and tests outrank this document.
- `C:\Users\benny\Downloads\synthesis.txt` accepted that Layer 3 is real and bounded, but rejected treating mockups, Codesight summaries, progress manifests, or rendered UI presence as complete runtime proof.
- Authentication/security work remains deferred by explicit operator instruction; this note does not reopen that lane.

## Live-Boundary Evidence

- `backend/app/services/layer3_workbench.py` admits only `dataset_version` and `aps_content_document` as Layer 3 source classes.
- The same workbench lists `rag_vector_index`, `arbitrary_local_directory`, `broad_file_upload`, `web_connector`, and `unbounded_runtime_db` as unsupported source classes.
- `backend/app/services/layer3_workbench.py` reports `qualitative_execution`, `hybrid_execution`, and `rag_vector_retrieval` feature flags as `False`.
- `backend/app/services/layer3_state_action_contract.py` keeps `qualitative_execution`, `hybrid_execution`, `rag_vector_retrieval`, `provider_public_url`, `connector_destination_dispatch`, `package_mutation_reconstruction`, `frontend_only_durable_state`, `hidden_llm_planning`, and `auth_security_hardening` in `STATE_ACTION_DEFERRED_CAPABILITIES` with `admitted: False`.
- `backend/tests/test_layer3_workbench.py` and `backend/tests/test_layer3_api.py` assert key deferred capabilities remain unadmitted and do not become action ids.
- `backend/tests/test_layer3_page.py` proves frontend session recovery markers exist, including server revalidation and Gate B draft restoration markers. That is not proof of full mockup activation.

## Mockup Boundary

The mockup files under `next_milestone_plans/layer3-mockups/` are target-state design/specification artifacts. They may guide later freeze writing, but they do not admit:

- broad execution;
- qualitative or hybrid execution;
- RAG/vector/semantic retrieval;
- broad local upload or directory source expansion;
- provider/public URL support;
- connector/destination dispatch;
- package mutation or reconstruction;
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
- Scope limit: this is delivery-path fail-closed proof only. It does not implement artifact cleanup, artifact reconstruction, provider/public URLs, connector dispatch, package mutation/reconstruction, signed-reference concurrency/revocation, source widening, or full mockup activation.
- `backend/tests/test_layer3_model_exports.py` is the scoped live proof for the synthesis `CL11` model-discoverability gap. The `L3*` SQLAlchemy models are re-exported from `app.models`; this is import-surface cleanup only and does not change model definitions, schema, migrations, persistence behavior, routes, or runtime state.

## Supported Next-Action Boundary

The synthesis-supported direction after the already-landed proof/state/refactor slices is:

- continue narrow state/proof/refactor hardening;
- correct stale labels that could cause future overclaims;
- preserve fail-closed deferred capability markers;
- defer broad feature activation until a separate freeze and proof plan admit exactly one lane.

This note blocks broad activation from mockup, progress, or Codesight evidence alone.
