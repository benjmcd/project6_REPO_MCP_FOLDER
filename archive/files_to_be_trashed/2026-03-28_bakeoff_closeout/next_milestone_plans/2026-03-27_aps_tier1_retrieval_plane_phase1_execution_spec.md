# APS Tier1 Retrieval Plane Phase 1 Execution Spec

## Status

Planning only. This document is an execution-grade planning packet for Phase 1. It is still not authorization to edit code or run migrations.

This packet resolves the remaining Phase 1 ambiguities from the earlier Phase 1 direction-planning pass.

## Canonical Basis

This spec is grounded in the live root authority surfaces:

- `docs/nrc_adams/nrc_aps_authority_matrix.md`
- `docs/nrc_adams/nrc_aps_reader_path.md`
- `docs/nrc_adams/nrc_aps_status_handoff.md`
- `docs/postgres/postgres_status_handoff.md`
- `project6.ps1`
- `backend/app/models/models.py`
- `backend/app/schemas/api.py`
- `backend/app/services/nrc_aps_content_index.py`
- `backend/app/services/nrc_aps_evidence_bundle_contract.py`
- `backend/app/services/nrc_aps_evidence_bundle.py`
- `backend/app/services/analysis.py`
- `backend/alembic/versions/0008_aps_content_index_tables.py`
- `backend/alembic/versions/0009_aps_document_processing_metadata.py`
- `backend/alembic/versions/0010_visual_page_refs_json.py`

## Phase 1 Slice Classification

This is a bounded Tier1 PostgreSQL retrieval slice.

It is:

- additive
- shadow-first
- parity-validated
- default-cutover-deferred

It is not:

- a Phase 8 reopening
- a lower-layer document-processing milestone
- an Evidence Bundle redesign
- an upper-layer schema-widening slice
- a vector or semantic slice

## Phase 1 Settled Decisions

The following decisions are resolved for Phase 1:

- Use a derived retrieval table, not a materialized view.
- Keep the retrieval plane current-state-only. Do not add retrieval-history tables in Phase 1.
- Keep `search_text` equal to canonical `chunk_text` in Phase 1.
- Use PostgreSQL lexical acceleration through an expression-index strategy over `search_text`. Do not require a literal `tsvector` storage column in SQLite-shaped lanes.
- Keep Phase 1 lexical-only. Do not add vector columns, extension requirements, or embedding tables.
- Keep Phase 1 search semantics exactly aligned with current `normalize_query_tokens()` and current list/search ordering rules. PostgreSQL search acceleration is for candidate pruning only, not for semantic or ranking changes.
- Keep shadow build explicit and operator-invoked. Do not piggyback retrieval-plane maintenance onto canonical content-index upserts, existing validate actions, or migrations.
- Keep Phase 1 public-surface behavior unchanged by default.
- Use a dedicated validate-only parity action for verification.
- Do not introduce a new public API endpoint in Phase 1.
- If operator comparison is needed after parity, prefer a dedicated internal/CLI comparison path over a public feature-flagged endpoint.

## Source Compatibility Contract

Phase 1 retrieval rows must preserve the current lower retrieval/output shape already emitted by `_serialize_index_row()` and typed by `ConnectorRunContentUnitOut` / `NrcApsContentSearchOut`.

The retrieval plane must therefore be able to reproduce, without widening:

- `content_id`
- `chunk_id`
- `content_contract_id`
- `chunking_contract_id`
- `chunk_ordinal`
- `start_char`
- `end_char`
- `chunk_text`
- `chunk_text_sha256`
- `page_start`
- `page_end`
- `unit_kind`
- `quality_status`
- `run_id`
- `target_id`
- `accession_number`
- `content_units_ref`
- `normalized_text_ref`
- `diagnostics_ref`
- `blob_ref`
- `download_exchange_ref`
- `discovery_ref`
- `selection_ref`
- `normalized_text_sha256`
- `blob_sha256`
- `effective_content_type`
- `document_class`
- `page_count`
- `visual_page_refs`

