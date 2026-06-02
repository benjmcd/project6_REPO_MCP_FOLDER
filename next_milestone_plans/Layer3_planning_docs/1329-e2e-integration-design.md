# 1329 - SEC XBRL End-To-End Statement Packet Integration Design

Milestone:
`sec_xbrl_end_to_end_statement_packet_integration_design_v1`

Base authority: `project6-origin/main` at
`527abcb8d0891d7a42c1ca77f3733397f3d4ae6c`

Prior milestone:
`sec_xbrl_nonlocal_production_admission_or_historical_backfill_disposition_v1`

## Status

Planning-only Tier-2 design/pre-review over current main.

This pass records the missing integration lane between already-landed SEC XBRL
subsystems. It does not implement runtime behavior. It does not touch schema,
`models.py`, Alembic migrations, durable persistence code, backend API/UI,
operator workflow runtime behavior, source acquisition, Arelle subprocess
execution, value reveal, default-on behavior, raw runtime artifacts, or
production-readiness posture.

Future implementation is Tier 2 because it will orchestrate durable projection
and statement-packet persistence plus operator-review workflow creation. Under
the current softened SEC XBRL merge policy, that future pass must record exact
Tier-2 surfaces, narrow tests, rollback or containment notes, and independent
review when practical or when concrete risk triggers remain.

## Claim Ledger

Repo-confirmed:

- `backend/app/services/layer3_sec_xbrl_projection_persistence.py` owns
  `materialize_redacted_projection_set(...)`.
- `backend/app/services/layer3_sec_xbrl_statement_packet_persistence.py` owns
  `materialize_redacted_statement_packet(...)`.
- `backend/app/services/layer3_sec_xbrl_operator_review_workflow.py` owns
  `open_redacted_operator_review_workflow(...)` and
  `record_redacted_operator_review_decision(...)`.
- `backend/app/services/layer3_sec_xbrl_statement_assembly.py` owns
  `assemble_reviewable_statement_packet(...)`.
- Current `backend/app` and `diagnostics` callers include a validate-only
  statement-assembly diagnostic, but no non-test caller that materializes a
  redacted projection set or materializes a redacted statement packet from real
  validated filing evidence.
- `backend/app/api/layer3.py` wires downstream auth, value-reveal, and
  operator-review workflow surfaces, but it does not import projection
  persistence, statement-packet persistence, or statement assembly.
- Existing downstream tests compose projection persistence, statement-packet
  persistence, and operator workflow using test fixtures, not the committed
  real-corpus runner output.

Carried-forward:

- The preceding session review identified the same product seam: components are
  individually implemented and verified, but current main does not yet compose
  validated filing evidence into persisted projection, persisted statement
  packet, and opened operator review workflow in one bounded path.

Inference:

- The next useful SEC XBRL product slice is not another independent leaf
  capability. It is a contract-mapping and adapter/orchestration pass that
  proves the already-built stages can be connected without widening source,
  value, redaction, or production-readiness authority.
- The committed redacted runner report is not sufficient by itself to create
  persisted statement packets. A future implementation needs governed offline
  storage/receipt inputs plus in-memory canonical projection and statement-role
  organization evidence.

## Current Contract Map

1. Governed offline storage and receipts remain the filing-evidence authority.
   The first implementation pass must run offline against already-acquired
   storage only. It must not invoke live SEC network access, source acquisition,
   or Arelle subprocesses.
2. `project_issuer_canonical_facts_by_periods(...)` produces a private
   multi-period canonical projection. That private projection may contain
   transient raw/private fields such as `_value`, `_unit`, `_period_key`,
   `_decimals`, `resolved_fact_id`, `sidecar_receipt_hash`,
   `value_store_hash`, and dataset-version references.
3. A redacted persistence adapter must transform the private projection into
   the shape required by `materialize_redacted_projection_set(...)`. The
   persisted projection must contain `value_redacted: true`,
   `resolved_fact_provenance_present`, sidecar/value-store hashes, dataset
   version evidence where available, and no raw value, raw unit, raw period,
   resolved fact id, issuer identity, accession, local path, SEC URL, or raw
   runtime payload.
4. `organize_canonical_projection_by_statement(...)` requires projection items
   and statement-role view records. If statement-role authority is missing,
   ambiguous, or synthetic, the integration pass must fail closed rather than
   infer final statement semantics.
