# 1295 - SEC XBRL Operator Review Decision Submit Design

Milestone:

`sec_xbrl_operator_review_decision_submit_design_v1`

## Status

Planning-only Tier-2 risk-assessed design entry.

This document admits no runtime implementation by itself. It does not add or change
`models.py`, Alembic migrations, schema, durable persistence, API/UI, rendered browser
controls, value reveal, default-on behavior, source acquisition, SEC network execution,
Arelle invocation, delivery/export, raw runtime artifacts, authorization behavior,
redaction posture, or production-readiness claims.

## Authority

Canonical governance is `SEC-XBRL-MERGE-GATE-VERIFIER-POLICY.md`. A future
operator-review decision submit implementation is Tier 2 because it would record a
durable operator decision over SEC XBRL workflow authority. Under the softened policy,
that implementation needs exact Tier-2 surface documentation, narrow tests,
rollback/containment notes, and independent review when practical or when a concrete
risk trigger is present.

Current repo authority before this design:

- `1287-projection-persist-impl.md` landed redacted projection persistence.
- `1289-statement-packet-persist-impl.md` landed redacted statement-packet
  persistence.
- `1291-operator-review-workflow-impl.md` landed the durable server-owned
  operator-review workflow control envelope.
- `1292-operator-review-workflow-status-api.md` landed the read-only status API:
  `POST /api/v1/layer3/sec-xbrl/operator-review/workflow/status`.
- `1294-rendered-status.md` landed the read-only rendered status panel over that API.
- `backend/app/services/layer3_sec_xbrl_operator_review_workflow.py` still marks
  `submit_operator_review_decision` blocked with
  `requires_separate_decision_submit_freeze`.

## Selected Next Implementation Boundary

The next code-bearing slice should be a durable decision receipt materializer over an
existing `l3_sec_xbrl_operator_review_workflow` row. It should establish immutable
decision identity, idempotency, redaction checks, workflow binding, and rollback before
any rendered submit control is introduced.

Admitted future implementation surfaces:

- `backend/app/models/models.py`: one SEC XBRL operator-review decision receipt ORM
  model only.
- `backend/app/models/__init__.py`: export of that model only.
- `backend/alembic/versions/<next>_layer3_sec_xbrl_operator_review_decision.py`: one
  additive decision receipt table and indexes only.
- `backend/app/services/layer3_sec_xbrl_operator_review_workflow.py` or a small sibling
  owner service: decision receipt materialization and status projection helpers.
- `backend/tests/test_sec_xbrl_operator_review_workflow.py` or a focused sibling test:
  schema, service, idempotency, redaction, and rollback coverage.
- A short implementation doc plus progress/proof manifest updates.

Not admitted in that first implementation:

- rendered UI submit controls or browser decision submission;
- workflow-open API expansion;
- value reveal, raw values, or persisted raw resolved fact authority;
- issuer identity, accessions, raw period dates, SEC URLs, local paths, operator
  identity/contact fields, freeform operator notes, sidecar payloads, value-store
  payloads, or residual magnitudes;
- delivery/export, download, connector dispatch, provider/public URLs, or handoff;
- source acquisition, live SEC network, Arelle subprocess invocation, or taxonomy cache
  mutation;
- default-on behavior;
- production-readiness, final financial-statement semantics, filing-wide
  canonicalization, or comparability claims.

## Proposed Durable Shape

Use one additive table:

`l3_sec_xbrl_operator_review_decision`

One row records one immutable operator-review decision over one existing workflow row.
The first implementation should admit at most one decision receipt per workflow. Any
later reopen, supersession, or appeal model requires a separate design because it changes
the lifecycle semantics.

Required fields:

- `sec_xbrl_operator_review_decision_id`: UUID primary key.
- `sec_xbrl_operator_review_workflow_id`: foreign key to
  `l3_sec_xbrl_operator_review_workflow`.
