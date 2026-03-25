# NRC APS Replay Gate Runbook

> Status note (2026-03-11): current NRC APS status, proof artifacts, closed-layer guidance, and next-step handoff are frozen in [nrc_aps_status_handoff.md](nrc_aps_status_handoff.md). This runbook remains gate-specific/operator-procedural.

## Purpose
This runbook defines the local fail-closed replay workflow for NRC APS contract hardening.

The replay gate is network-free and validates:
- parser status classification (`ok`, `empty_body`, `invalid_json`, `non_dict_json`)
- search/document envelope normalization invariants
- count key handling and accession extraction
- logical-query to dialect compile roundtrip shape
- negotiator ordering (forced mode, capability preference, cooldown fallback)
- no opaque failures (every failure-class case must carry evidence refs)

## Canonical Corpus
- Path: `tests/fixtures/nrc_aps_replay/v1`
- Schema major: `1`
- Index file: `tests/fixtures/nrc_aps_replay/v1/index.json`
- Case files: `tests/fixtures/nrc_aps_replay/v1/cases/*.json`

## Pre-Merge Command Sequence
Run from repo root:

```powershell
.\project6.ps1 -Action build-nrc-aps-replay-corpus
.\project6.ps1 -Action check-nrc-aps-replay-corpus
.\project6.ps1 -Action validate-nrc-aps-replay
.\project6.ps1 -Action gate-nrc-aps
```

## Direct CLI
Equivalent direct commands:

```powershell
py -3.12 tools/nrc_aps_replay_gate.py build --source-root backend/app/storage_test/connectors --out tests/fixtures/nrc_aps_replay/v1
py -3.12 tools/nrc_aps_replay_gate.py check --source-root backend/app/storage_test/connectors --corpus tests/fixtures/nrc_aps_replay/v1
py -3.12 tools/nrc_aps_replay_gate.py validate --corpus tests/fixtures/nrc_aps_replay/v1 --report tests/reports/nrc_aps_replay_validation_report.json
```

## Artifacts
- Validation report: `tests/reports/nrc_aps_replay_validation_report.json`
- Corpus diff summary: `tests/reports/nrc_aps_replay_corpus_diff.json`

When corpus content changes, include the corpus diff summary in review so added/removed/changed replay cases and coverage deltas are explicit.

## Override Policy
- Optional override file: `tests/fixtures/nrc_aps_replay/overrides.json`
- Each override must include: `case_id`, `reason`, `expires_on`, `ignore_paths`
- Expired overrides are rejected and fail validation.
