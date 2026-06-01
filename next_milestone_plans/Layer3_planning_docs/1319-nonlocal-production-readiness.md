# 1319 - SEC XBRL Nonlocal Production-Readiness Design

Milestone: `sec_xbrl_default_on_nonlocal_production_readiness_design_v1`

Base authority: `project6-origin/main` at
`286e08c4ec567e3feb3914eca67b312553775e3c`

Prior milestone:
`next_milestone_plans/Layer3_planning_docs/1318-downstream-gate-selection.md`

## Status

Branch-local docs-only Tier-2 design/pre-review entry.

This pass does not implement or claim production readiness. It defines the
authority, containment, rollback, monitoring, redaction, and verification
contract required before any future SEC XBRL nonlocal/default-on production
readiness implementation, export/delivery design, or production enablement
claim is attempted.

No runtime behavior, config default, schema, `models.py`, Alembic migration,
durable persistence, backend API/UI, rendered control, operator workflow,
source acquisition, Arelle subprocess invocation, raw runtime artifact, value
reveal default, export/delivery, provider/connector dispatch, final statement
semantics, cross-company comparability, or production-readiness behavior is
admitted by this design pass.

## Current Authority

Repo-confirmed current main after PR `#2067`:

- `diagnostics/assessment/sec-xbrl-default-on-runtime-report.json` emits
  `decision: default_on_runtime_enabled`, `blocking_reasons: []`, and
  `next_slice: sec_xbrl_default_on_nonlocal_production_readiness_design_v1`.
- `diagnostics/assessment/sec-xbrl-default-on-admission-review-report.json`
  and `diagnostics/assessment/sec-xbrl-default-posture-decision-report.json`
  also advance to the same next slice.
- `backend/app/core/config.py` defaults local SEC XBRL fact-authority cutover
  to persisted Arelle sidecar authority.
- `backend/app/core/config.py` keeps raw internal value storage, Arelle corpus
  validation, value reveal, and controlled value-reveal submit default-off.
- `backend/app/core/config.py` requires `DEPLOYMENT_MODE=nonlocal` deployments
  to use explicit HTTPS origins, `AUTH_OWNER=proxy`,
  `TRUSTED_PROXY_MODE=true`, a non-empty proxy identity header, and storage
  exposure `auto` or `disabled`.
- `backend/app/core/config.py` requires
  `LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_NONLOCAL_AUTHORIZED=true` when
  `DEPLOYMENT_MODE=nonlocal` and Arelle fact-authority cutover is enabled.
- `backend/tests/test_layer3_api.py` proves local default-on behavior,
  nonlocal proxy-owned guardrails, direct-storage disabling in nonlocal mode,
  and fail-closed nonlocal configuration cases.
- `next_milestone_plans/Layer3_planning_docs/116_SECURITY_SOURCE_DELIVERY_BOUNDARY_FREEZE.md`
  records that repo-live configuration expects a proxy-owned nonlocal posture
  but does not itself prove inbound route-level operator authentication.

Carried-forward from the prior SEC XBRL gates and still current unless a later
implementation changes it:

- value reveal remains an explicit controlled flow, not a default-on behavior;
- export/delivery remains a separate exfiltration-class gate;
- source acquisition and corpus-validation Arelle execution remain separately
  default-off;
- final financial-statement semantics and cross-company comparability remain
  non-admitted.

Inference from the repo-confirmed boundary:

- The next implementation should not attempt to make the SEC XBRL runtime
  "production ready" by flipping one flag. It must first prove the deployment
  authority, proxy/auth boundary, rollback, observability, redaction, incident
  response, and non-admission boundaries listed here.

## Design Decision

The next admissible implementation should be a validate-first nonlocal
production-readiness gate, not production enablement.

The design selects a future
`sec_xbrl_default_on_nonlocal_production_readiness_gate_v1` slice that produces
repo-owned readiness evidence without enabling export/delivery, changing
runtime defaults, invoking Arelle, acquiring sources, revealing values, or
claiming production readiness from unverified deployment assumptions.

The gate should answer three questions:

1. Is current default-on SEC XBRL runtime evidence still clean on current main?
2. Is the nonlocal deployment boundary explicitly authorized and fail-closed?
3. Are the non-admitted surfaces still blocked: value reveal default-on,
   controlled submit default-on, raw value store default-on, source
   acquisition, corpus-validation Arelle execution, export/delivery, provider
   dispatch, and production-readiness claim?

If any answer is not proven, the gate must emit a blocked decision and identify
the missing authority. A blocked decision is acceptable and is safer than a
production-readiness overclaim.

## Authority Packet