- `client_request_id`: idempotency key, unique.
- `decision_basis_hash`: stable hash over the workflow id, workflow basis hash,
  statement-packet basis hash, source-projection basis hash, review decision,
  decision reason code, notes hash when present, and fixed decision vocabulary.
- `decision_schema_id`: expected `layer3.sec_xbrl_operator_review_decision.v1`.
- `workflow_basis_hash`, `statement_packet_basis_hash`, and
  `source_projection_basis_hash`: copied from the workflow row.
- `decision_mode`: initially only `redacted_statement_packet_operator_review_decision`.
- `review_decision`: one of `approved`, `changes_requested`, `rejected`, or `blocked`.
- `decision_status`: initially only `decision_recorded`.
- `redaction_policy`: must equal `redacted_no_values`.
- `decision_reason_code`: bounded enum such as `ready_for_next_freeze`,
  `needs_packet_revision`, `authority_gap`, `redaction_gap`, or `operator_blocked`.
- `decision_notes_present`: boolean.
- `decision_notes_hash`: nullable hash only; raw notes are not persisted.
- `decision_summary_json`: redacted counts and status summary only.
- `authority_refs_json`: workflow, packet, and projection ids/hashes only.
- `permitted_controls_after_decision_json`: status/inspection controls only.
- `blocked_controls_after_decision_json`: downstream controls still blocked until later
  freezes.
- `created_at` and `updated_at`.

Do not store raw operator notes, `_value`, `effective_value`, `amount`, raw
`resolved_fact_id`, raw CIK, raw accession, raw period dates, SEC URLs, local paths,
operator identity/contact data, raw sidecar/value-store payloads, or residual
magnitudes.

## Decision Contract

The materializer must:

1. accept only an existing server-owned `L3SecXbrlOperatorReviewWorkflow`;
2. require matching workflow id/hash authority when both are supplied;
3. reject missing, non-ready, non-redacted, tampered, or already-decided workflow rows;
4. require `redaction_policy=redacted_no_values`;
5. require the current workflow blocked controls to include
   `submit_operator_review_decision` before the decision receipt is recorded, proving
   this slice is retiring exactly that blocked control and no other one;
6. admit only `approved`, `changes_requested`, `rejected`, or `blocked` review
   decisions;
7. require a bounded `decision_reason_code`;
8. require notes evidence for `changes_requested`, `rejected`, and `blocked`, but store
   only `decision_notes_present=true` and `decision_notes_hash`;
9. reject raw values, raw resolved fact authority, raw issuer identity, raw accessions,
   raw period dates, SEC URLs, local paths, operator contact fields, source-acquisition
   fields, Arelle fields, delivery/export fields, and residual magnitude fields from
   any copied JSON or supplied decision evidence;
10. compute `decision_basis_hash` before writing;
11. be idempotent on `client_request_id` and `decision_basis_hash`;
12. write the decision row in one transaction and roll back the whole transaction on
    validation failure;
13. leave the workflow, statement-packet, and projection persistence rows unmutated.

The first implementation should not change the existing status API or rendered status
panel except through later separate freezes. It may expose a service-level status helper
for tests, but browser-visible decision status requires a later API/rendered lane.

## Post-Decision Control Vocabulary

Recording a decision does not by itself admit downstream action.

Permitted after decision receipt:

- `inspect_operator_review_decision_status`
- `inspect_redacted_statement_packet_counts`
- `inspect_review_exceptions`
- `inspect_statement_packet_authority`

Still blocked until separate freezes and proofs:

- `reveal_values`
- `export_statement_packet`
- `deliver_statement_packet`
- `refresh_from_sec_source`
- `invoke_arelle`
- `edit_statement_packet`
- `change_runtime_default`
- `open_operator_review_workflow`
- `render_operator_review_decision_submit_control`

An `approved` decision may make the workflow eligible for the next design lane, but it
must not directly enable value reveal, export/delivery, default-on behavior, source
acquisition, or production retention.

## Future API And UI Boundary

