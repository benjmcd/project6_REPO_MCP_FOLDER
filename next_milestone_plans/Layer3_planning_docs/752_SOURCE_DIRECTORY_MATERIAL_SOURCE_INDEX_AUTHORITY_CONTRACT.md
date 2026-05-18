# 752 - Source Directory Material Source Index Authority Contract

## Status

Status: branch-local source/index authority contract for `source_directory_material_source_index_authority_contract`.

Doc: `752_SOURCE_DIRECTORY_MATERIAL_SOURCE_INDEX_AUTHORITY_CONTRACT.md`.

Contract branch: `codex/l3-source-index-contract`.

Current-main checkpoint before contract: `12e7c776b7dc0c6e9a85b2c8c864b6a7790a55fe`.

Predecessor current-main sync doc: `751_SOURCE_DIRECTORY_MATERIAL_SOURCE_INDEX_AUTHORITY_FREEZE_CURRENT_MAIN_SYNC.md`.

Predecessor synced result: `current_main_synced_source_directory_material_source_index_authority_freeze`.

Selected posture from predecessor: `write_source_directory_material_source_index_authority_contract_before_rag_vector_or_qualitative_hybrid_runtime`.

Selected source/index contract: `source_directory_material_deterministic_text_index_authority`.

Selected implementation entry posture after current-main sync: `implement_source_directory_material_deterministic_text_index_authority_after_contract_sync`.

Runtime behavior introduced by this contract: `false`.

## Authority Order

The future implementation must resolve authority in this order:

1. `L3SourceDirectoryIngestionBatch`.
2. `L3SourceDirectoryIngestionFile`.
3. `L3MaterialSnapshot` with `source_shape == server_configured_directory_file`.
4. Matching source-directory file identity: `source_ingestion_batch_id`, `source_ingestion_file_id`, `content_sha256`, `file_identity_hash`, and `authority_basis_hash`.
5. Matching material authority: `material_snapshot_id`, material `payload_ref`, material `payload_hash`, and source provenance for the same source-directory file.
6. Contract identity `source_directory_material_deterministic_text_index_authority`.
7. Deterministic segmentation parameters frozen by implementation.

If any earlier authority is absent, stale, malformed, mismatched, partial, already superseded, or not tied to the same source-directory file, the future implementation must fail closed before producing source/index rows or derived index output.

## Selected Source/Index Substrate

This contract selects deterministic lexical/text source-index authority as the first source/index substrate for `server_configured_directory_file` material.

Selected future owner service: `backend/app/services/layer3_source_directory_text_index.py`.

Selected future API owner: none for this contract. A route is not admitted by this contract.

Selected future durable authority owner: a later implementation may add a compact `L3SourceDirectoryMaterialTextIndex` row and migration only for deterministic, replayable source/index metadata and segment summaries. The implementation must not write vector rows, embedding rows, retrieval rows, package rows, connector rows, or provider/public delivery rows.

Selected future index mode: `deterministic_text_segments`.

Selected source class: `server_configured_directory_file`.

Selected admitted file families: only the already admitted direct-child `.csv`, `.json`, `.txt`, and `.md` files represented by persisted source-directory batch/file rows and material snapshots.

The future deterministic text index may segment already admitted UTF-8 material into stable text segments using implementation-frozen parameters such as line windows, character windows, normalized row/text labels, byte/character ranges, and content hashes. It must not call a model, generate embeddings, create a vector index, perform retrieval queries, infer hidden analysis plans, or broaden source intake.

## Identity Contract

Each future source/index record or response must be derived from a canonical identity basis that includes:

- `source_ingestion_batch_id`;
- `source_ingestion_file_id`;
- `material_snapshot_id`;
- `content_sha256`;
- `file_identity_hash`;
- `authority_basis_hash`;
- `payload_hash`;
- `index_contract_id == source_directory_material_deterministic_text_index_authority`;
- `index_mode == deterministic_text_segments`; and
- implementation-frozen segmentation version and parameters.

