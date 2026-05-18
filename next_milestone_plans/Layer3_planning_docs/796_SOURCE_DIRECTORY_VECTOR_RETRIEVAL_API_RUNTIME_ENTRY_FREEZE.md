# 796 - Source Directory Vector Retrieval API Runtime Entry Freeze

## Status

Status: branch-local implementation-entry freeze and runtime proof for `source_directory_material_vector_retrieval_api_runtime_entry`.

Runtime doc: `796_SOURCE_DIRECTORY_VECTOR_RETRIEVAL_API_RUNTIME_ENTRY_FREEZE.md`.

Runtime branch: `codex/l3-source-ingest-family`.

Current-main preflight checkpoint: `8da8cc2ee419512b494d1f8ebafa528ac4e9c23c`.

Predecessor current-main sync doc: `795_PROVIDER_PUBLIC_DELIVERY_USE_FAKE_PROVIDER_RUNTIME_CURRENT_MAIN_SYNC.md`.

Predecessor synced result: `current_main_synced_provider_public_delivery_use_fake_provider_redacted_runtime_implementation`.

Selected from posture: `select_source_expansion_ingestion_named_source_family_after_provider_public_delivery_use_runtime_sync`.

Source-family adoption result: current main already has `current_main_synced_source_directory_material_deterministic_vector_retrieval_runtime` over `server_configured_operator_directory_text_table_source_family`.

Selected implementation action: `implement_source_directory_material_vector_retrieval_api_after_existing_source_family_and_vector_retrieval_runtime_sync`.

Runtime result: `source_directory_material_vector_retrieval_api_runtime_implemented_branch_local`.

Runtime behavior introduced by this pass: `true`.

## Canonical Source Of Truth

The current live authority files for this implementation-entry freeze and runtime proof are:

- `742_SOURCE_EXPANSION_INGESTION_SOURCE_FAMILY_SELECTION_FREEZE.md`;
- `743_SOURCE_EXPANSION_INGESTION_SOURCE_FAMILY_SELECTION_FREEZE_CURRENT_MAIN_SYNC.md`;
- `788_SOURCE_DIRECTORY_MATERIAL_DETERMINISTIC_VECTOR_RETRIEVAL_RUNTIME_PROOF.md`;
- `789_SOURCE_DIRECTORY_MATERIAL_DETERMINISTIC_VECTOR_RETRIEVAL_RUNTIME_CURRENT_MAIN_SYNC.md`;
- `795_PROVIDER_PUBLIC_DELIVERY_USE_FAKE_PROVIDER_RUNTIME_CURRENT_MAIN_SYNC.md`;
- `backend/app/services/layer3_source_directory_ingestion.py`;
- `backend/app/services/layer3_source_directory_material_admission.py`;
- `backend/app/services/layer3_source_directory_text_index.py`;
- `backend/app/services/layer3_source_directory_vector_index.py`;
- `backend/app/services/layer3_source_directory_vector_retrieval.py`;
- `backend/app/api/layer3.py`; and
- `backend/tests/test_layer3_source_directory_vector_retrieval.py`.

The selected source family remains the already-synced server-configured local operator directory source family containing direct child `.csv`, `.json`, `.txt`, and `.md` files only.

The selected retrieval authority remains `source_directory_material_deterministic_vector_retrieval_authority`.

## Frozen Runtime Surface

This pass admits only a backend API wrapper over the existing deterministic local vector retrieval service.

The implemented API route is:

- `POST /api/v1/layer3/source/ingestion/server-configured-directory/vector-retrieval`.

The implemented response schema is:

- `layer3.source_directory_vector_retrieval.v1`.

The implemented API owner is:

- `backend/app/api/layer3.py`.

The implemented proof owner is:

- `backend/tests/test_layer3_source_directory_vector_retrieval.py`.

The API request requires current source-directory material and index authority fields:

- `client_request_id`;
- `material_snapshot_id`;
- `source_ingestion_batch_id`;
- `source_ingestion_file_id`;
- `content_sha256`;
- `file_identity_hash`;
- `authority_basis_hash`;
- `payload_hash`;
- `index_authority_hash`;
- `embedding_index_authority_hash`;
- `query_text`; and
- optional `top_k`.

## Runtime Behavior

The route calls `source_directory_material_vector_retrieval(db, payload)` and returns deterministic local vector retrieval results for already-admitted source-directory material.

The route returns ranked segment metadata and retrieval authority hashes. It does not return raw local paths, raw vectors, normalized feature maps, prompt payloads, provider payloads, package payloads, connector payloads, source file bytes, or frontend state.

The route preserves the existing fail-closed source-directory authority path:

- stale embedding index authority returns blocked response state;
- stale text/vector index authority remains blocked by the service path;
- live source-file drift remains blocked by the text-index authority path;
- unsupported/extra API request fields fail closed before service execution; and
- no downstream package, connector, analysis-run, pass-run, retrieval-row, vector-store, or frontend durable rows are created.

## Non-Admission Boundary

This implementation-entry freeze and runtime proof admits no new source family, arbitrary source ingestion, arbitrary recursive ingestion, PDFs, OCR, Office documents, arbitrary binaries, archives, web connectors, caller-supplied paths, caller-supplied URLs, browser-supplied file bytes, local upload expansion, durable vector-store row write, durable embedding row write, durable retrieval row write, vector database, persistent vector store, RAG execution, context-packet mutation, qualitative generation runtime, prompt/model/provider runtime, provider-public delivery/use broadening, provider-private signed URL generation/use, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, auth/security broadening, rendered controls, full mockup activation, frontend-durable authority, raw local path exposure, or source `L3OutputPackage` mutation.

## Proof Coverage

Focused proof command:

`python -m pytest .\backend\tests\test_layer3_source_directory_vector_retrieval.py -q`

Branch-local result: `5 passed`.

The focused proof covers:

- deterministic vector retrieval service behavior;
- API route response schema `layer3.source_directory_vector_retrieval.v1`;
- API route status `available`;
- API route deterministic ranked items;
- stale embedding authority fail-closed response;
- forbidden prompt/provider API fields rejected;
- no raw local path in API response;
- no raw vector or normalized features in retrieval items;
- no durable retrieval rows, vector-store rows, package rows, connector rows, pass-run rows, analysis-run rows, or frontend durable rows; and
- negative invariants for persistent vector store, RAG execution, prompt/model/provider runtime, and network egress remain false.

## Next Posture

The next exact posture after merge is `await_current_main_sync_for_source_directory_material_vector_retrieval_api_runtime`.

After current-main sync, do not continue additional same-family vector retrieval API proof loops unless current-main evidence shows a concrete unresolved defect or named downstream reader.

The next major implementation-bearing lane should be `select_source_directory_qualitative_hybrid_analysis_api_surface_after_vector_retrieval_api_sync`, because current main already has service-level qualitative-hybrid analysis but no backend API surface for that analysis runtime.
