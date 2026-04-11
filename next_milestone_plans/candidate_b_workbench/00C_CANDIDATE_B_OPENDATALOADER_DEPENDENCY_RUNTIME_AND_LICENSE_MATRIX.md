# 00C - Candidate B OpenDataLoader Dependency, Runtime, and License Matrix

## Purpose

Freeze the exact dependency/runtime/legal posture for Candidate B v1.

v6 strengthens v5 in two ways:
- the package pin now includes the currently verified wheel SHA256
- the dependency posture now chooses one preferred workbench-only delivery form instead of leaving it equally ambiguous

---

## A. Repo runtime target (authoritative for v1)

Candidate B v1 must align to the repo runtime stated by the live root README:
- Windows PowerShell
- Python 3.12 via `py -3.12`

This is the repo execution target.
It takes precedence over weaker generic library minima when planning repo work.

---

## B. OpenDataLoader runtime requirement and exact source posture

Directly verified release sources for this pass:
- exact PyPI release JSON: `https://pypi.org/pypi/opendataloader-pdf/2.0.0/json`
- exact published wheel: `opendataloader_pdf-2.0.0-py3-none-any.whl`
- project homepage declared by PyPI: `https://github.com/opendataloader-project/opendataloader-pdf`

The exact 2.0.0 release description states:
- Python 3.9 or later
- Java 11+ on `PATH`

The exact 2.0.0 PyPI metadata states:
- `Requires-Python >=3.10`

For Candidate B v1 that becomes:
- Python 3.12 (repo target)
- Java 11+ (library/runtime requirement)

No lower Python version is approved for repo execution planning in v1.

---

## C. Candidate B v1 package pin

The directly verified release pinned for Candidate B v1 is:
- `opendataloader-pdf==2.0.0`

Directly verified published wheel:
- filename: `opendataloader_pdf-2.0.0-py3-none-any.whl`
- SHA256: `18093fa87a3089abdba14043c187f85c6a4af48c4597710de32d90e95666313e`

Pin rule:
- v1 docs pin `opendataloader-pdf==2.0.0`
- preferred workbench requirements sidecar uses that exact pin plus the verified hash
- implementation preflight must still revalidate whether the published release line changed before code is opened
- if the adopted version changes, the docs must be updated **before** code is merged

---

## D. License posture

Directly verified nuance for this pass:
- the exact 2.0.0 wheel metadata does **not** carry a populated `License` field
- the exact 2.0.0 wheel inspected in the planning pass did not expose an embedded license file
- the isolated preflight install for `opendataloader-pdf==2.0.0` exposes `License-Expression: Apache-2.0` in the installed distribution metadata
- the exact 2.0.0 PyPI release description states that pre-2.0 remains MPL-2.0 and 2.0+ moves to Apache-2.0
- the project homepage declared by PyPI points to the GitHub repository that also presents the project as Apache-2.0 licensed

Therefore the working legal posture for Candidate B v1 is:
- the exact pinned installed distribution used for isolated workbench preflight now directly presents `Apache-2.0` through `License-Expression`
- workbench-only exploration may target the v2 Apache-2.0 branch
- broader adoption should still re-check the upstream repo/tag license surface at implementation time because the legacy `License` field in the wheel metadata remains unpopulated

---

## E. Dependency surface in v1

### Hard rule
Do **not** modify `backend/requirements.txt` in Candidate B v1.

Reason:
- Candidate B is not integrated runtime work in v1
- the live repo's lower-layer owner path remains PyMuPDF-based
- widening backend runtime dependencies before proof would overstate Candidate B readiness

### Preferred v1 dependency posture
Create and use a dedicated sidecar requirements file under tests/workbench space:
- `tests/requirements_nrc_aps_candidate_b_opendataloader.txt`

Preferred contents:
```text
opendataloader-pdf==2.0.0 --hash=sha256:18093fa87a3089abdba14043c187f85c6a4af48c4597710de32d90e95666313e
```

Use with:
```powershell
py -3.12 -m pip install --require-hashes -r tests/requirements_nrc_aps_candidate_b_opendataloader.txt
```

### Emergency local-preflight fallback only
If the sidecar file has not yet been created and a local exploratory proof must happen first,
this is the only acceptable fallback:
```powershell
py -3.12 -m pip install opendataloader-pdf==2.0.0
```

That fallback is not the preferred reproducible path.
If it is used, the next pass must convert to the hashed sidecar file before any merge-oriented work.

---

## F. Other dependency/control rules

### Allowed in v1
- `opendataloader-pdf==2.0.0`
- Java 11+ as a required local runtime prerequisite once execution opens

### Forbidden in v1
- hybrid backend packages or services
- Docling or other AI backend additions
- Node.js package adoption for Candidate B v1
- direct Java/JAR integration as the v1 path
- changes to backend runtime dependency surfaces

---

## G. Why this dependency posture is correct

This posture is the smallest one that is:
- reproducible
- repo-aligned
- legally explicit
- hash-verifiable
- reversible
- non-invasive to the current lower-layer owner path

That is exactly what Candidate B v1 needs.
