# 766 - Source Directory Material Retrieval-Augmented Context Packet Runtime Proof

## Status

Status: branch-local runtime proof for `source_directory_material_retrieval_augmented_context_packet_runtime_proof`.

Runtime proof doc: `766_SOURCE_DIRECTORY_MATERIAL_RETRIEVAL_AUGMENTED_CONTEXT_PACKET_RUNTIME_PROOF.md`.

Runtime branch: `codex/l3-rag-qual-impl`.

Current-main checkpoint before implementation: `58634b9aab1bacffb06c8f5b86009050a3cea7c3`.

Predecessor current-main sync doc: `765_SOURCE_DIRECTORY_MATERIAL_QUALITATIVE_HYBRID_CONTEXT_PACKET_AUTHORITY_CONTRACT_CURRENT_MAIN_SYNC.md`.

Predecessor synced result: `current_main_synced_source_directory_material_qualitative_hybrid_context_packet_authority_contract`.

Selected implementation action: `implement_source_directory_material_retrieval_augmented_context_packet_authority_after_contract_sync`.

Runtime status after implementation: `source_directory_material_retrieval_augmented_context_packet_runtime_implemented_branch_local`.

Runtime behavior introduced by this pass: `true`.

## Implemented Surface

The implementation adds `backend/app/services/layer3_source_directory_context_packet.py`.

The proof adds `backend/tests/test_layer3_source_directory_context_packet.py`.

No backend route, API DTO, response model, database model, migration, durable context-packet row, source-index durable row, retrieval durable row, vector index, embedding generation, qualitative generation runtime, prompt/model/provider runtime, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, rendered control, full mockup activation, frontend-durable authority, source expansion, arbitrary source ingestion, raw local path exposure, or source `L3OutputPackage` mutation is added.

## Runtime Behavior

The new service function is `source_directory_material_retrieval_augmented_context_packet(db, payload)`.

The service first validates the exact context-packet request field set, then calls `source_directory_material_text_retrieval(db, payload)` before assembling any context-packet response.

The service validates the returned `retrieval_contract_id` as `source_directory_material_deterministic_lexical_retrieval_authority` and the returned `retrieval_mode` as `deterministic_lexical_segment_retrieval`.

The response schema is `layer3.source_directory_context_packet.v1`, with `context_packet_contract_id: source_directory_material_retrieval_augmented_context_packet_authority`, `context_packet_mode: retrieval_augmented_qualitative_context_packet`, deterministic `context_packet_hash`, stable query tokens, source/material/index/retrieval authority IDs and hashes, bounded `limit` and `offset`, and response-safe context packet items.

The context packet items expose only rank position, segment ID, segment sequence, line range, char range, segment hash, bounded `text_excerpt`, matched unique query term count, and summed term frequency.

The service returns `source_index_rows_written: False`, `retrieval_rows_written: False`, `context_packet_rows_written: False`, `qualitative_generation_rows_written: False`, `analysis_run_rows_written: False`, and `package_rows_written: False`.

No-match results return `total: 0` and `items: []` without falling back to vector, embedding, prompt/model/provider, source expansion, connector, package, or qualitative generation behavior.

## Proof Coverage

Focused test `backend/tests/test_layer3_source_directory_context_packet.py` proves:

- successful context packet construction over deterministic lexical retrieval output;
- deterministic replay of `context_packet_hash`;
- stale `index_authority_hash` rejection through the retrieval path;
- stale source/material authority rejection through the text-index path;
- empty-query rejection through the retrieval path;
- forbidden prompt/vector/runtime-db-write field rejection;
- unknown field rejection;
- bounded `limit` and `offset` behavior with deterministic rank positions;
- no-match response preservation; and
- no `L3PassRun`, `AnalysisRun`, `L3OutputPackage`, `ConnectorRun`, or `ConnectorRunTarget` side effects.

Validation:

- `python -m py_compile .\backend\app\services\layer3_source_directory_context_packet.py .\backend\tests\test_layer3_source_directory_context_packet.py` PASS;
- `python -m pytest .\backend\tests\test_layer3_source_directory_context_packet.py -q` PASS, `4 passed`; and
- branch-local planning/progress/checker validation must pass before PR.

## Still Blocked

Backend route behavior, API DTOs, response models, database models, migrations, source-index durable rows, retrieval durable rows, durable context-packet rows, vector indexing, embedding generation, qualitative generation runtime, prompt/model/provider runtime, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, rendered controls, full mockup activation, frontend-durable authority, hidden LLM planning, arbitrary source ingestion, arbitrary recursive ingestion, broad local upload, PDFs, OCR, Office documents, arbitrary binaries, web connectors, caller-supplied paths/URLs/globs, browser-supplied file bytes, browser/operator path editing, raw local path exposure, and source `L3OutputPackage` mutation remain blocked.

## Next Posture

The next exact posture after merge is `await_current_main_sync_for_source_directory_material_retrieval_augmented_context_packet_runtime_proof`.

After that sync, pivot to `select_next_qualitative_hybrid_analysis_authority_after_context_packet_runtime_sync` only if current-main evidence confirms this runtime is cleanly synced and no concrete same-family context-packet defect remains.
