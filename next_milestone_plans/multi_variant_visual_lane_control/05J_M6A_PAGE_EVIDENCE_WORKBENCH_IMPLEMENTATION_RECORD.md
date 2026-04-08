# 05J M6A PageEvidence Workbench Implementation Record

## Purpose

Record the achieved M6A PageEvidence workbench lane so the active pack can treat the workbench as implemented and locally validated without implying direct M6 admission.

This document is an implementation record, not a new control packet.
Direct admission remains governed separately by `03AA` + `05H`.

---

## Outcome

The bounded M6A lane is implemented in the clean worktree using only the default owner boundary frozen by `05I`.

Implemented owner files:

- `backend/app/services/nrc_aps_page_evidence.py`
- `tools/run_nrc_aps_page_evidence_workbench.py`
- `backend/tests/test_nrc_aps_page_evidence.py`
- `tests/test_nrc_aps_page_evidence_workbench.py`

No inspect-only compatibility files required widening.

---

## What the workbench now provides

1. A dedicated internal PageEvidence service exists.
2. Candidate A can be executed through an isolated standalone runner.
3. The workbench emits explicit JSON evidence reports to caller-owned output paths.
4. Candidate A remains pre-admission:
   - no non-`baseline` selector value is admitted
   - integrated runtime behavior remains unchanged by default
   - no review/runtime/report/export identity surfaces were widened

---

## Implemented shape

### Shared internal surface

`backend/app/services/nrc_aps_page_evidence.py` provides:

- threshold normalization for PageEvidence tuning inputs
- per-page evidence extraction using live PyMuPDF APIs
- deterministic signal collection for:
  - word count
  - text block count
  - image count
  - drawing count
  - text coverage ratio
  - image coverage ratio
  - drawing coverage ratio
  - combined visual coverage ratio
- a conservative projected legacy visual class:
  - `diagram_or_visual`
  - `text_heavy_or_empty`

### Standalone workbench runner

`tools/run_nrc_aps_page_evidence_workbench.py` provides:

- explicit fixture-ID execution against the repo-native NRC APS fixture manifest
- explicit PDF-path execution for isolated local analysis
- caller-owned report output via `--report`
- threshold tuning via:
  - `--text-word-threshold`
  - `--visual-coverage-threshold`
- fail-closed handling for unknown fixture IDs, missing PDF paths, and PDF-open failures

---

## Validation executed

All validation was run from the clean M6A worktree with `PYTHONPATH=backend`.

### Required M6A workbench bundle

Command:

```powershell
$env:PYTHONPATH='backend'; python -m pytest backend/tests/test_nrc_aps_page_evidence.py tests/test_nrc_aps_page_evidence_workbench.py tests/test_import_guardrail.py -q
```

Result:

- `9 passed`

### Required baseline-compatibility bundle

Command:

```powershell
$env:PYTHONPATH='backend'; python -m pytest backend/tests/test_nrc_aps_run_config.py tests/test_nrc_aps_document_processing.py tests/test_nrc_aps_artifact_ingestion.py tests/test_nrc_aps_artifact_ingestion_gate.py -q
```

Result:

- `35 passed`

### Standalone runner smoke execution

Command:

```powershell
$env:PYTHONPATH='backend'; python tools/run_nrc_aps_page_evidence_workbench.py --report "$env:TEMP\mvvlc_page_evidence_smoke.json" --fixture-id scanned --fixture-id born_digital
```

Result:

- exit code `0`

---

## No-drift determination

The lane satisfies the `05I` no-drift assertions:

- baseline integrated runtime remains unchanged by default
- no non-`baseline` selector value is admitted through the owner path
- no new outward review/API/report/export identity fields were introduced
- no review/runtime/report/export/package visibility rules were widened
- no shared runtime roots were seeded or contaminated by validation
- workbench outputs remain isolated to caller-owned or temp paths

No changes were made to:

- `connectors_nrc_adams.py`
- `nrc_aps_artifact_ingestion.py`
- `nrc_aps_document_processing.py`
- `review_nrc_aps_runtime.py`

---

## M6A judgment

M6A is now approve-as-is for the standalone PageEvidence workbench lane.

That means:

- the dedicated workbench surface exists
- the required M6A validation bundles pass
- Candidate A remains pre-admission
- the baseline owner path remains unchanged by default

This does **not** mean:

- Candidate A is admitted
- any non-`baseline` selector value is approved
- M6 direct admission is complete

---

## Next step

The next justified MVVLC step is no longer M6A implementation.

The next justified step is:

1. define the exact M6B Candidate A target record
2. name one exact non-`baseline` selector value
3. attach the approval basis and comparison/evidence refs for that value
4. then execute the later direct-admission lane under `03AA` + `05H`

Until that target record exists, direct admission remains fail-closed.
