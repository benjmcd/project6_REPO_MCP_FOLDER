# 798 - Source Directory Qualitative-Hybrid Analysis API Runtime Entry Freeze

## Status

Status: branch-local implementation-entry freeze and runtime proof for `source_directory_material_context_packet_qualitative_hybrid_analysis_api_runtime_entry`.

Runtime doc: `798_SOURCE_DIRECTORY_QUALITATIVE_HYBRID_ANALYSIS_API_RUNTIME_ENTRY_FREEZE.md`.

Runtime branch: `codex/l3-qual-api`.

Current-main preflight checkpoint: `f08391c10823329714e6e57fe01bc25f5f066e87`.

Predecessor current-main sync doc: `797_SOURCE_DIRECTORY_VECTOR_RETRIEVAL_API_RUNTIME_CURRENT_MAIN_SYNC.md`.

Predecessor synced result: `current_main_synced_source_directory_material_vector_retrieval_api_runtime`.

Selected from posture: `select_source_directory_qualitative_hybrid_analysis_api_surface_after_vector_retrieval_api_sync`.

Source-analysis adoption result: current main already has `current_main_synced_source_directory_material_context_packet_qualitative_hybrid_analysis_runtime` over `source_directory_material_retrieval_augmented_context_packet_authority`.

Selected implementation action: `implement_source_directory_material_context_packet_qualitative_hybrid_analysis_api_after_existing_service_runtime_sync`.

Runtime result: `source_directory_material_context_packet_qualitative_hybrid_analysis_api_runtime_implemented_branch_local`.

Runtime behavior introduced by this pass: `true`.

## Canonical Source Of Truth

The current live authority files for this implementation-entry freeze and runtime proof are:

- `772_SOURCE_DIRECTORY_MATERIAL_CONTEXT_PACKET_QUALITATIVE_HYBRID_ANALYSIS_RUNTIME_PROOF.md`;
- `773_SOURCE_DIRECTORY_MATERIAL_CONTEXT_PACKET_QUALITATIVE_HYBRID_ANALYSIS_RUNTIME_CURRENT_MAIN_SYNC.md`;
- `797_SOURCE_DIRECTORY_VECTOR_RETRIEVAL_API_RUNTIME_CURRENT_MAIN_SYNC.md`;
- `backend/app/services/layer3_source_directory_context_packet.py`;
- `backend/app/services/layer3_source_directory_qualitative_analysis.py`;
- `backend/app/api/layer3.py`; and
- `backend/tests/test_layer3_source_directory_qualitative_analysis.py`.

The selected source family remains `server_configured_operator_directory_text_table_source_family`.

The selected qualitative-hybrid authority remains `source_directory_material_context_packet_qualitative_hybrid_analysis_authority`.

The selected context-packet authority remains `source_directory_material_retrieval_augmented_context_packet_authority`.

## Frozen Runtime Surface

This pass admits only a backend API wrapper over the existing deterministic extractive source-directory qualitative-hybrid analysis service.

The implemented API route is:

- `POST /api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis`.

The implemented response schema is:

- `layer3.source_directory_qualitative_analysis.v1`.

The implemented API owner is:

- `backend/app/api/layer3.py`.

The implemented proof owner is:

- `backend/tests/test_layer3_source_directory_qualitative_analysis.py`.

The API request requires current source-directory material, text-index, retrieval, and context-packet authority fields:

- `client_request_id`;
- `analysis_question`;
- `analysis_focus`;
- `material_snapshot_id`;
- `source_ingestion_batch_id`;
- `source_ingestion_file_id`;
- `content_sha256`;
- `file_identity_hash`;
- `authority_basis_hash`;
- `payload_hash`;
- `index_authority_hash`;
- `query_text`;
- optional `limit`; and
- optional `offset`.

## Runtime Behavior

The route calls `source_directory_material_context_packet_qualitative_hybrid_analysis(db, payload)` and returns deterministic extractive qualitative-hybrid analysis over already-admitted source-directory material and context-packet authority.

The route returns the deterministic qualitative analysis hash, context-packet hash, source/material/index authority hashes, query tokens, bounded evidence summary, salient terms, supporting segment references, coverage notes, and analysis limits. It does not return raw local paths, full segment text, raw vectors, embeddings, prompt payloads, provider payloads, package payloads, connector payloads, source file bytes, or frontend state.

The route preserves the existing fail-closed authority path:

- stale index authority returns blocked response state through the context-packet retrieval path;
- stale source-file authority remains blocked by the text-index path;
- context-packet authority mismatches remain blocked by the qualitative-analysis service;
- unsupported or extra API request fields fail closed before service execution; and
- no downstream package, connector, analysis-run, pass-run, retrieval-row, context-packet row, qualitative-analysis row, vector-store row, or frontend durable rows are created.

## Non-Admission Boundary

This implementation-entry freeze and runtime proof admits no new source family, arbitrary source ingestion, arbitrary recursive ingestion, PDFs, OCR, Office documents, arbitrary binaries, archives, web connectors, caller-supplied paths, caller-supplied URLs, browser-supplied file bytes, local upload expansion, durable context-packet row write, durable qualitative-analysis row write, durable qualitative-generation row write, durable retrieval row write, durable vector-store row write, durable embedding row write, vector database, persistent vector store, new RAG execution, vector indexing, embedding generation, prompt/model/provider runtime, provider-public delivery/use broadening, provider-private signed URL generation/use, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, auth/security broadening, rendered controls, full mockup activation, frontend-durable authority, raw local path exposure, or source `L3OutputPackage` mutation.

## Proof Coverage

Focused proof command:

`python -m pytest .\backend\tests\test_layer3_source_directory_qualitative_analysis.py -q`

Branch-local result: `5 passed`.

The focused proof covers:

- deterministic qualitative-hybrid analysis service behavior;
- API route response schema `layer3.source_directory_qualitative_analysis.v1`;
- API route status `available`;
- API route deterministic context-packet grounded evidence sections;
- stale index authority fail-closed response;
- forbidden prompt/provider API fields rejected;
- no raw local path in API response;
- no full segment text in supporting segment response;
- no durable retrieval rows, context-packet rows, qualitative-analysis rows, qualitative-generation rows, vector-store rows, package rows, connector rows, pass-run rows, analysis-run rows, or frontend durable rows; and
- negative invariants for vector indexing, embedding generation, qualitative generation, prompt/model/provider runtime, connector dispatch, provider-public delivery, and network egress remain false.

## Next Posture

The next exact posture after merge is `await_current_main_sync_for_source_directory_material_context_packet_qualitative_hybrid_analysis_api_runtime`.

After current-main sync, do not continue additional same-family qualitative-hybrid API proof loops unless current-main evidence shows a concrete unresolved defect or named downstream reader.

The next major implementation-bearing lane should be selected from the remaining Layer 3 end-to-end gaps: package lifecycle/mutation/reconstruction, controlled handoff/export/delivery readers that are not yet synced, operator-visible review/status surfaces, provider-public real exposure only after exposure/security/revocation authority, real connector dispatch only after target/credential/network/receipt/auth authority, or retrieval/indexing expansion only after a new source/index authority is selected.
