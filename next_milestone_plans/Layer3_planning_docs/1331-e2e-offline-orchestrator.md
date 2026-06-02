# 1331 - SEC XBRL Offline Evidence Orchestrator

Milestone:
`sec_xbrl_e2e_offline_evidence_orchestrator_v1`

Base authority: `project6-origin/main` at
`c2248ea9d4f4fcc97987e6f2144fa6cc5875cabe`

Prior milestone:
`sec_xbrl_e2e_statement_packet_integration_phase0_contract_map_v1`

## Status

Branch-local Tier-2 risk-assessed service proof.

This pass adds an offline, already-loaded evidence orchestrator that composes
the current SEC XBRL canonical projection, redacted projection persistence,
redacted statement-packet persistence, and operator-review workflow services.
It does not add schema, `models.py`, Alembic migrations, backend API/UI,
source acquisition, Arelle subprocess execution, value reveal, runtime-default
changes, raw runtime artifacts, or a production-readiness claim.

The Tier-2 surface is durable persistence composition through existing
materializers in isolated test state. No persistence schema or materializer
implementation changes are introduced.

## Claim Ledger

Repo-confirmed:

- `backend/app/services/layer3_sec_xbrl_e2e_offline_orchestrator.py` accepts an
  explicit in-memory offline evidence bundle rather than a storage path or live
  source-acquisition request.
- The orchestrator requires governed sidecar `resolved_fact_projection`,
  sidecar receipt hash, value-store hash, value records, companyfacts, and
  statement-role authority records before persistence.
- Sidecar `resolved_fact_projection` entries must be object-shaped, hash-fresh
  when `resolved_fact_inventory_hash` is present, bound to resolved fact ids,
  raw-value-free, and marked `value_redacted: true`.
- Value-store records must hash to the declared value-store hash, and optional
  sidecar value-store authority hashes must match.
- Statement-role authority records are normalized and rejected if they expose
  raw identity, accession, SEC URL, or local-path authority.
- The orchestrator builds private canonical projection output, adapts it to
  redacted projection persistence, builds a reviewable statement packet, and
  only then calls the existing materializers/workflow opener.
- `backend/tests/test_sec_xbrl_e2e_offline_orchestrator.py` proves the happy
  path and three fail-closed paths in isolated in-memory DB state.

Inference:

- The next implementation gap is not the in-memory composition contract. It is
  a bounded offline evidence loading/diagnostic layer that can locate
  operator-supplied governed artifacts without source acquisition, Arelle
  invocation, raw runtime artifact persistence, or production admission.

## Contract Boundary

Input is already-loaded offline evidence:

- `companyfacts`;
- governed sidecar receipt with `resolved_fact_records` and
  `resolved_fact_projection`;
- value store with `value_records`;
- statement-role view records; and
- optional dataset version id.

Output is an opened redacted operator-review workflow and hash-only authority
summary. Public output rejects raw identity, accessions, SEC URLs, local paths,
and raw value fields.

## Fail-Closed Rules

- Missing companyfacts, sidecar receipt, value store, or statement-role
  authority blocks before persistence.
- Missing sidecar `resolved_fact_projection` blocks before persistence.
- Stale sidecar projection hash or value-store hash blocks before persistence.
- Statement-role records that do not bind projected facts block statement-packet
  readiness before persistence.
- Raw identity, accession, SEC URL, local path, or raw values in public
  authority/output block admission.

## Containment And Rollback

Existing materializers still commit per stage; this service does not claim a
single cross-stage transaction. Containment is:

- authority and statement-packet preflight before the first persistence write;
- isolated in-memory DB verification;
- no schema/model/migration changes; and
- hash-only public provenance.

Rollback is code and tracking only: remove the orchestrator service, remove the
focused test file, and revert this planning/proof/manifest entry. No database
rollback is required by this branch because no schema or migration changes are
introduced.

## Non-Goals

- no production runtime activation;
- no API/UI route;
- no source acquisition, live SEC network access, or Arelle subprocess;
- no schema, `models.py`, Alembic migration, or model change;
- no durable persistence schema or materializer change;
- no value reveal or default-on behavior;
- no operator packet submission; and
- no production-readiness claim.

## Verification

Focused verification:

`python -m pytest ./backend/tests/test_sec_xbrl_e2e_offline_orchestrator.py -q`

Result: `4 passed`.

Adapter plus orchestrator verification:

`python -m pytest ./backend/tests/test_sec_xbrl_e2e_integration.py ./backend/tests/test_sec_xbrl_e2e_offline_orchestrator.py -q`

Result: `8 passed`.

Broader verification:

`python -m pytest` over explicit `./backend/tests/test_sec_xbrl*.py`
enumeration.

Result: `379 passed, 3 warnings`.

`python -m py_compile ./backend/app/services/layer3_sec_xbrl_e2e_offline_orchestrator.py ./backend/tests/test_sec_xbrl_e2e_offline_orchestrator.py`

Result: pass.

`python ./tools/l3-target-selection-validate.py --expect frozen`

Result: pass.

`python ./tools/l3-progress-check.py`

Result: pass.

`python -c "import json; ..."` over the two Layer 3 manifests with
`utf-8-sig`.

Result: pass.

Path-aware redaction/residual scan over committed SEC XBRL reports.

Result: `59` reports scanned with `0` identity hits, `0` raw scalar value
hits, and `0` nonzero residual magnitudes.

`git diff --check`

Result: pass, with Git LF-to-CRLF working-copy warnings only.

## Next Safe Action

Open a bounded offline evidence loader/diagnostic pass only after review of
this service proof. That pass should locate already-acquired operator evidence,
build this in-memory evidence bundle, and stop if any required governed
authority is absent, stale, raw, ambiguous, or only obtainable through live
source acquisition.
