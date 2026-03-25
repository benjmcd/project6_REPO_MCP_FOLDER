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
- **The Next Milestone Bounding:** `docs/nrc_adams/phase_8_contract.md` (Provisional bridge reconciliation/validation above accepted Phase 7A outputs) **with the acceptance condition being successful APS table materialization; Evidence Bundle remains a downstream consumer**
