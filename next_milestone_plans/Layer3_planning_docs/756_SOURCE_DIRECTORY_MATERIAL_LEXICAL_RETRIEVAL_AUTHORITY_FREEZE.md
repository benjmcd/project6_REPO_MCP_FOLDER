# 756 - Source Directory Material Lexical Retrieval Authority Freeze

## Status

Status: branch-local retrieval authority selection freeze for `source_directory_material_lexical_retrieval_authority`.

Doc: `756_SOURCE_DIRECTORY_MATERIAL_LEXICAL_RETRIEVAL_AUTHORITY_FREEZE.md`.

Planning branch: `codex/l3-retrieval-selection`.

Current-main checkpoint before freeze: `3cbf4dda3640e58210f93b4ff6aa81bf84dede5d`.

Predecessor current-main sync doc: `755_SOURCE_DIRECTORY_MATERIAL_DETERMINISTIC_TEXT_INDEX_RUNTIME_CURRENT_MAIN_SYNC.md`.

Predecessor synced result: `current_main_synced_source_directory_material_deterministic_text_index_runtime`.

Selected next posture from predecessor: `select_next_retrieval_or_qualitative_hybrid_authority_after_text_index_runtime_sync`.

Selected exact next authority question: `source_directory_material_lexical_retrieval_authority_contract`.

Runtime behavior introduced by this freeze: `false`.

## Repo-Confirmed Authority

Current main proves bounded source-directory source/index authority through:

- `backend/app/services/layer3_source_directory_text_index.py`;
- canonical upstream authorities `L3SourceDirectoryIngestionBatch`, `L3SourceDirectoryIngestionFile`, and `L3MaterialSnapshot`;
- source shape `server_configured_directory_file`;
- deterministic `deterministic_text_segments`;
- segmentation version `line-window-v1`;
- replay-stable `index_authority_hash`; and
- focused tests in `backend/tests/test_layer3_source_directory_ingestion.py`.

Current main also proves retrieval and qualitative-hybrid runtime remain unadmitted:

- `backend/app/services/layer3_source_directory_text_index.py` reports `retrieval_query_enabled: False`, `vector_index_enabled: False`, `embedding_generation_enabled: False`, and `qualitative_hybrid_runtime_enabled: False`;
- `backend/app/services/layer3_source_boundary.py` reports `rag_vector_enabled: False`;
- `backend/app/services/layer3_source_directory_material_admission.py` reports `eligible_for_rag_vector_index: False`; and
- `backend/app/services/layer3_qual_aps_execution.py` reports `hybrid_execution_enabled: False` and `rag_vector_retrieval_enabled: False`.

The repo's current APS retrieval plane gives an implementation precedent for deterministic lexical retrieval over materialized authority rows: `backend/app/services/aps_retrieval_plane_contract.py`, `backend/app/services/aps_retrieval_plane.py`, and `backend/app/services/aps_retrieval_plane_read.py` use canonical identity, source signatures, token normalization, lexical matching, stable ranking, and fail-closed materialization checks. That APS plane remains APS-specific authority over `ApsRetrievalChunk`; it is not source-directory retrieval authority and is not generalized by this freeze.

## Frozen Selection

This freeze selects `source_directory_material_lexical_retrieval_authority_contract` as the next exact planning/control artifact.

That contract must choose the first retrieval authority over the already-synced source-directory deterministic text index before any qualitative-hybrid analysis runtime. The selected first retrieval mode is `deterministic_lexical_segment_retrieval` over `deterministic_text_segments`, not vector retrieval.

The selected future retrieval authority is `source_directory_material_deterministic_lexical_retrieval_authority`.

The selected future owner service is `backend/app/services/layer3_source_directory_text_retrieval.py`.

The contract must bind retrieval identity to the existing source/index authorities and stale-authority checks: `source_ingestion_batch_id`, `source_ingestion_file_id`, `material_snapshot_id`, `content_sha256`, `file_identity_hash`, `authority_basis_hash`, `payload_hash`, `index_authority_hash`, `index_mode`, and `segmentation_version`.

The contract may define a later bounded query request shape, but it must keep that future shape deterministic and local: query text normalization, token matching, stable score fields, stable segment tie-breakers, bounded limit/offset, redacted errors, and no prompt/model/provider behavior.

## Whole-Program Milestone Sequence

This freeze sets the next milestone ladder as:

1. Current branch: merge and current-main sync this `source_directory_material_lexical_retrieval_authority` selection freeze.
2. Next branch: write `source_directory_material_lexical_retrieval_authority_contract` with exact input, output, ranking, stale-authority, error, and negative-invariant terms.
3. Next sync: prove that retrieval contract is review-cleared and current-main synced.
4. Next implementation: implement the deterministic lexical segment retrieval service only if the synced contract admits it.
5. Next sync: prove the lexical retrieval runtime is current-main synced and still writes no vector/source-index rows unless separately admitted.
6. Next selection: choose the first qualitative-hybrid analysis authority that consumes retrieval results, or stop if no named analysis use case is admitted.
7. Later lanes, each requiring its own freeze, contract, implementation/proof, review clearance, and current-main sync: qualitative-hybrid output taxonomy, package construction/review/commit for new outputs, package mutation/reconstruction if needed, handoff/export/delivery, operator-visible status/review surfaces, provider-public exposure, real connector dispatch, retrieval/indexing expansion, and production auth/security tied to the first external/public/credentialed surface.

## Still Blocked

This freeze admits no runtime behavior, backend route behavior, service behavior, model change, migration, rendered UI control, source-index rows, vector index, embedding generation, retrieval query runtime, qualitative-hybrid analysis runtime, qualitative broadening, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, full mockup activation, frontend-durable authority, hidden LLM planning, arbitrary source ingestion, arbitrary recursive ingestion, broad local upload, PDFs, OCR, Office documents, arbitrary binaries, web connectors, caller-supplied paths/URLs/globs, browser-supplied file bytes, browser/operator path editing, raw local path exposure, prompt/model/provider runtime, or source `L3OutputPackage` mutation.

## Next Posture

The next exact posture after merge is `current_main_sync_source_directory_material_lexical_retrieval_authority_freeze`.

After that sync, the next exact posture is `write_source_directory_material_lexical_retrieval_authority_contract_before_qualitative_hybrid_runtime`.
