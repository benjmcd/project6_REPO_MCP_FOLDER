# 00N - Candidate B OpenDataLoader Execution Envelope and Package Verification

## Purpose

Freeze the exact execution-day envelope for Candidate B v1 so that implementation does not improvise around environment or package state.

---

## A. Required execution envelope

Candidate B v1 must run under:
- Windows PowerShell
- `py -3.12`
- Java 11+ available on `PATH`
- Python-launched OpenDataLoader invocation only

No other envelope is approved in v1.

---

## B. Required package verification posture

### Preferred reproducible posture
Use a dedicated workbench requirements sidecar with the exact pin and verified hash.

Example contents:
```text
opendataloader-pdf==2.0.0 --hash=sha256:18093fa87a3089abdba14043c187f85c6a4af48c4597710de32d90e95666313e
```

Install with:
```powershell
py -3.12 -m pip install --require-hashes -r tests/requirements_nrc_aps_candidate_b_opendataloader.txt
```

### Minimum verification if the hash-locked sidecar is not yet present
Capture all of the following into the proof report:
```powershell
py -3.12 --version
java -version
py -3.12 -m pip show opendataloader-pdf
```

If the reported version is not `2.0.0`, stop and update the docs before continuing.

---

## C. Current committed artifact note

The committed Candidate B reports on `main` capture a historical workbench run, not a portable machine snapshot for every future environment.

What those committed artifacts prove:
- the historical workbench run used `opendataloader-pdf==2.0.0`
- the committed proof and compare artifacts both captured `odl_package_sha256_expected`
- the committed proof report explicitly recorded `odl_package_sha256_verified: null` with a reason
- the committed compare report recorded `odl_package_sha256_verified: null` without the paired reason field
- the reports captured Java/Python execution-envelope fields for that historical run

What they do **not** prove:
- that every future machine already has Java 11+ on `PATH`
- that current `main` can be treated as already rerun locally without a fresh preflight
- that the installed package directory was reconstructed back to the pinned wheel hash

---

## D. Required environment capture fields

Capture at minimum:
- Python version
- Python executable path
- Java version string
- Java vendor string if available
- working directory
- repo root
- PATH-derived Java resolution result
- ODL package version
- ODL hash posture (`verified_hash`, `unverified_local_install`, etc.)

---

## E. Batch and resource posture

Current committed `main` implementation uses one whole-document batch per fixture.
That split is recorded in the provenance block with:
- batch membership
- batch count
- split reason

Current committed split reason:
- `per_document_external_image_provenance_isolation`

No per-page or regime-selective split is allowed in v1.

---

## F. Temporary and output directory posture

All temporary or durable ODL outputs must remain under the approved Candidate B workbench roots.
The default ODL behavior of writing beside the input file must be overridden.

Approved durable raw-output root:
- `tests/reports/nrc_aps_candidate_b_opendataloader_raw/<run_id>/...`

---

## G. Exact stop conditions

Stop immediately if any of the following is true:
- `py -3.12` is not available
- Java is not available on `PATH`
- the installed ODL package version differs from the frozen pin
- the working output root is not the approved run-scoped Candidate B root
- the invocation path widens beyond the current approved Python-launched workbench contract

---

## H. Why this doc exists

Without an explicit execution envelope,
Candidate B proof results are too easy to misattribute.
This doc removes that ambiguity before any implementation work starts.
