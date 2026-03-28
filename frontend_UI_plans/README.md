# NRC APS Planning And Bake-Off Set

This folder contains the planning/specification set for the NRC APS review UI work and the later APS retrieval-plane bake-off rounds.

## Purpose

The goal of this planning set is to define a repo-fit frontend review surface that lets a user:

- inspect the canonical NRC APS pipeline as a stable system view
- inspect a specific NRC APS run as a realized artifact graph
- navigate between pipeline stages, persisted files, and run metadata without mutating any runtime or report state

## Canonical Source Of Truth

For this planning set, the authority hierarchy is:

1. live backend/API/runtime surfaces in the root repo
2. current root control/status docs
3. design references used only for layout/interaction inspiration

Primary live authority surfaces:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\main.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\api\router.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\docs\nrc_adams\nrc_aps_authority_matrix.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\docs\nrc_adams\nrc_aps_status_handoff.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\storage_test_runtime\lc_e2e\20260327_062011\local_corpus_e2e_summary.json`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\storage_test_runtime\lc_e2e\20260327_062011\`

Design references:

- `C:\Users\benny\Downloads\frontend_UI_UX_planning_context_reference_ref1.drawio.svg`
- `C:\Users\benny\Downloads\frontend_UI_UX_planning_context_reference_ref2.drawio.svg`

## Files In This Planning Set

- `nrc_aps_review_ui_spec.md`
  - primary product/spec document
- `nrc_aps_review_ui_data_contract.md`
  - additive read-only endpoint and model contract
- `nrc_aps_review_ui_open_decisions.md`
  - frozen defaults and non-critical implementation discretion
- `nrc_aps_review_ui_implementation_blueprint.md`
  - exact repo-fit module/file layout and implementation ownership plan
- `nrc_aps_review_ui_canonical_graph_registry.md`
  - exhaustive canonical NRC APS node registry, edge registry, and view projections
- `nrc_aps_review_ui_mapping_and_reviewability_rules.md`
  - run discovery, reviewability, node-artifact mapping, and mismatch handling rules
- `nrc_aps_review_ui_dependency_and_asset_strategy.md`
  - asset strategy, frontend dependency policy, and serving strategy
- `nrc_aps_review_ui_validation_plan.md`
  - validation matrix, golden fixture usage, and non-regression expectations
- `nrc_aps_review_ui_example_payloads.md`
  - concrete example payloads derived from the verified golden run
- `agent_bakeoff_execution_protocol.md`
  - controlled A/B process for running Jules and Antigravity separately against the same scope
- `agent_bakeoff_local_setup.md`
  - exact local branch/worktree setup, lane paths, and frozen starting commit for the bake-off
- `agent_bakeoff_brief.md`
  - vendor-neutral implementation brief to hand to each agent
- `agent_bakeoff_scope_slice_01.md`
  - first bounded implementation slice for the comparison run
- `agent_bakeoff_rubric.md`
  - scoring rubric for comparing the two outputs on equal terms
- `agent_bakeoff_submission_checklist.md`
  - required delivery artifacts each agent run must provide for evaluation
- `agent_bakeoff_prompt_jules.md`
  - ready-to-paste Jules prompts for the dry-run round and Slice 01 implementation round
- `agent_bakeoff_prompt_antigravity.md`
  - ready-to-paste Antigravity prompts for the dry-run round and Slice 01 implementation round
- `agent_bakeoff_local_setup_phase1.md`
  - exact local lane mapping for the Phase1 retrieval-plane bake-off
- `agent_bakeoff_phase1_brief.md`
  - vendor-neutral brief for the Tier1 retrieval-plane Phase1A bake-off slice
- `agent_bakeoff_phase1_scope.md`
  - strict bounded scope for the first retrieval-plane implementation round
- `agent_bakeoff_phase1_implementation_blueprint.md`
  - repo-fit file/module ownership plan for the retrieval-plane slice
- `agent_bakeoff_phase1_validation_plan.md`
  - required validation and non-regression checks for the retrieval-plane slice
- `agent_bakeoff_phase1_submission_checklist.md`
  - required delivery artifacts for the retrieval-plane bake-off round
- `agent_bakeoff_phase1_rubric.md`
  - scoring rubric for the retrieval-plane bake-off round
- `agent_bakeoff_prompt_antigravity_phase1.md`
  - ready-to-paste Antigravity prompts for the retrieval-plane dry run and implementation round
- `agent_bakeoff_prompt_jules_phase1.md`
  - ready-to-paste Jules GitHub-mirror prompts for the retrieval-plane dry run and implementation round
- `agent_bakeoff_local_setup_phase1b.md`
  - exact local lane mapping for the Phase1B operator retrieval read-path bake-off
- `agent_bakeoff_phase1b_brief.md`
  - vendor-neutral brief for the Tier1 retrieval-plane Phase1B slice
- `agent_bakeoff_phase1b_scope.md`
  - strict bounded scope for the operator-only retrieval read-path round
- `agent_bakeoff_phase1b_implementation_blueprint.md`
  - repo-fit file and module ownership plan for the Phase1B slice
- `agent_bakeoff_phase1b_validation_plan.md`
  - required validation and non-regression checks for the Phase1B slice
- `agent_bakeoff_phase1b_submission_checklist.md`
  - required delivery artifacts for the Phase1B bake-off round
- `agent_bakeoff_phase1b_rubric.md`
  - scoring rubric for the Phase1B bake-off round
- `agent_bakeoff_prompt_antigravity_phase1b.md`
  - ready-to-paste Antigravity prompts for the Phase1B dry run and implementation round
- `agent_bakeoff_prompt_jules_phase1b.md`
  - ready-to-paste Jules prompts for the Phase1B dry run and implementation round
- `agent_bakeoff_local_setup_phase1c.md`
  - exact local lane mapping for the Phase1C validate-only cutover-proof bake-off
- `agent_bakeoff_phase1c_brief.md`
  - vendor-neutral brief for the Tier1 retrieval-plane Phase1C slice
- `agent_bakeoff_phase1c_scope.md`
  - strict bounded scope for the validate-only public cutover-proof round
- `agent_bakeoff_phase1c_implementation_blueprint.md`
  - repo-fit file and module ownership plan for the Phase1C slice
- `agent_bakeoff_phase1c_validation_plan.md`
  - required validation and non-regression checks for the Phase1C slice
- `agent_bakeoff_phase1c_submission_checklist.md`
  - required delivery artifacts for the Phase1C bake-off round
- `agent_bakeoff_phase1c_rubric.md`
  - scoring rubric for the Phase1C bake-off round
- `agent_bakeoff_prompt_antigravity_phase1c.md`
  - ready-to-paste Antigravity prompts for the Phase1C dry run and implementation round
- `agent_bakeoff_prompt_jules_phase1c.md`
  - ready-to-paste Jules prompts for the Phase1C dry run and implementation round
- `agent_bakeoff_local_setup_phase1d.md`
  - exact local lane mapping for the Phase1D public run-scoped retrieval cutover bake-off
- `agent_bakeoff_phase1d_brief.md`
  - vendor-neutral brief for the Tier1 retrieval-plane Phase1D slice
- `agent_bakeoff_phase1d_scope.md`
  - strict bounded scope for the public run-scoped cutover round
- `agent_bakeoff_phase1d_implementation_blueprint.md`
  - repo-fit file and module ownership plan for the Phase1D slice
- `agent_bakeoff_phase1d_validation_plan.md`
  - required validation and non-regression checks for the Phase1D slice
- `agent_bakeoff_phase1d_submission_checklist.md`
  - required delivery artifacts for the Phase1D bake-off round
- `agent_bakeoff_phase1d_rubric.md`
  - scoring rubric for the Phase1D bake-off round
- `agent_bakeoff_prompt_antigravity_phase1d.md`
  - ready-to-paste Antigravity prompts for the Phase1D dry run and implementation round
- `agent_bakeoff_prompt_jules_phase1d.md`
  - ready-to-paste Jules prompts for the Phase1D dry run and implementation round
- `agent_workspaces\jules\`
  - dedicated bake-off workspace/output directory for Jules
- `agent_workspaces\antigravity\`
  - dedicated bake-off workspace/output directory for Antigravity

## Planning Boundaries

- This planning set is NRC APS specific.
- This planning set assumes a read-only UI.
- This planning set does not authorize implementation changes by itself.
- This planning set does not authorize file preview, run execution, polling, or mutation as part of v1.

## Current Bake-Off Status

There are now five distinct bake-off packets in this folder:

- the historical Slice 01 review-UI packet
- the historical Phase1A APS Tier1 retrieval-plane packet
- the historical Phase1B APS Tier1 operator retrieval read-path packet
- the historical Phase1C APS Tier1 validate-only cutover-proof packet
- the current Phase1D APS Tier1 public run-scoped cutover packet

Use the Phase1D packet for the next retrieval bake-off round. Do not reuse the Slice 01, Phase1A, Phase1B, or Phase1C prompts for the Phase1D round.

For both Jules and Antigravity, start a brand-new session or task for each new milestone round. Do not reuse an older Slice 01, Phase1A, Phase1B, or Phase1C thread and try to steer it onto Phase1D.

## Carry-Forward QA Guardrails

The current review UI baseline has already been live-validated. Those learnings must be carried forward when planning later milestones:

- verified pass conditions:
  - graph renders
  - filesystem tree expands
  - file click opens the details drawer
  - default run selection is correct
- known non-blocking debt:
  - graph-node-to-tree visual reveal is only partial
  - the drawer overlays the tree instead of preserving a visible third-pane feel
  - header/button styling still needs polish

Those known UI issues are not blockers for the retrieval-plane bake-off. They are regression guardrails:

- later milestones must not break the verified pass conditions
- do not opportunistically broaden a backend retrieval slice into UI redesign work unless the prompt explicitly asks for that

## Active Phase1D Packet

- `agent_bakeoff_local_setup_phase1d.md`
- `agent_bakeoff_phase1d_brief.md`
- `agent_bakeoff_phase1d_scope.md`
- `agent_bakeoff_phase1d_implementation_blueprint.md`
- `agent_bakeoff_phase1d_validation_plan.md`
- `agent_bakeoff_phase1d_submission_checklist.md`
- `agent_bakeoff_phase1d_rubric.md`
- `agent_bakeoff_prompt_antigravity_phase1d.md`
- `agent_bakeoff_prompt_jules_phase1d.md`