`diagnostics_ref` must follow linkage-authoritative semantics only.

## Logical DDL

The Phase 1 retrieval plane should be implemented as one table with the following logical row shape.

This is a logical contract, not a requirement that every physical column exist identically in every dialect. Phase 1 must keep the cross-dialect retrieval row portable while allowing PostgreSQL-only lexical acceleration.

```text
table aps_retrieval_chunk_v1
  aps_retrieval_chunk_id         string(36)   primary key
  retrieval_contract_id          string(64)   not null
  run_id                         string(36)   not null
  target_id                      string(36)   not null
  content_id                     string(64)   not null
  chunk_id                       string(64)   not null
  content_contract_id            string(64)   not null
  chunking_contract_id           string(64)   not null
  normalization_contract_id      string(64)   null
  accession_number               string(255)  null

  chunk_ordinal                  integer      not null
  start_char                     integer      not null
  end_char                       integer      not null
  page_start                     integer      null
  page_end                       integer      null
  unit_kind                      string(64)   null
  chunk_text                     text         not null
  chunk_text_sha256              string(64)   not null
  search_text                    text         not null

  content_status                 string(64)   not null
  quality_status                 string(32)   null
  effective_content_type         string(128)  null
  document_class                 string(64)   null
  page_count                     integer      not null

  content_units_ref              string(1024) null
  normalized_text_ref            string(1024) null
  normalized_text_sha256         string(64)   null
  diagnostics_ref                string(1024) null
  blob_ref                       string(1024) null
  blob_sha256                    string(64)   null
  download_exchange_ref          string(1024) null
  discovery_ref                  string(1024) null
  selection_ref                  string(1024) null
  visual_page_refs_json          text         null

  source_signature_sha256        string(64)   not null
  source_observed_at             timestamptz  not null
  rebuilt_at                     timestamptz  not null
  created_at                     timestamptz  not null
```

Physicalization rules:

- PostgreSQL may accelerate lexical candidate pruning from `search_text`, but only if the chosen prefilter is proven no-false-negative against current `normalize_query_tokens()` containment semantics for the bounded Phase 1 query suite.
- SQLite-shaped lanes must not be forced to emulate a literal `tsvector` type.
- If PostgreSQL-specific search state is needed beyond `search_text`, keep it dialect-local and out of the cross-dialect logical row contract.
- If that no-false-negative proof is not met, retrieval-backed search must fall back to Python-side lexical filtering over retrieval rows in Phase 1 rather than shipping semantics drift.

## Constraints And Indexes

Required uniqueness:

```text
unique(retrieval_contract_id, run_id, target_id, content_id, chunk_id)
```

Required lookup and ordering indexes:

```text
btree(run_id, content_id, chunk_ordinal, target_id)
btree(run_id, quality_status, document_class)
btree(content_id, chunk_id)
```

Conditional PostgreSQL lexical-acceleration index when semantics-safe candidate pruning is enabled:

```text
gin(to_tsvector('simple', search_text))
```

Optional Phase 1 index only if profiling proves need:

```text
btree(run_id, accession_number)
```

Do not add vector indexes in Phase 1.

## Build Source Query

The retrieval-plane build query must use the same join authority as current `list_content_units_for_run()` and `search_content_units()`:

- `ApsContentLinkage`
- join `ApsContentDocument` on `content_id + content_contract_id + chunking_contract_id`
- join `ApsContentChunk` on `content_id + content_contract_id + chunking_contract_id`

The build must serialize canonical row content using the same field semantics as `_serialize_index_row()`, including linkage-only `_resolve_diagnostics_ref()`.

## Signature Payload

`source_signature_sha256` must be computed over the canonical retrieval-visible payload, not over timestamps.

The exact logical payload should be:

