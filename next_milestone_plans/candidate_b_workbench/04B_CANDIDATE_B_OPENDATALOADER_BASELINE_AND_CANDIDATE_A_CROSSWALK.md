# 04B - Candidate B OpenDataLoader Baseline and Candidate A Crosswalk

## Purpose

Define what Candidate B must compare against now and what remains optional.

## A. Primary mandatory comparison in this objective

The primary mandatory comparison target is the current live lower-layer baseline truth:
- current `nrc_aps_document_processing.process_document(...)` outputs
- current lower-layer proof corpus
- current lower-layer tests and invariants

This comparison is mandatory because it is directly repo-grounded and reflects the current default runtime baseline.

## B. Secondary Candidate A comparison in this objective

Secondary comparison against Candidate A is optional, but if it is used it must use the exact frozen anchors below.

### Frozen Candidate A comparison anchors
- pinned workbench artifact:
  - `tests/reports/mvvlc_candidate_a_page_evidence_workbench_report_v1.json`
  - SHA256: `2A999C1CC2452FDFD539349B9D324241CE2D35B04864CAFA854EB0DEB77E5959`
- current Candidate A service baseline:
  - `backend/app/services/nrc_aps_page_evidence.py`
  - SHA256: `F0E8B7FF2FCC917FE834B61E39ADC1645012B16EBB0EC0E189454462FDCD1D8A`
- current Candidate A runner baseline:
  - `tools/run_nrc_aps_page_evidence_workbench.py`
  - SHA256: `DDC9F457ECDB70A7E74F46ACEBBE5A3F474A573C31124E5C85BD20D70361FBA8`
- current admitted-candidate authority docs:
  - `05L_M6B_CANDIDATE_A_APPROVED_TARGET_RECORD.md`
  - `05Q_POST_ADMISSION_RETAIN_BASELINE_MERGED_MAIN_CLOSURE_AND_HANDOFF.md`
  - `next_milestone_plans/pageevidence/README_PAGEEVIDENCE_STRENGTHENING_PACK.md`

Hard rules:
- do not regenerate the pinned Candidate A artifact inside this objective
- do not guess Candidate A comparison anchors from memory or filename patterns
- if a future implementation wants a different Candidate A reference set, freeze it explicitly before using it

## C. Win and divergence taxonomy

### `program_relevant_gain`
Candidate B reveals structural or layout evidence that is genuinely useful relative to current baseline outputs.

### `expected_semantic_divergence`
Candidate B differs because OpenDataLoader exposes richer semantics that the current repo does not model directly.
This is not a win by itself.

### `protected-baseline divergence`
Candidate B appears different on preserve-lane, OCR-control, or outward-contract classes that remain owned by the current merged baseline.
This does not justify broadening scope.

## D. Comparison rule summary

- baseline comparison is mandatory
- Candidate A comparison is optional
- any Candidate A comparison must use the exact frozen refs above
- neither comparison authorizes runtime integration or admission
