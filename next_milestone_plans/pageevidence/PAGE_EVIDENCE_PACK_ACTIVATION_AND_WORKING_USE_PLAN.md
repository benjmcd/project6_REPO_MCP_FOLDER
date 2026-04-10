# PageEvidence Pack Activation And Working-Use Plan

## Purpose

Provide the procedural narrative for using this prepared standalone PageEvidence pack safely for local refinement, pre-adoption planning, and later insertion/adoption preparation.

This document is operational and non-normative.
Normative rules are governed by the active control docs listed in the README doc classification table.
Use that table as the complete authority map rather than treating the short consultation order in this document as a full precedence list.

If this document appears to conflict with a normative doc, the normative doc wins.

---

## Standalone-use vs adoption rule

- local standalone refinement/use may proceed with the current pack filenames and no ordinalization
- repo-native active control authority requires insertion/adoption using `PAGE_EVIDENCE_PACK_ACTIVATION_AND_VERIFICATION_CHECKLIST.md`
- repo-native insertion on this branch must be reconciled against `next_milestone_plans/multi_variant_visual_lane_control/README_INDEX.md` and the retained-default authority chain `03AC` / `05O` / `05P` / `05Q`

---

## Working sequence

1. Determine whether the session is local standalone refinement/use or insertion/adoption preparation.
2. Re-read the live repo truth surfaces directly.
3. Confirm the prepared pack still matches those truth surfaces, or record any contradiction explicitly before relying on the pack.
4. Consult the normative docs in the recommended order before refining the pack or planning implementation.
5. If a rule change is needed, place it in the relevant normative doc first rather than only in an operational companion doc.
6. If the pack is being prepared for repo-native authority, route that work through the insertion/post-insertion checklist instead of assuming adoption.
7. If unresolved contradiction or lane-class ambiguity remains, stop in audit/recon mode and escalate through the normative docs.

---

## Canonical live truth surfaces to re-read

At minimum, re-read:

- `backend/app/services/nrc_aps_page_evidence.py`
- `tools/run_nrc_aps_page_evidence_workbench.py`
- `backend/app/services/nrc_aps_document_processing.py`
- `backend/tests/test_nrc_aps_run_config.py`
- `backend/tests/test_nrc_aps_page_evidence.py`
- `tests/test_nrc_aps_document_processing.py`
- `tests/test_nrc_aps_page_evidence_workbench.py`
- `tests/fixtures/nrc_aps_docs/v1/manifest.json`
- `tests/reports/mvvlc_candidate_a_page_evidence_workbench_report_v1.json`

Also inspect the real downstream/hidden-consumer surfaces relevant to:

- `visual_page_refs`
- projected class logic
- PageEvidence artifacts
- retrieval
- review/document trace
- report/export/package persistence

---

## Consultation order

Use the pack in this order:

1. front door / README
2. boundary / separation doc
3. execution packet
4. selector-semantics policy
5. Lane A equivalence gate
6. representative fixture lock
7. schema/artifact compatibility policy
8. hidden-consumer checklist
9. blast-radius / before-after topology
10. pass-level allowed file manifest
11. roadmap / decision notes
12. operational companion docs as needed, including the traceability matrix, operator execution sheet, implementation-record template, and insertion/post-insertion checklist

---

## Escalation flow

If any of the following occurs, stop and route the issue through the relevant normative docs instead of patching around it here:

- live repo truth contradicts a normative pack assumption
- the needed work appears to widen beyond Lane Class A
- representative-fixture behavior may not remain materially equivalent
- hidden-consumer compatibility becomes unclear
- `nrc_aps_document_processing.py` appears necessary in Pass 1
- the pack is ready to be treated as repo-native active authority

Use the insertion/post-insertion checklist for the last case.

---

## Result

This plan is satisfied once truth re-establishment is complete, the relevant normative docs have been consulted, and any adoption/insertion question has been routed through the dedicated checklist rather than assumed.
