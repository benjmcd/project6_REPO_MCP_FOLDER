# 1290 - SEC XBRL Operator Review Workflow Design

Milestone:

`sec_xbrl_operator_review_workflow_design_v1`

## Status

Planning-only Tier-2 risk-assessed design entry.

This document admits no runtime write path by itself. It does not add `models.py` rows,
Alembic migrations, persistence services, API/UI, value reveal, default-on behavior,
source acquisition, Arelle invocation, delivery/export, raw runtime artifacts, or
production-readiness claims.

## Authority

Canonical governance is `SEC-XBRL-MERGE-GATE-VERIFIER-POLICY.md`. This is a Tier-2
design lane because the selected follow-on implementation would add durable
operator-review workflow state over persisted redacted statement packets. Tier-2
remains risk-assessed: exact touched surfaces, narrow tests, and rollback or
containment notes are required; independent review is sought when practical or when a
concrete risk trigger is present.

Current repo authority before this design:

- `1288-statement-packet-persistence.md` selected durable redacted statement-packet
  persistence as the required predecessor to operator review.
- `1289-statement-packet-persist-impl.md` documents the landed statement-packet
  persistence implementation and its rollback/containment proof.
- `backend/app/services/layer3_sec_xbrl_statement_packet_persistence.py` materializes
  persisted redacted statement packets from persisted projection authority.
- `backend/app/models/models.py` owns the current SEC XBRL projection and
  statement-packet tables.
- Candidate B operator workflow/status docs and services establish the local pattern:
  server-owned authority, redacted status projections, forbidden caller-supplied
  authority/path fields, explicit allowed/blocked controls, and separate freezes for
  lifecycle mutation, API, or rendered UI expansion.

## Selected First Workflow Slice

The first implementation slice should create a durable server-owned control envelope
over an existing `l3_sec_xbrl_statement_packet_set`. It should not create an operator
route or rendered UI yet. The purpose is to establish review authority, control
vocabulary, provenance binding, idempotency, and rollback before any operator-visible
surface can consume the workflow.

Admitted first-slice surfaces:

- `backend/app/models/models.py`: SEC XBRL operator-review workflow ORM model only.
- `backend/alembic/versions/<next>_layer3_sec_xbrl_operator_review_workflow.py`:
  one additive workflow table and indexes only.
- A small service module that opens a redacted workflow envelope from an existing
  persisted statement-packet set.
- Focused tests for schema, idempotency, containment, redaction, empty packet
  fail-closed behavior, statement-packet binding, and no default-on behavior.

Not admitted in the first implementation slice:

- API routes, rendered UI, browser controls, or operator-submitted review decisions;
- delivery/export, download, connector dispatch, provider/public URLs, or handoff;
- value reveal or persisted raw values;
- raw issuer identity, raw accessions, raw resolved fact authorities, raw period dates,
  local paths, SEC URLs, operator contact fields, or residual magnitudes;
- source acquisition, live SEC network, Arelle subprocess invocation, or taxonomy cache
  mutation;
- default-on behavior;
- production-readiness or final financial-statement semantics claims.

## Proposed Durable Shape

Use one additive table for the first implementation:

`l3_sec_xbrl_operator_review_workflow`

One row per deterministic operator-review workflow envelope over one persisted
statement-packet set.

Required fields:

- `sec_xbrl_operator_review_workflow_id`: UUID primary key.
- `sec_xbrl_statement_packet_set_id`: foreign key to `l3_sec_xbrl_statement_packet_set`.
- `client_request_id`: idempotency key, unique.
- `workflow_basis_hash`: stable hash over the redacted workflow envelope, unique.
- `workflow_schema_id`: expected `layer3.sec_xbrl_operator_review_workflow.v1`.
- `statement_packet_basis_hash`: copied from the persisted statement-packet set.
- `source_projection_basis_hash`: copied from the persisted statement-packet set.
- `control_mode`: initially only `redacted_statement_packet_review_only`.
- `review_status`: initially only `review_ready`.
- `redaction_policy`: must equal `redacted_no_values`.
- `statement_count`, `row_count`, `review_exception_count`.
- `review_ready`: boolean copied from the statement-packet set.
- `permitted_controls_json`: control vocabulary only, no values.
- `blocked_controls_json`: blocked future controls with reasons.
- `authority_refs_json`: redacted ids and hashes only.
- `review_summary_json`: counts and status summary only.
- `created_at` and `updated_at`.

Do not store `_value`, `effective_value`, `amount`, raw `resolved_fact_id`, raw CIK,
raw accession, raw period dates, SEC URLs, local paths, operator identity/contact data,
raw sidecar/value-store payloads, or residual magnitudes in this table.

## Workflow Control Vocabulary

The first implementation records the control envelope but does not expose controls.
The envelope should use this vocabulary so later API/UI slices are not forced to infer
meaning from persistence rows:

Permitted in the first envelope:

- `inspect_redacted_statement_packet_counts`
- `inspect_review_exceptions`
- `inspect_statement_packet_authority`
- `defer_review_decision`

Blocked until separate freezes and proofs:

- `submit_operator_review_decision`
- `reveal_values`
- `export_statement_packet`
- `deliver_statement_packet`
- `refresh_from_sec_source`
- `invoke_arelle`
- `edit_statement_packet`
- `change_runtime_default`

