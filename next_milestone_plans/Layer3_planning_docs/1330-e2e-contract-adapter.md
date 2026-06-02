# 1330 - SEC XBRL End-To-End Contract Adapter

Milestone:
`sec_xbrl_e2e_statement_packet_integration_phase0_contract_map_v1`

Base authority: `project6-origin/main` at
`527abcb8d0891d7a42c1ca77f3733397f3d4ae6c`

Prior milestone:
`sec_xbrl_end_to_end_statement_packet_integration_design_v1`

## Status

Branch-local Tier-2 risk-assessed adapter and binding proof.

This pass implements the first Phase 0 contract bridge from private canonical
projection output to the existing redacted persistence/workflow services. It
does not add schema, `models.py`, Alembic migrations, backend API/UI, source
acquisition, Arelle subprocess execution, value reveal, runtime-default
changes, raw runtime artifacts, or production-readiness behavior.

The implementation touches service behavior because statement assembly must
preserve period refs and assign statement row indexes per statement-period for
multi-period persisted packet binding. That behavior is necessary for the
existing statement-packet persistence contract, which binds rows by period,
statement, statement row index, canonical id, basis, family, and source QName.

## Claim Ledger

Repo-confirmed:

- `backend/app/services/layer3_sec_xbrl_e2e_integration.py` adapts private
  canonical projection output into redacted projection-persistence payloads.
- The adapter strips raw/private value and authority fields before persistence
  payload emission while preserving hash-only sidecar/value-store provenance.
- The same adapter can build a redacted reviewable statement packet from
  private projection items plus statement-role view records.
- `backend/app/services/layer3_sec_xbrl_statement_assembly.py` now carries
  `period_ref` and `period_index` through public packet rows when supplied, and
  assigns `statement_row_index` per `(statement, period_ref, period_index)`.
- `backend/tests/test_sec_xbrl_e2e_integration.py` proves a two-period fixture
  can flow through redacted projection persistence, redacted statement-packet
  persistence, and operator-review workflow opening in isolated in-memory DB
  state.

Inference:

- The next implementation gap is no longer the pure adapter shape. It is the
  offline evidence reader/orchestrator that invokes the adapter using real
  governed sidecar/value-store/statement-role authority, with rollback or
  containment around the existing committing materializers.

## Contract Boundary

The adapter has two outputs:

1. redacted projection persistence payload:
   - ready multi-period projection status;
   - period refs/indexes;
   - projected concepts only;
   - `value_redacted: true`;
   - `resolved_fact_provenance_present: true`;
   - sidecar receipt hash, value-store hash, and optional dataset version id;
   - no raw value, resolved fact id, sidecar receipt id, period key, accession,
     CIK, SEC URL, local path, raw period date, or raw runtime payload.
2. reviewable statement packet:
   - built from private in-memory projection rows;
   - statement-role view records are the A-role corroboration authority;
   - period refs/indexes are retained in packet rows;
   - row indexes are scoped by statement and period so persistence binding can
     match projection facts exactly.

## Repo-Confirmed Authority Split

The next orchestrator must join two governed authority families; it must not
assume one receipt contains both:

- Resolved-fact and value-store authority comes from
  `backend/app/services/layer3_sec_xbrl_sidecar.py`
  (`read_sec_edgar_arelle_resolved_fact_authority_sidecar_receipt` and
  `read_sec_edgar_arelle_resolved_fact_authority_internal_value_store`), where
  the governed sidecar receipt writes `resolved_fact_records`,
  `resolved_fact_projection`, sidecar hashes, and internal value-store metadata.
- Statement-role placement authority comes from
  `backend/app/services/layer3_sec_edgar_html_inline_xbrl_fact_statement_classification.py`
  (`statement_role_view_from_retained_records` and
  `inspect_sec_edgar_html_inline_xbrl_fact_statement_classification_status`) and
  may be packaged by
  `backend/app/services/layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product.py`
  (`inspect_sec_edgar_html_inline_xbrl_statement_candidate_product_status`).

The next offline orchestrator must fail closed if either family is absent,
hash-stale, mismatched, raw, or available only by live source acquisition.

## Fail-Closed Rules

- Projection input must be ready canonical projection output.
- Every projected fact must have resolved-fact provenance, either direct
  `resolved_fact_id` or derived source ids.
- Sidecar and value-store hashes must be 64-character lowercase hex hashes.
- Missing or empty projected facts block the adapter.
- Missing statement-role authority produces a blocked statement packet rather
  than a review-ready packet.
- Raw identity, accession, SEC URL, local path, raw period date, or raw runtime
  references are rejected before output.

## Containment And Rollback

No data migration or persisted production state is introduced. Rollback is code
only:

- remove `backend/app/services/layer3_sec_xbrl_e2e_integration.py`;
- revert the period-ref/period-index propagation in statement assembly;
- remove `backend/tests/test_sec_xbrl_e2e_integration.py`; and
- revert the Layer 3 docs/manifests/proof entries for this milestone.

Existing one-period statement assembly behavior remains compatible because rows
without period refs still use the prior per-statement row ordering.

## Non-Goals

- no production runtime activation;
- no API/UI route;
- no source acquisition, live SEC network access, or Arelle subprocess;
- no schema, `models.py`, Alembic migration, or model change;
- no durable persistence service change beyond exercising existing services in
  tests;
- no value reveal or default-on behavior;
- no operator packet submission or production-admission claim.

## Verification

Focused verification:

`python -m pytest ./backend/tests/test_sec_xbrl_e2e_integration.py ./backend/tests/test_sec_xbrl_statement_assembly.py ./backend/tests/test_sec_xbrl_statement_packet_persistence.py ./backend/tests/test_sec_xbrl_operator_review_workflow.py -q`

Result: `109 passed, 4 warnings`.

`python -m py_compile ./backend/app/services/layer3_sec_xbrl_e2e_integration.py ./backend/app/services/layer3_sec_xbrl_statement_assembly.py ./backend/tests/test_sec_xbrl_e2e_integration.py`

Result: pass.

Broader verification:

`python -m pytest` over explicit `./backend/tests/test_sec_xbrl*.py`
enumeration.

Result: `375 passed, 3 warnings`.

`python ./tools/l3-target-selection-validate.py --expect frozen`

Result: pass.

`python ./tools/l3-progress-check.py`

Result: pass.

`python -c "import json; ..."` over the two Layer 3 manifests with
`utf-8-sig`.

Result: pass.

`git diff --check`

Result: pass, with Git LF-to-CRLF working-copy warnings only.

Path-aware redaction/residual scan over committed SEC XBRL reports.

Result: `59` reports scanned with `0` identity hits, `0` raw scalar value
hits, and `0` nonzero residual magnitudes.

## Next Safe Action

Open `sec_xbrl_e2e_offline_evidence_orchestrator_design_v1` or a narrower
offline diagnostic proof that reads already-acquired governed storage, builds
the private canonical projection and statement-role records, uses this adapter,
and stops before production admission if any authority source is missing,
ambiguous, raw, or only available through live acquisition.
