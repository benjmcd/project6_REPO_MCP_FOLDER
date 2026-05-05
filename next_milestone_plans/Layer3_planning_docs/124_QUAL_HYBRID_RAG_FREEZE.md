# Layer 3 Qualitative Hybrid RAG Freeze

Status: qualitative/hybrid/RAG implementation-entry freeze for single APS-document-only runtime on branch `codex/l3-qual-hybrid-rag-freeze` from `project6-origin/main=c134b581`.

This artifact freezes the current qualitative execution boundary and prevents broad qualitative, hybrid, or RAG/vector execution from being inferred from mockups, planning prose, progress summaries, or the already-live single APS-document qualitative pass. It does not add an execution engine, route, model, migration, package/handoff/export behavior, source ingestion, connector/destination dispatch, provider/public URL behavior, hidden LLM planning, full mockup activation, or authentication/security work.

## Authority Snapshot

- authority_worktree: `C:\Users\benny\Downloads\worktree_for_audits`
- implementation_branch: `codex/l3-qual-hybrid-rag-freeze`
- baseline_ref: `project6-origin/main`
- baseline_commit: `c134b581`
- owner service: `backend/app/services/layer3_qual_aps_execution.py`
- proof test: `backend/tests/test_layer3_qual_aps_execution.py`
- progress checker: `tools/l3-progress-check.py`
- source gates: `105_deferred-gates.md`, `114_QUAL_APS_EXEC_FREEZE.md`, `115_QUAL_APS_EXEC_CONTRACT.md`, `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md`, `118_L3_GOAL_AUDIT.md`, `119_L3_QUAL_APS_EXEC_ENTRY_FREEZE.md`, and `120_L3_CLOSEOUT.md`

## Decision

The selected qualitative/hybrid/RAG mode is exactly:

- selected_qualitative_hybrid_rag_mode: `single_aps_doc_qualitative_pass_only`

Only the already-admitted execution lane remains available:

- `single_aps_doc_qualitative_pass`

The following runtime capabilities remain unsupported and must fail closed:

- `broad_qualitative_execution`
- `qualitative_associated_cohort_execution`
- `comparative_qualitative_execution`
- `cross_document_synthesis`
- `hybrid_execution`
- `rag_vector_retrieval`
- `hidden_llm_planning`
- `qualitative_package_handoff_export`

No broad qualitative execution, qualitative cohort execution, comparative execution, cross-document synthesis, hybrid execution, RAG/vector retrieval, hidden LLM planning, qualitative package/handoff/export, source widening, connector/destination dispatch, or package mutation/reconstruction is admitted.

## Runtime Contract

`backend/app/services/layer3_qual_aps_execution.py` owns a response-safe contract:

- schema: `layer3.qualitative_hybrid_rag_boundary_contract.v1`
- mode: `single_aps_doc_qualitative_pass_only`
- admitted_execution_modes: `["single_aps_doc_qualitative_pass"]`
- single_aps_doc_qualitative_execution_enabled: `True`
- broad_qualitative_execution_enabled: `False`
- qualitative_associated_cohort_execution_enabled: `False`
- comparative_qualitative_execution_enabled: `False`
- cross_document_synthesis_enabled: `False`
- hybrid_execution_enabled: `False`
- rag_vector_retrieval_enabled: `False`
- hidden_llm_planning_enabled: `False`
- qualitative_package_handoff_export_enabled: `False`
- source_widening_enabled: `False`
- connector_destination_dispatch_enabled: `False`
- package_mutation_reconstruction_enabled: `False`
- requires_later_freeze: `True`

The runtime contract is proof metadata only. It does not create a `L3PassRun`, create an `AnalysisRun`, write a package, write an output artifact, start source retrieval, call a connector, invoke an LLM provider, or add a rendered UI control.

## Positive Invariants

- The exact admitted qualitative runtime remains `single_aps_doc_qualitative_pass`.
- `qualitative_hybrid_rag_boundary_contract()` exposes the single-pass mode and every blocked qualitative/hybrid/RAG family.
- `STATE_ACTION_ADMITTED_CAPABILITIES` continues to admit only `single_aps_doc_qualitative_execution` for qualitative execution.
- `STATE_ACTION_DEFERRED_CAPABILITIES` continues to keep `broad_qualitative_execution`, `hybrid_execution`, `rag_vector_retrieval`, and `hidden_llm_planning` admitted false.
- Workbench feature flags continue to report `single_aps_doc_qualitative_execution` as true and `broad_qualitative_execution`, `hybrid_execution`, and `rag_vector_retrieval` as false.
- `tools/l3-progress-check.py` fails if the owner service, contract helper, forbidden runtime fields, or doc freeze terms drift.

## Negative Invariants

This freeze must prove no accidental:

- broad qualitative execution
- qualitative cohort execution
- comparative qualitative execution
- cross-document synthesis
- hybrid execution
- RAG/vector retrieval or source expansion
- hidden LLM planning
- qualitative package/handoff/export
- source/schema/runtime widening
- `L3PassRun` creation by the contract helper
- `AnalysisRun` creation by the contract helper
- output/package/handoff/export artifact creation by the contract helper
- connector/destination dispatch
- provider/public URL support
- frontend-only durable state
- package mutation/reconstruction
- full mockup activation
- authentication/security scope reopening

## Test And Proof Plan

Required local proof:

- `python -m py_compile .\backend\app\services\layer3_qual_aps_execution.py .\tools\l3-progress-check.py`
- `python -m pytest .\backend\tests\test_layer3_qual_aps_execution.py -q`
- `python .\tools\l3-progress-check.py`
- `git diff --check`

Optional regression proof before merge:

- `python -m pytest .\backend\tests\test_layer3_api.py .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_qual_aps_execution.py -q -k "single_aps_doc_qualitative or broad_qualitative or hybrid or rag_vector"`

## Acceptance Criteria

This slice is accepted only when:

- this file exists and names `single_aps_doc_qualitative_pass_only`;
- `backend/app/services/layer3_qual_aps_execution.py` exposes `qualitative_hybrid_rag_boundary_contract()` with the exact single-pass admission and all broad qualitative/hybrid/RAG flags false;
- `backend/tests/test_layer3_qual_aps_execution.py` proves the contract and blocked runtime fields;
- `tools/l3-progress-check.py` requires this freeze, the contract helper, the proof test, and the blocked capability families;
- `105_deferred-gates.md`, `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md`, `118_L3_GOAL_AUDIT.md`, and `120_L3_CLOSEOUT.md` reference this freeze without claiming broad qualitative/hybrid/RAG execution;
- required local proof commands pass.