The future implementation must record or return enough identity detail to prove deterministic replay against the same source-directory file and material snapshot. A changed file hash, authority basis hash, payload hash, material snapshot id, segmentation version, or contract id must make prior index authority stale.

## Request And Runtime Contract

This contract does not admit a new route.

The next implementation may choose one of these narrow code-bearing shapes only after this contract is merged and current-main synced:

- a service-level helper used by targeted tests;
- a validate-only command/test helper that fails closed on empty runtime and never seeds artifacts; or
- a later separately frozen route if service-level proof is insufficient.

Allowed future inputs:

- persisted `source_ingestion_batch_id`;
- persisted `source_ingestion_file_id`;
- persisted `material_snapshot_id`;
- current source-directory file identity hashes; and
- implementation-frozen segmentation options, if the implementation proves those options cannot broaden source authority.

Forbidden future inputs include caller-supplied paths, URLs, glob patterns, recursive flags, browser-supplied file bytes, raw file payload overrides, arbitrary text bodies, package payload overrides, provider/model identifiers, embedding options, vector index options, retrieval query text, connector targets, destination selectors, credential fields, auth bypass fields, frontend-only state, and package mutation flags.

## State Contract

Allowed future state effects, if implementation admits durable state:

- read existing source-directory batch/file rows;
- read existing `L3MaterialSnapshot` rows for `server_configured_directory_file` material;
- write deterministic source/index metadata tied to the same batch/file/material authority; and
- mark or report stale source/index authority when upstream source or material hashes drift.

Forbidden state effects:

- writing vector index, embedding, retrieval query, qualitative-hybrid analysis, package, package payload, connector, destination, provider delivery, public/signed URL, auth/security, browser-storage, rendered UI, `AnalysisArtifact`, `ConnectorRun`, `ConnectorRunTarget`, or source `L3OutputPackage` state;
- mutating `L3SourceDirectoryIngestionBatch`, `L3SourceDirectoryIngestionFile`, `L3MaterialSnapshot`, package rows, source package rows, package payload files, handoff/export records, or APS retrieval chunks;
- seeding runtime state from validate actions; and
- treating existing APS `ApsRetrievalChunk` authority as source-directory text-index authority.

## Proof Contract

Minimum implementation proof after current-main sync:

- focused unit tests for deterministic text segmentation over `.txt`, `.md`, `.csv`, and `.json` material snapshots admitted from source-directory files;
- stale-authority tests for changed `content_sha256`, `file_identity_hash`, `authority_basis_hash`, `payload_hash`, and segmentation version;
- negative tests proving no embeddings, vector rows, retrieval rows, connector rows, package rows, package payload rewrites, provider calls, credentials, network egress, rendered controls, or frontend-durable state are produced;
- tests proving empty runtime fails closed and validate-only paths do not seed or generate artifacts;
- regression proof that existing source-directory ingestion, material preview, Gate B admission, and Gate C typing still pass; and
- progress checker coverage for the implementation proof and current-main sync.

No headed or headless browser proof is required unless a later freeze admits rendered UI changes.

## Still Blocked

This contract admits no runtime behavior, backend route behavior, service behavior, model change, migration, rendered UI control, source/index rows, vector index, embedding generation, retrieval query, qualitative-hybrid analysis runtime, qualitative broadening, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, full mockup activation, frontend-durable authority, hidden LLM planning, arbitrary source ingestion, arbitrary recursive ingestion, broad local upload, PDFs, OCR, Office documents, arbitrary binaries, web connectors, caller-supplied paths/URLs/globs, browser-supplied file bytes, browser/operator path editing, or source `L3OutputPackage` mutation.

## Next Posture

The next exact posture after merge is `current_main_sync_source_directory_material_source_index_authority_contract`.

After that sync, the next exact posture is `implement_source_directory_material_deterministic_text_index_authority_after_contract_sync`.

Do not implement vector indexing, embedding generation, retrieval query runtime, qualitative-hybrid analysis runtime, routes, provider/model calls, connector dispatch, source expansion, package mutation, rendered controls, frontend-durable authority, or auth/security broadening until a later current-main-selected freeze explicitly admits that behavior.