## Route, UI, Browser, And Authorization Boundaries

The eventual API route should be frozen separately after the durable control envelope
lands. The planned route family is:

- `POST /api/v1/layer3/sec-xbrl/operator-review/workflow/open`
- `POST /api/v1/layer3/sec-xbrl/operator-review/workflow/status`

The eventual rendered UI should be frozen separately after the API/status route is
available. The planned rendered surface is a read-only SEC XBRL panel under
`/review/layer3`, consuming only server-returned redacted workflow status.

Browser proof is not required for the first service/table slice because no rendered UI
or browser-reachable route is admitted. Any later rendered slice must include headed
and headless browser proof and must prove that no values, raw identities, accessions,
period dates, SEC URLs, local paths, or residual magnitudes render.

Authorization assumptions:

- The first implementation has no route and no caller-visible workflow controls.
- A later route slice must document the exact current FastAPI access boundary it uses
  before code lands.
- A later route slice must reject browser/client supplied paths, SEC URLs, raw
  identifiers, raw facts, operator contact fields, and arbitrary workflow state.
- A later route slice must treat the persisted statement-packet set as server-owned
  authority and must not let a caller override packet rows, counts, hashes, or
  redaction posture.

## Write Contract

The control-envelope materializer must:

1. accept only an existing persisted `L3SecXbrlStatementPacketSet`;
2. reject missing, empty, not-ready, or non-redacted statement-packet sets;
3. require `value_policy=redacted_no_values` on the packet set;
4. require `total_review_rows > 0`;
5. compute `workflow_basis_hash` from the packet id, packet basis hash, source
   projection basis hash, row counts, review exception count, review readiness, and the
   fixed control vocabulary before writing;
6. replay only when the same `client_request_id` resolves to the same
   `workflow_basis_hash`; the same `workflow_basis_hash` under a different
   `client_request_id` fails closed until a separate alias policy is frozen;
7. reject raw value fields, raw issuer identity keys, raw accessions, raw period dates,
   SEC URLs, local paths, operator contact fields, raw resolved fact authorities, and
   residual magnitude fields in any JSON copied into the workflow envelope;
8. write the workflow row in one transaction;
9. roll back the whole transaction on validation failure.

The materializer must not call SEC network paths, invoke Arelle, acquire sources,
mutate taxonomy/cache state, reveal values, emit route/UI state, or record an operator
review decision.

## Rollback And Containment

The schema migration must be additive. Downgrade drops only the new SEC XBRL
operator-review workflow table and indexes.

Containment requirements for the implementation PR:

- Runtime default remains off.
- No route or UI reaches the workflow table in the first slice.
- Tests run in isolated temporary DB state.
- Failed materialization leaves no partial workflow row.
- Replaying the same request returns the existing workflow envelope instead of
  duplicating rows; same-basis/new-request replay fails closed rather than silently
  aliasing authority.
- Statement-packet persistence rows are read as authority inputs, not mutated.
- If downgrade is exercised after test data exists, only the new workflow table is
  removed.

If a later PR admits API/UI controls, submitted review decisions, exports, delivery, or
production retention, authorization, rollback, and retention controls must be revisited
before that PR lands.

## Verification Required For First Implementation

Minimum local verification:

- focused operator-review workflow model/service tests;
- migration upgrade/downgrade or project-standard equivalent migration proof;
- missing packet, empty packet, and not-ready packet fail-closed tests;
- raw value/raw identity/raw accession/raw period date/local path/SEC URL/operator
  contact/residual magnitude rejection tests;
- statement-packet-set binding proof;
- exact-request replay and same-basis/new-request mismatch tests for
  `client_request_id` and `workflow_basis_hash`;
- partial-write rollback test;
- `python -m pytest ./backend/tests/test_sec_xbrl_statement_packet_persistence.py -q`;
- full `backend/tests/test_sec_xbrl*.py` suite;
- `python ./tools/l3-target-selection-validate.py --expect frozen`;
- `python ./tools/l3-progress-check.py`;
- py_compile on touched Python files;
- JSON parse for changed manifests/reports;
- redaction scan across changed SEC XBRL committed reports or proof artifacts;
- `git diff --check`.

CI must be green before merge. Independent review is recommended if the implementation
widens beyond one additive workflow table and one owner service, changes redaction
posture, adds a route/UI surface, or leaves authority ambiguous after audit. Under the
softened policy, merge is blocked by failing CI checks (author-enforced; `main` has no
branch-protection required-status-check gate), unresolved
critical/blocking findings, missing rollback or containment notes, unclear authority, or
an explicit operator instruction requiring review.

## Follow-On After Control Envelope

Only after the durable workflow control envelope lands and is verified should the
project select exactly one of these follow-on lanes:

1. `sec_xbrl_operator_review_workflow_status_api_v1`: read-only API/status over the
   persisted workflow envelope.
2. `sec_xbrl_operator_review_workflow_rendered_status_v1`: read-only rendered
   `/review/layer3` panel over the status API, with headed and headless browser proof.
3. `sec_xbrl_operator_review_decision_submit_design_v1`: separate governance for any
   operator-submitted review decision.

None of those follow-ons may reveal values, change defaults, export/deliver packets,
invoke SEC/Arelle/source acquisition, or claim production readiness without a separate
freeze and proof.
