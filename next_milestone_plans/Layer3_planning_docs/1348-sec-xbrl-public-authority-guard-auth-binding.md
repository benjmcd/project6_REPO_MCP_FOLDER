# SEC XBRL Public Authority Guard Auth-Binding Family

## Milestone

`sec_xbrl_public_authority_guard_auth_binding_family_v1`

## Purpose

Continue public-authority guard consolidation by migrating the auth-binding
raw-reference helper to the shared SEC XBRL public-authority guard while
preserving its narrower auth-binding behavior.

## Scope

This tranche is limited to:

- Extending `layer3_sec_xbrl_public_authority_guard.py` with opt-in variants
  for bare `sec.gov` references, Windows paths anywhere in a string, and local
  workspace/temp/user path segments.
- Migrating `layer3_sec_xbrl_auth_binding.py` to delegate `_reject_raw_reference`
  to the shared guard.
- Refreshing the committed nonlocal admission-disposition diagnostic report that
  embeds the auth-binding service source hash, with no decision/posture widening.
- Preserving auth-binding's behavior of not treating raw period dates as
  rejected receipt references.
- Adding focused shared-guard tests for the auth-binding text variants.

## Non-goals

This tranche does not edit config, models, Alembic migrations, backend routes,
UI, persistence schema, proof JSON, diagnostic reports except a source-hash-only refresh of the nonlocal admission-disposition report, source acquisition,
Arelle invocation, live SEC network access, runtime defaults, value-reveal
behavior, production-readiness posture, or activation-lane behavior.

Operator-review, E2E integration, multi-filing evidence gate, and remaining
redaction-helper service migrations stay out of scope for separate
service-family tranches.

## Acceptance evidence

Branch-local verification:

- focused auth-binding guard suites: `18 passed`
- full `backend/tests/test_sec_xbrl*.py`: `455 passed, 3 warnings`
- `python ./tools/l3-progress-check.py`: PASS
- `python ./tools/l3-target-selection-validate.py --expect frozen`: PASS
- progress/proof manifest JSON parse: PASS
- `git diff --check`: PASS (line-ending warnings only)

## Risk controls

The shared guard extension is additive and default-preserving. Auth-binding
opts into only the variants its existing helper already enforced, and explicitly
keeps raw period-date scanning disabled for receipt-reference checks.