A future implementation may claim nonlocal production-readiness only from a
server/deployment-owned authority packet. Browser, API request, rendered UI,
operator-review decision, local storage, copied headers, or freeform notes must
not self-authorize nonlocal/default-on posture.

Minimum required fields for the authority packet:

- `deployment_mode`: must be `nonlocal` for a nonlocal-readiness claim;
- `deployment_owner_ref`: redacted stable operator/deployment owner reference;
- `approval_record_ref`: redacted stable reference to the deployment approval;
- `approval_record_hash`: stable hash of the approval record;
- `proxy_boundary_mode`: must identify external trusted proxy or later
  repo-owned in-app auth mode;
- `proxy_identity_header`: name only, not an observed operator identity value;
- `allowed_origins_policy_hash`: hash of explicit HTTPS origin policy;
- `storage_exposure_policy`: must be `auto` or `disabled`;
- `arelle_fact_authority_nonlocal_authorized`: must be true;
- `rollback_owner_ref`: redacted stable owner reference for rollback authority;
- `incident_owner_ref`: redacted stable owner reference for incident handling;
- `redaction_policy_id`: current SEC XBRL redaction policy identifier;
- `verification_run_ref`: stable reference to the readiness verification run.

The future gate must reject authority packets containing raw operator identity,
email address, raw issuer identity, accession, CIK, SEC URL, local path, raw
sidecar payload, raw value-store payload, raw values, or residual magnitudes.

## Deployment Boundary

The nonlocal deployment boundary is proxy-owned unless a later implementation
adds in-app auth.

Required proxy-owned posture:

- `DEPLOYMENT_MODE=nonlocal`;
- explicit HTTPS `ALLOWED_ORIGINS`, no wildcard;
- `AUTH_OWNER=proxy`;
- `TRUSTED_PROXY_MODE=true`;
- non-empty `PROXY_IDENTITY_HEADER`;
- no direct storage mount exposure;
- no route/request/UI/operator-review field that can override default-on,
  value-reveal, source-acquisition, Arelle, or export behavior.

This design does not prove an external proxy is actually deployed. Future
production-readiness admission must therefore either:

- attach redacted deployment evidence that proves the proxy boundary, direct
  FastAPI bypass prevention, TLS/origin ownership, and identity-header trust; or
- stop and require a separate in-app auth/security implementation lane before
  nonlocal exposure.

## Rollback And Containment

Rollback must be non-destructive and one operational step:

- set `LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_CUTOVER_ENABLED=false` or deploy
  the equivalent rollback profile;
- preserve sidecar, projection, statement-packet, operator-review, decision,
  value-reveal authority, and controlled-submit rows without deletion or
  mutation;
- keep value reveal and controlled submit default-off;
- keep source acquisition and corpus-validation Arelle execution default-off;
- keep export/delivery and provider dispatch non-admitted;
- record a blocked or rollback decision in the readiness report if default-on
  evidence is absent, stale, contradictory, or unredacted.

Any implementation that needs schema downgrade, table rewrite, data deletion,
raw value migration, source reacquisition, live SEC network execution, or
synchronous Arelle invocation is outside this design and must stop for separate
pre-review.

## Observability And Incident Triggers

The future readiness gate should define only redacted, count/hash/status
observability. It must not emit raw filings, raw values, raw sidecar payloads,
operator identities, accessions, SEC URLs, local paths, or residual magnitudes.

Minimum readiness signals:

- current default-on runtime decision and report hash;
- nonlocal config validation result;
- explicit nonlocal Arelle authorization result;
- proxy/auth boundary evidence presence;
- storage exposure result;
- rollback command/profile presence;
- redaction scan result;
- residual-magnitude scan result;
- source-acquisition/Arelle/live-network non-execution result;
- value-reveal/default-submit/default-on-export non-admission result;
- incident owner and follow-up trigger hashes.

Incident/follow-up triggers:

- missing or stale sidecar authority in nonlocal default-on operation;
- proxy boundary evidence absent or ambiguous;
- wildcard/non-HTTPS origin, direct storage exposure, or trusted proxy disabled;
- value reveal, controlled submit, source acquisition, or corpus-validation
  Arelle accidentally default-on;
- any raw value, identity, accession, SEC URL, local path, operator contact, raw
  payload, or nonzero residual magnitude appears in committed reports;
- export/delivery, provider dispatch, production-readiness, final-statement
  semantics, or cross-company comparability is claimed by runtime/report output.

## Future Implementation Boundary

Tier-1 future implementation is acceptable only if it remains validate-only:

- a diagnostic/report/test gate that reads current config/report/source
  authority;
