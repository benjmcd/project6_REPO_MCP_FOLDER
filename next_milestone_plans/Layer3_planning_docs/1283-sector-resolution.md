# 1283 - Sector Family Resolution

Milestone:

`sec_xbrl_sector_conditioned_canonical_families_v1_resolution_presence_conditioned`

## Scope

This implementation slice adds opt-in sector-family resolution to the SEC XBRL canonical projection runtime. The canonical source of truth is `backend/app/services/layer3_sec_xbrl_canonical_concepts.py`.

The default projection path remains universal-only. Sector families are considered only when the caller passes `include_sector_families=True`.

Files in this slice:

- `backend/app/services/layer3_sec_xbrl_canonical_concepts.py`
- `diagnostics/assessment/sec-xbrl-sector-family-coverage.py`
- `diagnostics/assessment/sec-xbrl-sector-family-coverage-report.json`
- `diagnostics/assessment/sec-xbrl-canonical-projection.py`
- `diagnostics/assessment/sec-xbrl-canonical-projection-report.json`
- `backend/tests/test_sec_xbrl_sector_family_coverage.py`
- `backend/tests/test_sec_xbrl_canonical_projection.py`
- `next_milestone_plans/Layer3_planning_docs/1283-sector-resolution.md`

## Runtime Contract

`CanonicalConcept` now carries a `family` qualifier. Universal concepts keep the existing public key shape, while sector-family concepts use a family-qualified key so they cannot collide with universal concepts.

The sector-family registry is centralized in the canonical runtime module and shared by the coverage diagnostic. It defines three v1 families:

- `extractive`
- `banking`
- `insurance`

Activation is concept-presence driven and not primary-SIC gated. Primary SIC is still mapped to a sector-class label, but that label cannot suppress reported family concepts.

The activation rule is:

`anchor_concepts_activate_supporting_concepts_do_not`

Banking keeps common interest concepts as supporting concepts only. For example, `us-gaap:InterestExpense` alone records banking evidence but does not activate the banking family. A banking anchor such as `ifrs-full:GrossLoanCommitments` activates the banking family, after which the supporting banking interest concepts may project if their governed facts exist.

## Preserved Defaults

Default canonical projection remains:

- `include_sector_families`: `false`
- universal defined count: `22`
- sector-family defined count: `0`

Opt-in banking activation adds six banking concepts. The current slice proves activation semantics only; it does not claim filing-wide canonicalization.

## Non-Goals

This slice does not enable runtime defaults, fetch SEC data, invoke Arelle, reveal values, persist new runtime artifacts, assemble final statements, perform dimensional roll-forward handling, add per-period projections, emit linkbase relationships, claim production readiness, or admit final financial-statement semantics.

## Proof

Focused tests:

- `backend/tests/test_sec_xbrl_sector_family_coverage.py`
- `backend/tests/test_sec_xbrl_canonical_projection.py`

Focused result:

`python -m pytest ./backend/tests/test_sec_xbrl_sector_family_coverage.py ./backend/tests/test_sec_xbrl_canonical_projection.py`

Result: `19 passed`.

Regenerated validate-only reports:

- `diagnostics/assessment/sec-xbrl-sector-family-coverage-report.json`
- `diagnostics/assessment/sec-xbrl-canonical-projection-report.json`

## Next Posture

`sec_xbrl_statement_assembly_deferred_pending_linkbase_emission_v1`

Follow-on implementation is tracked in `next_milestone_plans/Layer3_planning_docs/1284-statement-packet.md`.
