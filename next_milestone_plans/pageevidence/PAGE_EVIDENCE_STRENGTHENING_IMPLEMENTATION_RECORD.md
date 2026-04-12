# PageEvidence Strengthening Implementation Record

## Purpose

Record the landed PageEvidence strengthening step so this root-local pack can treat the service-layer structural-separation objective as implemented and validated without implying that every later prepared pass is complete.

This document is an implementation record for the landed step, not a new program-decision amendment.

Merged-main anchor:

- `project6-origin/main` includes merge commit `7787f782`
- that merge contains landed implementation commit `fdbe3850` (`refactor: split pageevidence document extraction from projection`)

---

## Taxonomy note

Within this record:

- **Lane classes** describe the overall strengthening lane posture
- **Step classes** describe the concrete change classes actually executed inside that lane

This landed step is not a claim that every prepared pass in the pack has already been executed.

---

## Outcome

A bounded Pass 1 PageEvidence strengthening step was implemented and merged using only the default service-owner boundary:

- whole-document shared evidence extraction is now separable from Candidate A whole-document projection
- the compatibility wrapper for whole-document callers remains in place
- the integrated processing seam remained untouched
- later prepared passes remain open only if explicitly reopened

---

## Lane classification

### Chosen lane class

- `Lane Class A - behavior-preserving substrate strengthening`

### Justification

- current admitted selector identity remained unchanged
- no new selector value or version was introduced
- no production edit to `backend/app/services/nrc_aps_document_processing.py` was required
- no hidden-consumer surface was widened
- the landed step stayed within the service-owner boundary and its focused unit coverage

### Selector-semantics handling

- `current admitted selector semantics preserved`

Justification:

- `candidate_a_page_evidence_v1` remained the only admitted non-`baseline` value
- page-level projection logic remained in the existing Candidate A projection path
- `analyze_pdf_bytes(...)` retained candidate-shaped whole-document output by wrapping the new shared extractor with a projection helper

---

## Module / dependency posture

- primary modules/components affected:
  - `backend/app/services/nrc_aps_page_evidence.py`
  - `backend/tests/test_nrc_aps_page_evidence.py`
- no new helper module/file was added; the new helpers were added inside the existing PageEvidence service module
- dependency posture remained unchanged; the landed step continued using the existing `fitz` / `PyMuPDF` dependency posture only
- no new dependency was proposed, required, or escalated

---

## Traceability summary

| File | Change class | Direct risk | Indirect risk | Required tests/bundles run | Rollback target |
|---|---|---|---|---|---|
| `backend/app/services/nrc_aps_page_evidence.py` | `R`, `C` | whole-document service output shape; compatibility-wrapper behavior | workbench artifact interpretation; caller assumptions about candidate-shaped output | `backend/tests/test_nrc_aps_page_evidence.py`; `tests/test_nrc_aps_page_evidence_workbench.py`; `tests/test_nrc_aps_document_processing.py` | revert landed split commit lineage beginning at `fdbe3850` |
| `backend/tests/test_nrc_aps_page_evidence.py` | `R` | stale or missing contract coverage | weaker detection of mutation/contract regressions | `backend/tests/test_nrc_aps_page_evidence.py` | revert with service change if needed |

Reference control docs:

- `PAGE_EVIDENCE_FILE_TO_TEST_TO_BUNDLE_TRACEABILITY_MATRIX.md`
- `PAGE_EVIDENCE_BLAST_RADIUS_AND_BEFORE_AFTER_TOPOLOGY.md`

---

## Files changed

### Primary owner files changed

- `backend/app/services/nrc_aps_page_evidence.py`
- `backend/tests/test_nrc_aps_page_evidence.py`

### Conditionally widened files changed

- `None.`

### Inspect-only files confirmed unchanged

- `tools/run_nrc_aps_page_evidence_workbench.py`
- `backend/app/services/nrc_aps_document_processing.py`
- `tests/test_nrc_aps_page_evidence_workbench.py`

---

## What the landed step now provides

1. whole-document PageEvidence can now emit a candidate-neutral shared document evidence record
2. Candidate A whole-document projection is now available as a separate helper layered on top of shared document evidence
3. `analyze_pdf_bytes(...)` remains a compatibility wrapper for existing whole-document callers
4. page-level extraction and page-level Candidate A projection remain available and unchanged in role
5. no runner/report adaptation, field enrichment, disagreement expansion, or behavior recalibration was landed in this step

