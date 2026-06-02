# 1333 - SEC XBRL Offline CompanyFacts Oracle Packet

Milestone:
`sec_xbrl_offline_companyfacts_oracle_packet_v1`

Base authority: `project6-origin/main` at
`6105a7e86185a06ea00ad45e336ffef59ef785ae`

Prior milestone:
`sec_xbrl_offline_evidence_loader_diagnostic_v1`

## Status

Branch-local Tier-2 risk-assessed validate-only packet diagnostic.

Current-main reconciliation on `project6-origin/main` at
`b5b22385dacc2b98455c4337ca087b31adf73756` records that the same FIZZ storage
now fails the stricter offline-evidence loader before the CompanyFacts oracle
missing check.

This pass adds a CompanyFacts oracle packet validator for already-acquired SEC
XBRL offline evidence. It reads the governed offline storage admitted by the
offline evidence loader and an optional operator-supplied CompanyFacts JSON. It
does not acquire CompanyFacts, download from the SEC, invoke Arelle, persist
database rows, expose API/UI, reveal values, change defaults, or claim
production readiness.

## Claim Ledger

Repo-confirmed:

- `backend/app/services/layer3_sec_xbrl_offline_companyfacts_oracle_packet.py`
  returns a blocked report when no CompanyFacts JSON is supplied.
- Blocked reports preserve the first base offline-storage blocker, including
  redacted `details`, before evaluating CompanyFacts-specific readiness.
- After base storage is admitted, the missing-oracle blocked report keeps the
  base offline storage authority hash/counts while marking
  `operator_review_creation_ready: false` and
  `production_admission_ready: false`.
- When a CompanyFacts JSON is supplied, the validator builds the existing
  offline evidence bundle with that oracle and requires canonical
  multi-period projection readiness with at least one projected fact.
- The ready report exposes only hashes and counts; it does not expose raw
  values, accessions, SEC URLs, local paths, or fact ids.
- `backend/tests/test_sec_xbrl_offline_evidence_loader.py` proves both the
  missing-oracle blocked path and the supplied-oracle ready path.
- The post-merge review fix preserves base offline-storage blockers before the
  oracle-missing blocker and requires at least one CompanyFacts observation
  plus at least one oracle-confirmed projection before reporting packet
  readiness.
- The committed report for the current FIZZ offline storage is blocked with
  `sec_xbrl_offline_evidence_loader_field_missing` and
  `details.field: fact_inventory_hash`; this base-storage blocker is preserved
  before the oracle-missing check.
- A current content-shape scan under `C:/Users/benny/Downloads/sandbox_temp`
  still found no CompanyFacts-shaped JSON payloads, so the CompanyFacts oracle
  remains a later operator-supply requirement after storage authority is
  reconciled.

Inference:

- The next implementation gap is external to repo code: the operator must first
  supply or regenerate governed offline storage whose statement-classification
  receipt carries a matching top-level `fact_inventory_hash`, then supply an
  offline CompanyFacts JSON for the same evidence authority before operator
  review creation readiness can be claimed.

## Contract Boundary

Inputs:

- already-acquired SEC XBRL offline storage;
- expected sidecar and statement-classification hashes when disambiguation is
  required; and
- optional operator-acquired offline CompanyFacts JSON.

Outputs:

- redacted validate-only packet report; and
- if CompanyFacts is supplied and projection is ready, a hash/count-only oracle
  packet readiness decision.

## Fail-Closed Rules

- Missing CompanyFacts JSON blocks with
  `companyfacts_oracle_packet_missing`.
- Missing, malformed, or non-object CompanyFacts JSON blocks before projection.
- Offline storage authority errors are inherited from the offline evidence
  loader, including redacted blocker details, and block before packet readiness.
- Supplied CompanyFacts must produce a ready canonical multi-period projection
  with at least one projected fact.
- Public report output must reject raw accessions, SEC URLs, local paths, raw
  identity text, fact ids, and raw values.

