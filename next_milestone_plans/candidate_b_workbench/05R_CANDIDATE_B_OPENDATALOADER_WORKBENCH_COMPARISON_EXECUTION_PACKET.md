# 05R — Candidate B OpenDataLoader Workbench Comparison Execution Packet

## Purpose

Turn the v6 planning pack into an execution-ready workbench packet with minimal implementer inference.

For the next bounded compare-surface hardening lane, pair this packet with:

- `05T_CANDIDATE_B_OPENDATALOADER_COMPARE_SURFACE_IMPLEMENTATION_PLAN.md`
- `08E_CANDIDATE_B_OPENDATALOADER_COMPARE_SURFACE_VALIDATION_PLAN.md`

---

## A. What this packet is for

This packet authorizes only:
- tests/report-side Candidate B implementation
- workbench dependency sidecar creation
- corpus-label sidecar creation
- proof/compare/retention-manifest artifact generation

It does **not** authorize:
- service-layer integration
- runtime selector work
- endpoint/report/persistence widening
- `backend/requirements.txt` changes
- hybrid/docling additions

---

## B. Approved new files

Approved new files in v1 include only:
- `tests/requirements_nrc_aps_candidate_b_opendataloader.txt`
- `tests/fixtures/nrc_aps_docs/v1/candidate_b_opendataloader_labels.json`
- `tests/test_nrc_aps_candidate_b_opendataloader.py`
- `tests/test_nrc_aps_candidate_b_opendataloader_compare.py` (future optional compare surface; not present in current committed `main`)
- durable Candidate B reports under `tests/reports/`
- raw Candidate B outputs under the run-scoped Candidate B raw root
- adopted docs under the chosen non-authoritative docs destination

---

## C. Explicitly forbidden implementation targets

Still forbidden in v1:
- `backend/app/services/...`
- `backend/requirements.txt`
- outward NRC APS endpoint/report/export/context/deterministic artifact surfaces
- any runtime artifact namespace used by existing NRC APS flows

Bounded follow-on exception:

- `project6.ps1` remains untouched for the currently committed v1 workbench posture
- the separate compare-surface hardening lane in `05T` may add one repo-native Candidate B compare action only

---

## D. Exact implementation sequence

1. confirm on-disk repo truth surfaces required by `00G`
2. create the hashed workbench requirements sidecar
3. create/freeze the labels sidecar before running Candidate B
4. capture the execution envelope required by `00N`
5. run the existing baseline lower-layer proof unchanged
6. implement the Candidate B tests/report workbench only
7. generate proof, compare, and retention-manifest artifacts
8. run the non-interference sequence defined in `08D`
9. decide using the v6 decision categories only

At no point may the implementer jump directly from proof to integration.

---

## E. Why this execution packet is correct

It binds Candidate B to the repo's existing lower-layer proof harness,
keeps all changes reversible,
and makes the implementation prove non-interference instead of merely asserting it.

For the polished compare-surface lane, the main missing ergonomic pieces are:

- a repo-native `project6.ps1` action
- a dedicated compare runner
- a fresh baseline-summary generator so normal use no longer depends on a historical compare artifact path
