# 03Z Exact M5 Baseline Visibility and Runtime-Root Coexistence Mechanism

## Purpose

Freeze the exact M5 coexistence / visibility mechanism before implementation.

This document answers the specific question left open by `03I`, `03N`, `03Q`, `03S`, `03T`, `03Y`, and `05F`:

- what exact signal distinguishes baseline-visible runs from experiment-hidden runs
- why runtime-root naming alone is insufficient
- what default review/runtime/report/export behavior must do with that signal
- why the current M5 barrier lane does not need to widen into the connector/processing owner path by default

---

## Verified live anchors this mechanism is built on

1. `review_nrc_aps_runtime_roots.candidate_review_runtime_roots(...)` always includes the default `storage_test_runtime/lc_e2e` bases and also appends a normalized configured `settings.storage_dir` when present.
2. If the configured `settings.storage_dir` is named `storage` or `storage_test_runtime`, normalization appends `/lc_e2e`; if it is differently named, the resolved configured root is still allowlisted directly.
3. `review_nrc_aps_runtime.discover_runtime_bindings()` and `find_runtime_binding_for_run(run_id)` derive run discoverability from those allowlisted summary-backed review roots.
4. `review_nrc_aps_catalog.discover_candidate_runs()` builds the baseline-facing run selector from discovered runtime bindings.
5. `review_nrc_aps_catalog._load_connector_run(binding)` is best-effort and may return `None`; summary-backed historical roots can still remain selector candidates without a `ConnectorRun` row.
6. Run-bound review API surfaces either:
   - resolve `find_review_root_for_run(run_id)` directly, or
   - resolve `runtime_db_session_for_run(run_id)`, which itself depends on discovered runtime bindings.
7. `nrc_aps_evidence_report.py`, `nrc_aps_evidence_report_export.py`, and `nrc_aps_evidence_report_export_package.py` resolve `ConnectorRun` directly by `run_id` / `owner_run_id` from persisted source artifacts and write refs / summaries into shared `run.query_plan_json`.
8. `connectors_sciencebase.py` later merges those shared `query_plan_json` report-ref keys outward.
9. `connectors_nrc_adams.py` already persists the canonical selector control key in `ConnectorRun.request_config_json["visual_lane_mode"]`.
10. Current integrated runtime still fail-closes non-baseline values back to `baseline`; therefore the barrier lane frozen here is about coexistence / visibility control, not upstream admission of new non-baseline run creation.

---

## Rejected mechanisms

### 1. Runtime-root naming alone

Rejected.

Reason:
- default review/runtime discovery already allowlists any configured `settings.storage_dir`
- a differently named root can still become baseline-discoverable if it is routed through that setting

Therefore path naming is necessary but not sufficient.

### 2. Review-summary/root-name heuristics alone

Rejected.

Reason:
- review/catalog/API surfaces expose `run_id`
- report/export/package services resolve `ConnectorRun` directly by `run_id` / `owner_run_id`
- shared `ConnectorRun.query_plan_json` refs are later surfaced outward by `connectors_sciencebase.py`

Therefore filesystem naming alone cannot carry the visibility boundary.

### 3. A new duplicated visibility key in `query_plan_json`

Rejected as the default design.

Reason:
- the repo already has a persisted canonical control slot: `ConnectorRun.request_config_json["visual_lane_mode"]`
- duplicating the classification into a second run-level control key would create policy-duplication and drift debt before it is justified

Do not introduce a new public or semi-public visibility key unless later execution evidence proves the existing canonical control slot is insufficient.

---

## Exact canonical visibility signal

The canonical baseline-facing visibility signal for M5 is:

- `ConnectorRun.request_config_json["visual_lane_mode"]`

Normalization rule for visibility classification:

