# 772 - Source Directory Material Context-Packet Qualitative-Hybrid Analysis Runtime Proof

## Status

Status: branch-local runtime proof for `source_directory_material_context_packet_qualitative_hybrid_analysis_runtime_proof`.

Runtime proof doc: `772_SOURCE_DIRECTORY_MATERIAL_CONTEXT_PACKET_QUALITATIVE_HYBRID_ANALYSIS_RUNTIME_PROOF.md`.

Runtime branch: `codex/l3-qual-analysis-runtime`.

Current-main checkpoint before implementation: `047b8c7b0cc1f33399956ae150bc09e37f78868d`.

Predecessor current-main sync doc: `771_SOURCE_DIRECTORY_MATERIAL_CONTEXT_PACKET_QUALITATIVE_HYBRID_ANALYSIS_CONTRACT_CURRENT_MAIN_SYNC.md`.

Predecessor synced result: `current_main_synced_source_directory_material_context_packet_qualitative_hybrid_analysis_contract`.

Selected implementation action: `implement_source_directory_material_context_packet_qualitative_hybrid_analysis_after_contract_sync`.

Runtime status after implementation: `source_directory_material_context_packet_qualitative_hybrid_analysis_runtime_implemented_branch_local`.

Runtime behavior introduced by this pass: `true`.

## Implemented Surface

The implementation adds `backend/app/services/layer3_source_directory_qualitative_analysis.py`.

The proof adds `backend/tests/test_layer3_source_directory_qualitative_analysis.py`.

No backend route, API DTO, response model, database model, migration, durable qualitative analysis row, durable context-packet row, source-index durable row, retrieval durable row, vector index, embedding generation, prompt/model/provider runtime, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, rendered control, full mockup activation, frontend-durable authority, source expansion, arbitrary source ingestion, raw local path exposure, or source `L3OutputPackage` mutation is added.

## Runtime Behavior

The new service function is `source_directory_material_context_packet_qualitative_hybrid_analysis(db, payload)`.

The service first validates the exact qualitative-analysis request field set, then calls `source_directory_material_retrieval_augmented_context_packet(db, payload)` before assembling any qualitative-analysis response.

The service validates the returned `context_packet_contract_id` as `source_directory_material_retrieval_augmented_context_packet_authority`, the returned `context_packet_mode` as `retrieval_augmented_qualitative_context_packet`, and the returned `schema_id` as `layer3.source_directory_context_packet.v1`.

The response schema is `layer3.source_directory_qualitative_analysis.v1`, with `analysis_contract_id: source_directory_material_context_packet_qualitative_hybrid_analysis_authority`, `analysis_mode: context_packet_grounded_qualitative_hybrid_analysis`, deterministic `qualitative_analysis_hash`, the source context-packet hash, stable query tokens, source/material/index/context authority IDs and hashes, bounded `limit` and `offset`, and deterministic extractive sections.

The deterministic extractive sections are `evidence_summary`, `salient_terms`, `supporting_segments`, `coverage_notes`, and `analysis_limits`.

The `supporting_segments` response exposes only segment ID, rank position, segment sequence, line range, segment hash, bounded quote excerpt copied from `text_excerpt`, matched unique query term count, summed term frequency, and deterministic support label.

The service returns `context_packet_rows_written: False`, `qualitative_analysis_rows_written: False`, `qualitative_generation_rows_written: False`, `analysis_run_rows_written: False`, `package_rows_written: False`, and `connector_rows_written: False`.

No-match results return `total: 0`, `supporting_segments: []`, coverage label `no_context_matches`, and explicit `analysis_limits` without falling back to vector, embedding, prompt/model/provider, source expansion, connector, package, or qualitative generation behavior.

## Proof Coverage

Focused test `backend/tests/test_layer3_source_directory_qualitative_analysis.py` proves:

- successful deterministic qualitative-hybrid analysis over an admitted context packet;
- deterministic replay of `qualitative_analysis_hash`;
- returned context-packet authority validation;
- stale `index_authority_hash` rejection through the context-packet and retrieval path;
- stale source/material authority rejection through the text-index path;
- empty or whitespace-only `analysis_question` rejection;
- empty query rejection through context-packet authority;
- forbidden prompt/model/provider/vector/package/connector/path/runtime-db-write field rejection;
- unknown field rejection;
- bounded `limit` and `offset` propagation into context-packet authority;
- no-match response preservation with explicit `analysis_limits`; and
- no `L3PassRun`, `AnalysisRun`, `L3OutputPackage`, `ConnectorRun`, or `ConnectorRunTarget` side effects.

Validation:

- `python -m py_compile .\backend\app\services\layer3_source_directory_qualitative_analysis.py .\backend\tests\test_layer3_source_directory_qualitative_analysis.py` PASS;
- `python -m pytest .\backend\tests\test_layer3_source_directory_qualitative_analysis.py -q` PASS, `4 passed`; and
- branch-local planning/progress/checker validation must pass before PR.

## Still Blocked

Backend route behavior, API DTOs, response models, database models, migrations, durable qualitative analysis rows, durable context-packet rows, source-index durable rows, retrieval durable rows, vector indexing, embedding generation, qualitative generation runtime, prompt/model/provider runtime, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, rendered controls, full mockup activation, frontend-durable authority, hidden LLM planning, arbitrary source ingestion, arbitrary recursive ingestion, broad local upload, PDFs, OCR, Office documents, arbitrary binaries, web connectors, caller-supplied paths/URLs/globs, browser-supplied file bytes, browser/operator path editing, raw local path exposure, and source `L3OutputPackage` mutation remain blocked.

## Next Posture

The next exact posture after merge is `await_current_main_sync_for_source_directory_material_context_packet_qualitative_hybrid_analysis_runtime_proof`.

After that sync, pivot to `select_next_major_layer3_deferred_lane_after_source_directory_qualitative_analysis_runtime_sync` only if current-main evidence confirms this runtime is cleanly synced and no concrete same-family qualitative-analysis defect remains.
