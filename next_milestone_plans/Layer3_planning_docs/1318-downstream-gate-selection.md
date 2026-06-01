# 1318 - SEC XBRL Next Downstream Gate Selection

Milestone: `sec_xbrl_next_downstream_gate_design_selection_v1`

Base authority: `project6-origin/main` at `83b101731762bbefd1c7cb0f04b1da52446331d1`

Prior milestone: `next_milestone_plans/Layer3_planning_docs/1317-default-on-runtime-design.md`

Merged authority under selection: PR `#2065` at
`83b101731762bbefd1c7cb0f04b1da52446331d1`.

## Status

Branch-local Tier-1 docs-only downstream gate selection after the merged SEC
XBRL default-on runtime implementation.

This pass changes no runtime behavior. It admits no schema, `models.py`,
Alembic migration, persistence service, backend API/UI, operator workflow,
source acquisition, Arelle invocation, value reveal, export/delivery,
provider/connector dispatch, default-on expansion, raw runtime artifact,
production-readiness claim, final statement semantics claim, or cross-company
comparability claim.

## Current Authority

Repo-confirmed current main after PR `#2065`:

- `diagnostics/assessment/sec-xbrl-default-on-runtime-report.json` emits
  `decision: default_on_runtime_enabled` and `blocking_reasons: []`.
- Arelle resolved-fact sidecar authority is now the default SEC XBRL
  fact-authority runtime path.
- Missing sidecar authority remains fail-closed with no regex fallback during
  default-on operation.
- Explicit regex rollback remains available through
  `LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_CUTOVER_ENABLED=false`.
- Raw internal value storage remains separately default-off through
  `LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED=false`.
- Corpus-validation Arelle execution remains separately default-off through
  `LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED=false`.
- Nonlocal deployment with default-on cutover requires explicit
  `LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_NONLOCAL_AUTHORIZED=true`.
- Value reveal and controlled value-reveal submit remain separately gated and
  default-off.
- Export/delivery and production readiness remain non-admitted.

Post-merge verification on current main passed focused sidecar/default-on API
tests, the full SEC XBRL suite, the full Layer 3 API suite, target-selection
validation, progress check, py_compile, JSON/source-report validation,
redaction scan, residual-magnitude scan, and `git diff --check`.

## Candidate Gates Considered

1. `sec_xbrl_default_on_export_delivery_design_v1`

   Do not select now. Export/delivery is an exfiltration and downstream
   dispatch surface. It should not be designed as the next implementation lane
   until default-on nonlocal/production ownership, monitoring, rollback,
   redaction, and operating policy are designed.

2. `sec_xbrl_operator_auth_hardening_design_v1`

   Do not select as a standalone first gate. Operator-auth hardening is still
   a required production-readiness topic, but the default-on runtime switch is
   a deployment-owned server policy with no in-app operator toggle. The next
   design should include operator-auth implications as part of the deployment
   and production-readiness boundary instead of creating a narrower auth-only
   detour.

3. `sec_xbrl_default_on_production_readiness_implementation_v1`

   Do not select. Direct production-readiness implementation would be too broad
   and would skip the authority design needed for nonlocal authorization,
   rollout/rollback, monitoring, incident/audit handling, source/network/Arelle
   operating assumptions, and redaction guarantees.

4. `sec_xbrl_default_on_nonlocal_production_readiness_design_v1`

   Select as the next admissible gate. This is a design/pre-review lane only.
   It should define the authority, containment, verification, and stop
   conditions required before any default-on export/delivery or production
   implementation is attempted.

## Selection

Select `sec_xbrl_default_on_nonlocal_production_readiness_design_v1` as the
next SEC XBRL downstream gate.

The next pass should produce a design/pre-review artifact that defines:

- deployment owner and approval authority for nonlocal/default-on enablement;
- exact environment/config flags and forbidden request/UI/operator toggles;
- rollback from default-on sidecar authority to explicit regex mode;
- containment for raw internal value store, value reveal, and controlled submit;
- source acquisition and Arelle availability assumptions without executing
  source acquisition or invoking Arelle in the design pass;
- redaction, residual-magnitude, and committed-report scan requirements;
- observability, audit-event, and incident/follow-up triggers;
- canary/smoke verification scope for local and nonlocal deployment profiles;
- explicit non-admission of export/delivery until a later separate gate.

## Stop Conditions For The Next Design

Stop before any implementation if the design would require:

- enabling export/delivery or provider/connector dispatch;
- making value reveal default-on or automatic;
- exposing an API/UI/request/operator field that toggles default-on;
- adding schema, migrations, or durable production-retention behavior;
- executing live SEC network/source acquisition or invoking Arelle;
- persisting raw values, raw identities, raw accessions, period dates, local
  paths, SEC URLs, or raw sidecar/value-store payloads;
- claiming production readiness without explicit rollback, monitoring,
  redaction, authorization, and incident-response proof obligations.

## Required Future Proof

The later production/nonlocal design PR should prove:

- current-main default-on runtime evidence is still clean;
- nonlocal deployment is blocked without explicit authorization;
- no request, rendered UI, browser state, or operator-review decision can enable
  default-on;
- value reveal, controlled submit, raw internal value storage, source
  acquisition, and corpus-validation Arelle execution remain separately gated;
- export/delivery remains blocked until a later gate;
- rollback and containment are sufficient for local and nonlocal deployment
  profiles;
- verification commands include targeted default-on/nonlocal tests, full SEC
  XBRL tests, full Layer 3 API tests or a justified narrower substitute for a
  docs-only pass, target-selection frozen check, progress check, JSON/source
  validation, redaction scan, residual-magnitude scan, and `git diff --check`.

## Verification

Branch-local docs-only verification:

- `python ./tools/l3-target-selection-validate.py --expect frozen`
  - PASS
- `python ./tools/l3-progress-check.py`
  - PASS
- JSON parse with `utf-8-sig` for changed manifests
  - PASS
- added-line redaction/residual scan
  - PASS, `0` hits
- `git diff --check`
  - PASS

## Next Posture

`sec_xbrl_default_on_nonlocal_production_readiness_design_v1`
