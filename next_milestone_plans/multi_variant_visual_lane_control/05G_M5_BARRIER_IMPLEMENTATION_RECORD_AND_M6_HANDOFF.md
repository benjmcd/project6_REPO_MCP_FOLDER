# 05G M5 Barrier Implementation Record and M6 Handoff

## Purpose

Record the exact outcome of the bounded M5 coexistence / visibility barrier lane that was frozen by `03Z` and `05F`.

This doc is not a new execution packet.
It is the implementation/result record for the current clean M5 lane and the handoff note for the next M6 planning step.

---

## M5 result

The bounded M5 barrier lane is implemented and locally validated in the current clean worktree.

What this lane now makes true:

1. Arbitrary differently named configured storage roots are no longer baseline default-discoverable through `candidate_review_runtime_roots(...)`.
2. Baseline-facing runtime binding discovery now filters by the canonical persisted visibility signal:
   - `ConnectorRun.request_config_json["visual_lane_mode"]`
3. Summary-backed historical runtimes that lack a `ConnectorRun` row remain baseline-visible for backward compatibility.
4. Baseline-facing run selection and direct run-bound review access treat explicit non-baseline runs as absent.
5. Baseline-facing report / export / package persistence now fails closed for experiment-hidden runs and does not attach shared `query_plan_json` refs or failure refs for those runs.

---

## Actual owner-file set

### Changed owner files

- `backend/app/services/review_nrc_aps_runtime_roots.py`
- `backend/app/services/review_nrc_aps_runtime.py`
- `backend/app/services/nrc_aps_evidence_report.py`
- `backend/app/services/nrc_aps_evidence_report_export.py`
- `backend/app/services/nrc_aps_evidence_report_export_package.py`

### Changed test files

- `backend/tests/test_review_nrc_aps_api.py`
- `tests/test_nrc_aps_evidence_report.py`
- `tests/test_nrc_aps_evidence_report_export.py`
- `tests/test_nrc_aps_evidence_report_export_package.py`

### Widening record

No default-owner widening occurred.

This lane did **not** widen into:

- `backend/app/services/review_nrc_aps_runtime_db.py`
- `backend/app/services/review_nrc_aps_document_trace.py`
- `backend/app/api/review_nrc_aps.py`
- `backend/app/services/review_nrc_aps_catalog.py`
- `backend/app/services/connectors_nrc_adams.py`
- `backend/app/services/nrc_aps_artifact_ingestion.py`
- `backend/app/services/nrc_aps_document_processing.py`

---

## Validation record

### Targeted proof set

- `backend/tests/test_review_nrc_aps_api.py`
- `tests/test_nrc_aps_evidence_report.py`
- `tests/test_nrc_aps_evidence_report_export.py`
- `tests/test_nrc_aps_evidence_report_export_package.py`

Result:
- `26 passed`

### Required backend review/runtime bundle

Canonical repo-root `pytest` posture with `PYTHONPATH=backend`:

- `backend/tests/test_review_nrc_aps_catalog.py`
- `backend/tests/test_review_nrc_aps_api.py`
- `backend/tests/test_review_nrc_aps_details.py`
- `backend/tests/test_review_nrc_aps_tree.py`
- `backend/tests/test_review_nrc_aps_graph.py`
- `backend/tests/test_review_nrc_aps_document_trace_api.py`
- `backend/tests/test_review_nrc_aps_document_trace_service.py`
- `backend/tests/test_review_nrc_aps_document_trace_page.py`
- `backend/tests/test_review_nrc_aps_runtime_db.py`
- `backend/tests/test_diagnostics_ref_persistence.py`

Result:
- `141 passed`

### Required root-side report/export bundle plus context bundle

Canonical repo-root `pytest` posture with `PYTHONPATH=backend`:

- `tests/test_nrc_aps_evidence_report.py`
- `tests/test_nrc_aps_evidence_report_contract.py`
- `tests/test_nrc_aps_evidence_report_gate.py`
- `tests/test_nrc_aps_evidence_report_export.py`
- `tests/test_nrc_aps_evidence_report_export_contract.py`
- `tests/test_nrc_aps_evidence_report_export_gate.py`
- `tests/test_nrc_aps_evidence_report_export_package.py`
- `tests/test_nrc_aps_evidence_report_export_package_contract.py`
- `tests/test_nrc_aps_evidence_report_export_package_gate.py`
- `tests/test_api.py`
- `tests/test_nrc_aps_document_corpus.py`

Result:
- `111 passed`

### 06I rerun

The M5 lane changed runtime-root discovery and run-selector behavior, so `06I` was rerun against merged-main baseline commit `1fabb1ae`.

Tier 1:
- baseline aggregate median: `0.4644343s`
- candidate aggregate median: `0.4387757s`
- result: pass, no regression

Tier 2 declared-root fallback sample:
- baseline aggregate median: `0.5105426s`
- candidate aggregate median: `0.4876121s`
- result: pass, no regression

The preferred real-ADAMS timed Tier 2 sample remains a bounded residual.

---

## No-drift judgment

The current lane provides explicit no-drift evidence for:

- baseline run selector behavior
- baseline direct review-root/runtime DB access
- baseline review/document-trace/diagnostics surfaces
- baseline report/export/package persistence and retrieval
- baseline diagnostics-ref persistence

No outward API/schema widening was required.
No connector/processing owner-path widening occurred.

---

## Approve-as-is judgment

Under the frozen `05F` criteria, this bounded M5 barrier lane is now approve-as-is on the current clean branch.

That judgment is justified because the lane now provides:

1. the exact frozen coexistence mechanism
2. the exact baseline-facing visibility rule set
3. passing execution evidence for the required validation bundles
4. explicit no-drift proof for diagnostics/runtime DB/report-export surfaces
5. a refreshed `06I` result after touching runtime-root discovery and selector behavior

---

## What M5 still does not do

This lane does **not** itself admit new approved non-baseline integrated runs through the connector/processing owner path.

That remains later-scope work and was intentionally excluded by `03Z` and `05F`.

---

## Next justified move

The next justified MVVLC lane is no longer M5 mechanism implementation.
It is a separate M6 planning/freeze lane for controlled admission / promotion.

That next lane should freeze:

1. the exact approved non-baseline admission target and comparison rule
2. the exact owner-file widening into connector / processing path, if required
3. the exact baseline-comparison and explicit-approval gate
4. the exact validation packet for admitting one approved variant at a time without widening to multiple simultaneous integrated variants

Repo-native Python enforcement remains a valid parallel hardening lane, but it is not the primary next MVVLC milestone step.
