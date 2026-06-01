# 1322 - SEC XBRL Nonlocal In-App Auth Policy Validation

Milestone: `sec_xbrl_nonlocal_in_app_auth_policy_validation_v1`

Base authority: `project6-origin/main` at
`3f152c22b88498cc33588aa3a9cec769b365334c`

Prior milestone: `sec_xbrl_nonlocal_in_app_auth_design_v1`

## Status

Branch-local Tier-1 validate-only diagnostic/report/test pass.

This pass implements a deterministic, redacted policy-validation harness for
the SEC XBRL in-app auth boundary selected in doc `1321`. It does not wire auth
into FastAPI, install middleware, change config defaults, alter API behavior,
touch schema, modify `models.py`, add Alembic migrations, add durable
persistence, mutate operator workflow, reveal values, enable value reveal
default-on, acquire sources, invoke Arelle, perform export/delivery, dispatch
to providers/connectors, add raw runtime artifacts, change redaction posture,
or claim production readiness.

## Implemented Artifacts

- `diagnostics/assessment/sec-xbrl-in-app-auth-policy-validation.py`
  - validate-only policy model and report builder;
  - central SEC XBRL route-family map for the protected operator-review and
    controlled value-reveal surfaces;
  - forbidden request-field set covering auth/security, raw identity, proxy
    header, local path/URL, secret/token, raw value/value-store, default-on,
    source acquisition, Arelle, and export/delivery override inputs;
  - deterministic simulations for anonymous, malformed, proxy-header-only,
    spoofed-field, unsupported-role, stale-policy-hash, cross-owner, owner, and
    auditor cases;
  - fail-closed empty route-family map behavior.
- `diagnostics/assessment/sec-xbrl-in-app-auth-policy-validation-report.json`
  - committed redacted report with
    `decision: sec_xbrl_in_app_auth_policy_validation_passed` and
    `blocking_reasons: []`.
- `backend/tests/test_sec_xbrl_in_app_auth_policy_validation.py`
  - focused regression coverage for pass/block decisions, negative cases,
    owner/auditor role constraints, stale hash, cross-owner binding, and report
    redaction.

## Policy Boundary

The validated policy remains pre-runtime. It proves what the future in-app auth
implementation must enforce, not that current routes enforce it.

Repo-confirmed:

- the current SEC XBRL route families exist in `backend/app/api/layer3.py`;
- nonlocal deployment config still requires proxy-owned guardrails in
  `backend/app/core/config.py`;
- the Candidate B owner-access policy remains a hash-only request-context
  precedent in
  `backend/app/services/layer3_candidate_b_operator_workflow_access_policy.py`;
- the new report is redacted and does not include raw identity, local path,
  raw value, SEC URL, accession, or residual-magnitude evidence.

Inference:

- Route-level authorization cannot be claimed until a later implementation
  wires policy evaluation into API dependencies or middleware and chooses an
  owner-binding persistence strategy. This pass intentionally stops before that
  boundary.

## Validation Result

The diagnostic currently validates:

- six protected route families;
- owner access to all protected route families;
- auditor access only to redacted read-only operator-review status families;
- auditor denial for mutating routes and value-reveal routes;
- anonymous, missing, malformed, proxy-header-only, spoofed, unsupported-role,
  stale-policy-hash, and cross-owner cases fail closed;
- policy outputs expose only hashes, refs, role/route/status metadata, and
  booleans;
- current nonlocal production readiness remains unclaimed.

## Next Posture

Next exact posture:
`sec_xbrl_nonlocal_in_app_auth_owner_binding_strategy_v1`.

That next pass should decide whether future runtime enforcement uses additive
hash-only owner/workspace columns on SEC XBRL receipt tables, or a separate
hash-only auth-binding receipt/table keyed by existing SEC XBRL receipt ids and
basis hashes. Until that decision is made, do not claim complete cross-owner
isolation for already-persisted SEC XBRL receipts.

## Stop Conditions

Stop before the next implementation if it requires any of the following without
a separate explicit implementation instruction:

- runtime auth dependency or middleware changes;
- SEC XBRL route behavior changes;
- config default or `AUTH_OWNER` value changes;
- schema, `models.py`, Alembic, owner-binding persistence, or audit
  persistence;
- value reveal default-on or automatic value delivery;
- source acquisition, live SEC network, or Arelle subprocess execution;
- export/delivery, provider dispatch, public URL, or destination selection;
- production-readiness claim;
- raw identity, accessions, SEC URLs, local paths, raw values, or residual
  magnitude artifacts.

## Branch-Local Verification

Branch-local verification on
`codex/secxbrl-in-app-auth-policy-validation`:

- Focused policy validation test:
  `python -m pytest ./backend/tests/test_sec_xbrl_in_app_auth_policy_validation.py -q`
  - PASS: `7 passed`.
- Focused nonlocal/default-on API tests:
  `python -m pytest ./backend/tests/test_layer3_api.py -q -k
  "deployment_profile or default_arelle_cutover or arelle_sidecar or
  default_on or value_reveal"`
  - PASS: `27 passed, 249 deselected, 3 warnings`.
- Full SEC XBRL suite:
  `python -m pytest <29 backend/tests/test_sec_xbrl*.py files> -q`
  - PASS: `329 passed, 4 warnings`.
- `python -m py_compile` over touched Python files:
  - PASS.
- Report regeneration:
  `python ./diagnostics/assessment/sec-xbrl-in-app-auth-policy-validation.py
  --output diagnostics/assessment/sec-xbrl-in-app-auth-policy-validation-report.json`
  - PASS: `decision=sec_xbrl_in_app_auth_policy_validation_passed`.
- JSON validation:
  - PASS: changed JSON parsed with `python -m json.tool` and `utf-8-sig`.
- `python ./tools/l3-target-selection-validate.py --expect frozen`
  - PASS.
- `python ./tools/l3-progress-check.py`
  - PASS.
- Committed SEC XBRL report redaction/residual scan:
  - PASS: `57` SEC-like reports; `0` raw identity/path/SEC URL/accession
    hits; `0` nonzero residual-magnitude hits.
- `git diff --check`
  - PASS.
