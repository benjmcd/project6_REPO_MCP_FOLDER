# PageEvidence Pack Activation And Working-Use Plan

## Purpose

Freeze the step-by-step activation plan for using this standalone PageEvidence pack as the control surface for the current strengthening lane.

This document is operational. It does not widen the substantive scope of the strengthening lane.

---

## Activation rule

Before implementation planning or code edits begin:

1. confirm this pack is the active planning/control surface for the current lane
2. re-read the live repo truth surfaces directly
3. confirm the pack still matches those truth surfaces or record any contradiction explicitly
4. only then use the pack to guide Lane Class A planning/execution

Do not rely on memory or earlier summaries alone.

---

## Canonical live truth surfaces to re-read

At minimum, re-read:

- `backend/app/services/nrc_aps_page_evidence.py`
- `tools/run_nrc_aps_page_evidence_workbench.py`
- `backend/app/services/nrc_aps_document_processing.py`
- `backend/tests/test_nrc_aps_page_evidence.py`
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

## Working-use order

Use the pack in this order:

1. front door / README
2. boundary / separation doc
3. execution packet
4. selector-semantics policy
5. Lane A equivalence gate
6. representative fixture lock
7. hidden-consumer checklist
8. pass-level allowed file manifest
9. pass sequencing / commit choreography
10. operator execution sheet
11. implementation record template

---

## Stop conditions

Stop before implementation if any of the following is true:

- live repo truth contradicts a binding pack assumption
- the needed work would widen beyond Lane Class A
- representative-fixture behavior cannot remain materially equivalent
- hidden-consumer compatibility is unclear
- `nrc_aps_document_processing.py` appears necessary in Pass 1
- the pack can no longer explain the lane simply and narrowly

---

## Result

The pack is active and usable once truth re-establishment succeeds and no stop condition is hit.
