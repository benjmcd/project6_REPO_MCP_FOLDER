# 05R - Candidate B OpenDataLoader Workbench Comparison Execution Packet

## Purpose

Turn this frozen planning pack into an execution-ready workbench packet with minimal implementer inference.

This packet does not authorize current implementation by itself.
It defines the narrowest allowed future implementation lane if one is separately opened.

## A. What this packet is for

This packet authorizes only the following future workbench-side implementation classes:
- tests/report-side Candidate B implementation
- workbench dependency sidecar creation
- corpus-label sidecar creation
- proof, compare, and retention-manifest artifact generation

It does not authorize:
- service-layer integration
- runtime selector work
- endpoint, report, or persistence widening
- `backend/requirements.txt` changes
- helper-script or `project6.ps1` widening by default
- generic candidate framework work

## B. Approved new files for a later implementation pass

Approved new files include only:
- `tests/requirements_nrc_aps_candidate_b_opendataloader.txt`
- `tests/fixtures/nrc_aps_docs/v1/candidate_b_opendataloader_labels.json`
- optional `tests/fixtures/nrc_aps_docs/v1/candidate_b_opendataloader_manifest.json`
- `tests/support_nrc_aps_candidate_b_opendataloader.py`
- `tests/test_nrc_aps_candidate_b_opendataloader.py`
- `tests/test_nrc_aps_candidate_b_opendataloader_compare.py`
- durable Candidate B reports under `tests/reports/`
- raw Candidate B outputs under the run-scoped Candidate B raw root

## C. Explicitly forbidden implementation targets

Still forbidden:
- `backend/app/services/...`
- `backend/requirements.txt`
- `project6.ps1`
- `tools/` additions by default
- outward NRC APS endpoint, report, export, context, or deterministic artifact surfaces
- any runtime artifact namespace used by existing NRC APS flows

## D. Exact future implementation sequence

1. confirm clean main-based repo truth surfaces required by `00G`
2. confirm Candidate B is still non-admitted under `05P` and `05Q`
3. confirm the closed PageEvidence lane still remains hold-state only
4. confirm exact Candidate A optional comparison anchors from `04B`
5. revalidate OpenDataLoader package version, hash, license, Java availability, and wrapper API/signature
6. run the existing baseline lower-layer proof unchanged
7. freeze labels sidecar contents before running Candidate B
8. implement Candidate B only through approved tests/report workbench surfaces
9. generate proof, compare, and retention-manifest artifacts
10. run the non-interference sequence defined in `08D`
11. decide using workbench-only decision categories only

At no point may the implementer jump directly from proof to runtime integration.

## E. Why this packet is correct

It binds Candidate B to the current merged baseline, keeps all changes reversible, and makes implementation prove non-interference instead of merely asserting it.
