# Agent Bake-Off Brief: APS Tier1 Retrieval Plane Phase1A

## 1. Objective

Implement a bounded first slice of the APS Tier1 retrieval-plane Phase1 plan.

This is a backend-first additive slice. It is not a UI redesign, not a public read-path cutover, and not a semantic retrieval buildout.

## 2. Canonical Source Of Truth

Treat the following as the authority for this bake-off round:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\AGENTS.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\next_milestone_plans\2026-03-27_aps_tier1_retrieval_plane_phase1.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\docs\nrc_adams\nrc_aps_authority_matrix.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\docs\nrc_adams\nrc_aps_reader_path.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\docs\nrc_adams\nrc_aps_status_handoff.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\docs\postgres\postgres_status_handoff.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\core\config.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\models\models.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\services\nrc_aps_content_index.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\services\nrc_aps_artifact_ingestion.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\alembic\versions\0008_aps_content_index_tables.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\alembic\versions\0009_aps_document_processing_metadata.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\alembic\versions\0010_visual_page_refs_json.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_bakeoff_phase1_scope.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_bakeoff_phase1_implementation_blueprint.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_bakeoff_phase1_validation_plan.md`

## 3. Carried-Forward UI QA Guardrails

The current review UI baseline has already been verified and must not be regressed if this milestone touches any shared review/UI code.

Verified baseline behaviors:

- the NRC APS review graph renders
- the filesystem tree expands
- file selection opens the details drawer
- default run selection resolves correctly

Known non-blocking debt that is not part of this bake-off slice:

- graph-node-to-tree visual reveal is still only partial
- the drawer overlays the tree rather than preserving a dedicated third-pane feel
- header and toggle styling still needs polish

Implication for this round:

- do not broaden this retrieval-plane milestone into UI cleanup
- if a shared change unexpectedly touches the review UI surface, preserve the verified baseline behaviors above

## 4. Repo-Fit Constraints

You must preserve all of the following:

- root repo guardrails from `AGENTS.md`
- canonical APS evidence truth remains in `ApsContentDocument`, `ApsContentChunk`, and `ApsContentLinkage`
- this slice is additive only
- no default read-path cutover
- no public API behavior changes
- no review-UI redesign
- no schema widening above the retrieval layer
- validate-only semantics remain validate-only and fail closed on empty runtime
- no business artifact generation
- Tier1 PostgreSQL scope must remain explicit; do not assume SQLite-shaped behavior is the design ceiling for this slice

## 5. Explicit Non-Goals

Do not add in this round:

- embeddings
- vector indexes
- semantic extraction
- operator/public retrieval endpoints
- feature-flagged read-path cutover
- changes to evidence-bundle or higher APS artifact contracts
- opportunistic review-UI polishing
- migration of old large local assets or unrelated runtime cleanup

## 6. Working Style Requirements

- prefer the narrowest correct implementation
- keep derivation logic, contract logic, and validation logic separate
- keep the retrieval plane strictly derived from canonical APS truth
- make rebuild scope explicit
- make source-signature derivation explicit
- surface missing or invalid canonical prerequisites as validation failures, not silent fallbacks

## 7. Expected Deliverable Type

This is a code-and-tests deliverable for the bounded Phase1A slice defined in:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_bakeoff_phase1_scope.md`

## 8. Required Submission Material

Your output must satisfy:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_bakeoff_phase1_submission_checklist.md`

That includes explicit discussion of:

- introduced tech debt
- avoided tech debt
- any temporary compromises that would complicate later cutover, validation, or hybrid retrieval work

## 9. Evaluation Standard

Your work will be scored using:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_bakeoff_phase1_rubric.md`

## 10. Completion Standard

At the end of this slice, the implementation should support:

- an additive derived retrieval-plane table/model
- deterministic row derivation from canonical APS truth
- stable source-signature hashing for retrieval rows
- explicit run-scoped rebuild logic
- validate-only parity checks over the derived rows
- focused tests grounded in canonical APS content/linkage truth

This slice is not complete if it only adds schema without derivation or validation logic.
