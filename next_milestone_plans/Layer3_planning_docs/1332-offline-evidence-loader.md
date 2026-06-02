# 1332 - SEC XBRL Offline Evidence Loader Diagnostic

Milestone:
`sec_xbrl_offline_evidence_loader_diagnostic_v1`

Base authority: `project6-origin/main` at
`c55f345a7f151d0de8c65b82f4dcd20cf5a5082d`

Prior milestone:
`sec_xbrl_e2e_offline_evidence_orchestrator_v1`

## Status

Branch-local Tier-2 risk-assessed loader/diagnostic proof.

This pass adds a validate-only loader for already-acquired offline SEC XBRL
storage. It locates governed sidecar, internal value-store, statement-role
classification, and bridge dataset-version receipts, builds the existing
offline orchestrator evidence bundle, and emits a redacted diagnostic readiness
report.

It does not add schema, `models.py`, Alembic migrations, backend API/UI,
source acquisition, SEC network access, Arelle subprocess execution, value
reveal, runtime-default changes, raw runtime artifacts, operator source
workflow, or a production-readiness claim.

The Tier-2 surface is a service path that can feed already-acquired evidence
into the existing durable operator-review composition path in tests. No
persistence schema or production runtime activation is introduced.

## Claim Ledger

Repo-confirmed:

- `backend/app/services/layer3_sec_xbrl_offline_evidence_loader.py` reads only
  an operator-supplied local storage directory and optional CompanyFacts JSON.
- The loader requires exactly one governed sidecar receipt unless an expected
  sidecar hash disambiguates the storage.
- The loader requires the sidecar `resolved_fact_projection`, verifies its
  hash against `resolved_fact_inventory_hash`, verifies it binds every resolved
  fact id, and rejects non-redacted projection entries.
- The loader requires the matching internal value store, verifies sidecar
  lineage, value-store hash, and value-record count, and fails closed before
  bundle admission on stale value-store evidence.
- The loader requires exactly one statement-classification receipt unless an
  expected classification hash disambiguates the storage, and requires that
  classification authority bind to the selected sidecar receipt and resolved
  fact inventory.
- The loader requires bridge-derived dataset-version provenance instead of
  inventing or defaulting a dataset version id.
- The committed diagnostic report has status
  `offline_evidence_bundle_ready_without_companyfacts_oracle`, with
  `operator_review_creation_ready: false`,
  `production_admission_ready: false` and
  `production_admission_blocked_reason: companyfacts_oracle_not_supplied`.
- `backend/tests/test_sec_xbrl_offline_evidence_loader.py` proves one
  CompanyFacts-supplied loader-to-review path in isolated in-memory DB state,
  one redacted no-CompanyFacts diagnostic path, and two fail-closed stale or
  ambiguous authority paths.

Inference:

- The next gap is not offline storage discovery for the FIZZ evidence shape. It
  is the missing offline CompanyFacts oracle packet and any operator decision
  about whether a production-admission gate may consume that oracle.

## Contract Boundary

Input is already-acquired offline evidence:

- governed sidecar receipt with `resolved_fact_records` and
  `resolved_fact_projection`;
- sidecar internal value store with `value_records`;
- governed statement-classification receipt;
- bridge receipt carrying dataset-version provenance; and
- optional offline CompanyFacts JSON.

Output is either an in-memory evidence bundle for the existing offline
orchestrator, or a redacted readiness report. Public report output contains
hashes and counts only. It rejects raw accessions, SEC URLs, local paths, raw
identity text, and raw values.

## Fail-Closed Rules

- Missing storage, sidecar receipt, value store, statement-classification
  receipt, or bridge dataset-version provenance blocks admission.
- Ambiguous sidecar or statement-classification receipts block unless the
  expected hash selects one.
- Missing or stale sidecar `resolved_fact_projection` blocks admission.
- Stale value-store hash, mismatched value-store count, or sidecar/value-store
  lineage mismatch blocks admission.
- Statement classification that does not bind to the selected sidecar receipt
  and resolved-fact inventory blocks admission.
- Missing CompanyFacts does not block diagnostic bundle readiness, but it does
  block operator-review creation and production admission.

## Containment And Rollback

No schema or migration rollback is required. Rollback is code and tracking
only: revert this branch or archive the loader service, diagnostic script,
focused test file, diagnostic report, and this planning/proof/manifest entry
per repo convention.

The diagnostic writes only the committed redacted report. It does not mutate the
operator storage directory, seed runtime state, invoke Arelle, contact the SEC,
or write database rows. The focused happy-path test exercises existing
materializers only in isolated in-memory DB state.

## Non-Goals

- no production runtime activation;
- no API/UI route;
- no source acquisition, live SEC network access, or Arelle subprocess;
- no schema, `models.py`, Alembic migration, or model change;
- no durable persistence schema or materializer change;
- no value reveal or default-on behavior;
- no operator source workflow or raw runtime artifact persistence;
- no CompanyFacts acquisition or substitution; and
- no production-readiness claim.

## Verification

Focused loader verification:

`python -m pytest ./backend/tests/test_sec_xbrl_offline_evidence_loader.py -q`

Result: `4 passed`.

Loader plus offline orchestrator verification:

`python -m pytest ./backend/tests/test_sec_xbrl_offline_evidence_loader.py ./backend/tests/test_sec_xbrl_e2e_offline_orchestrator.py -q`

Result: `8 passed`.

Diagnostic regeneration:

`python ./diagnostics/assessment/sec-xbrl-offline-evidence-loader.py --storage-dir <operator-offline-storage> --expected-sidecar-receipt-hash 16cdcfc6e5486ccfdb2991fac7f46a03f53d802d60841f2e0ff6c488cdf5bb9d --expected-statement-classification-receipt-hash bd95ba6d396a7d645f11e8e0bc4f8e7ca5f6e12f2ec9f50a5f250f43ae938666`

Result: report status
`offline_evidence_bundle_ready_without_companyfacts_oracle`, with
`operator_review_creation_ready: false` and `production_admission_ready: false`.

Full SEC XBRL suite:

`python -m pytest` over explicit `./backend/tests/test_sec_xbrl*.py`
enumeration.

Result: `383 passed, 3 warnings`.

`python -m py_compile ./backend/app/services/layer3_sec_xbrl_offline_evidence_loader.py ./diagnostics/assessment/sec-xbrl-offline-evidence-loader.py ./backend/tests/test_sec_xbrl_offline_evidence_loader.py`

Result: pass.

`python ./tools/l3-target-selection-validate.py --expect frozen`

Result: pass.

`python ./tools/l3-progress-check.py`

Result: pass.

`python -c "import json; ..."` over changed JSON manifests/reports with
`utf-8-sig`.

Result: pass.

Path-aware redaction/residual scan over committed SEC XBRL reports.

Result: `60` reports scanned with `0` identity hits, `0` raw scalar value
hits, and `0` nonzero residual magnitudes.

`git diff --check`

Result: pass, with Git LF-to-CRLF working-copy warnings only.

## Next Safe Action

Do not claim production admission from this diagnostic. The next bounded pass
should supply or validate an operator-acquired offline CompanyFacts oracle
packet for the same evidence authority, without source acquisition, live SEC
network access, Arelle invocation, or raw value/public identity leakage.