```json
{
  "retrieval_contract_id": "aps_retrieval_chunk_v1",
  "content_id": "...",
  "chunk_id": "...",
  "content_contract_id": "...",
  "chunking_contract_id": "...",
  "normalization_contract_id": "...",
  "chunk_ordinal": 0,
  "start_char": 0,
  "end_char": 0,
  "page_start": null,
  "page_end": null,
  "unit_kind": null,
  "chunk_text": "...",
  "chunk_text_sha256": "...",
  "content_status": "...",
  "quality_status": "...",
  "run_id": "...",
  "target_id": "...",
  "accession_number": "...",
  "content_units_ref": "...",
  "normalized_text_ref": "...",
  "normalized_text_sha256": "...",
  "diagnostics_ref": "...",
  "blob_ref": "...",
  "blob_sha256": "...",
  "download_exchange_ref": "...",
  "discovery_ref": "...",
  "selection_ref": "...",
  "effective_content_type": "...",
  "document_class": "...",
  "page_count": 0,
  "visual_page_refs": []
}
```

Notes:

- `search_text` is intentionally excluded because Phase 1 fixes it equal to `chunk_text`.
- timestamps are intentionally excluded because signature must capture logical source state, not processing time.
- linkage-authoritative `diagnostics_ref` is mandatory in the signature payload.

## Rebuild Algorithm

The Phase 1 rebuild algorithm should be:

1. Select the rebuild scope.
2. Query canonical APS rows for that scope using the current join semantics.
3. Serialize the canonical retrieval-visible payload exactly as current APS list/search surfaces would.
4. Compute `source_signature_sha256`.
5. Build `search_text = chunk_text`.
6. Build PostgreSQL lexical-acceleration state from `search_text` only when the active dialect supports it and the chosen prefilter is allowed by the Phase 1 parity rules.
7. Upsert the retrieval row if absent.
8. Update the retrieval row if signature changed.
9. Leave the retrieval row untouched if signature is unchanged.
10. Reconcile any stale retrieval rows that were inside the scope but not seen in the rebuild.

For stale-row reconciliation, Phase 1 uses current-state-only semantics:

- rows not seen in the current rebuild scope should be deleted from the retrieval plane for that scope

## Search Config

Phase 1 should use one deterministic search config, not per-row heuristics.

Default candidate-pruning attempt:

- default Postgres simple lexical config

Reason:

- it minimizes Phase 1 branching
- it avoids premature language-specific stemming assumptions
- it keeps lexical parity reasoning simpler

Enable it only if bounded Tier1 PostgreSQL query-parity proof shows:

- no false negatives relative to current all-token containment semantics
- no ranking or pagination drift relative to the current Python contract

If that proof does not pass, disable database-side candidate pruning and keep retrieval-backed search on Python-side filtering over retrieval rows for Phase 1. If later evidence shows language-aware config is needed, that is a separate slice.

## Search Semantics Contract

Phase 1 retrieval-backed search must preserve current search behavior exactly.

Required contract:

- query tokenization must continue to use `normalize_query_tokens()`
- empty-query handling must continue to fail with `empty_query`
- candidate rows must satisfy all-token containment after current normalization
- PostgreSQL lexical acceleration may only act as a proven superset-safe prefilter; it must not widen, narrow, or redefine current token semantics
- any PostgreSQL prefilter that can exclude a row that current Python lexical matching would include is forbidden
- final result ranking must continue to sort by:
  1. `matched_unique_query_terms` descending
  2. `summed_term_frequency` descending
  3. `chunk_length` ascending
  4. `content_id` ascending
  5. `chunk_ordinal` ascending
  6. `run_id` ascending
  7. `target_id` ascending
- pagination must be applied after final ranking, not before

List ordering parity must remain:

1. `content_id` ascending
2. `chunk_ordinal` ascending
3. `target_id` ascending

Phase 1 is not allowed to replace the current lexical ranking contract with `ts_rank`, stemming-sensitive ranking, semantic retrieval, or database-native pagination that changes final row order.

