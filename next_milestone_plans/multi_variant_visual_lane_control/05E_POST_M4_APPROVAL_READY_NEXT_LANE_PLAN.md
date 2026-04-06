# 05E Post-M4 Approval-Ready Next-Lane Plan

## Purpose

Define what must be true before a new MVVLC implementation lane can honestly be reviewed as approve-as-is after merged M3/M4 baseline closure.

This doc is for the next later-scope lane only.
It does not reopen the accepted M3/M4 baseline selector/bootstrap path.

---

## Starting position

The current merged baseline is:

1. M3 implemented
2. M4 accepted through T1-T8 and the recorded `06I` local performance gate
3. still bounded to the PDF visual-lane seam
4. still baseline-default in normal runtime

The next milestone scope is M5, not M3/M4 rework.

---

## What approve-as-is means for the next lane

A reviewer should be able to approve the next lane without asking for:

1. architectural clarification about where experiment work is allowed to live
2. missing scope tightening around review/catalog/API/report/export exposure
3. missing no-drift rules for diagnostics, runtime DB, or persistence surfaces
4. missing validation strategy for isolated experiment invisibility
5. hidden file-scope widening after implementation begins
6. missing performance posture when artifact-aware paths are affected

If any of those remain unresolved, the lane is not yet approve-as-is.

---

## Required pre-implementation outputs

### 1. Re-verify the canonical live authority chain

Before implementation, re-audit the current merged root-live sources for:

- review-root discovery
- runtime-root allowlisting
- runtime DB access
- review catalog run discovery
- run-bound review API exposure
- run-bound report/export persistence
- diagnostics persistence

Minimum authority files:

- `backend/app/services/review_nrc_aps_runtime.py`
- `backend/app/services/review_nrc_aps_runtime_roots.py`
- `backend/app/services/review_nrc_aps_runtime_db.py`
- `backend/app/services/review_nrc_aps_catalog.py`
- `backend/app/api/review_nrc_aps.py`
- `backend/app/services/nrc_aps_evidence_report.py`
- `backend/app/services/nrc_aps_evidence_report_export.py`
- `backend/app/services/nrc_aps_evidence_report_export_package.py`
- `backend/app/services/nrc_aps_content_index.py`

### 2. Freeze the exact experiment runtime-root coexistence mechanism

The next lane must define, before code edits:

1. exact experiment root naming and placement
2. exact discovery-exclusion rule for default baseline review/runtime discovery
3. exact relationship between experiment roots and shared `ConnectorRun` rows
4. exact no-seeding / no-cross-run contamination rule

### 3. Freeze the exact baseline-facing visibility rules

The next lane must define, before code edits, what remains baseline-locked across:

- `get_runs()`
- review catalog selector surfaces
- overview/tree/node/file-detail/file-preview surfaces
- document selector / trace / source surfaces
- diagnostics / normalized-text / indexed-chunk / extracted-unit surfaces
- report / export / package persistence and retrieval surfaces

### 4. Freeze the exact no-drift rules

The next lane must define explicit no-change rules for:

- diagnostics-ref persistence semantics
- runtime DB binding and read-only access semantics
- baseline review-root resolution
- baseline report/export `run.query_plan_json` behavior
- baseline artifact/ref/hash/byte semantics where applicable

### 5. Produce the missing field-sensitivity map

Before approve-as-is execution, produce a standalone artifact that maps which review/report/export fields would expose experiment state if not locked down.

This is still missing in the current pack and should not remain implicit.

### 6. Freeze the exact implementation file set

The next lane must name:

- the owner files expected to change
- the validation-only files expected to remain edit-free
- the hidden-consumer files that must be inspected for compatibility only

If that file set cannot be named narrowly in advance, stay in audit mode.

---

## Required validation posture

The next lane must be validate-only and isolated by default.

Required rules:

1. do not seed shared runtime state
2. do not fabricate review roots to make tests pass
3. prefer isolated runtime/artifact roots
4. treat shared audited runtime data as read-only when it must be referenced
5. fail closed on empty or unavailable runtime state rather than silently generating replacement evidence

---

## Required approval evidence

Before the next lane can be described as approve-as-is, it must provide:

1. updated `00F` and `06E` entries matching the exact later-scope mechanism
2. the standalone field-sensitivity map
3. exact validation command bundles with isolated-runtime posture
4. proof that baseline-facing review/catalog/API/report/export surfaces remain locked as intended
5. proof that diagnostics/runtime DB semantics remain unchanged where required
6. proof that no experiment run becomes visible through baseline-default discovery
7. a refreshed `06I` performance assessment if artifact-aware or owner-path runtime cost may change

---

## Not required for approve-as-is

The next lane does not need to solve:

- repo-native CI enforcement of the Python acceptance path
- exhaustive archive/worktree/generated-surface audit
- M6 admission/promotion logic
- simultaneous integrated rollout of multiple non-baseline variants

Those can remain outside the lane if the later-scope implementation itself is fully specified and validated.

---

## Stop conditions

Stop instead of widening scope if the next lane appears to require:

1. public contract change
2. migration requirement unrelated to the narrow coexistence/visibility mechanism
3. OCR or hybrid OCR redesign
4. broad pipeline refactor outside the frozen seam and run-visibility surfaces
5. uncontrolled changes to baseline report/export/review behavior

---

## Recommended execution order

1. Re-audit the root-live authority chain.
2. Produce the standalone field-sensitivity map.
3. Freeze the exact coexistence mechanism and baseline-facing visibility rules.
4. Freeze the narrow implementation and validation packet.
5. Implement on a fresh merged-main worktree.
6. Run the affected grouped acceptance bundles plus any new isolation-specific tests.
7. Re-run `06I` if the changed surfaces justify it.
8. Freeze that lane separately from M3/M4 history.