5. `assemble_reviewable_statement_packet(...)` should run over the in-memory
   projection plus organization result to produce the redacted review packet.
   The adapter boundary must preserve enough private in-memory evidence to mark
   redaction honestly while stripping all private fields before persistence or
   reporting.
6. `materialize_redacted_statement_packet(...)` must bind every packet row to
   an already-persisted projection fact by period, statement, row index,
   canonical id, basis, requested basis, family, and source QName. Multi-period
   rows require explicit period refs.
7. `open_redacted_operator_review_workflow(...)` may open a bounded workflow
   only after the redacted statement packet set is materialized and review
   ready.

## Hard Seams To Resolve

- The public canonical projection helper strips fields that projection
  persistence needs for provenance. The integration adapter must consume private
  in-memory projection evidence and emit a strictly redacted persistence shape.
- Statement assembly needs enough private evidence to set redaction flags
  honestly, while projection persistence rejects private/raw fields. The bridge
  must make that split explicit and test it.
- Statement organization needs real statement-role authority. A first pass must
  define the exact allowed source for role-view records and fail closed when it
  is absent.
- Existing materializers commit internally. The first orchestration pass must
  either stay in an isolated diagnostic/runtime database with idempotent cleanup
  and containment notes, or explicitly refactor for caller-controlled
  transactions in a separate reviewed Tier-2 slice. It must not claim
  all-or-nothing cross-stage atomicity unless the code actually provides it.

## Proposed Next Work Package

Next posture:
`sec_xbrl_e2e_statement_packet_integration_phase0_contract_map_v1`

Phase 0 is read/design/contract-map first:

- verify the exact governed offline inputs needed to build the private
  canonical projection, statement-role organization evidence, and redacted
  persistence payloads;
- write adapter acceptance criteria and fixture contracts without creating a
  production route;
- define the narrow orchestrator entrypoint as a diagnostic/service proof over
  isolated runtime state, not an API/UI/default-on product surface;
- define rollback and containment for partially materialized projection sets,
  statement-packet sets, and workflow receipts; and
- stop if any required authority source is missing, ambiguous, raw, or only
  available by live acquisition.

Phase 1 can implement pure adapters with focused unit tests:

- private canonical projection to redacted projection-persistence payload;
- private projection plus statement organization to reviewable packet payload;
- packet row to persisted projection-fact binding checks; and
- redaction/residual guard tests over adapter outputs.

Phase 2 can implement the bounded orchestration proof only after Phase 0/1
contracts are clean:

- run offline only;
- use isolated runtime state;
- persist redacted projection set, materialize redacted statement packet, and
  open one operator-review workflow;
- emit a redacted diagnostic report with stable ids/hashes/counts only; and
- report partial-stage containment rather than claiming production readiness.

Phase 3 can exercise operator-acquired offline evidence only if the required
inputs are present. It must not synthesize, download, or substitute filings.

## Stop Conditions

- Any required change to `models.py`, Alembic, schema, API/UI, value reveal,
  default-on behavior, source acquisition, Arelle execution, or production
  readiness stops this lane and requires a separately scoped Tier-2 design.
- Any missing sidecar, value-store, statement-role, or offline filing authority
  stops the implementation pass as blocked.
- Any raw value, raw identity, raw accession, SEC URL, local path, local
  evidence filename, residual magnitude, or raw runtime payload in a committed
  report, persisted row, or workflow response stops the pass.
- Any claim that the committed aggregate runner report alone is sufficient to
  materialize statement packets stops the pass; the report is evidence, not the
  complete creation input.

## Verification Plan For Future Implementation

- focused adapter tests for projection redaction, statement packet assembly,
  row binding, fail-closed missing authority, and redaction residual guards;
- focused orchestration test over isolated runtime state proving projection set,
  statement packet set, and workflow creation with no raw values or identities;
- full `backend/tests/test_sec_xbrl*.py` suite by explicit file enumeration;
- `python ./tools/l3-target-selection-validate.py --expect frozen`;
- `python ./tools/l3-progress-check.py`;
- `py_compile` for every touched Python file;
- JSON/report validation with `utf-8-sig`;
- committed SEC XBRL report redaction and residual-magnitude scan; and
- `git diff --check`.

## Next Safe Action

Open `sec_xbrl_e2e_statement_packet_integration_phase0_contract_map_v1` as a
Tier-2 risk-assessed design/contract-map pass. The first deliverable should be
an exact input/output contract and fail-closed acceptance test plan for the
adapter/orchestrator seam, not production runtime activation.
