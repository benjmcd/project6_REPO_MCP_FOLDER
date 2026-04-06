# 05F M5 Approve-As-Is Execution Packet

## Purpose

Freeze the concrete execution packet for the next MVVLC milestone after merged M3/M4 closure.

This doc does **not** claim that the exact M5 coexistence mechanism is already implemented in live code.
`03Z` now freezes that mechanism itself.
This doc freezes the exact owner boundary, validation boundary, widening rules, and review expectations for implementing the frozen mechanism.

---

## Current milestone position

- M3 baseline-only selector bootstrap is merged and accepted.
- M4 acceptance closure is merged and recorded.
- `03Y` closes the standalone field-sensitivity inventory.
- `03Z` closes the exact coexistence / visibility mechanism design.
- The next milestone is M5: controlled experiment runtime-root coexistence plus baseline-facing visibility control.

What remains before M5 can be called approve-as-is is not another baseline closure pass.
It is a bounded M5 lane that implements and proves the frozen coexistence / visibility mechanism under the packet below.

---

## Canonical live authority chain for the M5 lane

The next lane must start from these live authority files:

- `backend/app/services/review_nrc_aps_runtime_roots.py`
- `backend/app/services/review_nrc_aps_runtime.py`
- `backend/app/services/review_nrc_aps_runtime_db.py`
- `backend/app/services/review_nrc_aps_catalog.py`
- `backend/app/api/review_nrc_aps.py`
- `backend/app/services/review_nrc_aps_document_trace.py`
- `backend/app/services/nrc_aps_content_index.py`
- `backend/app/services/nrc_aps_evidence_report.py`
- `backend/app/services/nrc_aps_evidence_report_export.py`
- `backend/app/services/nrc_aps_evidence_report_export_package.py`
- `backend/app/services/connectors_sciencebase.py`

The M5 lane must also respect the already-frozen control docs:

- `03I_RUNTIME_ROOT_AND_RUN_NAMESPACE_POLICY.md`
- `03K_DIAGNOSTICS_REF_PERSISTENCE_POLICY.md`
- `03L_RUNTIME_DB_BINDING_AND_ISOLATION_POLICY.md`
- `03N_EXPERIMENT_ISOLATION_MECHANISM_POLICY.md`
- `03Q_REVIEW_CATALOG_REPORT_VISIBILITY_BLOCKER_POLICY.md`
- `03S_REVIEW_API_ENDPOINT_EXPOSURE_MATRIX.md`
- `03T_REPORT_EXPORT_RUN_VISIBILITY_MATRIX.md`
- `03Y_REVIEW_REPORT_EXPORT_FIELD_SENSITIVITY_MAP.md`
- `03Z_EXACT_M5_BASELINE_VISIBILITY_AND_RUNTIME_ROOT_COEXISTENCE_MECHANISM.md`

---

## Exact lane outcome required

The next lane must make all of the following true:

1. experiment runtime roots do not become baseline-discoverable through default review/runtime discovery
2. experiment runs do not appear in baseline-facing run selectors
3. baseline-facing review endpoints do not expose experiment run state by `run_id`
4. baseline-facing report/export/package persistence does not make experiment outputs visible through shared `ConnectorRun.query_plan_json`
5. baseline diagnostics/runtime DB semantics for accepted baseline runs remain unchanged
6. baseline artifact/ref/hash/byte behavior remains unchanged where the lane does not explicitly reopen it

If the implementation cannot make all six true, it is not approve-as-is.

---

## Exact owner-file boundary

### Primary owner files expected to change

These are the only files that should be assumed editable at the start of the M5 lane:

- `backend/app/services/review_nrc_aps_runtime_roots.py`
- `backend/app/services/review_nrc_aps_runtime.py`
- `backend/app/services/review_nrc_aps_catalog.py`
- `backend/app/api/review_nrc_aps.py`
- `backend/app/services/nrc_aps_evidence_report.py`
- `backend/app/services/nrc_aps_evidence_report_export.py`
- `backend/app/services/nrc_aps_evidence_report_export_package.py`

### Conditional owner promotion files

These are **not** part of the default owner set.
They may become editable only if the primary owner path proves insufficient and the widening is recorded explicitly:

- `backend/app/services/review_nrc_aps_document_trace.py`
- `backend/app/services/review_nrc_aps_runtime_db.py`

### Inspect-only hidden-consumer files

These must be inspected for compatibility, but should remain edit-free unless a repo-confirmed blocker forces widening:

- `backend/app/services/nrc_aps_content_index.py`
- `backend/app/services/connectors_sciencebase.py`
- `backend/app/services/aps_retrieval_plane.py`
- `backend/app/services/aps_retrieval_plane_read.py`
- `backend/app/services/nrc_aps_evidence_bundle.py`
- `backend/app/schemas/review_nrc_aps.py`
- `backend/app/schemas/api.py`

### Exact scope exclusion

The default M5 barrier lane does **not** widen into:

- `backend/app/services/connectors_nrc_adams.py`
- `backend/app/services/nrc_aps_artifact_ingestion.py`
- `backend/app/services/nrc_aps_document_processing.py`

Reason:
- the canonical visibility signal already exists on persisted `ConnectorRun.request_config_json`
- `03Z` freezes a barrier implementation, not upstream admission of new non-baseline integrated run creation
- synthetic non-baseline run rows / runtime fixtures are sufficient to prove the barrier under the validation packet here

If the lane later expands from barrier implementation into actual integrated admission of approved non-baseline runs, that is a separate widening event and must be recorded explicitly.

---

## Exact validation boundary

### Required backend review/runtime bundle

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

### Required root-side report/export bundle

- `tests/test_nrc_aps_evidence_report.py`
- `tests/test_nrc_aps_evidence_report_contract.py`
- `tests/test_nrc_aps_evidence_report_gate.py`
- `tests/test_nrc_aps_evidence_report_export.py`
- `tests/test_nrc_aps_evidence_report_export_contract.py`
- `tests/test_nrc_aps_evidence_report_export_gate.py`
- `tests/test_nrc_aps_evidence_report_export_package.py`
- `tests/test_nrc_aps_evidence_report_export_package_contract.py`
- `tests/test_nrc_aps_evidence_report_export_package_gate.py`

### Additional root-side context bundle

- `tests/test_api.py`
- `tests/test_nrc_aps_document_corpus.py`

### Performance posture

Run `06I` again only if the M5 lane changes:

- runtime-root discovery cost
- run-selector/query behavior
- report/export/package owner-path runtime behavior
- other touched surfaces that can materially affect artifact-aware runtime cost

---

## Exact widening rules

The M5 lane must not widen casually.

Allowed widening trigger classes are only:

1. the chosen coexistence mechanism cannot be implemented without promoting `review_nrc_aps_document_trace.py`
2. the chosen coexistence mechanism cannot preserve baseline runtime-DB behavior without promoting `review_nrc_aps_runtime_db.py`
3. a supposedly inspect-only hidden consumer proves to be a real outward leak surface under execution evidence
4. the lane is explicitly widened from barrier implementation into upstream admission of new non-baseline integrated run creation

Every widening decision must be recorded explicitly in the final report as:

- file widened into
- reason class
- why the primary owner set was insufficient
- what new risk the widening introduced

---

## Exact no-drift assertions the lane must prove

The M5 lane must prove all of the following:

- baseline `get_runs()` behavior remains correct for baseline runs
- baseline overview/tree/node/file-detail/file-preview surfaces remain correct for baseline runs
- baseline document selector / trace / source / diagnostics / normalized-text / indexed-chunk / extracted-unit surfaces remain correct for baseline runs
- baseline report/export/package persistence and retrieval remain correct for baseline runs
- baseline diagnostics-ref persistence remains correct
- baseline runtime DB read-only access and review-root resolution remain correct
- experiment visibility is blocked or absent on baseline-facing surfaces by explicit design, not by accident

---

## Exact status language allowed at the end of the lane

The next lane may be described as approve-as-is only if it provides:

1. the exact coexistence mechanism
2. the exact visibility rule set
3. passing execution evidence for the required validation bundles
4. explicit no-drift findings for diagnostics/runtime DB/report-export surfaces
5. a refreshed `06I` result if the touched surfaces justify rerunning it

Do not use softer overclaim language such as:

- effectively complete
- done pending minor validation
- ready for promotion
- functionally closed

unless the formal evidence above actually exists.

---

## Immediate next action after this packet

The next justified move is:

1. create a fresh merged-main M5 implementation lane
2. re-audit the canonical authority files above
3. re-audit `03Z` and keep it only if live authority still matches
4. implement only within the packet frozen here
5. run the required validation bundles
6. freeze that lane separately

The mechanism is now prepared and frozen; bounded implementation is the next justified step.
