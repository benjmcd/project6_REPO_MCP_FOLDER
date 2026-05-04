# Layer 3 Qualitative APS Execution Contract

## Status

Current-main planning/control contract paired with `114_QUAL_APS_EXEC_FREEZE.md`.

This contract defines the minimum admissibility rules for any future qualitative APS content document execution lane. It does not allocate a live route, execution service, model/migration, result row, rendered control, document trace behavior, package behavior, provider/public URL behavior, connector/destination behavior, source-ingestion behavior, or runtime write.

## Authority Order

Use this order before auditing or extending qualitative APS content document execution:

1. current `project6-origin/main` source and tests;
2. `backend/app/models/models.py` for `ApsContentDocument`, `ApsContentChunk`, `ApsContentLinkage`, `L3MaterialSnapshot`, `L3TypingRecord`, `L3AnalysisUnit`, `L3AnalysisSet`, and `L3PassRun` schema truth;
3. `backend/app/services/layer3_workbench.py` for `aps_content_document` source preview, material preview, source trace, and Gate B snapshot authority;
4. `backend/app/services/layer3_typing_entry.py` for qualitative/document-chunk typing authority;
5. `backend/app/services/layer3_pass_entry.py` for the current wrapped-quantitative pass-entry/execution boundary;
6. `backend/tests/test_layer3_workbench.py`, `backend/tests/test_layer3_typing_entry.py`, and `backend/tests/test_layer3_pass_entry.py` for current proof boundaries;
7. docs `25`/`27` for older qualitative single-item planning-only context;
8. `105_deferred-gates.md`, `114_QUAL_APS_EXEC_FREEZE.md`, and this contract for current qualitative APS execution governance.

Browser screenshots, prototype trace samples, copied document text, operator memory, PR titles, branch names, or planning prose are never sufficient authority for enabling qualitative APS execution behavior.

## Contract Vocabulary

Reserved labels:

- `qual_aps_exec_not_admitted`;
- `single_aps_doc_qualitative_pass_candidate`;
- `qual_aps_doc_exec_ready`;
- `qual_aps_doc_exec_recorded`;
- `qual_aps_doc_exec_failed`;
- `qual_aps_doc_exec_review_ready`;
- `qual_aps_doc_exec_review_approved`;
- `qual_aps_doc_exec_review_rejected`.

These labels are not live states by themselves. They may be used only by a later implementation freeze, progress/control sync, or code lane that explicitly admits the qualitative APS document execution path.

## Admission Contract

The first implementation lane must admit at most one execution mode:

- `single_aps_doc_qualitative_pass`.

The admitted input must derive server-side from existing committed Layer 3 authority:

- one finalized `L3Session`;
- one `L3MaterialSnapshot` with `source_shape == "aps_content_document"`;
- one `L3TypingRecord` with `chosen_modality == "qualitative"` and `planning_shape_family == "document_chunks"`;
- one `L3AnalysisUnit` whose `member_snapshot_ids_json` contains that snapshot and whose `analysis_modality == "qualitative"`;
- one `L3AnalysisSet` with `set_type == "single_item"` or another explicitly frozen single-document set rule;
- one `ApsContentDocument` matching the snapshot `content_id`;
- zero or more `ApsContentLinkage` rows, with missing linkage handled by a specified fail-closed or degraded-trace rule;
- one ordered chunk set from `ApsContentChunk` matching `content_id`, `content_contract_id`, and `chunking_contract_id`;
- a fresh `client_request_id`.

The first lane must not admit qualitative associated-cohort execution, cross-document synthesis, hybrid execution, comparative execution, RAG/vector retrieval, generic prompt execution, or connector/provider/package side effects.

## Request Contract

A future request must be server-authority based and must include, or derive server-side:

- `session_id`;
- `analysis_unit_id` or another server-owned selected unit reference;
- `analysis_set_id` if the future freeze requires set binding;
- `material_snapshot_id`;
- `content_id`;
- selected execution mode;
- fresh `client_request_id`.

The request must not accept:

- `dataset_version_id`;
- raw document text;
- raw chunk text overrides;
- local filesystem paths;
- provider/object-store paths, bucket names, ACLs, URLs, or signed URLs;
- connector keys, destination ids, credentials, provider tokens, model secrets, or API keys;
- package payload bytes or package mutation fields;
- RAG/vector/LLM/model/prompt flags unless separately admitted;
- retry, cancel, recovery, batch, cohort, comparative, hybrid, or cross-modal flags unless separately admitted.

All qualitative APS execution authority must be resolved by the server from committed Layer 3 state and APS content tables.

## Input Material Contract

The future lane must specify:

