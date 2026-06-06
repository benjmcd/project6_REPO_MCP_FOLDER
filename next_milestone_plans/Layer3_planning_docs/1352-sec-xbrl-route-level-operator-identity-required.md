# 1352 SEC XBRL Route-Level Operator Identity Required

Target: `sec_xbrl_route_level_operator_identity_required_freeze_v1`.

This is the mode-3 escalation freeze following doc
`1351-sec-xbrl-proxy-identity-readonly-projection.md`. It selects the doc-200
mode `route_level_operator_identity_required`. It supersedes 1351's
`proxy_identity_read_only_projection` as the operative auth posture for the SEC
XBRL protected routes; the read-only identity projection surface from 1351
remains as the non-enforcing identity exposure.

Docs `199`/`200` stay byte-stable as the historical entry record.

## Repo-Confirmed Starting State (enforcement is already wired)

The six protected SEC XBRL route families already enforce server-derived
operator identity on their authenticated path. Confirmed in
`backend/app/api/layer3.py`:

```yaml
protected_routes:
  sec_xbrl_operator_review_workflow_status_read:   # GET/POST status
    enforcement: _sec_xbrl_policy_decision + _sec_xbrl_require_binding
  sec_xbrl_operator_review_decision_submit_write:
    enforcement: _sec_xbrl_policy_decision + owner binding
  sec_xbrl_operator_review_decision_status_read:
    enforcement: _sec_xbrl_policy_decision + binding
  sec_xbrl_value_reveal_authority_prepare_write:
    enforcement: _sec_xbrl_policy_decision + binding
  sec_xbrl_controlled_value_reveal_submit_write:
    enforcement: _sec_xbrl_policy_decision + binding
  sec_xbrl_controlled_value_reveal_submit_status_read:
    enforcement: layer3_sec_xbrl_in_app_auth_policy.authorize_sec_xbrl_route + binding
```

Dual-path contract (already implemented):
- when no specific receipt id/basis hash is referenced, the route serves the
  anonymous **redacted** projection (no identity required) — e.g.
  `inspect_redacted_operator_review_workflow_status`;
- when a specific receipt id/basis hash is referenced, the route requires a
  server-derived principal via `authorize_sec_xbrl_route` and an owner binding
  via `require_sec_xbrl_owner_binding`, raising `SecXbrlInAppAuthPolicyError` /
  `SecXbrlAuthBindingError` (rendered through `_sec_xbrl_auth_policy_error_response`).

Under the default `AUTH_OWNER=none` profile the derived principal is the single
local-operator dev identity, so local behavior is unchanged. Under
`AUTH_OWNER=proxy` the route fails closed (401/409) unless `TRUSTED_PROXY_MODE=true`
and a configured identity header are present.

## Decision

```yaml
entry_decision: mode_selected
selected_activation_mode: route_level_operator_identity_required
supersedes_operative_mode: proxy_identity_read_only_projection  # 1351 surface retained
runtime_status: route_level_enforcement_already_wired_now_formalized_and_proven
scope: sec_xbrl_lane_only
auth_owner_runtime_default: none_single_operator_dev_profile
value_reveal_feature_flags_default: off  # unchanged this freeze
reason: |
  route_level_operator_identity_required is the doc-200 mode that matches the
  enforcement already present on the six protected SEC XBRL routes. This freeze
  formalizes the selection and adds route-level fail-closed proof tests that did
  not previously exist at the HTTP layer. It changes no route behavior, no
  config default, and no feature flag.
```

## Runtime Admission (this freeze)

```yaml
runtime_admission:
  route_level_identity_enforcement_formalized: true   # already wired; now selected + proven
  new_route_level_denial_behavior: false              # no behavior change vs current main
  value_reveal_activation: false
  value_reveal_feature_flag_default_change: false
  controlled_submit_activation: false
  owner_binding_persistence_change: false
  operator_permission_matrix_change: false
  default_on_posture_change: false
  model_migration_change: false
  arelle_invocation: false
  live_sec_network_access: false
  diagnostic_report_change: false
  proof_json_change: false
  production_readiness_claim: false
```

## Negative Invariants

- no change to any existing route's admit/deny outcome (enforcement is already
  wired; this freeze only formalizes and proves it);
- no value-reveal activation and no flip of
  `layer3_sec_xbrl_controlled_value_reveal_submit_enabled` /
  `layer3_sec_edgar_arelle_value_reveal_enabled` (both remain default-off);
- no owner-binding persistence, schema, `models.py`, or Alembic change;
- no operator permission matrix change beyond the existing owner/auditor map;
- no raw identity, proxy header value, raw value, residual magnitude, local
  path, or URL in any error body or log (fail-closed errors expose only codes,
  hashes, and blocked-field labels);
- no production-readiness claim; the nonlocal readiness gate remains blocked
  pending its deployment authority packet;
- no new DTO, route, model, migration, UI, or config default.

## Acceptance Criteria

```yaml
acceptance:
  - id: mode_selected
    check: doc 1352 selects exactly route_level_operator_identity_required;
      docs 199/200 byte-stable.
  - id: enforcement_proof_proxy_fail_closed
    check: under AUTH_OWNER=proxy + TRUSTED_PROXY_MODE=true with no configured
      identity header, the authenticated path of each protected route fails
      closed (HTTP 401/409, auth-policy error code, no raw leak).
  - id: forbidden_field_rejected
    check: caller-supplied forbidden auth/identity/raw fields are rejected (400)
      on the protected routes.
  - id: anonymous_redacted_path_preserved
    check: under default AUTH_OWNER=none, the anonymous redacted path (no receipt
      referenced) still returns its redacted projection unchanged.
  - id: no_regression
    check: full test_sec_xbrl*.py and test_layer3_api.py pass (>= prior counts);
      l3-progress-check, l3-target-selection-validate --expect frozen, and
      git diff --check pass.
```

## Verification

```powershell
python -m pytest backend/tests/test_sec_xbrl_route_level_auth_enforcement.py -q
python -m pytest backend/tests/test_sec_xbrl*.py -q
python -m pytest backend/tests/test_layer3_api.py -q
python tools/l3-progress-check.py
python tools/l3-target-selection-validate.py --expect frozen
git diff --check
```

## Next Posture

After this freeze: a value-reveal activation freeze may make the controlled
value-reveal capability a deployment-enabled production path behind this enforced
identity surface — proving end-to-end that, with the feature flag enabled plus
the full lineage (operator review -> approved decision -> value-reveal authority
receipt -> controlled submit + operator confirmation) and a valid owner-bound
identity, the route returns transient revealed values, and fails closed when any
gate is missing. Do not flip the value-reveal feature-flag defaults or claim
production readiness without the deployment authority packet.
