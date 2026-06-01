# 1287 - SEC XBRL Projection Persistence Implementation

Milestone:

`sec_xbrl_projection_persistence_schema_materializer_v1`

## Scope

This Tier-2 implementation lands the first code-bearing slice selected by
`1286-projection-persistence.md`: additive redacted projection persistence schema plus
a deterministic materializer.

Files in this slice:

- `backend/app/models/models.py`
- `backend/app/models/__init__.py`
- `backend/alembic/versions/0038_layer3_sec_xbrl_projection_persistence.py`
- `backend/app/services/layer3_sec_xbrl_projection_persistence.py`
- `backend/tests/test_sec_xbrl_projection_persistence.py`
- `next_milestone_plans/Layer3_planning_docs/1287-projection-persist-impl.md`
- progress/proof tracking docs

## Runtime Contract

The materializer accepts already-built redacted canonical projection output and writes:

- one `l3_sec_xbrl_projection_set` envelope row, and
- one `l3_sec_xbrl_projection_fact` row per admitted redacted fact.

The materializer computes a stable `projection_basis_hash` from the redacted envelope,
replays only the same `client_request_id` with the same `projection_basis_hash`, rejects
same-basis/new-request replay until an alias policy is frozen, and rejects empty
projection sets, raw value fields, raw resolved-fact authority fields, raw accessions,
SEC URLs, raw issuer identity keys, raw period dates, and local paths before writing.

The service returns explicit non-action flags:

- `runtime_default_enabled=false`
- `value_reveal_performed=false`
- `source_acquisition_performed=false`
- `arelle_invoked=false`

## Tier-2 Surfaces

Touched Tier-2 surfaces:

- `models.py` ORM schema additions;
- Alembic migration `0038_layer3_sec_xbrl_projection_persistence`;
- deterministic persistence service over redacted projection rows.

Why necessary:

The next Layer 3 SEC XBRL workflow requires durable redacted projection authority before
persisted statement packets, API/UI review surfaces, operator workflow, value reveal, or
default-on behavior can be considered without duplicating or bypassing provenance.

## Containment

This implementation does not admit:

- API/UI/operator workflow;
- source acquisition, live SEC network, or Arelle invocation;
- value reveal or persisted raw values;
- raw issuer identity, raw accessions, raw period dates, raw resolved fact authorities,
  SEC URLs, local paths, raw sidecar payloads, or value-store payloads;
- persisted statement packet tables;
- default-on behavior;
- production-readiness or final financial-statement semantics claims.

Rollback/containment notes:

- migration downgrade drops only `l3_sec_xbrl_projection_fact` and
  `l3_sec_xbrl_projection_set` plus their indexes;
- tests use isolated SQLite runtime state;
- invalid redaction or authority input leaves no partial set/fact rows;
- replay of the same request does not duplicate rows; same-basis/new-request replay
  fails closed rather than silently aliasing authority.

## Proof

Focused test:

`python -m pytest ./backend/tests/test_sec_xbrl_projection_persistence.py -q`

Result: `12 passed`.

Broader verification and CI state are recorded in the PR that lands this slice.

## Next Posture

After this implementation lands and is verified on current main, the next design lane is
`sec_xbrl_persisted_statement_packet_design_v1`.

Persisted statement packets must consume the redacted persisted projection authority. They
must not recompute values, expose API/UI/operator workflow, reveal values, change defaults,
or claim production readiness without a separate freeze and proof.