---

## Implemented shape

### Shared evidence layer

The landed shared whole-document extractor is:

- `extract_pdf_document_evidence_bytes(...)`

It emits:

- `schema_id`
- `source_name`
- `source_sha256`
- `page_count`
- `config`
- `pages`

Demotions/removals from the shared whole-document layer:

- `candidate_id` is no longer intrinsic to the shared whole-document record
- `summary` is no longer intrinsic to the shared whole-document record
- page records remain shared extracted records and do not intrinsically carry `projected_visual_page_class`

### Candidate A projection layer

The landed whole-document projection helper is:

- `project_candidate_a_document_evidence(...)`

It now owns:

- whole-document Candidate A projection of page records
- candidate identity in the projected whole-document output
- projected summary generation for the compatibility-shaped whole-document path

What did not change:

- the underlying Candidate A page-level projection rule remained the existing one
- no threshold retuning or calibration retuning landed in this step
- no new false-positive or borderline-case rule was introduced

### Runner / reporting / evaluation

No runner/report file changed in the landed step.

Implications:

- no workbench runner adaptation landed
- no disagreement/evaluation expansion landed
- workbench compatibility for the existing whole-document call path was preserved by leaving the runner untouched and retaining `analyze_pdf_bytes(...)` as a compatibility wrapper

---

## Schema / artifact compatibility handling

- chosen core schema handling option:
  - keep the existing core schema id and avoid a version bump in this landed step
- chosen workbench artifact handling option:
  - preserve compatibility through the projected whole-document wrapper rather than changing the runner or artifact version in this step
- projected-class fields:
  - retained in projected/compatibility output
  - not retained as intrinsic shared whole-document fields
- candidate identity:
  - removed from the shared whole-document record
  - retained in projected/compatibility output
- version bump:
  - none

---

## Blast-radius and before/after topology summary

- change class:
  - primarily `R`
  - bounded `C` because compatibility-shaped whole-document output was preserved by wrapper behavior
- connection surfaces touched:
  - whole-document service output shape
  - unit-test expectations for shared vs projected whole-document output
  - indirect workbench compatibility through the unchanged runner path
- before-state topology:
  - whole-document PageEvidence handling fused shared extraction, candidate identity, projected page class, and summary in one service path
- after-state topology:
  - shared whole-document extraction helper
  - separate whole-document Candidate A projection helper
  - compatibility wrapper preserving the prior whole-document caller shape
- why this after-state is allowed:
  - it remained inside the default service-owner boundary
  - it left `nrc_aps_document_processing.py` untouched
  - it preserved the existing whole-document outward path through a compatibility wrapper rather than widening hidden-consumer scope

### Per-file touched-surface summary

#### `backend/app/services/nrc_aps_page_evidence.py`

- why it was touched:
  - to separate shared whole-document extraction from whole-document Candidate A projection
- direct ownership it changed:
  - whole-document service shape and helper boundaries
- direct blast radius:
  - shared document artifact meaning
  - projected compatibility output shape
- indirect blast radius:
  - workbench reader assumptions
  - historical artifact interpretation if the wrapper had drifted
- validation required:
  - service tests
  - workbench runner tests
  - integrated processing regression tests
- rollback target:
  - revert the landed split commit lineage beginning at `fdbe3850`

#### `backend/tests/test_nrc_aps_page_evidence.py`

- why it was touched:
  - to prove candidate-neutral shared document output and non-mutating projection behavior
- direct ownership it changed:
  - service contract regression coverage
- direct blast radius:
  - expected unit-test assertions
- indirect blast radius:
  - confidence in compatibility and no-mutation claims
- validation required:
  - service test bundle
- rollback target:
  - revert alongside the service-file change

---

## Validation executed

### Required substrate / projection bundle

Command:

```text
python -m pytest ./backend/tests/test_nrc_aps_page_evidence.py -q
```

Result:

- `10 passed`

### Runner / report compatibility bundle

Command:

```text
python -m pytest ./tests/test_nrc_aps_page_evidence_workbench.py -q
```

Result:

- `6 passed`

### Required baseline-compatibility bundle

Command:

