# NRC APS Documentation Authority Matrix

This document defines the strict, 7-level authority hierarchy for all NRC ADAMS APS documentation, code, and evidence surfaces in the repository.

## 1. Authority Hierarchy (Strongest to Weakest)

When conflicts exist, the lower-numbered truth plane strictly outranks the higher-numbered truth plane. Do NOT compress these levels.

1. **Artifact-backed evidence:** Actual physical proof of execution (e.g., `backend/app/storage_test_runtime/advanced_validation_runs/run_20260314_010136/**`, `artifact_audit_report.md`).
2. **Machine-readable accepted facts:** Synthesized, accepted factual counts (e.g., `handoff/phase_7a_closeout/accepted_facts.json`).
3. **Root authority/control docs:** Main governance surfaces (e.g., `docs/nrc_adams/nrc_aps_status_handoff.md`, this matrix).
4. **Live root implementation truth:** Executable code in the root (e.g., root `backend/app/services/*`).
5. **Handoff control/navigation docs:** Package-local navigation (e.g., `handoff/README.md`, `handoff/handoff_manifest.json`).
6. **Handoff mirrored code:** Explicitly stale codebase mirrors (e.g., `handoff/backend/*`).
7. **Stale/historical prose:** Old patch summaries, duplicate narrative reports, and explicitly registered lineage documents.

## 2. Conflict Resolution
- **Accepted Facts vs Evidence:** If `accepted_facts.json` (Level 2) and `artifact_audit_findings.json` (Level 1) or on-disk artifacts diverge, the Level 1 physical evidence strictly wins.
- **Root Code vs Handoff Code:** Level 4 (`backend/app/services/*`) ALWAYS outranks Level 6 (`handoff/backend/*`). Do not trust handoff mirrors as live implementation truth.
- **Provisional Bridge Constraints:** Bridge surfaces (`phase_8_contract.md`, `nrc_adams_index_builder.py`) belong to current active development (Levels 3/4) but are provisional and do NOT override or re-validate settled historical Phase 7A truth (Levels 1/2).

