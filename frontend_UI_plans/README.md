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
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\candidate_b_trace.html`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\candidate_b_trace.css`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\candidate_b_trace.js`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\vendor\`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\services\review_nrc_aps_graph.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\services\review_nrc_aps_overview.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\services\review_nrc_aps_tree.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\services\review_nrc_aps_details.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\services\review_nrc_aps_workbench_compare.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\services\review_nrc_aps_candidate_b_trace.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_api.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_document_trace_api.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_document_trace_service.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_document_trace_page.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_workbench_compare_api.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_workbench_compare_service.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_workbench_compare_page.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_candidate_b_trace_api.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_candidate_b_trace_service.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_candidate_b_trace_page.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\review_browser_fixture.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\review_browser_server.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_browser_server.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\requirements-browser.txt`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\e2e\nrc-aps-review.spec.js`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\playwright.config.js`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.github\workflows\playwright.yml`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\tools\seed_wb_compare.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\tests\test_seed_wb_compare.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\tests\support_nrc_aps_candidate_b_opendataloader.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\tests\test_nrc_aps_candidate_b_opendataloader.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\tools\validate_wb_prep.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\tests\test_validate_wb_prep.py`

The files in this folder are reference material, not the live implementation surface.

For canonical operator bring-up of the shipped review/document-trace/workbench/Candidate B Trace surfaces, start with [docs/nrc_adams/nrc_aps_ui_launch_runbook.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/docs/nrc_adams/nrc_aps_ui_launch_runbook.md).

Important runtime-fixture note:

- Several retained docs in this folder cite March 2026 `lc_e2e` runtime examples under `backend\app\storage_test_runtime\lc_e2e\...`.
- Current clean `main` does not guarantee that a populated local review runtime is already present under the checkout's allowlisted review-runtime roots.
- Treat runtime paths in this folder as operator-provided or historically referenced unless a given doc explicitly says they were revalidated in the current checkout.

Important implementation-scope note:

- the live document-trace implementation currently ships the page shell, document selector, trace manifest, source stream, diagnostics, normalized-text, indexed-chunks, and extracted-units surfaces
- the retained planning docs still describe a broader downstream-usage concept, but current live root implementation only carries that as an unavailable manifest tab placeholder, not as a shipped API route
- the workbench-compare planning docs in this folder now describe the separate shipped compare page and compare API family; they still do not revise the single-run contract of the shipped review page or document-trace page
- Candidate B-specific inspection still ships as the separate additive `Candidate B Trace` page and API family for bundle-scoped ODL inspection; it does not widen the single-run `document-trace` contract. A later explicit runtime-admission reopen now admits Candidate B as the opt-in `document_processing_engine="candidate_b_opendataloader_pdf"` processing path, exposes that engine metadata on the existing review `/runs` selector response, renders Candidate B / OpenDataLoader PDF labels in the existing review and document-trace run selectors plus run identity panels, and exposes admitted Candidate B runtime runs as an explicit Workbench Compare source kind alongside the preserved bundle source path.

Current shipped-baseline note:

- the merged post-PR50 UI baseline is now the reference posture for this folder:
  - `/review/nrc-aps`
  - `/review/nrc-aps/document-trace`
  - `/review/nrc-aps/workbench-compare`
  - `/review/nrc-aps/candidate-b-trace`
- the root repo now also carries repo-native browser regression coverage for that shipped compare + Candidate B Trace flow via:
  - `e2e/nrc-aps-review.spec.js`
  - `playwright.config.js`
  - `.github/workflows/playwright.yml`
  - `backend/tests/review_browser_fixture.py`
  - `backend/tests/review_browser_server.py`
  - `backend/tests/requirements-browser.txt`
- the root repo now also carries fixed-fixture same-checkout prep plus validate-only gates for populated compare, bundle-sourced Candidate B Trace validation, and explicit runtime-sourced Candidate B Compare validation via:
  - `tools/validate_wb_prep.py`
  - `tests/test_validate_wb_prep.py`
