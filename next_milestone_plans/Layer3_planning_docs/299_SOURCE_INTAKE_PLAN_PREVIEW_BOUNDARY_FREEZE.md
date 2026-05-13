# 299 Source Intake Plan Preview Boundary Freeze

## Status

Status: planning/control freeze for `source_intake_plan_preview_boundary`.

Implementation branch: `codex/l3-source-intake-plan-preview-freeze`.

Date: 2026-05-13.

Runtime predecessor: `source_intake_gate_c_typing_entry`.

Governing current-main predecessor docs: `297_SOURCE_INTAKE_GATE_C_TYPING_ENTRY_FREEZE.md` and `298_SOURCE_INTAKE_GATE_C_TYPING_ENTRY.md`.

## Selected Boundary

Selected runtime family: `source_breadth_runtime`.

Selected runtime mode: `source_intake_plan_preview_boundary`.

Named operator/product use case: `operator_uploaded_single_source_previews_plan_after_gate_c_typing`.

Canonical source of truth: server-owned Gate C state derived from `L3SourceIntakeRecord`, specifically finalized `L3Session` state plus `L3AnalysisSet`, `L3AnalysisUnit`, and `L3MaterialSnapshot` rows whose snapshot `source_shape` is `operator_uploaded_single_source` and whose analysis modality is qualitative.

Admitted route surface for the future implementation: the existing `POST /api/v1/layer3/plan/preview` path may return preview-only plan material for a session whose source-intake Gate C typing has already committed.

This freeze creates no runtime behavior by itself. It only authorizes the next code-bearing slice to add the narrow owner-service plan-preview admission rule for source-intake qualitative single-item sets.

## Repo-Confirmed Failure Boundary

Current main now admits source-intake through Gate B and Gate C typing:

- Gate B can create server-owned `L3Session`, `L3SelectionManifest`, `L3Descriptor`, and `L3MaterialSnapshot` state for `operator_uploaded_single_source`.
- Gate C typing can materialize source-intake as qualitative `document_chunks`, with an atomic analysis unit and no `AnalysisRun` side effect.

Current plan preview is a separate boundary. `backend/app/services/layer3_pass_entry.py` classifies analysis sets for plan preview in `_classify_sets`. It admits:

- quantitative `dataset_version` single-item sets;
- quantitative dataset-version associated cohorts when the cohort input can be prepared;
- qualitative APS content-document single-item sets through `qualitative_aps_candidate_exclusion_reason`.

A source-intake qualitative singleton is not the same authority as an APS content document. The current qualitative path is APS-specific and rejects non-APS content-document source shapes. Therefore source-intake plan preview requires a separate named admission rule rather than being inferred from Gate C typing.

## Future Implementation Contract

The future implementation may add one source-intake plan-preview admission path with these semantics:

- Input authority must be existing committed Gate C state: `L3AnalysisSet`, `L3AnalysisUnit`, and `L3MaterialSnapshot` rows for `operator_uploaded_single_source`.
- The analysis set must be `single_item`.
- The analysis unit must be `atomic` and `qualitative`.
- The analysis unit must reference exactly one source-intake material snapshot.
- The snapshot identity must include a source-intake record identifier or candidate identity trace from Gate B.
- The preview must remain preview-only; it must not create `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, `AnalysisArtifact`, `L3OutputPackage`, package review state, connector dispatch state, RAG/vector state, provider URL state, local file authority, or auth/security state.
- The preview must use a source-intake-specific pass scope and source gate, not the APS qualitative source gate.
- Plan approval remains blocked until a separate freeze admits source-intake plan approval semantics.

The future implementation must preserve existing plan-preview guards:

- fail closed when Gate C typing is not committed;
- fail closed when no analysis sets exist;
- fail closed when an analysis plan or pass run already exists;
- fail closed when plan revision control requires recovery or refresh;
- fail closed for unsupported adjacent qualitative source shapes.

## Required Future Proof

The next implementation must include targeted backend proof for:

- `operator_uploaded_single_source` Gate C output produces one preview-only planned pass from the existing plan-preview owner service.
- The planned pass uses a source-intake-specific pass scope and source gate.
- The plan preview source summary reports `operator_uploaded_single_source`.
- The preview hash is deterministic for the server-owned source-intake Gate C basis.
- Plan preview creates no `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, `AnalysisArtifact`, `L3OutputPackage`, connector dispatch, provider URL, RAG/vector, local path/local-directory, auth/security, or package state.
- Source-intake plan approval remains blocked or unadmitted unless a later freeze selects it.
- APS qualitative behavior and quantitative dataset-version behavior remain unchanged.
- Unsupported adjacent qualitative source shapes remain blocked.

If rendered controls are changed in the implementation, headed and headless browser proof must both exercise the changed plan-preview path. If no rendered controls change, backend/API proof is sufficient.

## Blocked Scope

The following remain explicitly blocked:

- plan approval for source-intake
- execution start
- package construction or mutation
- handoff/export prepare or dispatch
- connector/destination dispatch
- provider/private signed URL prepare
- web connector retrieval
- RAG/vector indexing
- generic source upload
- broad file upload
- local path or local directory authority
- model or migration changes
- new backend route
- rendered UI changes unless separately necessary and proven headed/headless
- auth/security behavior
- non-text binary preview
- frontend-only durable authority

## Next Allowed Action

Next allowed code-bearing action: `implement_source_intake_plan_preview_boundary` only.

Stop condition for the next pass: current-main proof that source-intake Gate C qualitative output can produce preview-only plan material from server-owned authority, with targeted tests, no downstream side effects, no unresolved code-review comments, and no plan approval/execution/package widening.
