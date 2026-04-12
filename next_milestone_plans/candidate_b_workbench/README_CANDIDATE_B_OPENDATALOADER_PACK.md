# README — Candidate B OpenDataLoader Planning Pack (v6 Execution-Determinism Hardening)

## Purpose

This folder is the root-local planning branch copy of the Candidate B OpenDataLoader pack.
It is not the adopted merged-main hold-state authority copy.

v6 exists because v5 was repo-grounded but still left too much execution-day inference.
The remaining weakness was not macro-scope. It was determinism.

The live repo already gives the correct strategic anchor:
- the root `README.md` says the NRC APS upper analytical layers remain frozen
- the root `README.md` says the lower document-processing layer is reopened additively around deterministic media detection, PyMuPDF-based PDF extraction, OCR wiring, and manifest-driven proof
- the root `README.md` names the active proof lane built around `tests/fixtures/nrc_aps_docs/v1/manifest.json`, `tests/support_nrc_aps_doc_corpus.py`, `tests/test_nrc_aps_document_corpus.py`, `tests/test_nrc_aps_document_processing.py`, and `project6.ps1 -Action prove-nrc-aps-document-processing`
- the live service tree shows a large outward NRC APS surface that Candidate B v1 must not touch
- the live lower-layer processing/test files define current owner-path invariants that Candidate B must compare against, not weaken or replace

v6 therefore hardens five specific areas:
1. exact execution envelope and package verification
2. exact ODL→repo output crosswalk and non-equivalence map
3. explicit non-interference proof sequence
4. stricter corpus regime labeling
5. resolved output-retention / raw-output isolation policy

---

## Core program truth retained in v6

- `baseline` remains the integrated default posture.
- `candidate_a_page_evidence_v1` remains the only admitted non-`baseline` value.
- Candidate B remains **workbench-only, non-admitted, non-integrated**.
- No runtime admission/defaulting/promotion work begins by implication.
- No service/API/review/evidence/context/export surface is modified in Candidate B v1.
- Candidate B v1 is still a **tests/report comparator over the existing lower-layer proof harness**.

Branch-local authority note:
- use this root copy as planning material for the separate root-local planning branch
- do not confuse it with the stronger adopted Candidate B pack carried in the merged-main worktree
- do not treat its execution-contract statements as proof that the current root checkout or current merged-main worktree locally reproduce the same workbench artifacts

---

## What v6 changes decisively

### 1. Version and package truth are now frozen more tightly
- v6 keeps the currently verified PyPI v2 release pin: `opendataloader-pdf==2.0.0`
- v6 adds the exact verified wheel SHA256 for that release
- v6 adds implementation-day package revalidation rules so package drift cannot happen silently

### 2. The execution envelope is now explicit
- Python-wrapper only
- Windows PowerShell + `py -3.12` + Java 11+
- batch-first conversion model
- exact package/version/hash capture
- exact stop rules for Java/Python/package mismatch

### 3. The compare layer is now less interpretive
- v6 adds an explicit ODL→repo output crosswalk
- it also documents the fields that have **no** valid equivalence to current repo truth
- that prevents false “wins” driven by richer semantic output that is not program-relevant

### 4. The proof sequence is now harder
- baseline proof first
- Candidate B workbench run second
- non-interference checks third
- baseline proof re-run fourth
- decision only after that

### 5. Output handling is now less ambiguous
- raw ODL outputs are isolated under a run-scoped workbench root
- raw ODL outputs are **not** committed by default
- durable proof/compare/retention-manifest artifacts are the only approved commit candidates in v1

---

## New docs in v6

1. `00N_CANDIDATE_B_OPENDATALOADER_EXECUTION_ENVELOPE_AND_PACKAGE_VERIFICATION.md`
   - exact runtime/package/hash/preflight contract

2. `04C_CANDIDATE_B_OPENDATALOADER_OUTPUT_CROSSWALK_AND_NON_EQUIVALENCE_MAP.md`
   - exact ODL field → repo comparison mapping
   - exact non-equivalent repo fields

3. `08D_CANDIDATE_B_OPENDATALOADER_NONINTERFERENCE_PROOF_SEQUENCE.md`
   - exact baseline / Candidate B / rerun sequence
   - exact interference stop conditions

---

## Newly strengthened docs in v6

- `00C` dependency/runtime/license matrix
- `00D` config and process contract
- `00E` artifact schema and provenance contract
- `00F` failure modes / validation / observability
- `04A` field registry and comparison semantics
- `05R` execution packet
- `06A` corpus manifest and labeling guide
- `06R` remaining open items and decision gates
- `08A` commands / validation / decision runbook
- `08C` test matrix and triage protocol
- `09A` output isolation / retention / event registry

---

## Recommended reading order

1. `README_CANDIDATE_B_OPENDATALOADER_PACK.md`
2. `00A_CANDIDATE_B_OPENDATALOADER_HANDOFF_AND_DECISION_MAP.md`
3. `00M_CANDIDATE_B_OPENDATALOADER_REPO_TRUTH_ANCHORS_AND_REFERENCES.md`
4. `00B_CANDIDATE_B_OPENDATALOADER_REPO_SURFACE_MAP_AND_TOUCH_POLICY.md`
5. `00C_CANDIDATE_B_OPENDATALOADER_DEPENDENCY_RUNTIME_AND_LICENSE_MATRIX.md`
6. `00N_CANDIDATE_B_OPENDATALOADER_EXECUTION_ENVELOPE_AND_PACKAGE_VERIFICATION.md`
7. `00D_CANDIDATE_B_OPENDATALOADER_CONFIG_AND_PROCESS_CONTRACT.md`
8. `04A_CANDIDATE_B_OPENDATALOADER_FIELD_REGISTRY_AND_COMPARISON_SEMANTICS.md`
9. `04C_CANDIDATE_B_OPENDATALOADER_OUTPUT_CROSSWALK_AND_NON_EQUIVALENCE_MAP.md`
10. `05R_CANDIDATE_B_OPENDATALOADER_WORKBENCH_COMPARISON_EXECUTION_PACKET.md`
11. `06A_CANDIDATE_B_OPENDATALOADER_CORPUS_MANIFEST_AND_LABELING_GUIDE.md`
12. `08A_CANDIDATE_B_OPENDATALOADER_COMMANDS_VALIDATION_AND_DECISION_RUNBOOK.md`
13. `08D_CANDIDATE_B_OPENDATALOADER_NONINTERFERENCE_PROOF_SEQUENCE.md`
14. `06R_CANDIDATE_B_OPENDATALOADER_REMAINING_OPEN_ITEMS_AND_DECISION_GATES.md`

---

## Bottom line

v6 is not broader than v5.
It is narrower and harder.
That is the correct direction.

Candidate B v1 still remains a local workbench comparator.
What v6 adds is the missing execution discipline required to keep that statement true during real implementation.
