# Layer 3 Source Expansion Freeze

Status: source expansion implementation-entry freeze for supported-source-only runtime on branch `codex/l3-source-expansion-freeze` from `project6-origin/main=3c46dc77`.

This artifact freezes the current source boundary and prevents broad source/upload expansion from being inferred from mockups, planning prose, or generic upload routes. It does not add source ingestion, local upload, local directory traversal, web connector source retrieval, RAG/vector retrieval, unbounded runtime DB source reads, schema/model/migration changes, connector/destination dispatch, provider/public URLs, package mutation/reconstruction, broad qualitative/hybrid/RAG execution, full mockup activation, or authentication/security work.

## Authority Snapshot

- authority_worktree: `C:\Users\benny\Downloads\worktree_for_audits`
- implementation_branch: `codex/l3-source-expansion-freeze`
- baseline_ref: `project6-origin/main`
- baseline_commit: `3c46dc77`
- owner service: `backend/app/services/layer3_source_boundary.py`
- proof test: `backend/tests/test_layer3_source_boundary.py`
- progress checker: `tools/l3-progress-check.py`
- source gates: `105_deferred-gates.md`, `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md`, `118_L3_GOAL_AUDIT.md`, and `120_L3_CLOSEOUT.md`

## Decision

The selected source expansion mode is exactly:

- selected_source_expansion_mode: `supported_source_classes_only`

Only the already-admitted source classes remain available:

- `dataset_version`
- `aps_content_document`

The following source families remain unsupported and must fail closed:

- `rag_vector_index`
- `arbitrary_local_directory`
- `broad_file_upload`
- `web_connector`
- `unbounded_runtime_db`

No source upload, local directory ingestion, broad file upload, web connector source, RAG/vector retrieval, or unbounded runtime DB source is admitted.

## Runtime Contract

`backend/app/services/layer3_source_boundary.py` owns a response-safe contract:

- schema: `layer3.source_boundary_contract.v1`
- mode: `supported_source_classes_only`
- source_upload_enabled: `False`
- local_directory_enabled: `False`
- broad_file_upload_enabled: `False`
- web_connector_enabled: `False`
- rag_vector_enabled: `False`
- unbounded_runtime_db_enabled: `False`
- requires_later_freeze: `True`

The runtime contract is proof metadata only. It does not add a route, database row, artifact, source ingestion path, file copy, upload target, connector call, vector index, runtime DB query, or UI control.

## Positive Invariants

- `SUPPORTED_SOURCE_CLASSES` remains exactly `("dataset_version", "aps_content_document")`.
- `UNSUPPORTED_SOURCE_CLASSES` remains exactly `("rag_vector_index", "arbitrary_local_directory", "broad_file_upload", "web_connector", "unbounded_runtime_db")`.
- Workbench preflight and source preview use the source-boundary helper instead of redeclaring source classes locally.
- Source and material candidate id parsing returns classes only for supported source families.
- `source_boundary_contract()` exposes the supported-only mode and all blocked source expansion families.
- `tools/l3-progress-check.py` fails if the supported or unsupported source families drift.

## Negative Invariants

This freeze must prove no accidental:

- broad source/upload expansion
- source upload or local upload admission
- local directory source admission
- broad file upload admission
- web connector source admission
- RAG/vector source or retrieval admission
- unbounded runtime DB source admission
- schema/model/migration change
- `L3PassRun` creation
- `AnalysisRun` creation
- output/package/handoff/export artifact creation
- connector/destination dispatch
- provider/public URL support
- frontend-only durable state
- hidden LLM planning
- package mutation/reconstruction
- full mockup activation
- authentication/security scope reopening

## Test And Proof Plan

Required local proof:

- `python -m py_compile .\backend\app\services\layer3_source_boundary.py .\tools\l3-progress-check.py`
- `python -m pytest .\backend\tests\test_layer3_source_boundary.py -q`
- `python .\tools\l3-progress-check.py`
- `git diff --check`

Optional regression proof before merge:

- `python -m pytest .\backend\tests\test_layer3_api.py .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_source_boundary.py -q -k "source_boundary or unsupported_source_class or source_preview"`

## Acceptance Criteria

This slice is accepted only when:

- this file exists and names `supported_source_classes_only`;
- `backend/app/services/layer3_source_boundary.py` exposes `source_boundary_contract()` with all source expansion flags false;
- `backend/tests/test_layer3_source_boundary.py` proves the contract and unsupported families;
- `tools/l3-progress-check.py` requires this freeze, the contract helper, and the blocked source families;
- `105_deferred-gates.md`, `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md`, `118_L3_GOAL_AUDIT.md`, and `120_L3_CLOSEOUT.md` reference this freeze without claiming broad source/upload expansion;
- required local proof commands pass.
