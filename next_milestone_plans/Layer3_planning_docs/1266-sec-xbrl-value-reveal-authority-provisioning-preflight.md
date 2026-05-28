# 1266 - SEC XBRL Value-Reveal Authority Provisioning Preflight

## Target

`sec_edgar_arelle_value_reveal_operator_exercise_authority_provisioning_v1`

## Purpose

Doc `1265` proves the operator exercise cannot run from current configured storage because the required persisted Arelle sidecar and bridge/dataset authorities are absent. This packet adds a validate-only preflight for the next pass.

The preflight does not fetch SEC data, run Arelle, create sidecars, create datasets, create audit receipts, reveal values, or enable defaults. It only checks whether the environment is ready for a separately granted authority-provisioning run.

## Diagnostic

Script:

`diagnostics/assessment/sec-xbrl-value-reveal-authority-provisioning-preflight.py`

Report:

`diagnostics/assessment/sec-xbrl-value-reveal-authority-provisioning-preflight-report.json`

Current decision:

`authority_provisioning_preflight_requires_explicit_grant_or_environment`

## Required For A Future Provisioning Run

The actual provisioning run requires an explicit operator grant for:

- live SEC network acquisition using the existing governed connector/source-artifact path
- descriptive SEC User-Agent and existing rate limit
- Arelle subprocess extraction with pinned/off-workspace environment
- taxonomy package and cache paths outside the repo and synced workspace
- isolated storage/runtime state for retained source bytes, sidecar receipts, internal value stores, bridge receipts, and dataset rows

No committed default may be flipped. `LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED`, `LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_CUTOVER_ENABLED`, and `LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED` remain default-off in source.

## Stop Conditions

The provisioning run must stop before reveal if any required authority is missing:

- no retained source bytes
- no READY Arelle sidecar receipt
- no persisted internal value store
- no bridge receipt with matching `dataset_version_id` and `dataset_version_hash`
- no runtime database row for the dataset version
- lineage mismatch between sidecar, source artifact, bridge, and dataset
- redaction scan failure

## Non-Goals

- no default-on Arelle cutover
- no default-on value reveal
- no operator reveal request in the provisioning pass
- no raw values committed
- no raw identity, SEC URL, accession, ticker, local path, storage root, contact, or provider/browser authority disclosure
- no final financial-statement semantics claim
- no cross-company comparability claim
- no Candidate B routing for SEC semantics
- no RAG, model, provider, auth, or UI expansion

## Next Slice

Still:

`sec_edgar_arelle_value_reveal_operator_exercise_authority_provisioning_v1`

The next run must either receive explicit permission to perform the governed live/Arelle authority provisioning, or point the isolated runtime at an already-retained authority set and rerun the preflight plus operator-exercise runner.
