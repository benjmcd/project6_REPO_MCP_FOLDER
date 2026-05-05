# Layer 3 Qualitative APS Execution Entry Freeze

Status: branch-local implementation-entry freeze for a future qualitative APS content-document execution lane.

This file does not implement qualitative execution, add a route, add a service, add a model or migration, change `/review/layer3`, create `L3PassRun`, create `AnalysisRun`, write artifacts, enable package/handoff/export, or admit hybrid/RAG/vector behavior. It narrows the next admissible qualitative work to one exact future implementation lane so runtime work cannot be inferred from mockups, progress prose, or generic qualitative wording.

## Why This Lane

The broader active goal still includes connector/destination dispatch, package mutation/reconstruction, broad source/upload expansion, qualitative/hybrid/RAG execution, and full mockup activation. Current authority does not support implementing those broad items.

The only deferred lane with a concrete live authority chain and an already named first mode is qualitative APS content-document execution:

- `backend/app/services/layer3_workbench.py` already supports `aps_content_document` as a source class and keeps `rag_vector_index`, `arbitrary_local_directory`, `broad_file_upload`, `web_connector`, and `unbounded_runtime_db` unsupported.
- `aps_content_document_candidates(...)` and material preview expose `ApsContentDocument`, `ApsContentLinkage`, `ApsContentChunk`, and `layer3.aps_content_document_source_trace.v1` authority.
- Gate B can persist an `aps_content_document` material snapshot.
- `backend/app/services/layer3_typing_entry.py` maps `aps_content_document` to `planning_shape_family == "document_chunks"` and `chosen_modality == "qualitative"`.
- `backend/app/services/layer3_pass_entry.py` and `backend/app/services/layer3_workbench.py` still admit only wrapped quantitative selected-pass execution, with `run_analysis(..., dataset_version_id=...)` and `ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS`.
- `backend/app/models/models.py::AnalysisRun.dataset_version_id` is non-nullable, so APS document execution cannot safely masquerade as the current quantitative `AnalysisRun` path without either a schema decision or a separate result-state strategy.
- `backend/tests/test_layer3_workbench.py`, `backend/tests/test_layer3_typing_entry.py`, and `backend/tests/test_layer3_pass_entry.py` prove current APS-document selection/typing and current qualitative fail-closed behavior.

This lane outranks connector/destination dispatch because no repo-confirmed connector/destination authority or destination lifecycle has been selected. It outranks package mutation/reconstruction because existing package construction/submit is bounded and current docs keep mutation, amendment, rewrite, reconstruction, and supersession out. It outranks broad source/upload/RAG because those source classes are explicitly unsupported. It outranks full mockup activation because mockups are target-state artifacts, not implementation authority.

## Selected Future Lane

Name: `single_aps_doc_qualitative_pass`.

Type: implementation-entry freeze only.

Future implementation may admit exactly one qualitative execution mode:

- one committed Layer 3 session;
- one `L3MaterialSnapshot` with `source_shape == "aps_content_document"`;
- one `L3AnalysisUnit` with `analysis_modality == "qualitative"`;
- one `L3AnalysisSet` that binds exactly that unit under a single-document rule;
- one matching `ApsContentDocument`;
- ordered `ApsContentChunk` rows for that document;
- optional `ApsContentLinkage` trace refs under a specified degraded-trace rule;
- one fresh `client_request_id`;
- one response-safe qualitative output record with bounded findings/caveats and trace refs.

No other qualitative, hybrid, RAG, vector, cohort, comparative, cross-document, connector, provider, package, or full-mockup behavior is admitted.

## Required Implementation Shape

A future code slice must choose the least invasive owner shape that preserves the quantitative path:

- preferred owner: a new service module, `backend/app/services/layer3_qual_aps_execution.py`;
- allowed integration: narrow calls from `backend/app/services/layer3_workbench.py` only after session, plan, unit, set, source, chunk, idempotency, and stale-authority checks pass;
- forbidden shortcut: calling `run_analysis(...)` with a synthetic or converted `DatasetVersion`;
- forbidden shortcut: extending wrapped quantitative `execute_selected_pass_run(...)` in a way that weakens its `dataset_version_id` and engine-family checks;
- forbidden shortcut: accepting raw document text, chunk text overrides, local paths, provider paths, URLs, connector ids, destination ids, prompt/model flags, package bytes, or source-expansion fields from the browser.

Before code begins, the implementation prompt must explicitly decide one of these result-state strategies:

1. No schema path: write only existing `L3PassRun` JSON summary and `output_payload_ref` metadata for the qualitative pass, with no `AnalysisRun`.
2. Schema path: add a separately frozen model/migration for qualitative execution records before code uses durable result rows.