- that prep gate fails closed on empty, donor, ambiguous, missing-runtime-run-id, or incoherent same-checkout prep state and should precede populated operator validation
- the preserved bundle-scoped Candidate B Trace path now also includes compare/trace return-context preservation, artifact availability/unavailable-state affordances, and fixture navigation/status over the existing Workbench Compare targets API
- current repo-native browser coverage proves the single-target `Fixture 1 of 1` disabled-navigation state; active multi-fixture Previous/Next navigation requires a prepared state with multiple comparable targets
- future work should start from that shipped posture rather than from pre-compare or pre-trace assumptions
- future work should stay additive and lane-scoped unless a repo-confirmed blocker requires a broader reopen

Ordered next-decision note:

- the repo-native browser regression lane is now landed, and the root Playwright workflow is no longer a placeholder-only scaffold
- future browser work should now be explicit expansion or refinement of the targeted NRC APS coverage, not a rehash of whether the root workflow is authoritative at all
- the current-horizon Candidate B scope decision is now resolved:
  - retain the shipped bundle-scoped compare + Candidate B Trace boundary
  - do not drift into runtime-style admission or selector integration by accident
- only reopen a wider Candidate B runtime-admission program if a concrete operator/product requirement proves the shipped bundle-scoped model insufficient
- that wider program has now been explicitly reopened through processing-engine admission, existing `/runs` runtime metadata, rendered review/document-trace selector visibility, and additive Workbench Compare runtime-source integration; it is not yet Candidate B Trace parity for admitted runtime runs, document-trace parity expansion, DB schema/model/migration work, broad route widening, persistence redesign, or new run-submission UI work
- same-checkout prepared-state workflow hardening is now landed through the validate-only prep gate and canonical prep sequence
- for the preserved bundle-scoped Candidate B Trace path, further operator ergonomics should improve only where justified and should not be described as runtime Candidate B Trace parity
- current `main` also includes the merged planning-only broader-workbench prep packet rooted in `next_milestone_plans/Layer3_planning_docs/24_L3_WB_FREEZE.md` from PR `#165` and `next_milestone_plans/Layer3_planning_docs/26_L3_WB_INPUTS.md` from PR `#168`; that deferred additive lane still does not rename, replace, or activate the currently shipped review/document-trace/workbench/Candidate B surfaces
- documentation closeout is now landed for the active UI/operator front doors:
  - `frontend_UI_plans/README.md` remains the front-door index
  - `docs/nrc_adams/nrc_aps_ui_launch_runbook.md` owns the canonical launch contract
  - `nrc_aps_review_ui_startup_and_smoke_test.md` is the concise startup walkthrough layered on top of that launch contract
  - `wb-compare-validation.md` owns same-checkout prep, `tools/validate_wb_prep.py`, populated compare + Candidate B Trace validation, and explicit runtime-source Candidate B validation
  - `nrc_aps_frontend_ui_operator_validation_guide.md` owns the broader manual validation pass after launch and prep succeed

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
  - canonical same-checkout prep plus populated compare/Candidate B Trace validation and explicit runtime-source Candidate B validation flows
- `nrc_aps_review_ui_startup_and_smoke_test.md`
  - concise startup walkthrough for the review/document-trace/compare surfaces, layered on top of the root launch runbook
- `nrc_aps_frontend_ui_operator_validation_guide.md`
  - broader end-to-end manual validation guide after launch and compare prep succeed
- `nrc_aps_runtime_db_reconceptualization_and_next_steps.md`
  - current-state reconceptualization of the NRC APS runtime DB model after the now-landed runtime-centric shift and transparency pass, plus the already-landed document-trace guardrails around large-doc rendering and audited data paths, with only further evidence-driven optimization left as an optional later step

## Archived Bake-Off Material

The retired Jules/Antigravity bake-off artifacts, prompts, mirrors, and workspaces were moved out of the live planning surface to:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\archive\files_to_be_trashed\2026-03-28_bakeoff_closeout\`

That archive area now holds the obsolete bake-off packet files, agent workspaces, mirror repos, and related worktrees that are no longer intended to drive active implementation.