## Shadow Build Rules

Phase 1 shadow-build behavior must be explicit and separate from validation.

Required rules:

- retrieval-plane build is a non-validate operator/internal action
- validate-only parity actions must never build or seed retrieval rows
- migrations must never backfill retrieval rows
- canonical content-index upserts must not automatically maintain retrieval rows in Phase 1
- any shadow-build invocation must declare a bounded scope
- if no scope is declared, the shadow-build surface must fail closed rather than perform an implicit broad rebuild

Allowed bounded scopes:

- run scope
- target scope

Exact bounded-scope semantics:

- run scope requires `run_id` and no `target_id`
- target scope requires `target_id`; `run_id` may be omitted
- if both `run_id` and `target_id` are supplied, the operation remains target scope and must fail closed unless that target resolves to the same run
- a supplied `target_id` that does not resolve is a scope failure, not an empty-scope success
- a supplied `run_id` that does not resolve is a scope failure, not an empty-scope success

Full-scope rebuild remains out of base Phase 1 unless explicitly opened later.

## Scope Wiring Rules

Phase 1 build and parity validation must share one explicit bounded-scope contract.

Required rules:

- the shadow-build surface and the validate-only parity surface must accept the same explicit bounded scope inputs
- the bounded scope contract is `run_id` and/or `target_id`; tool/CLI spellings should stay aligned as `--run-id`, `--target-id`, `-NrcApsRunId`, and `-NrcApsTargetId`
- Phase 1 parity validation must not discover latest runs implicitly
- Phase 1 parity validation must fail closed when no explicit bounded scope is supplied
- Phase 1 parity validation must fail closed on conflicting or unresolved scope inputs
- Phase 1 operator parity validation must run against Tier1 PostgreSQL for the exact bounded scope that was shadow-built
- Tier2/Tier3 SQLite-shaped lanes remain proof and compatibility lanes; they are not the authoritative parity surface for this Tier1 PostgreSQL milestone

## Read-Path Rules

Phase 1 Stage 1 and Stage 2:

- no public route behavior changes
- `router.py` continues to call existing list/search functions by default

Phase 1 Stage 3, if opened:

- add a dedicated operator-only comparison path
- do not expose it as a new public route
- prefer a CLI/operator action under `project6.ps1` or a dedicated internal comparison helper

Phase 1 Stage 4, if opened later:

- a separate cutover proposal may repoint `content-search` default reads
- that proposal must be justified by parity proof
- that proposal is out of scope for this execution packet

## Validator Contract

Phase 1 should add one validate-only parity artifact.

This validator operates only on explicit `run_scope` or `target_scope`. Full-scope validation remains out of base Phase 1.

Recommended logical schema:

```json
{
  "schema_id": "aps.retrieval_plane_validation.v1",
  "schema_version": 1,
  "retrieval_contract_id": "aps_retrieval_chunk_v1",
  "validated_at_utc": "2026-03-27T00:00:00Z",
  "scope": {
    "run_id": null,
    "target_id": null,
    "mode": "run_scope|target_scope"
  },
  "passed": true,
  "canonical_row_count": 0,
  "retrieval_row_count": 0,
  "counts_match": true,
  "missing_in_retrieval": [],
  "orphan_retrieval_rows": [],
  "field_mismatches": [],
  "ordering_mismatches": [],
   "search_parity_failures": [],
   "diagnostics_authority_mismatches": [],
   "reasons": [],
   "payload_sha256": "..."
}
```

Required failure classes:

- `retrieval_row_missing`
- `retrieval_orphan_row`
- `retrieval_field_mismatch`
- `retrieval_ordering_mismatch`
- `retrieval_search_parity_mismatch`
- `retrieval_diagnostics_authority_mismatch`
- `retrieval_contract_mismatch`
- `retrieval_scope_empty`
- `retrieval_scope_invalid`

## Verification Matrix

Phase 1 implementation must be verified at four levels.

### 1. Unit Level