```text
python -m pytest ./tests/test_nrc_aps_document_processing.py -q
```

Result:

- `28 passed`
- warnings only; no failures

### Disagreement / evaluation bundle

Command:

```text
Not run for this landed step.
```

Result:

- no disagreement/evaluation logic changed in the landed step
- no separate disagreement/evaluation validation bundle was required for this record

---

## Rollback / change-control summary

- substrate-only structural separation was isolated from any runner/report adaptation
- no behavior-changing Candidate A recalibration was mixed into the landed step
- historical artifacts remain interpretable because the runner was left unchanged and the compatibility wrapper preserved candidate-shaped whole-document output
- the landed step is revertible as a narrow owner-boundary change set

---

## Hidden-consumer compatibility summary

| Surface | Status | Compatibility handling | Widening required |
|---|---|---|---|
| ingestion/indexing | untouched in this landed step | preserved by no-touch boundary | no |
| models/schemas | untouched in this landed step | preserved by no-touch boundary | no |
| retrieval | untouched in this landed step | preserved by no-touch boundary | no |
| evidence bundles | no direct file touch in this landed step | preserved by unchanged integrated seam and compatibility wrapper | no |
| review/runtime | untouched in this landed step | preserved by no-touch boundary | no |
| report/export/package | untouched in this landed step | preserved by no-touch boundary | no |
| workbench readers/artifacts | runner unchanged; compatibility retained | preserved by unchanged runner plus `analyze_pdf_bytes(...)` wrapper | no |

---

## No-drift determination

The landed step satisfies the frozen no-drift assertions for the touched service-owner path and the integrated processing seam because:

- current baseline-default runtime posture remained unchanged
- Candidate A remained the only admitted non-`baseline` value
- no new outward review/API/report/export identity field was introduced
- no hidden-consumer file was changed
- no broader candidate framework was introduced by implication
- `backend/app/services/nrc_aps_document_processing.py` remained untouched
- the focused service, workbench, and integrated processing regression bundles passed

Explicit findings:

- the landed step is appropriately described as behavior-preserving substrate strengthening
- no evidence in the executed bundles showed drift in the integrated admitted Candidate A seam
- broader later-pass claims would be overstatement and are intentionally not made here

---

## Widening record

- `No widening beyond the frozen default owner set was required.`

---

## Residual weaknesses / bounded non-goals

- runner/report adaptation remains unimplemented
- no additive internal evidence-field enrichment landed
- no disagreement/evaluation expansion landed
- the whole-document compatibility wrapper remains candidate-shaped by design for existing callers
- the pinned historical Candidate A workbench artifact remains the governing historical reference unless later explicitly superseded

---

## Judgment

This landed step may be described as approve-as-is for the service-layer structural-separation objective only if it is framed narrowly:

1. shared whole-document evidence extraction is now separable from Candidate A whole-document projection
2. current admitted Candidate A behavior and selector posture remain unchanged
3. no broader hidden-consumer widening occurred
4. later prepared passes remain explicitly unimplemented unless separately reopened

This does **not** mean:

- broad visual-understanding subsystem complete
- general multi-candidate policy framework complete
- runner/report adaptation complete
- field enrichment complete
- disagreement/evaluation expansion complete
- future Candidate B lane authorized

---

## Next justified move

`stable hold after landed Pass 1 structural-separation step`

If the lane reopens later, the next justified move is a separate bounded decision about one of:

1. runner/report adaptation with compatibility bridge
2. fixed internal evidence-field enrichment
3. evaluation/disagreement expansion
4. outward-contract cleanup if explicitly justified

---

## Pass sequencing summary

Actual landed implementation order:

1. add shared whole-document extraction helper and whole-document Candidate A projection helper inside the existing PageEvidence service file
2. retain `analyze_pdf_bytes(...)` as the compatibility wrapper for whole-document callers
3. add focused service tests proving candidate-neutral shared document output and non-mutating projection
4. validate workbench runner and integrated processing regression bundles
5. do not mix runner/report adaptation, field enrichment, disagreement expansion, or behavior recalibration into the landed step

Difference from the original prepared choreography:

- the landed step implemented the service-layer structural-separation objective directly
- no separate runner/report adaptation pass was bundled into the same change set
- no separate cleanup-only commit was required because the landed change remained narrow and revertible without additional lifecycle-only edits
