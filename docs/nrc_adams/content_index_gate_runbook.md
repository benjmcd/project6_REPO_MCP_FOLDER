# NRC APS Content Index Gate Runbook

> Status note (2026-03-11): current NRC APS status, proof artifacts, closed-layer guidance, and next-step handoff are frozen in [nrc_aps_status_handoff.md](nrc_aps_status_handoff.md). This runbook remains gate-specific/operator-procedural.

## Purpose
This runbook defines the local fail-closed gate for APS content-unit indexing artifacts and artifact-vs-DB parity.

The gate validates:
- run artifact schema: `aps.content_index_run.v1`
- failure artifact schema: `aps.content_index_failure.v1` (when present)
- per-target content artifact schema: `aps.content_units.v1`
- contract ids: `aps_content_units_v1` + `aps_chunking_v1`
- artifact checksums and refs
- derived DB parity for document/chunk/linkage rows

## Command
Run from repo root:

```powershell
.\project6.ps1 -Action validate-nrc-aps-content-index
```

Direct CLI:

```powershell
py -3.12 tools/nrc_aps_content_index_gate.py --report tests/reports/nrc_aps_content_index_validation_report.json
```

Optional direct CLI controls:
- `--run-id <id>` (repeatable): validate specific run(s) only.
- `--limit <n>`: validate latest `n` NRC APS runs when `--run-id` is not supplied.
- `--allow-empty`: do not fail when no matching runs are found.

## Validation Report
- Path: `tests/reports/nrc_aps_content_index_validation_report.json`
- Schema: `aps.content_index_gate.v1`
- Includes per-run failure classes such as:
  - `missing_content_units_ref`
  - `unresolvable_content_units_ref`
  - `content_units_schema_mismatch`
  - `unknown_contract_id`
  - `artifact_db_document_missing`
  - `artifact_db_chunk_count_mismatch`
  - `artifact_db_chunk_missing`
  - `artifact_db_chunk_field_mismatch`
  - `artifact_db_linkage_missing`
  - `checksum_mismatch`

## Pre-Merge Sequence
Use the APS local gate sequence:

```powershell
.\project6.ps1 -Action gate-nrc-aps
```

This executes APS tests plus replay, sync-drift, safeguard, artifact-ingestion, and content-index fail-closed validators.
