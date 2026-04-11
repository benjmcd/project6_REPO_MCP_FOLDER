# 00C - Candidate B OpenDataLoader Dependency, Runtime, and License Matrix

## Purpose

Freeze the planned workbench-only dependency, runtime, and license posture for Candidate B.

This document records the dependency posture a future implementation pass would have to satisfy.
It does not promote that posture to current repo-runtime authority.

## A. Repo runtime target

Candidate B must align to the repo runtime stated by the live root README:
- Windows PowerShell
- Python 3.12 via `py -3.12`

That is the repo execution target for any workbench activity performed inside this repo.

## B. Planned OpenDataLoader runtime requirement

The Candidate B plan assumes an OpenDataLoader posture that requires:
- Python 3.12 for repo execution
- Java 11+ as an external runtime prerequisite

Important boundary:
- Java presence is not baseline repo truth in this pass
- package metadata, package hash, and wrapper signature are not promoted here to live repo truth
- a future implementation pass must revalidate those points before code begins

## C. Planned package pin

The currently frozen workbench-only planned pin is:
- `opendataloader-pdf==2.0.0`

The currently frozen planned wheel hash is:
- `sha256:18093fa87a3089abdba14043c187f85c6a4af48c4597710de32d90e95666313e`

Hard rule:
- treat that pin and hash as a planned starting posture only
- revalidate package version, wheel hash, and license posture on implementation day
- if any of them changed, amend the pack before implementation proceeds

## D. License posture

Planned v1 legal posture:
- OpenDataLoader PDF v2 branch only
- no pre-v2 adoption
- no fallback to a differently licensed branch by convenience

A future implementation pass must confirm the current package license before code begins.

## E. Dependency surface rules

### Hard rule
Do not modify `backend/requirements.txt` in this objective.

Reason:
- Candidate B is not integrated runtime work
- the live repo lower-layer owner path remains the current merged baseline
- widening backend runtime dependencies before proof would overstate Candidate B readiness

### Preferred workbench-only posture
Use a dedicated sidecar requirements file under `tests/`:
- `tests/requirements_nrc_aps_candidate_b_opendataloader.txt`

Preferred contents:
```text
opendataloader-pdf==2.0.0 --hash=sha256:18093fa87a3089abdba14043c187f85c6a4af48c4597710de32d90e95666313e
```

Preferred install form:
```powershell
py -3.12 -m pip install --require-hashes -r tests/requirements_nrc_aps_candidate_b_opendataloader.txt
```

### Emergency local-preflight fallback only
If the sidecar file does not exist yet and a local exploratory preflight is needed first:
```powershell
py -3.12 -m pip install opendataloader-pdf==2.0.0
```

That fallback is not reproducible enough for merge-oriented implementation work.

## F. Allowed and forbidden dependency posture

Allowed in a future workbench-only implementation pass:
- `opendataloader-pdf==2.0.0` after revalidation
- external Java 11+ after preflight confirmation

Forbidden in this objective:
- backend runtime dependency widening
- Node-based or CLI-based delivery forms by default
- direct Java/JAR integration as the first path
- Docling or other hybrid AI stack additions
- generic candidate framework dependencies

## G. Why this posture is correct

This is the smallest dependency posture that is:
- reversible
- isolated
- compatible with a workbench-only objective
- explicit about license and runtime assumptions
- still subordinate to the current merged baseline