The implementation must stop if it tries to reuse `AnalysisRun` while `AnalysisRun.dataset_version_id` remains non-nullable and no legitimate `DatasetVersion` exists for the APS document.

## In-Scope Future Files

Likely in scope for the future implementation:

- `backend/app/services/layer3_qual_aps_execution.py`
- `backend/app/services/layer3_workbench.py`
- `backend/app/api/layer3.py`
- `backend/tests/test_layer3_api.py`
- `backend/tests/test_layer3_pass_entry.py`
- a new focused test file such as `backend/tests/test_layer3_qual_aps_execution.py`

Conditionally in scope only if separately frozen:

- `backend/app/models/models.py`
- `backend/alembic/versions/*.py`

Out of scope for the first future implementation:

- `backend/app/review_ui/static/layer3.js`
- `e2e/layer3-workbench.spec.js`
- provider/public URL services
- connector or destination services
- package mutation/reconstruction services
- source ingestion/upload/local-directory/RAG/vector services
- document trace rendering or native PDF overlay files

Rendered UI can be added only after backend/API behavior is proven or in a separate UI freeze with headed and headless browser proof.

## Positive Invariants

A future implementation must prove:

- the admitted path runs only for `single_aps_doc_qualitative_pass`;
- the server derives source authority from committed `L3Session`, `L3MaterialSnapshot`, `L3TypingRecord`, `L3AnalysisUnit`, `L3AnalysisSet`, `ApsContentDocument`, `ApsContentChunk`, and optional `ApsContentLinkage` rows;
- chunk ordering is deterministic by `chunk_ordinal`, then `chunk_id`;
- output binds to content id, content contract id, chunking contract id, material snapshot id, analysis unit id, analysis set id, chunk ids, chunk hashes, and linkage refs when available;
- duplicate `client_request_id` behavior is deterministic;
- stale session, stale preview/plan/unit/set/source authority, wrong modality, wrong source shape, missing document, missing chunks, empty chunks beyond the selected policy, malformed request fields, and wrong document all fail closed;
- existing APS document selection, material preview, Gate B snapshot, and Gate C typing tests still pass.

## Negative Invariants

A future implementation must explicitly prove no accidental:

- `DatasetVersion` creation or aligned-wide-table conversion for APS document chunks;
- wrapped quantitative `run_analysis(..., dataset_version_id=...)` call for APS document execution;
- qualitative associated-cohort execution;
- hybrid execution;
- RAG/vector retrieval;
- cross-document synthesis;
- connector/destination dispatch;
- provider/public URL generation;
- package mutation/reconstruction/amendment/supersession;
- handoff/export/delivery/signed-reference behavior;
- source ingestion/upload/local-directory widening;
- schema/model/migration change unless separately frozen;
- frontend-only durable state;
- hidden LLM planning;
- full mockup activation.

## Required Proof Plan

Minimum future backend proof:

- service success test for one `single_aps_doc_qualitative_pass`;
- API success test only if a route is added;
- missing chunks fail closed with no partial state;
- wrong source shape fails closed;
- wrong modality fails closed;
- wrong analysis set or multi-document set fails closed;
- stale material snapshot or content id mismatch fails closed;
- duplicate `client_request_id` same authority returns deterministic same state;
- duplicate `client_request_id` different authority fails closed;
- forbidden request fields fail closed;
- no `DatasetVersion` rows are created;
- no wrapped quantitative `run_analysis(...)` call is made;
- no connector, provider/public URL, package mutation, handoff/export, source-widening, hybrid, RAG/vector, or full mockup side effects occur.

Minimum regression proof:

- `python -m pytest .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_typing_entry.py .\backend\tests\test_layer3_pass_entry.py -q`
- focused new qualitative APS execution tests;
- `python .\tools\l3-progress-check.py`
- `git diff --check`

Browser proof is not required for a backend/service-only implementation. If any rendered `/review/layer3` or document-trace behavior changes, both headless and headed Chromium proof become required.

## Stop Conditions

Stop before implementation if the slice requires:

- more than one qualitative mode;
- any RAG/vector or LLM planning behavior;
- accepting browser-supplied raw text, paths, URLs, connector/destination fields, package bytes, or model flags;
- changing APS ingestion or document processing;
- changing document-trace rendering;
- creating package/handoff/export/provider/connector behavior;
- mutating package payloads;
- adding schema/model/migration work without a separate schema freeze;
- claiming docs `114`/`115`, this file, or mockups made qualitative execution live.
