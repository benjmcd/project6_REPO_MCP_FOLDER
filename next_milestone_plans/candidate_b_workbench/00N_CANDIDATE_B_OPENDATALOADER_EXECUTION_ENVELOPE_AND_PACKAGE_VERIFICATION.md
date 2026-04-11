# 00N — Candidate B OpenDataLoader Execution Envelope and Package Verification

## Purpose

Freeze the planned execution-day envelope for Candidate B v1 so that implementation does not improvise around environment or package state.

This doc records the required preflight posture for a future implementation pass.
It does not claim that package, Java, or wrapper-signature verification has already been completed in this planning pass.

---

## A. Required execution envelope

Candidate B v1 must run under:
- Windows PowerShell
- `py -3.12`
- Java 11+ available on `PATH`
- Python-wrapper OpenDataLoader invocation only

No other envelope is approved in v1.

---

## B. Required package verification posture

### Preferred reproducible posture
Use a dedicated workbench requirements sidecar with the exact planned pin and planned hash, then revalidate both on implementation day.

Example contents:
```text
opendataloader-pdf==2.0.0     --hash=sha256:18093fa87a3089abdba14043c187f85c6a4af48c4597710de32d90e95666313e
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

## C. Required environment capture fields

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

## D. Batch and resource posture

Candidate B v1 should use one corpus-level batch when feasible.
If splitting is required due to timeout or memory pressure:
- split only at whole-document boundaries
- record batch membership and reason
- keep the config identical across batches

No per-page or regime-selective split is allowed in v1.

---

## E. Temporary and output directory posture

All temporary or durable ODL outputs must remain under the approved Candidate B workbench roots.
The default ODL behavior of writing beside the input file must be overridden.

Approved durable raw-output root:
- `tests/reports/nrc_aps_candidate_b_opendataloader_raw/<run_id>/...`

---

## F. Exact stop conditions

Stop immediately if any of the following is true:
- `py -3.12` is not available
- Java is not available on `PATH`
- the installed ODL package version differs from the frozen pin
- the working output root is not the approved run-scoped Candidate B root
- the invocation path is CLI/JAR/Node instead of the Python wrapper

---

## G. Why this doc exists

Without an explicit execution envelope,
Candidate B proof results are too easy to misattribute.
This doc removes that ambiguity before any implementation work starts.