- no schema, persistence, API/UI, runtime-default, source acquisition, Arelle,
  value reveal, export/delivery, provider dispatch, or redaction-posture change;
- fail-closed on absent/ambiguous authority;
- redacted report output only.

Tier-2 pre-review is required before any future slice touches:

- runtime default changes beyond the already-admitted default-on local posture;
- in-app auth/security or operator identity projection;
- schema, persistence, or audit-event tables;
- production-retention behavior;
- value reveal or controlled submit defaults;
- export/delivery or provider/connector dispatch;
- source acquisition or Arelle execution;
- any redaction posture change.

## Acceptance Criteria For The Next Gate

The next implementation PR should be admissible only if all of the following are
true:

- it emits a committed redacted report for
  `sec_xbrl_default_on_nonlocal_production_readiness_gate_v1`;
- current default-on runtime evidence remains `default_on_runtime_enabled` with
  no blocking reasons;
- nonlocal config validation requires proxy-owned posture and explicit Arelle
  nonlocal authorization;
- the report distinguishes `production_readiness_designed` or
  `production_readiness_blocked` from actual production readiness;
- proxy-boundary authority is present or the report blocks production-readiness
  admission;
- no browser/API/UI/operator-review field can toggle default-on;
- value reveal, controlled submit, raw internal value store, source acquisition,
  corpus-validation Arelle execution, export/delivery, and provider dispatch
  remain separately gated and default-off;
- rollback/containment is documented and testable;
- redaction and residual-magnitude scans pass over committed SEC XBRL reports;
- focused default-on/nonlocal tests, full SEC XBRL tests, target-selection
  frozen check, progress check, JSON validation, py_compile for touched Python
  files, and `git diff --check` pass.

## Stop Conditions

Stop before implementation or merge if the design or future gate would require:

- production readiness to be claimed without proxy/auth proof or in-app auth;
- export/delivery or provider/connector dispatch;
- value reveal default-on or automatic value delivery;
- raw internal value store default-on;
- source acquisition or Arelle subprocess execution;
- schema/model/migration/persistence changes without a separate Tier-2 plan;
- direct storage exposure in nonlocal mode;
- wildcard or non-HTTPS origins in nonlocal mode;
- request, rendered UI, browser state, operator-review decision, or local
  storage authority to toggle default-on;
- raw values, raw identities, accessions, period dates, SEC URLs, local paths,
  operator contacts, raw sidecar/value-store payloads, or residual magnitudes in
  committed reports;
- final financial-statement semantics or cross-company comparability claims.

## Review Checklist

Independent or operator review should focus on:

- whether the authority packet is sufficient and still redacted;
- whether the external proxy assumption is explicit enough or should force an
  in-app auth/security lane first;
- whether the future implementation can stay Tier 1 validate-only;
- whether rollback is actually one-step and non-destructive;
- whether value reveal/export/delivery remain separate gates;
- whether monitoring/incident triggers catch the realistic failure modes;
- whether the design avoids turning a docs/report gate into a production
  readiness claim.

## Branch-Local Verification

Docs-only validation on branch
`codex/secxbrl-nonlocal-readiness-design`:

- Focused default-on/nonlocal API tests:
  `python -m pytest ./backend/tests/test_layer3_api.py -q -k
  "deployment_profile or default_arelle_cutover or arelle_sidecar or
  default_on or value_reveal"`
  - PASS: `27 passed, 249 deselected, 3 warnings`.
- Full SEC XBRL suite:
  `python -m pytest <27 backend/tests/test_sec_xbrl*.py files> -q`
  - PASS: `319 passed, 4 warnings`.
- JSON parse with `python -m json.tool` over the changed manifests and
  current default-on runtime report:
  - PASS.
- `python ./tools/l3-target-selection-validate.py --expect frozen`
  - PASS.
- `python ./tools/l3-progress-check.py`
  - PASS.
- Added-diff redaction scan:
  - PASS: `0` hits.
- Committed SEC XBRL report redaction/residual scan:
  - PASS: `55` reports, `0` redaction hits, `0` residual/magnitude hits.
- `git diff --check`
  - PASS.

No Python runtime or test file was touched by this design pass, so
`py_compile` is not applicable to the branch-local diff.

## Next Posture

Next safe implementation lane:

`sec_xbrl_default_on_nonlocal_production_readiness_gate_v1`

That lane should be a validate-only diagnostic/report/test gate unless the
operator explicitly authorizes a broader Tier-2 implementation. It should not
implement export/delivery, provider dispatch, source acquisition, Arelle
execution, schema/persistence, value reveal default-on, or production
enablement.
