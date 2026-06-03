# SEC XBRL Public Authority Guard Value-Reveal Family

## Milestone

`sec_xbrl_public_authority_guard_value_reveal_family_v1`

## Purpose

Continue the SEC XBRL public-authority guard consolidation after the
persistence-family pilot by migrating the value-reveal authority and controlled
value-reveal submit services to shared raw/local text-reference scanning and
shared forbidden-key inventory helpers.

## Scope

This tranche is limited to:

- Extending `layer3_sec_xbrl_public_authority_guard.py` with behavior-preserving
  variant controls for operator-contact scans, CIK full-match scans, and
  current-mapping forbidden-key inventory.
- Migrating `layer3_sec_xbrl_value_reveal_authority.py` to the shared guard
  while preserving its service-specific error class, error codes, messages,
  details, and attestation-specific raw-decimal/contact checks.
- Migrating `layer3_sec_xbrl_controlled_value_reveal_submit.py` to the shared
  guard while preserving its exact request-key denylist and CIK full-match
  redaction behavior.
- Adding focused tests for the new shared guard API variants.

## Non-goals

This tranche does not edit config, models, Alembic migrations, backend routes,
UI, persistence schema, proof JSON, diagnostic reports, value-store behavior,
source acquisition, Arelle invocation, live SEC network access, runtime
defaults, production-readiness posture, or activation-lane behavior.

Operator-review, E2E integration, auth-binding, multi-filing evidence gate, and
remaining redaction-helper service migrations stay out of scope for separate
service-family tranches.

## Acceptance evidence

Branch-local verification:

- focused value-reveal guard suites: `83 passed, 3 warnings`
- full `backend/tests/test_sec_xbrl*.py`: `454 passed, 3 warnings`
- `python ./tools/l3-progress-check.py`: PASS
- `python ./tools/l3-target-selection-validate.py --expect frozen`: PASS
- progress/proof manifest JSON parse: PASS
- `git diff --check`: PASS (line-ending warnings only)

## Risk controls

The shared guard extension is additive and default-preserving. Persistence-family
callers keep their existing defaults. The two migrated services keep their local
variant denylist decisions where those decisions are service-specific rather
than universal public-authority semantics.
