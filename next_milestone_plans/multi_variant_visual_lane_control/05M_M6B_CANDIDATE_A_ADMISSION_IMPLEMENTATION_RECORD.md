# 05M M6B Candidate A Admission Implementation Record

## Purpose

Record the achieved M6B Candidate A direct-admission lane so the active pack can treat the current clean worktree as implemented and locally validated without overstating merged-`main` closure.

This document is an implementation record, not a new control packet.
The governing admission boundary remains `03AA` + `05H`, and the exact approved target remains `05L`.

---

## Outcome

The bounded M6B lane is implemented in the current clean worktree within the default owner boundary frozen by `05H`.

Implemented owner files:

- `backend/app/services/connectors_nrc_adams.py`
- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/review_nrc_aps_runtime.py`
- `backend/tests/test_nrc_aps_run_config.py`
- `backend/tests/test_review_nrc_aps_api.py`
- `tests/test_nrc_aps_document_processing.py`

Audited-but-unchanged default owner file:

- `backend/app/services/nrc_aps_artifact_ingestion.py`

No conditional owner files required widening.

---

## What the lane now provides

1. The integrated owner path now preserves exactly one approved non-`baseline` selector value:
   - `candidate_a_page_evidence_v1`
2. `baseline` remains the default for:
   - missing values
   - invalid values
   - unsupported values
   - unapproved non-`baseline` values
3. Candidate A is now admitted only through the already-frozen PDF visual-preservation seam.
4. Candidate A reuses the existing deterministic PageEvidence mechanism from `05J`.
5. Candidate A remains narrow:
   - no OCR-routing change
   - no policy tuning
   - no outward variant-identity field
   - no report/export/schema widening
6. Review/runtime visibility now admits the one approved Candidate A value while preserving the M5 barrier for every other non-approved value.

---

## Implemented shape

### Request normalization

`backend/app/services/connectors_nrc_adams.py` now:

- preserves `baseline`
- preserves `candidate_a_page_evidence_v1`
- fail-closes every other non-`baseline` `visual_lane_mode` value to `baseline`
- continues to exclude `visual_lane_mode` from `query_payload_inbound`

### Seam-local PDF behavior

`backend/app/services/nrc_aps_document_processing.py` now:

- preserves `baseline`
- preserves `candidate_a_page_evidence_v1`
- fail-closes every other value to `baseline`
- routes the admitted Candidate A value through a dedicated seam-local helper
- reuses `app.services.nrc_aps_page_evidence.analyze_pdf_page_evidence(...)`
- derives the Candidate A `has_visual` decision from deterministic PageEvidence image/drawing/coverage signals
- preserves the existing baseline classification helper contract for outward page-class behavior
- falls back to the baseline visual-lane helper if PageEvidence computation fails

### Review/runtime visibility

`backend/app/services/review_nrc_aps_runtime.py` now:

- treats `candidate_a_page_evidence_v1` as baseline-visible operationally
- continues to hide every other explicit non-`baseline` value
- does not add any outward variant label or identity field

---

## Validation executed

All validation below was run from the current clean M6B worktree with `PYTHONPATH=backend`.

### Required owner-path bundle

Command:

```powershell
$env:PYTHONPATH='backend'; python -m pytest backend/tests/test_nrc_aps_run_config.py tests/test_nrc_aps_document_processing.py tests/test_nrc_aps_artifact_ingestion.py tests/test_nrc_aps_artifact_ingestion_gate.py -q
```

Result:

- `44 passed`
- includes committed targeted regression coverage for the approved `ML17123A319.pdf` Candidate A preservation delta

### Changed review API surface

Command:

```powershell
$env:PYTHONPATH='backend'; python -m pytest backend/tests/test_review_nrc_aps_api.py -q
```

Result:

- `13 passed`

### Required governance bundle

Command:

```powershell
$env:PYTHONPATH='backend'; python -m pytest tests/test_nrc_aps_replay_gate.py tests/test_nrc_aps_promotion_gate.py tests/test_nrc_aps_promotion_tuning.py tests/test_nrc_aps_safeguard_gate.py tests/test_nrc_aps_safeguards.py tests/test_nrc_aps_sync_drift.py tests/test_nrc_aps_live_batch.py tests/test_nrc_aps_live_validation.py -q
```

Result:

- `25 passed`

### Required M5 no-drift backend bundle

Command:

```powershell
$env:PYTHONPATH='backend'; python -m pytest backend/tests/test_review_nrc_aps_catalog.py backend/tests/test_review_nrc_aps_api.py backend/tests/test_review_nrc_aps_details.py backend/tests/test_review_nrc_aps_tree.py backend/tests/test_review_nrc_aps_graph.py backend/tests/test_review_nrc_aps_document_trace_api.py backend/tests/test_review_nrc_aps_document_trace_service.py backend/tests/test_review_nrc_aps_document_trace_page.py backend/tests/test_review_nrc_aps_runtime_db.py backend/tests/test_diagnostics_ref_persistence.py -q
```

Result:

- `142 passed`

### Required root-side report/export/context bundle

Command:

```powershell
$env:PYTHONPATH='backend'; python -m pytest tests/test_nrc_aps_evidence_report.py tests/test_nrc_aps_evidence_report_contract.py tests/test_nrc_aps_evidence_report_gate.py tests/test_nrc_aps_evidence_report_export.py tests/test_nrc_aps_evidence_report_export_contract.py tests/test_nrc_aps_evidence_report_export_gate.py tests/test_nrc_aps_evidence_report_export_package.py tests/test_nrc_aps_evidence_report_export_package_contract.py tests/test_nrc_aps_evidence_report_export_package_gate.py tests/test_api.py tests/test_nrc_aps_document_corpus.py -q
```

Result:

- `111 passed`

### Required `06I` local performance gate

#### Tier 1 mandatory deterministic core-processing corpus

Fixtures:

- `born_digital.pdf`
- `mixed.pdf`
- `scanned.pdf`

Policy:

- one warm-up pass
- three measured runs per fixture
- same interpreter and machine
- validate-only isolated temp storage

Result:

- baseline aggregate median: `0.4224926000024425 s`
- Candidate A aggregate median: `0.4162112000012712 s`
- aggregate delta: `-1.4867%`
- worst fixture delta: `+0.6193%` on `scanned.pdf`

Threshold status:

- PASS against the `06I` Tier 1 gate

#### Tier 2 stronger artifact-aware comparison

Fixtures:

- `ML17123A319.pdf`
- `mixed.pdf`
- `scanned.pdf`

Artifact posture:

- `artifact_storage_dir` enabled
- isolated temp storage per measured run

Result:

- baseline aggregate median: `0.47272610000072746 s`
- Candidate A aggregate median: `0.4722068999981275 s`
- aggregate delta: `-0.1098%`
- worst fixture delta: `+4.4863%` on `ML17123A319.pdf`

Threshold status:

- PASS against the `06I` Tier 2 gate

### Admitted behavior watch-note

The Tier 2 comparison confirmed one substantive-but-approved behavior delta:

- under Candidate A, `ML17123A319.pdf` preserves one visual page where baseline preserved none

This remains within the exact `05L` approved scope because:

- the delta is seam-local
- it affects visual significance / preservation behavior only
- it does not widen outward identity/schema surfaces

---

## No-drift determination

The lane satisfies the `05H` no-drift assertions:

- `baseline` remains default
- `candidate_a_page_evidence_v1` is the only admitted non-`baseline` value
- all other non-`baseline` values remain fail-closed and experiment-hidden
- no new outward review/API/report/export identity fields were introduced
- diagnostics-ref persistence remains correct
- runtime DB binding and review-root resolution remain correct
- report/export/package surfaces remain green under the required bundle
- no conditional owner-file widening was required

This lane does **not**:

- promote Candidate A to the default
- reopen OCR-routing or hybrid OCR
- admit Candidate B or Candidate C
- implement broader policy-tuning or promotion/defaulting behavior

---

## M6B judgment

M6B Candidate A direct admission is now approve-as-is in the current clean worktree.

That means:

- the one approved selector value is admitted through the integrated owner path
- the required `05H` validation bundles pass
- `06I` is rerun and passes
- the M5 barrier remains intact for every non-approved value

This does **not** mean:

- merged `main` already contains the achieved M6B lane
- Candidate A is now the default
- broader promotion/defaulting or later candidate admission is implicitly approved

---

## Next justified move

The next justified operational move is no longer more M6B implementation work.

It is:

1. freeze and review this achieved M6B lane
2. merge it if the recorded validation and no-drift findings hold
3. treat any later post-admission promotion/defaulting, deprecation, or additional candidate work as separate scope requiring a new explicit freeze rather than inference from this lane
