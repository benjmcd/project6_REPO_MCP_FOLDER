# NRC APS Evidence Bundle Gate Runbook

> Status note (2026-03-11): current NRC APS status, proof artifacts, closed-layer guidance, and next-step handoff are frozen in [nrc_aps_status_handoff.md](nrc_aps_status_handoff.md). This runbook remains gate-specific/operator-procedural.

## Purpose
This runbook defines the local fail-closed validator for APS evidence-bundle retrieval artifacts.

The gate validates:
- bundle schema: `aps.evidence_bundle.v1`
- bundle failure schema: `aps.evidence_bundle_failure.v1`
- gate schema output: `aps.evidence_bundle_gate.v1`
- request identity and bundle identity derivation
- ordering determinism and snippet bounds
- provenance ref presence/resolvability
- artifact-vs-DB parity for indexed chunk evidence

## Command
Run from repo root:

```powershell
.\project6.ps1 -Action validate-nrc-aps-evidence-bundle
```

Direct CLI:

```powershell
py -3.12 tools/nrc_aps_evidence_bundle_gate.py --report tests/reports/nrc_aps_evidence_bundle_validation_report.json
```

Optional CLI controls:
- `--run-id <id>` (repeatable): validate specific run(s) only.
- `--limit <n>`: validate latest `n` NRC APS runs when `--run-id` is not supplied.
- `--allow-empty`: do not fail when no matching runs are found.

## Validation Report
- Path: `tests/reports/nrc_aps_evidence_bundle_validation_report.json`
- Schema: `aps.evidence_bundle_gate.v1`
- Stable failure classes include:
  - `missing_bundle_ref`
  - `unresolvable_bundle_ref`
  - `bundle_schema_mismatch`
  - `bundle_failure_schema_mismatch`
  - `unknown_contract_id`
  - `request_identity_mismatch`
  - `missing_provenance_ref`
  - `unresolvable_provenance_ref`
  - `ordering_drift_detected`
  - `snippet_out_of_bounds`
  - `checksum_mismatch`
  - `artifact_db_divergence`

## Pre-Merge Sequence
Use the APS gate sequence:

```powershell
.\project6.ps1 -Action gate-nrc-aps
```
