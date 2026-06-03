# 1346 SEC XBRL public authority guard consolidation

Target: `sec_xbrl_public_authority_guard_persistence_family_v1`.

This slice begins consolidation of duplicated SEC XBRL raw/local authority
guards after the diagnostic-framework rollout and report-leak guard extraction.
It is intentionally limited to the projection and statement-packet persistence
family, where the duplicated raw value keys, raw authority keys, raw reference
regexes, recursion, period-date scan, and unadmitted-key inventory have the
same behavior shape.

## Scope

- Add a pure shared scanner module:
  `backend/app/services/layer3_sec_xbrl_public_authority_guard.py`.
- Migrate only:
  `layer3_sec_xbrl_projection_persistence.py` and
  `layer3_sec_xbrl_statement_packet_persistence.py`.
- Preserve the service-local exception classes, error codes, messages, and
  details payloads.
- Keep residual-magnitude behavior as a statement-packet-specific variant by
  passing the residual key set into the shared scanner.
- Add focused tests for the shared scanner and keep the existing service tests
  as behavior-preservation proof.

## Non-goals

- No API route, UI, schema, `models.py`, Alembic, config, diagnostics report,
  proof JSON, runtime-default, value-reveal, source-acquisition, live-network,
  or Arelle changes.
- No migration of operator-review workflow, value-reveal authority,
  controlled-submit, E2E integration/orchestrator, auth-binding, or multi-filing
  gate guards in this slice. Those surfaces have additional route/auth/contact,
  CIK, or runtime semantics and need separate scoped passes.
- No production-readiness claim.

## Acceptance

- Projection and statement-packet persistence still reject raw values, raw
  authority identifiers, raw local/source references, and raw period dates with
  their existing service-specific error codes.
- Statement-packet persistence still rejects residual-magnitude fields with its
  existing residual-specific error code.
- The shared scanner has direct focused tests for raw-key detection,
  text-pattern detection, period-date scan control, residual variants, and
  unadmitted-key inventory.
- Full SEC XBRL tests, Layer 3 progress check, frozen target-selection
  validation, manifest JSON parse, and `git diff --check` pass before merge.

## Future follow-up

After this persistence-family pilot lands, migrate the remaining raw/local
authority guards in smaller service-family tranches. The next candidates are
operator-review workflow and value-reveal/controlled-submit helpers, but only
after their additional raw-contact, CIK, route/auth, and value-reveal semantics
are explicitly accounted for.
