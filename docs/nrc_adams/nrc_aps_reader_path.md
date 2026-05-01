# NRC APS Reader Path

Use these paths to navigate the repository based on your current objective.

**CRITICAL AUTHORITY WARNINGS:**
1. **STALE MIRRORS:** `handoff/backend/*` is explicitly NOT implementation authority. It is a stale mirror. Always refer to live root `backend/app/services/*`.
2. **MISSING PATH NOISE:** Root `README.md` and `REPO_INDEX.md` may reference root `tests/...` and `tools/...` that are not established from current workspace evidence. These are not safe authority paths unless their on-disk presence is directly confirmed.
3. **PROVISIONAL DEVELOPMENT:** `nrc_adams_index_builder.py` is an active development artifact for bridging logic. The `phase_8_contract.md` now reflects the final closed contract.

## Canonical Read Order (Fresh Session Entry)
To establish a rigorous mental model without inheriting prior session context, read strictly in this order:
1. `docs/nrc_adams/nrc_aps_authority_matrix.md` (to understand truth planes)
2. `docs/nrc_adams/nrc_aps_status_handoff.md` (canonical root status)
3. `handoff/phase_7a_closeout/accepted_facts.json` (machine-readable proof counts)
4. `handoff/START_HERE.txt` (handoff control parameters)

## Included vs Excluded Boundaries
- **INCLUDE:** Root `docs/nrc_adams/`, Root `backend/app/services/` (implementation truth), `handoff/phase_7a_closeout/`, and Phase 7A validation test artifacts.
- **EXCLUDE / IGNORE:** `handoff/backend/*` (stale), `.venvs/`, `*.db`, `tmp/`, `data_actual/`, and `.env` credentials.

## Context Maps
- **The True Proof Evidence:** `backend/app/storage_test_runtime/advanced_validation_runs/run_20260314_010136/artifact_audit/artifact_audit_report.md`
- **Phase 8 (Closed):** `docs/nrc_adams/phase_8_contract.md`. Phase 8 APS table materialization is complete; all invariants satisfied in closure-run-005 (41 targets, 41 linkages, 40 distinct content IDs, 40 documents). Current `main` now already includes the bounded continuation above that closed analytical ceiling; use `docs/nrc_adams/nrc_aps_status_handoff.md` for the live merged-main continuation posture rather than treating this line as a pending next-step marker.

## Review / Compare Operator Path
For the shipped NRC APS review surfaces on current `main`, use these docs in order:

1. `docs/nrc_adams/nrc_aps_ui_launch_runbook.md` - canonical launch contract for binding and starting the shipped review/document-trace/workbench/Candidate B Trace surfaces
2. `frontend_UI_plans/README.md` - retained UI reference index and supporting operator/reference docs
3. `frontend_UI_plans/nrc_aps_review_ui_startup_and_smoke_test.md` - concise startup walkthrough layered on top of the launch runbook
4. `frontend_UI_plans/wb-compare-validation.md` - same-checkout prep, `tools/validate_wb_prep.py`, populated Workbench Compare plus Candidate B Trace validation, and explicit runtime-source Candidate B validation
5. `frontend_UI_plans/nrc_aps_frontend_ui_operator_validation_guide.md` - broader manual validation pass after launch and prep succeed

Candidate B runtime-admission note:
- The older Candidate B workbench pack remains the authority for bundle-scoped compare/trace history and guardrails, but it did not authorize runtime admission.
- The later explicit runtime-admission reopen is currently implemented as the opt-in `document_processing_engine="candidate_b_opendataloader_pdf"` processing path on the existing NRC APS run-submit flow, optional runtime metadata on the existing review `/runs` selector response, rendered Candidate B / OpenDataLoader PDF labels in the existing review/document-trace run selectors and identity panels, and an explicit Candidate B runtime source kind in Workbench Compare alongside the preserved bundle source path.
- Use `docs/nrc_adams/nrc_aps_status_handoff.md` and the live source files named there before making Candidate B Trace parity, document-trace parity expansion, DB schema/model/migration, broad route, persistence, or new run-submission UI claims.
