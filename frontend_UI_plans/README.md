# NRC APS UI Planning Set

This folder now contains the retained design and implementation-reference documents for the NRC APS review UI surface.

## Purpose

The retained files here are the UI-facing planning references for:

- the canonical NRC APS pipeline shape
- the internal review UI data contract
- node/artifact mapping and reviewability rules
- validation expectations for the review surface
- the separate document-trace workspace for run-scoped source-to-extraction inspection
- the separate workbench-compare workspace for same-corpus baseline, Candidate A, and Candidate B comparison

These files remain useful as design and maintenance references even though the separate Jules/Antigravity bake-off packet is no longer part of the active repo surface.

## Canonical Source Of Truth

For the live UI and API behavior, the canonical implementation source of truth is in the root repo backend surface:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\main.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\api\review_nrc_aps.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\schemas\review_nrc_aps.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\services\review_nrc_aps_catalog.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\services\review_nrc_aps_runtime.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\services\review_nrc_aps_document_trace.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\index.html`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\review.css`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\review.js`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\document_trace.html`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\document_trace.css`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\document_trace.js`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\workbench_compare.html`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\workbench_compare.css`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\workbench_compare.js`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\vendor\`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\services\review_nrc_aps_graph.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\services\review_nrc_aps_overview.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\services\review_nrc_aps_tree.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\services\review_nrc_aps_details.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\services\review_nrc_aps_workbench_compare.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_api.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_document_trace_api.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_document_trace_service.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_document_trace_page.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_workbench_compare_api.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_workbench_compare_service.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_workbench_compare_page.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\tools\seed_wb_compare.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\tests\test_seed_wb_compare.py`

The files in this folder are reference material, not the live implementation surface.

Important runtime-fixture note:

- Several retained docs in this folder cite March 2026 `lc_e2e` runtime examples under `backend\app\storage_test_runtime\lc_e2e\...`.
- The root-local branch now carries an adopted review/runtime fixture at `backend\app\storage_test_runtime\lc_e2e\20260327_062011`.
- That adopted runtime now backs the validate-only root T8 review/document-trace bundle.
- Historical runtime references in this folder remain historical unless a given doc explicitly says it was revalidated against the adopted root-local runtime.

Important implementation-scope note:

- the live document-trace implementation currently ships the page shell, document selector, trace manifest, source stream, diagnostics, normalized-text, indexed-chunks, and extracted-units surfaces
- the retained planning docs still describe a broader downstream-usage concept, but current live root implementation only carries that as an unavailable manifest tab placeholder, not as a shipped API route
- the workbench-compare planning docs in this folder now describe the separate shipped compare page and compare API family; they still do not revise the single-run contract of the shipped review page or document-trace page

## Retained Documents

- `nrc_aps_review_ui_spec.md`
  - primary UI/product specification
- `nrc_aps_review_ui_data_contract.md`
  - internal read-only review API contract reference
- `nrc_aps_review_ui_open_decisions.md`
  - frozen defaults and implementation discretion notes
- `nrc_aps_review_ui_implementation_blueprint.md`
  - repo-fit module/layout blueprint for the review UI
- `nrc_aps_review_ui_canonical_graph_registry.md`
  - canonical stage/node/edge registry and projection intent
- `nrc_aps_review_ui_mapping_and_reviewability_rules.md`
  - node/file mapping and reviewability rules
- `nrc_aps_review_ui_dependency_and_asset_strategy.md`
  - frontend dependency and asset strategy
- `nrc_aps_review_ui_validation_plan.md`
  - review-UI validation expectations
- `nrc_aps_review_ui_example_payloads.md`
  - example payloads derived from the golden run
- `nrc_aps_document_trace_ui_spec.md`
  - product specification for the separate run-scoped document-trace workspace
- `nrc_aps_document_trace_ui_data_contract.md`
  - additive read-only route and payload plan for the document-trace workspace
- `nrc_aps_document_trace_ui_implementation_blueprint.md`
  - repo-fit module, file, and phase blueprint for implementing document trace
- `nrc_aps_document_trace_ui_validation_plan.md`
  - validation requirements for document-trace behavior, safety, and regression control
- `nrc_aps_document_trace_ui_phase_partition_plan.md`
  - bounded Antigravity-oriented implementation phase partition for document trace
- `bbox_overlay_execution_plan.md`
  - bounded execution plan for the document-trace bbox overlay addendum
- `bbox_overlay_implementation_prompt.txt`
  - implementation-pass prompt for the bbox overlay addendum
- `wb-compare-spec.md`
  - product specification for a separate workbench compare workspace across baseline, Candidate A, and Candidate B
- `wb-compare-contract.md`
  - additive backend compare API and compare-model contract for the workbench workspace
- `wb-compare-blueprint.md`
  - repo-fit module, route, and implementation blueprint for the workbench compare lane
- `wb-compare-validation.md`
  - validate-only test and operator verification plan for the workbench compare workspace
- `nrc_aps_review_ui_startup_and_smoke_test.md`
  - operator startup and smoke-test guide for the review UI, document-trace, and workbench-compare surfaces
- `nrc_aps_frontend_ui_operator_validation_guide.md`
  - practical end-to-end validation guide for the current review UI, document-trace, and workbench-compare surfaces
- `nrc_aps_runtime_db_reconceptualization_and_next_steps.md`
  - current-state reconceptualization of the NRC APS runtime DB model and the recommended next implementation order

## Archived Bake-Off Material

The retired Jules/Antigravity bake-off artifacts, prompts, mirrors, and workspaces were moved out of the live planning surface to:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\archive\files_to_be_trashed\2026-03-28_bakeoff_closeout\`

That archive area now holds the obsolete bake-off packet files, agent workspaces, mirror repos, and related worktrees that are no longer intended to drive active implementation.