Required tests:

- signature payload stability
- no-op upsert when signature unchanged
- update on signature change
- stale-row deletion within rebuild scope
- linkage-authoritative diagnostics behavior
- search ordering compatibility against current deterministic tie-break rules
- PostgreSQL candidate-pruning safety or explicit fallback behavior for representative bounded-query cases
- explicit scope-resolution behavior for:
  1. run-only scope
  2. target-only scope
  3. run-plus-target consistent scope
  4. run-plus-target conflicting scope

### 2. Integration Level

Required tests:

- build retrieval plane from canonical APS fixture/runtime data
- validate parity report passes on known-good APS runtime
- current public content-search route remains unchanged by default
- current public content-units listing remains unchanged by default
- bounded Tier1 PostgreSQL query-parity proof covers representative query cases before database-side candidate pruning is enabled

The bounded query-parity proof must include at least:

- single-token alpha query
- multi-token all-match query
- punctuation/normalization query where current `normalize_query_tokens()` collapses punctuation
- mixed-case query
- duplicate-token query
- numeric or accession-like token query
- zero-result query
- tie-order query that exercises the current deterministic secondary sort keys
- run-scoped search case

### 3. Validate-Only Operator Level

Required operator behavior:

- retrieval-plane build must remain separate from retrieval-plane validation
- new retrieval-plane validator must be validate-only
- validator must fail closed on empty runtime
- validator must fail closed when explicit bounded scope is omitted
- validator must not rely on latest-run discovery as a substitute for explicit scope
- validator must target Tier1 PostgreSQL for the actual shadow-built scope
- validator must not seed or generate business artifacts

### 4. Cutover-Gate Level

Not part of base Phase 1 implementation.

If opened later, required proofs would be:

- parity between current and retrieval-plane-backed reads for the exact surface being cut over
- preserved output schema
- deterministic ordering preserved
- no diagnostics-authority regressions

## Required Non-Regression Boundaries

The implementation must not:

- change canonical APS table contracts
- change Evidence Bundle assembly semantics
- change lower-layer document-processing behavior
- change artifact-ingestion semantics
- weaken any validate-only rule
- violate the canonical `app.*` import-path guardrail
- introduce dependency on OCR proof reruns unless lower-layer behavior changed

## Tech-Debt Controls

Controls settled for Phase 1:

- no retrieval history table
- no embeddings
- no public API expansion
- no default cutover
- no language-specific search branching
- no lower-tier redesign

Phase 1 intentionally accepts:

- dual-state debt between APS truth and retrieval shadow state
- one additional validator surface
- one explicit non-validate shadow-build surface

Phase 1 intentionally rejects:

- long-lived dual-read public behavior
- semantic debt disguised as lexical work
- document-level diagnostics fallback debt

## Deliverables

If implemented exactly to this packet, the deliverables should be:

- one new retrieval table
- one explicit shadow-build path
- one validate-only parity artifact/report
- one operator entrypoint for parity validation
- supporting tests for serializer compatibility, signature stability, rebuild correctness, and parity

No other deliverables are required for Phase 1.

## Completion Standard

Phase 1 is execution-complete only when all of the following are true:

- the shadow retrieval plane exists in Tier1 PostgreSQL
- it is derived only from canonical APS truth
- it reproduces current retrieval-visible fields without schema widening
- it preserves linkage-authoritative diagnostics semantics
- if PostgreSQL lexical candidate pruning is enabled, it is proven not to change current search semantics
- if that proof is not met, retrieval-backed search remains semantics-correct without database-side candidate pruning in Phase 1
- it can be shadow-built only through a separate non-validate surface
- its parity validator passes on the intended scope
- default public APS read behavior is still unchanged

## Next Planning Surface After This Packet

If more specificity is still required after this packet, the next document should be narrowly limited to:

- exact migration skeleton
- exact ORM model shape
- exact validator action and report file naming
- exact test inventory and scope mapping