## Containment And Rollback

No schema or migration rollback is required. Rollback is code and tracking
only: revert this branch or archive the packet validator, diagnostic script,
diagnostic report, focused test additions, and planning/proof/manifest entries
per repo convention.

The diagnostic reads only already-acquired local files and writes only the
committed redacted report. It does not mutate operator storage, seed runtime
state, invoke Arelle, contact the SEC, or write database rows.

## Non-Goals

- no CompanyFacts acquisition, download, or substitution;
- no production runtime activation;
- no API/UI route;
- no source acquisition, live SEC network access, or Arelle subprocess;
- no schema, `models.py`, Alembic migration, or model change;
- no durable persistence schema or materializer change;
- no value reveal or default-on behavior;
- no operator source workflow or raw runtime artifact persistence; and
- no production-readiness claim.

## Verification

Focused packet verification:

`python -m pytest ./backend/tests/test_sec_xbrl_offline_evidence_loader.py -q`

Result: `17 passed`.

Post-merge review-fix focused packet verification:

`python -m pytest ./backend/tests/test_sec_xbrl_offline_evidence_loader.py -q`

Result: `17 passed`.

Diagnostic regeneration:

`python ./diagnostics/assessment/sec-xbrl-offline-companyfacts-oracle-packet.py --storage-dir <operator-offline-storage> --expected-sidecar-receipt-hash 16cdcfc6e5486ccfdb2991fac7f46a03f53d802d60841f2e0ff6c488cdf5bb9d --expected-statement-classification-receipt-hash bd95ba6d396a7d645f11e8e0bc4f8e7ca5f6e12f2ec9f50a5f250f43ae938666`

Result: report status `offline_companyfacts_oracle_packet_blocked`, with
blocking reason `sec_xbrl_offline_evidence_loader_field_missing` and
`blocked_reasons[0].details.field: fact_inventory_hash`.

Loader plus offline orchestrator verification:

`python -m pytest ./backend/tests/test_sec_xbrl_offline_evidence_loader.py ./backend/tests/test_sec_xbrl_e2e_offline_orchestrator.py -q`

Result: `21 passed`.

Post-merge review-fix loader plus offline orchestrator verification:

`python -m pytest ./backend/tests/test_sec_xbrl_offline_evidence_loader.py ./backend/tests/test_sec_xbrl_e2e_offline_orchestrator.py -q`

Result: `21 passed`.

Full SEC XBRL suite:

`python -m pytest` over explicit `./backend/tests/test_sec_xbrl*.py`
enumeration.

Result: `396 passed, 3 warnings`.

`python -m py_compile ./backend/app/services/layer3_sec_xbrl_offline_companyfacts_oracle_packet.py ./diagnostics/assessment/sec-xbrl-offline-companyfacts-oracle-packet.py ./backend/tests/test_sec_xbrl_offline_evidence_loader.py`

Result: pass.

`python ./tools/l3-target-selection-validate.py --expect frozen`

Result: pass.

`python ./tools/l3-progress-check.py`

Result: pass.

`python -c "import json; ..."` over changed JSON manifests/reports with
`utf-8-sig`.

Result: `511` JSON files parsed, including `49` committed SEC XBRL reports.

Path-aware redaction/residual scan over committed SEC XBRL reports.

Result: `49` reports scanned with `0` identity hits, `0` raw scalar value
hits, and `0` nonzero residual magnitudes.

`git diff --check`

Result: pass, with Git LF-to-CRLF working-copy warnings only.

## Next Safe Action

First supply or regenerate governed offline storage whose statement-classification
receipt carries a top-level `fact_inventory_hash` matching
`authority_hashes.fact_inventory_hash`. Then provide an operator-acquired
offline CompanyFacts JSON for the same filing authority and rerun this packet
diagnostic with `--companyfacts-json`. Do not download, synthesize, substitute,
or infer the CompanyFacts payload.