- chunk ordering: `ApsContentChunk.chunk_ordinal`, then `chunk_id`;
- chunk inclusion limits and behavior when chunk count exceeds limits;
- handling for empty `chunk_text`, missing `chunk_text_sha256`, invalid char ranges, missing pages, and quality statuses;
- whether missing `ApsContentLinkage` blocks execution or records a degraded trace caveat;
- how `visual_page_refs_json`, `content_units_ref`, `normalized_text_ref`, `diagnostics_ref`, `selection_ref`, and `discovery_ref` are bound to result provenance;
- whether page ranges are advisory trace only or required citation authority;
- how the input hash is computed and persisted or returned.

The future lane must not re-fetch source documents, re-run APS ingestion, or alter APS content rows.

## Execution Owner Contract

The future freeze must choose one owner model:

- extend `backend/app/services/layer3_pass_entry.py` with a separate qualitative engine family and hard fail-closed checks; or
- add a separate service-owned qualitative APS execution module that composes around Layer 3 session, typing, and pass-entry state without widening the quantitative path.

If the chosen owner cannot avoid mixing qualitative document execution with wrapped quantitative `DatasetVersion` execution, implementation must stop and return to planning.

The first implementation must not call `run_analysis(...)` with a `dataset_version_id` for APS content documents.

## Result Contract

A future result may expose only response-safe metadata and bounded qualitative outputs:

- execution mode;
- status;
- content document identity;
- chunk ids and chunk hashes used;
- citation refs and page refs when available;
- response-safe findings;
- response-safe caveats;
- result-review readiness;
- idempotency status;
- operator-visible next actions.

The response must not expose:

- local filesystem paths;
- raw provider object paths;
- credentials, tokens, connector secrets, or destination secrets;
- package payload bytes;
- raw prompt or internal model trace;
- public/provider URLs;
- connector/destination dispatch metadata unless separately admitted.

The future freeze must decide whether outputs are called findings, facts, insights, caveats, results, or another bounded term. The implementation must use that vocabulary consistently in API, UI, tests, docs, and progress artifacts.

## Review And Package Contract

Before any qualitative APS result reaches package review, handoff/export, APS handoff dispatch, delivery, signed reference, provider/public URL, connector/destination dispatch, or external consumer behavior, a separate downstream freeze must define:

- result-review semantics for qualitative APS output;
- package compatibility and package kind;
- citation rendering and trace proof;
- allowed handoff/export target, if any;
- no-leakage and response-safe output rules.

`114_QUAL_APS_EXEC_FREEZE.md` and this contract do not make qualitative results packageable or dispatchable.

## Security Contract

The future lane must fail closed for:

- missing or stale session, snapshot, typing, unit, set, document, chunk, or linkage authority;
- wrong source shape;
- wrong modality;
- wrong set type;
- missing content document;
- empty or over-limit chunk input unless the future freeze defines a safe degraded mode;
- malformed request fields;
- duplicate idempotency keys with mismatched authority;
- attempts to supply `dataset_version_id`, raw text, paths, provider URLs, connector fields, package bytes, model flags, or source expansion flags.

No local path, source path, provider credential, connector secret, destination secret, package byte, raw model prompt, or unredacted internal trace may be returned or logged as response-visible output.

## Test Contract

Minimum future proof:

- focused tests for the one admitted `single_aps_doc_qualitative_pass` path;
- tests proving qualitative-only APS document sets remain blocked except for the exact admitted path;
- tests proving qualitative associated-cohort, hybrid, comparative, RAG, vector, LLM, connector, provider/public URL, package, handoff/export, and source-ingestion side effects remain blocked;
- tests proving `dataset_version_id`, `DatasetVersion` materialization, and wrapped quantitative `run_analysis(...)` are not used for APS document execution;
- tests for missing chunks, empty chunks, stale snapshot, wrong source shape, wrong modality, wrong set, wrong document, missing linkage, duplicate idempotency, and malformed request fields;
- tests for result/citation/trace binding to `content_id`, chunk ids, chunk hashes, linkage refs, and source trace refs;
- no-leakage tests for local paths, provider paths, credentials, connector/destination details, package bytes, raw prompts, and source rows;
- headed and headless browser proof if any rendered `/review/layer3` or document trace behavior changes.

## Implementation Stop Conditions

Stop and return to planning if implementation would require:

- more than one qualitative execution mode;
- cohort, hybrid, comparative, cross-modal, RAG, vector, or LLM behavior;
- accepting raw text or source paths from the browser;
- converting APS document chunks into `DatasetVersion` rows or aligned-wide-table inputs;
- using current quantitative pass-entry execution without a separately frozen qualitative engine family;
- changing document trace rendering or native PDF overlays without a rendered UI freeze and browser proof;
- creating package/handoff/export/provider/connector behavior in the same lane;
- schema/model/migration changes not named before code;
- changing APS ingestion or source processing;
- treating docs-only governance as live implementation.