- if a `ConnectorRun` row exists and the normalized value is exactly `baseline`, the run is baseline-visible
- if a `ConnectorRun` row exists and the normalized value is missing/empty, the run is baseline-visible
- if a `ConnectorRun` row exists and the normalized value is anything other than `baseline`, the run is experiment-hidden
- if no `ConnectorRun` row exists for an otherwise valid summary-backed historical runtime binding, treat that binding as baseline-visible for backward compatibility

This is a fail-closed rule for explicit non-baseline metadata while still preserving legacy summary-backed baseline fixtures and historical runs.

---

## Exact runtime-root coexistence rule

The M5 coexistence mechanism is two-layered:

### Layer 1: root placement

Experiment review/runtime roots must not rely on the baseline default-discovery contract.

That means:
- do not place experiment roots under the default summary-backed baseline roots by accident
- do not route experiment roots through baseline-facing `settings.storage_dir`
- do not treat a differently named configured storage root as sufficient protection by itself

### Layer 2: run-metadata visibility filtering

Default baseline-facing discovery must additionally filter by the canonical run-level visibility signal above.

That means:
- discovered runtime bindings are only baseline-visible if their run metadata qualifies
- direct `run_id` access must not bypass that visibility filter

Path separation and run-metadata visibility filtering are both required.

---

## Exact baseline-facing behavior rules

### Review/runtime/catalog/API

Baseline-facing surfaces must treat experiment-hidden runs as absent.

This applies to:
- `get_runs()`
- default-run selection
- overview / tree / node / file-detail / file-preview surfaces
- document selector / trace / source / visual-artifact / diagnostics / normalized-text / indexed-chunks / extracted-units surfaces

Required behavior:
- experiment-hidden runs must not appear in the baseline-facing run selector
- direct baseline-facing `run_id` access for experiment-hidden runs must fail closed as not found / absent
- baseline-visible runs must retain their current behavior unchanged

### Report / export / package persistence

Baseline-facing report/export/package owner-path persistence must be baseline-visible only.

Required behavior:
- if the owner/source `ConnectorRun` is experiment-hidden, the service must not attach refs or summaries into shared `ConnectorRun.query_plan_json`
- baseline-visible runs keep the current persistence behavior
- missing `ConnectorRun` rows keep current behavior rather than inventing new persistence side effects

### Diagnostics / runtime DB semantics

No new classification logic may alter read-only runtime DB behavior or diagnostics-ref persistence semantics for baseline-visible runs.

---

## Exact owner-boundary implication

The default `05F` owner boundary remains correct for the barrier implementation frozen here.

Why:
- the canonical visibility signal already lives on `ConnectorRun.request_config_json`
- baseline-facing leak surfaces live in runtime-root discovery, runtime binding resolution, review catalog/API, and run-bound report/export/package persistence
- synthetic non-baseline `ConnectorRun` rows and runtime fixtures are sufficient to prove the barrier behavior under tests

Therefore this exact M5 barrier lane does **not** need to widen into:
- `connectors_nrc_adams.py`
- `nrc_aps_artifact_ingestion.py`
- `nrc_aps_document_processing.py`

by default.

If a later lane expands from coexistence / visibility control into actual integrated admission of approved non-baseline run creation, that is a separate widening event and must be recorded explicitly.

---

## Exact non-goals of this mechanism freeze

This document does **not** authorize:
- upstream admission of new non-baseline integrated runtime values
- new public schema keys for run visibility
- query-plan duplication of the canonical visibility signal
- OCR / hybrid OCR redesign
- report/export contract widening
- runtime DB redesign
- summary-format migration

---

## Validation implication

Implementation under `05F` must prove this mechanism with:
- baseline-visible runs that still behave exactly as before
- synthetic experiment-hidden runs that are absent from baseline-facing discovery and direct run-bound access
- synthetic experiment-hidden report/export/package requests that do not write shared `query_plan_json` refs

This proof belongs in the frozen `05F` validation boundary.

---

## Result

The exact M5 coexistence / visibility mechanism is now frozen.

The next justified step is no longer discovery of the mechanism.
It is bounded implementation of this mechanism under `05F`.
