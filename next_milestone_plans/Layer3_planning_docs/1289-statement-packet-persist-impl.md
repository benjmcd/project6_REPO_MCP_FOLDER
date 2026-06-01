# 1289 - SEC XBRL Statement Packet Persistence Implementation

Milestone:

`sec_xbrl_statement_packet_persistence_schema_materializer_v1`

## Scope

This Tier-2 implementation lands the first code-bearing slice selected by
`1288-statement-packet-persistence.md`: additive redacted statement-packet persistence
schema plus a deterministic materializer.

Files in this slice:

- `backend/app/models/models.py`
- `backend/app/models/__init__.py`
- `backend/alembic/versions/0039_layer3_sec_xbrl_statement_packet_persistence.py`
- `backend/app/services/layer3_sec_xbrl_statement_packet_persistence.py`
- `backend/tests/test_sec_xbrl_statement_packet_persistence.py`
- `next_milestone_plans/Layer3_planning_docs/1289-statement-packet-persist-impl.md`
- progress/proof tracking docs

## Runtime Contract

The materializer accepts an existing persisted redacted projection set plus an
already-built redacted reviewable statement packet and writes:

- one `l3_sec_xbrl_statement_packet_set` envelope row;
- one `l3_sec_xbrl_statement_packet_statement` row per statement section; and
- one `l3_sec_xbrl_statement_packet_row` row per admitted redacted packet row.

The materializer computes a stable `packet_basis_hash` from the redacted packet envelope
and the persisted projection basis hash, replays only the same `client_request_id` with
the same `packet_basis_hash`, rejects same-basis/new-request replay until an alias
policy is frozen, and rejects empty packets, raw value fields, raw resolved-fact
authority fields, raw accessions, SEC URLs, raw issuer identity keys, raw period dates,
local paths, and residual magnitude fields before writing.

Rows must bind to persisted projection facts. Current single-period packet rows may omit
period refs only when the persisted projection set has exactly one period. Multi-period
projection packets must carry explicit period refs.

The service returns explicit non-action flags:

- `runtime_default_enabled=false`
- `value_reveal_performed=false`
- `source_acquisition_performed=false`
- `arelle_invoked=false`
- `operator_workflow_enabled=false`

## Tier-2 Surfaces

Touched Tier-2 surfaces:

- `models.py` ORM schema additions;
- Alembic migration `0039_layer3_sec_xbrl_statement_packet_persistence`;
- deterministic persistence service over redacted statement-packet rows.

Why necessary:

The next Layer 3 SEC XBRL workflow requires durable redacted statement-packet authority
before API/UI review surfaces, operator workflow, delivery/export, value reveal, or
default-on behavior can be considered without bypassing persisted projection provenance.

## Containment

This implementation does not admit:

- API/UI/operator workflow;
- delivery/export;
- source acquisition, live SEC network, or Arelle invocation;
- value reveal or persisted raw values;
- raw issuer identity, raw accessions, raw period dates, raw resolved fact authorities,
  SEC URLs, local paths, raw sidecar payloads, value-store payloads, or residual
  magnitude rows;
- default-on behavior;
- production-readiness or final financial-statement semantics claims.

Rollback/containment notes:

- migration downgrade drops only `l3_sec_xbrl_statement_packet_row`,
  `l3_sec_xbrl_statement_packet_statement`, and `l3_sec_xbrl_statement_packet_set` plus
  their indexes;
- tests use isolated SQLite runtime state;
- invalid redaction, authority, period-binding, or projection-fact binding input leaves
  no partial packet set/statement/row records;
- replay of the same request does not duplicate rows; same-basis/new-request replay
  fails closed rather than silently aliasing authority;
- projection persistence rows are read as authority inputs and are not mutated.

## Proof

Focused test:

`python -m pytest ./backend/tests/test_sec_xbrl_statement_packet_persistence.py -q`

Result: `10 passed`.

Broader verification and CI state are recorded in the PR that lands this slice.

## Next Posture

After this implementation lands and is verified on current main, the next design lane is
`sec_xbrl_operator_review_workflow_design_v1`.

The operator-review workflow must consume persisted redacted statement-packet authority.
It must not reveal values, change defaults, deliver/export packets, or claim production
readiness without a separate freeze and proof.
