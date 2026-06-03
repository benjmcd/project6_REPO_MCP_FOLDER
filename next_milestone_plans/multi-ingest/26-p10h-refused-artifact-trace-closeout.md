# Phase P10H Refused Artifact Trace Closeout

## Scope

Phase P10H adds read-only Layer 3 workbench trace/detail surfacing for APS parser-level unsupported-media artifact refusals.

Canonical authority is the persisted APS artifact-ingestion report chain:

- `ConnectorRun.query_plan_json.aps_artifact_ingestion_report_refs.aps_artifact_ingestion`
- `aps.artifact_ingestion_run.v1`
- `aps.artifact_ingestion_target.v1`

The implemented trace endpoint emits `layer3.aps_refused_artifact_traces.v1` with `layer3.aps_refused_artifact_trace.v1` rows only for `artifact_unsupported_media_type` target failures.

## Implemented Boundary

- Adds `layer3_workbench.aps_refused_artifact_traces(...)`.
- Adds `GET /api/v1/layer3/aps-refused-artifact-traces`.
- Renders parser-level refused artifacts in the existing source-family summary panel.
- Carries run ID, target ID, accession, failure code/stage/message, media evidence, artifact refs, and read-only authority refs.
- Requires the target artifact ref to resolve, any declared target-row SHA-256 to match the referenced file bytes, and the target payload to pass existing APS target-artifact validation before surfacing a trace.
- Keeps every refused artifact `selectable=false`, `materialization_state="refused_without_material_candidate"`, and `admission_state="not_admitted_to_layer3_material"`.

## Negative Boundary

This phase does not:

- create material candidates;
- admit generic XML/HTML or unsupported forms;
- add source shapes or database schema;
- seed or generate runtime artifacts;
- reinterpret Gate C unsupported material snapshots;
- connect mixed qualitative-plus-table package semantics;
- add or depend on Onlook.

Invalid, missing, checksum-mismatched, schema-version-mismatched, malformed, or non-target report refs fail closed by producing no parser-level refused artifact trace rows.

## Validation Plan

Passed commands:

- `python -m pytest .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_page.py -q`: `47 passed`, `3 warnings`.
- `python -m pytest .\backend\tests\test_layer3_api.py -q`: `276 passed`, `4 warnings`.
- `python .\tools\validate_structure.py`: `errors: 0`, `warnings: 283` existing local-path/documentation warnings.
- `python .\tools\l3-progress-check.py`: `PASS`.
- `python .\tools\l3-target-selection-validate.py --expect frozen`: `PASS (frozen)`.
- `git diff --check`: passed with line-ending conversion warnings only.

Browser validation:

- `npx playwright test .\e2e\layer3-workbench.spec.js --project=chromium --grep "typed and deferred APS source-family guardrails"`: `1 passed`.
- `npx playwright test .\e2e\layer3-workbench.spec.js --project=chromium --headed --grep "typed and deferred APS source-family guardrails"`: `1 passed`.

## Residual Work

The remaining broader roadmap is mixed-source package semantics over admitted parser/material authority, legacy CSV bridge deprecation after generic bridge adoption proof, and future refusal trace classes only when a new server-owned failure authority is audited.
