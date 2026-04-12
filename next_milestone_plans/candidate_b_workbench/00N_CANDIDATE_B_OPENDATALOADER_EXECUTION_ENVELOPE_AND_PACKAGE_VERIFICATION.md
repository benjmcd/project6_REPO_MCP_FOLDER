# 00N - Candidate B OpenDataLoader Execution Envelope and Package Verification

## Purpose

Freeze the exact execution-day envelope for Candidate B v1 so that implementation does not improvise around environment or package state.

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

## C. Current workspace preflight snapshot for this pass

No Candidate B execution was performed in this pass.
The direct local preflight checks returned:
- `py -3.12 --version` -> `Python 3.12.10`
- default shell state: `java -version` unresolved on `PATH`, `JAVA_HOME` empty
- discoverable local install found at `C:\Program Files\Eclipse Adoptium\jdk-17.0.18.8-hotspot\bin\java.exe`
- session-local env fix used for confirmation:
  - `$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-17.0.18.8-hotspot'`
  - `$env:PATH="$env:JAVA_HOME\bin;$env:PATH"`
- `java -version` after the session-local fix -> Temurin OpenJDK `17.0.18+8`
- isolated worktree-local venv created at `.candidate_b_preflight_venv`
- `.\.candidate_b_preflight_venv\Scripts\python.exe -m pip install --require-hashes -r tests/requirements_nrc_aps_candidate_b_opendataloader.txt` -> success
- isolated `pip show opendataloader-pdf` -> `Version: 2.0.0`
- isolated installed module root -> `.candidate_b_preflight_venv\Lib\site-packages\opendataloader_pdf`
- isolated wrapper/API verification -> `__all__ == ["run", "convert", "run_jar"]`, `run()` deprecated, `convert(...)` signature matches the frozen contract

Interpretation:
- the Python side of the execution envelope is present
- Java 11+ is present on this machine but not on the default shell `PATH`
- the approved execution envelope is ready once the documented session-local `JAVA_HOME` / `PATH` fix is applied
- the exact ODL package is now installed only inside the isolated preflight venv, not as a repo-runtime dependency

So the execution envelope is frozen,
and this machine is ready for a real Candidate B run only under the documented session-local Java env fix plus the isolated preflight venv.

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

Candidate B v1 should use one corpus-level batch when feasible.
If splitting is required due to timeout or memory pressure:
- split only at whole-document boundaries
- record batch membership and reason
- keep the config identical across batches

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
- the invocation path is CLI/JAR/Node instead of the Python wrapper

---

## H. Why this doc exists

Without an explicit execution envelope,
Candidate B proof results are too easy to misattribute.
This doc removes that ambiguity before any implementation work starts.
