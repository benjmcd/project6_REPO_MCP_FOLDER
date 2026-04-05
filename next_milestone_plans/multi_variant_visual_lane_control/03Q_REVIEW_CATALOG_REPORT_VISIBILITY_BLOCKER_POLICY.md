# 03Q Review/Catalog/Report Visibility Blocker Policy

## Purpose

Make explicit a blocker that earlier revisions still left too implicit:
experiments may remain visible to baseline-facing surfaces even when runtime and artifact roots are separated.

## Verified live evidence

### Catalog run discovery
`backend/app/services/review_nrc_aps_catalog.py:discover_candidate_runs()`
- enumerates summary-backed review roots via `discover_review_roots()`
- merges them with `ConnectorRun` rows
- builds the run selector list from them

### Review API run listing
`backend/app/api/review_nrc_aps.py:get_runs()`
- returns `discover_candidate_runs()` directly

### Review API run-bound exposure
`backend/app/api/review_nrc_aps.py` exposes run-bound endpoints for:
- pipeline definition
- overview / tree
- node details
- file details / preview
- document selector rows
- trace manifests
- source blobs
- diagnostics
- normalized text
- indexed chunks
- extracted units

These surfaces first resolve `find_review_root_for_run(run_id)`.
The document-trace/source subset then passes the run-scoped review root plus DB session into document-trace/source helpers, while the overview/tree/node/file subset uses the same resolved root in its own review helpers.

## Current blocker rule

No claim that experiments are “out-of-band” is acceptable unless it also answers:

1. Are experiment runs present in discovered summary-backed review roots or the candidate-run selector inputs?
2. Are experiment runs present in the catalog run selector?
3. Are experiment runs queryable through review API endpoints by `run_id`?
4. If yes, how is that prevented or consciously deferred?

## Current first-pass interpretation

For the first integrated baseline-only phase:

- baseline-facing review/catalog/API surfaces must remain baseline-normalized,
- experiment visibility through those surfaces is a blocker, not a caveat,
- separate storage/artifact roots alone are not enough.

## Additional verified live evidence: report/export

### Evidence report
`nrc_aps_evidence_report.py`
- derives `run_id` from source payloads
- resolves `ConnectorRun`
- persists report refs/summaries into `run.query_plan_json`

### Evidence report export
`nrc_aps_evidence_report_export.py`
- derives `run_id` from source report payloads
- resolves `ConnectorRun`
- persists export refs/summaries into `run.query_plan_json`

### Evidence report export package
`nrc_aps_evidence_report_export_package.py`
- resolves `owner_run_id`
- rejects cross-run package composition in v1
- resolves `ConnectorRun`
- persists package refs/summaries into `run.query_plan_json`

## Current conclusion

The visibility blocker is now directly verified across:
- review/catalog/API surfaces, and
- report/export/package surfaces.

So separate runtime/artifact roots are definitively insufficient, by themselves, for first-phase experiment invisibility.
