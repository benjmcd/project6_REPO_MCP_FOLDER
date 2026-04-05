# 03T Report/Export Run Visibility Matrix

## Purpose

Enumerate the verified report/export surfaces that remain tied to shared run identity and therefore defeat any claim that root separation alone is sufficient isolation.

## Verified surfaces

### Evidence report assembly
- file: `nrc_aps_evidence_report.py`
- source run identity: `run_id` from persisted source citation-pack payload
- shared state coupling: `_candidate_run(db, run_id)` -> `ConnectorRun`
- persistence coupling: writes report refs/summaries into `run.query_plan_json`

### Evidence report export
- file: `nrc_aps_evidence_report_export.py`
- source run identity: `run_id` from persisted source report payload
- shared state coupling: `_candidate_run(db, run_id)` -> `ConnectorRun`
- persistence coupling: writes export refs/summaries into `run.query_plan_json`

### Evidence report export package
- file: `nrc_aps_evidence_report_export_package.py`
- source run identity: `owner_run_id`
- shared state coupling: `_candidate_run(db, owner_run_id)` -> `ConnectorRun`
- persistence coupling: writes package refs/summaries into `run.query_plan_json`
- additional constraint: rejects cross-run package composition in v1

## Operational implication

If experiment runs share the same run-visible report/export surfaces, then:
- separate storage roots do not make them invisible,
- separate artifact roots do not make them invisible,
- baseline-facing report/export state can still incorporate experiment-derived outputs.

## First-pass rule

No experiment is sufficiently isolated for the first integrated phase if it remains able to:
- resolve a baseline-visible `ConnectorRun`,
- persist report/export/package refs or summaries into shared `run.query_plan_json`,
- or become selectable/retrievable through baseline-facing run-bound report/export surfaces.
