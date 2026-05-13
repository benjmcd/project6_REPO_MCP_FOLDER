# 297 Source Intake Gate C Typing Entry Freeze

## Status

Status: planning/control freeze for `source_intake_gate_c_typing_entry`.

Implementation branch: `codex/l3-source-intake-gate-c-freeze`.

Date: 2026-05-13.

Runtime predecessor: `source_intake_gate_b_rendered_admission_controls`.

Governing current-main predecessor docs: `293_SOURCE_INTAKE_GATE_B_MATERIAL_ADMISSION_FREEZE.md`, `294_SOURCE_INTAKE_GATE_B_MATERIAL_ADMISSION_RUNTIME.md`, `295_SOURCE_INTAKE_GATE_B_RENDERED_ADMISSION_CONTROLS_FREEZE.md`, and `296_SOURCE_INTAKE_GATE_B_RENDERED_ADMISSION_CONTROLS.md`.

## Selected Boundary

Selected runtime family: `source_breadth_runtime`.

Selected runtime mode: `source_intake_gate_c_typing_entry`.

Named operator/product use case: `operator_uploaded_single_source_commits_gate_c_typing`.

Canonical source of truth: server-owned Gate B state derived from `L3SourceIntakeRecord`, specifically `L3Session`, latest `L3SelectionManifest`, `L3Descriptor`, and `L3MaterialSnapshot` rows whose snapshot `source_shape` is `operator_uploaded_single_source` and whose source identity points back to the admitted source-intake record.

Admitted route surface for the future implementation: `POST /api/v1/layer3/gate-c/preview` with `commit_typing=true` for an existing Gate B session produced by `POST /api/v1/layer3/gate-b/decision` from a server-previewed `mat-source_intake_record-` candidate.

This freeze creates no runtime behavior by itself. It only authorizes the next code-bearing slice to add the narrow owner-service typing rule and API proof required for `operator_uploaded_single_source` to become a committed Gate C qualitative typing entry.

## Repo-Confirmed Failure Boundary

Live Gate B state already admits source-intake material into the normal Layer 3 flow: the current Gate B path creates `L3Session`, `L3SelectionManifest`, descriptors, and `L3MaterialSnapshot` rows for approved material, and the rendered workbench can reach the existing Gate C controls after #879/#880.

Live Gate C typing does not yet admit source-intake material. `backend/app/services/layer3_typing_entry.py` currently supports only these `source_shape` values in `SUPPORTED_TYPING_RULES`:

- `dataset_version`
- `aps_content_document`

Therefore a session whose material snapshot has `source_shape` `operator_uploaded_single_source` is not a proven successful Gate C typing path. The next implementation must solve exactly this unsupported-shape boundary; it must not skip ahead to plan preview, execution, package construction, connector dispatch, RAG/vector indexing, or provider URL behavior.

## Future Implementation Contract

The future implementation may add one typing rule for `operator_uploaded_single_source` with these semantics:

- `planning_shape_family`: `document_chunks`
- `candidate_modalities`: `qualitative`
- `chosen_modality`: `qualitative`
- `unit_kind`: `atomic`
- `confidence_basis`: frozen source-intake text-document default, not browser state or operator override

The implementation must prove that the source-intake Gate C commit is anchored to durable server rows already created by Gate B. The browser may initiate the request, but browser state must remain transient only and must not become durable authority.

The implementation must preserve existing Gate C invariants:

- require a finalized `L3Session`
- require the latest server-owned `L3SelectionManifest`
- fail closed when no `L3MaterialSnapshot` exists
- fail closed when typing records, analysis units, analysis groups, or analysis sets already exist for the session
- create only `L3TypingRecord`, `L3AnalysisUnit`, `L3AnalysisGroup`, and `L3AnalysisSet` rows needed for Gate C typing
- leave plan approval, execution start, package/handoff/export, connector/destination dispatch, RAG/vector retrieval, provider/private URL behavior, model/migration changes, and auth/security behavior out of scope

## Required Future Proof

The next implementation must include targeted backend proof for:

- `operator_uploaded_single_source` material snapshot commits to a qualitative `document_chunks` Gate C typing record.
- The resulting analysis unit remains atomic and refers to the source-intake material snapshot id.
- The typing basis records `source_shape` `operator_uploaded_single_source`, `planning_shape_family` `document_chunks`, and a source-intake-specific rule version or confidence basis.
- Replaying Gate C commit after typing exists fails closed through the existing duplicate typing guard.
- Sessions without source-intake material snapshots still fail closed as before.
- Unsupported adjacent source shapes remain unsupported unless separately admitted by a future freeze.
- Gate C typing creates no `L3PassRun`, `AnalysisRun`, `AnalysisArtifact`, `L3OutputPackage`, package review/submit state, connector dispatch receipt, provider URL, local file authority, RAG/vector index, or auth/security state.

If rendered controls are changed in the implementation, headed and headless browser proof must both exercise the changed Gate C path. If no rendered controls change, browser proof is not required for this freeze; backend/API proof is sufficient.

## Blocked Scope

The following remain explicitly blocked:

- generic source upload
- broad file upload
- local path or local directory authority
- web connector retrieval
- RAG/vector indexing
- plan preview behavior beyond normal Gate C readiness
- plan approval
- execution start
- package construction or mutation
- handoff/export prepare or dispatch
- connector/destination dispatch
- provider/private signed URL prepare
- model or migration changes
- new backend route
- rendered UI changes unless separately necessary and proven headed/headless
- auth/security behavior
- frontend-only durable authority
- non-text binary preview

## Next Allowed Action

Next allowed code-bearing action: `implement_source_intake_gate_c_typing_entry` only.

Stop condition for the next pass: current-main proof that `operator_uploaded_single_source` can commit Gate C qualitative typing from existing Gate B server authority, with targeted tests and no unresolved code-review comments.
