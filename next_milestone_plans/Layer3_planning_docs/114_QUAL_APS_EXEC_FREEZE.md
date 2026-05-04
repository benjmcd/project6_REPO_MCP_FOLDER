# Layer 3 Qualitative APS Execution Freeze

## Status

Current-main planning/control freeze for qualitative APS content document execution after PR `#525` connector/destination dispatch governance.

This document does not implement qualitative execution, add a route, change `/review/layer3`, change document trace rendering, add a model or migration, mutate package/handoff/export behavior, widen source ingestion, dispatch to connectors or destinations, create provider/public URLs, or create runtime rows/files. It freezes the decision that qualitative APS content document execution remains not admitted until a later implementation-entry freeze proves one exact APS-document execution contract.

## Current Live Boundary

Current `project6-origin/main` supports APS content documents as selectable and traceable Layer 3 material:

- `backend/app/services/layer3_workbench.py` lists `aps_content_document` as a supported source class.
- `aps_content_document_candidates(...)` returns indexed APS content-document candidates from `ApsContentDocument` and `ApsContentLinkage`.
- `material_preview(...)` can produce `aps_content_document` material candidates with `planning_shape_family == "document_chunks"`, source identity, source provenance, chunk summary, and `layer3.aps_content_document_source_trace.v1`.
- `gate_b_decision(...)` can persist selected `aps_content_document` material as `L3MaterialSnapshot` rows with source trace provenance.
- `backend/app/services/layer3_typing_entry.py` maps `aps_content_document` snapshots to `candidate_modalities_json == ["qualitative"]`, `chosen_modality == "qualitative"`, and `planning_shape_family == "document_chunks"`.
- `backend/tests/test_layer3_workbench.py` proves APS content document candidate listing, material-preview trace, and Gate B snapshot persistence.
- `backend/tests/test_layer3_typing_entry.py` proves APS content documents type as qualitative document chunks.

Current pass entry remains wrapped quantitative:

- `backend/app/services/layer3_pass_entry.py` admits `quantitative_single_item_dataset_version` and `quantitative_associated_cohort_dataset_version` scopes.
- `execute_selected_pass_run(...)` requires `engine_family == "wrapped_quantitative_analysis"`.
- single-item execution requires a `dataset_version_id`.
- associated-cohort execution derives an aligned wide-table `DatasetVersion` before calling `run_analysis(...)`.
- `run_analysis(...)` is still invoked with `dataset_version_id` and an admitted quantitative method name.
- `backend/tests/test_layer3_pass_entry.py` proves qualitative-only sets fail closed with no `L3AnalysisPlan`, `L3PassRun`, or `AnalysisRun`.

PR `#513` UI/theme trace alignment is representation-only over one APS content-document trace sample. It is not execution authority.

## Decision

Qualitative APS content document execution remains blocked.

The next admissible step is not runtime implementation. The next admissible step is a later implementation-entry freeze only if live repo evidence and operator need prove that selectable/typed APS document chunks must produce a bounded Layer 3 result inside the workbench chain.

If that evidence exists later, the first implementation lane must choose exactly one initial execution mode:

- `single_aps_doc_qualitative_pass`: execute one selected `aps_content_document` analysis unit for one committed Layer 3 session, with bounded chunk/citation/trace input and one response-safe qualitative result record.

Do not implement associated-cohort qualitative execution, hybrid execution, comparative execution, cross-document synthesis, RAG, vector retrieval, generic LLM orchestration, document-trace rendering changes, connector dispatch, provider/public URLs, or package mutation in the first qualitative APS execution lane.

## Required Activation Evidence

Before implementation can begin, the future lane must prove:

- one concrete operator task that cannot be satisfied by selection trace, material preview, typing display, document trace UI, or existing quantitative execution;
- the exact source unit contract from `L3MaterialSnapshot.source_shape == "aps_content_document"` and `L3AnalysisUnit.analysis_modality == "qualitative"`;
- the exact APS document identity requirements, including `content_id`, `content_contract_id`, `chunking_contract_id`, and linkage/target/run authority when present;
- the exact chunk ordering, windowing, limit, empty-chunk, missing-linkage, missing-text, page-range, and quality-status rules;
- the exact citation/trace requirements for chunk refs, page refs, accession number, content units ref, normalized text ref, and visual page refs;
- the exact owner service or module and whether `backend/app/services/layer3_pass_entry.py` is extended in place or composed around by a separate qualitative owner;
- the exact result schema, result status vocabulary, caveat/finding terminology, review semantics, and downstream package compatibility;
- tests proving qualitative APS execution cannot accidentally reuse `DatasetVersion` quantitative execution or `run_analysis(..., dataset_version_id=...)`;
- tests proving missing chunks, stale snapshots, wrong source shape, wrong modality, wrong analysis set, malformed request fields, duplicate idempotency keys, and unsupported engine/method choices fail closed.

## Non-Goals

This freeze does not admit:

- qualitative execution implementation;
- qualitative associated-cohort execution;
- hybrid, comparative, cross-modal, RAG, vector, LLM, agent, DAG, queue, retry, cancel, or recovery behavior;
- using `DatasetVersion`, aligned-wide-table materialization, or existing wrapped quantitative `run_analysis(...)` as the qualitative APS document execution engine;
- source ingestion/upload/local-directory expansion;
- document trace rendering changes or native PDF overlay changes;
- `/review/layer3` rendered controls;
- package construction, package-review submit, handoff/export, APS handoff dispatch, external export/download, same-origin delivery, signed references, provider/public URLs, connector/destination dispatch, or package payload mutation;
- schema/model/migration changes;
- runtime snapshot DB writes;
- full mockup activation.

## Required Future Implementation Scope

A future implementation-entry freeze must name:

- exact execution mode: `single_aps_doc_qualitative_pass`;
- exact service seam and whether it extends or bypasses `layer3_pass_entry.py`;
- exact request shape and forbidden request fields;
- exact response shape and response-safe provenance fields;
- exact durable state rows, if any; if new rows are required, the freeze must name model/migration ownership before code;
- exact idempotency and stale-authority behavior;
- exact result-review and package compatibility behavior;
- exact UI behavior if rendered controls are changed;
- exact browser proof if rendered controls or document trace views change;
- exact focused backend tests and no-go leakage tests.

## Stop Conditions

Stop before implementation if the intended change needs:

- a qualitative engine that is not bounded to one APS content document;
- source ingestion changes or document re-processing;
- a schema/model/migration change not named by the future freeze;
- `DatasetVersion` or aligned-wide-table conversion as a shortcut for qualitative document chunks;
- client-supplied document text, local paths, raw provider paths, connector ids, destination ids, URLs, package bytes, model prompts, or execution flags;
- RAG/vector/LLM behavior without a separate governance freeze;
- document trace or `/review/layer3` rendered changes without headed and headless browser proof;
- package/handoff/export/provider/connector behavior as a side effect;
- a claim that docs `25`/`27`, PR `#513`, or current APS content-document trace support already made qualitative execution live.

## Proof Required For A Later Implementation

The first implementation PR must prove:

- `aps_content_document` selection, material preview, Gate B snapshot, and Gate C qualitative typing remain unchanged unless explicitly governed;
- qualitative APS execution is disabled by default outside the exact `single_aps_doc_qualitative_pass` path;
- qualitative-only sets no longer fail closed only for the single admitted path, while all other qualitative/hybrid/cohort paths still fail closed;
- no `DatasetVersion` row, aligned-wide-table materialization, or wrapped quantitative `run_analysis(...)` call is used for APS document execution;
- result payloads bind to exact session, material snapshot, analysis unit, analysis set, content document, chunk ids, linkage refs, and trace refs;
- missing/stale/wrong authority fails closed without creating partial result/package/handoff/export state;
- no local filesystem path, provider credential, connector secret, destination secret, package payload byte, raw prompt, or raw provider object key leaks to API/UI responses or audit payloads;
- existing provider/public URL, connector/destination dispatch, durable signed-reference, same-origin delivery, package/handoff/export, quantitative execution, and UI behavior remain unchanged.