A later API lane may add:

`POST /api/v1/layer3/sec-xbrl/operator-review/workflow/decision/submit`

That lane must be separately frozen before code lands. It must use `extra="forbid"`,
document the current FastAPI access boundary, reject caller-supplied paths/URLs/raw
facts/raw identifiers/operator contact fields, and pass only bounded decision fields to
the owner service.

A later rendered UI lane may add a submit control only after the API lane lands and is
verified. Browser proof must be both headed and headless, and must assert that no raw
values, identities, accessions, period dates, SEC URLs, local paths, operator contact
fields, freeform notes, residual magnitudes, source-acquisition controls, Arelle
controls, delivery/export controls, value reveal controls, or default-on controls render.

## Rollback And Containment

The implementation migration must be additive. Downgrade drops only
`l3_sec_xbrl_operator_review_decision` plus its indexes and constraints.

Containment requirements:

- runtime default remains off;
- workflow rows are authority inputs and are not mutated by decision receipt creation;
- statement-packet and projection rows are not mutated;
- invalid authority, duplicate workflow decision, raw evidence, or notes-policy failure
  leaves no partial decision row;
- replay of the same request returns the existing decision receipt instead of
  duplicating rows;
- no route/UI reaches the decision table until a later API/rendered freeze lands;
- no downstream value reveal, delivery/export, source acquisition, Arelle, default-on, or
  production-readiness behavior is enabled by the decision receipt.

## Verification Required For First Implementation

Minimum local verification:

- focused operator-review decision model/service tests;
- migration upgrade/downgrade or project-standard equivalent migration proof;
- missing, mismatched, tampered, non-ready, non-redacted, and already-decided workflow
  fail-closed tests;
- decision enum and reason-code validation tests;
- notes policy tests proving raw notes are not persisted and notes hashes are recorded
  only after raw-reference scans pass;
- raw value/raw identity/raw accession/raw period date/local path/SEC URL/operator
  contact/source-acquisition/Arelle/delivery-export/residual-magnitude rejection tests;
- idempotent replay tests for `client_request_id` and `decision_basis_hash`;
- partial-write rollback test;
- workflow, statement-packet, and projection non-mutation proof;
- `python -m pytest ./backend/tests/test_sec_xbrl_operator_review_workflow.py -q`;
- full `backend/tests/test_sec_xbrl*.py` suite;
- `python ./tools/l3-target-selection-validate.py --expect frozen`;
- `python ./tools/l3-progress-check.py`;
- py_compile on touched Python files;
- JSON parse for changed manifests/reports;
- redaction scan across changed SEC XBRL committed reports or proof artifacts;
- residual-magnitude scan across changed SEC XBRL committed reports or proof artifacts;
- `git diff --check`.

CI must be green before merge. Independent review is recommended if the implementation
widens beyond one additive decision table and one owner service, changes redaction
posture, exposes an API/rendered submit control, admits raw notes, or leaves authority
ambiguous after audit. Merge is blocked by failed required checks, unresolved
critical/blocking findings, missing rollback or containment notes, unclear authority, or
an explicit operator instruction requiring review.

## Follow-On After Decision Receipt

Only after a durable decision receipt lands and is verified on current main should the
project select exactly one follow-on lane:

1. `sec_xbrl_operator_review_decision_submit_api_v1`: route-level submission over the
   owner service, if the first implementation did not expose a route.
2. `sec_xbrl_operator_review_decision_status_api_v1`: read-only status over a recorded
   decision.
3. `sec_xbrl_operator_review_decision_rendered_submit_freeze_v1`: rendered submit UI
   freeze after API proof.
4. `sec_xbrl_value_reveal_authority_design_v1`: only after approved decision receipts
   are durable and status-readable, and only as a separate value-reveal governance lane.

None of those follow-ons may reveal values, change defaults, export/deliver packets,
invoke SEC/Arelle/source acquisition, or claim production readiness without a separate
freeze and proof.
