# PageEvidence File-to-Test-to-Bundle Traceability Matrix

## Purpose

Provide an implementation-facing matrix that maps each relevant change surface to:

- likely change class
- direct and indirect blast radius
- required tests/bundles
- rollback target
- escalation trigger

This document exists so implementers do not have to synthesize traceability from multiple docs manually.

---

## Matrix

| File / Surface | Typical Change Class | Direct Risk | Indirect Risk | Required Tests / Bundles | Rollback Target | Escalation Trigger |
|---|---|---|---|---|---|---|
| `backend/app/services/nrc_aps_page_evidence.py` | `R`, `P`, `C` | core evidence meaning, projection meaning, artifact shape | runner compatibility, admitted Candidate A semantics, historical artifact interpretation | `backend/tests/test_nrc_aps_page_evidence.py`, `tests/test_nrc_aps_page_evidence_workbench.py`, disagreement/evaluation bundle | revert core service change independently if possible | any material Candidate A output drift on representative fixtures |
| one projection/helper file under `backend/app/services/` (Pass 2 only if needed) | `R`, `C` | extractor/projection boundary semantics, helper import stability | runner compatibility, temptation to widen into the protected integrated seam | service bundle, runner bundle, representative equivalence checks, targeted integrated seam sanity if import/wiring changes | revert helper plus its import wiring together | any need to touch `nrc_aps_document_processing.py` or any representative drift |
| `tools/run_nrc_aps_page_evidence_workbench.py` | `R`, `C` | workbench artifact shape, report generation, path/timestamp semantics | pinned artifact comparability, durable review of historical outputs | `tests/test_nrc_aps_page_evidence_workbench.py`, disagreement/evaluation bundle | revert runner/report changes independently | artifact meaning or schema drift without compatibility bridge |
| one evaluation/disagreement helper under `tools/` (Pass 4 only) | `R`, `C` | disagreement/report semantics, deterministic summary meaning | pinned artifact comparability, reviewer interpretation drift | runner bundle, disagreement/evaluation bundle, artifact compatibility checks | revert helper/report path independently | artifact meaning drift or pressure toward outward schema widening |
| `backend/tests/test_nrc_aps_page_evidence.py` | support | test contract drift | weak guarantees if outdated | service bundle | revert test-only changes or align with final service contract | tests no longer isolate extractor vs projection responsibilities |
| `tests/test_nrc_aps_page_evidence_workbench.py` | support | runner/report contract drift | durable artifact expectations weaken | runner bundle | revert test-only changes or align with final runner contract | workbench outputs no longer covered by deterministic assertions |
| `backend/app/services/nrc_aps_document_processing.py` | `R`, `P`, `H` | integrated owner-path behavior, admitted Candidate A semantics | retrieval, evidence bundle, review/report/export, performance | baseline-compat bundle, document-processing tests, hidden-consumer checks, possibly performance gate | separate seam-local commit if possible | any admitted Candidate A behavior drift or downstream persisted-output drift |
| `tests/test_nrc_aps_document_processing.py` | support | seam regression expectations | hidden admitted-behavior drift may go undetected if weak | baseline-compat bundle | revert test-only change or update after approved behavior amendment | representative fixture outcomes change |
| Hidden-consumer readers (inspect-only by default) | `H`, `C` | reader compatibility | review/report/export or retrieval interpretation drift | hidden-consumer checklist, no-drift checks | revert reader touch independently | any required reader/code change beyond inspect-only posture |

---

## Use rule

1. Classify the proposed file change using the blast-radius doc.
2. Find the corresponding row in this matrix.
3. Record the required test/bundle path before implementation begins.
4. If no row fits cleanly, stop and add one before proceeding.
5. If no row beyond already-validated surfaces becomes active, do **not** open the next pass only for structural preference.

---

## Practical interpretation

The matrix should make it difficult to perform any of the following accidentally:

- core service edits without runner/test impact review
- admitted-behavior changes without escalation
- artifact-shape changes without compatibility handling
- seam-local runtime edits without downstream no-drift checks


---

## Lane/pass interpretation note

Use this matrix together with:

- `PAGE_EVIDENCE_LANE_A_EQUIVALENCE_AND_NO_DRIFT_GATE.md`
- `PAGE_EVIDENCE_PASS_LEVEL_ALLOWED_FILE_MANIFEST.md`

The matrix does not override those docs; it operationalizes them at file/test level.
