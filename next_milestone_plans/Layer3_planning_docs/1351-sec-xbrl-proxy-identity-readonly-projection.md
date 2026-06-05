# 1351 SEC XBRL Proxy Identity Read-Only Projection

Target: `sec_xbrl_proxy_identity_read_only_projection_freeze_v1`.

This doc is the `next_follow_up` activation freeze anticipated by doc
`1350-sec-xbrl-activation-lane-selection.md` and by the auth entry layer
(`199_AUTH_SECURITY_ENTRY_FREEZE.md` / `200_AUTH_SECURITY_ENTRY_CONTRACT.md`),
which both state that "a later freeze must choose exactly one mode before code".
It chooses exactly one mode: `proxy_identity_read_only_projection`.

Docs `199` and `200` remain the byte-stable historical *entry* record. Their
`entry_decision: deferred` / `selected_mode: null` reflect the entry-layer
decision at that point in time. This freeze is the later activation layer that
those docs deferred to; it does not edit them.

## Purpose

Select and implement the narrowest auth mode from the doc-200 allowed set:
`proxy_identity_read_only_projection`. This mode derives a server-authoritative
operator identity and exposes it as a **read-only projection** of response-safe
references. It adds NO route-level enforcement, NO authorization escalation, NO
owner-binding persistence change, NO value reveal, and NO default-on runtime
change.

The projection follows the established repo idiom for read-only live
projections (see `mockup_activation_readiness` projection contracts in
`backend/tests/test_layer3_api.py`: `*_read_only_live_projection_contract`).

## Repo-Confirmed Starting State

```yaml
repo_confirmed:
  identity_derivation_present:
    evidence:
      - backend/app/services/layer3_sec_xbrl_in_app_auth_policy.py
        (_server_derived_principal derives AUTH_OWNER=none dev principal or
         AUTH_OWNER=proxy + TRUSTED_PROXY_MODE=true proxy principal as hashes)
  deployment_profile_guardrails_present:
    evidence:
      - backend/app/core/config.py (auth_owner, proxy_identity_header,
        proxy_groups_header, trusted_proxy_mode, storage_exposure,
        nonlocal fail-closed validation)
  policy_invoked_live_but_permissive_under_default:
    evidence:
      - backend/app/api/layer3.py (_sec_xbrl_policy_decision /
        authorize_sec_xbrl_route called on the six protected SEC XBRL route
        families; under AUTH_OWNER=none the single owner principal is admitted,
        so default local behavior is unchanged)
  validate_only_policy_proof_present:
    evidence:
      - diagnostics/assessment/sec-xbrl-in-app-auth-policy-validation.py
      - backend/tests/test_sec_xbrl_in_app_auth_policy_validation.py
```

## Doc-vs-Code Drift Note (honesty)

The auth policy module is already imported and `authorize_sec_xbrl_route` is
already invoked by the live SEC XBRL operator-review and value-reveal routes.
Under the default `AUTH_OWNER=none` profile this is behavior-preserving (single
owner principal, all owner routes admitted). The entry docs `199`/`200` and the
1350 activation-lane doc describe the *governance* decision as deferred; the
*derivation code* nonetheless already exists. This freeze reconciles that drift
by formally selecting the read-only-projection mode for the SEC XBRL lane and by
adding the one missing live artifact: a server-authoritative identity
**projection** surface. It does not change the existing route admit/deny
behavior.

## Decision

```yaml
entry_decision: mode_selected
selected_activation_mode: proxy_identity_read_only_projection
runtime_status: read_only_projection_implemented
scope: sec_xbrl_lane_only
auth_owner_runtime_default: none_single_operator_dev_profile
nonlocal_runtime_default: fail_closed_unless_proxy_owned_guardrails
reason: |
  proxy_identity_read_only_projection is the narrowest doc-200 mode. It surfaces
  the already-derived server principal as response-safe projection metadata
  without introducing route-level authorization, tenant/session ownership,
  operator permission enforcement escalation, owner-binding persistence changes,
  value reveal, or default-on runtime changes. It is the foundational identity
  surface that later escalation modes (route_level_operator_identity_required,
  session_tenant_owner_authorization) build on.
```

## Read-Only Identity Projection Contract

```yaml
projection_contract:
  contract_id: sec_xbrl_proxy_identity_read_only_live_projection_contract
  schema_id: layer3.sec_xbrl_proxy_identity_projection.v1
  selected_auth_mode: proxy_identity_read_only_projection
  server_authority_contract: |
    server_derived_proxy_or_local_identity_hash_read_only_projection
  derivation_source: layer3_sec_xbrl_in_app_auth_policy._server_derived_principal
  response_safe_fields:
    - selected_auth_mode
    - auth_owner_mode            # AUTH_OWNER_none_* | AUTH_OWNER_proxy_*
    - projection_status          # admitted | blocked_untrusted_proxy_identity |
                                 # blocked_missing_identity_authority |
                                 # blocked_auth_owner_not_admitted
    - actor_ref_hash             # null when blocked
    - workspace_ref_hash         # null when blocked
    - default_role               # owner
    - protected_route_families   # read-only metadata copy (family, allowed
                                 # roles, mutating, may_expose_revealed_values)
    - policy_schema_id
  status_projection:
    - State.sessionSummary.sec_xbrl_identity_projection
  fail_closed_result: blocked_no_runtime_identity_authority
  negative_boundaries:
    - route_level_enforcement_escalation
    - operator_permission_matrix_change
    - owner_binding_persistence_change
    - value_reveal_activation
    - controlled_submit_activation
    - default_on_runtime_change
    - raw_operator_identity_exposure
    - raw_proxy_header_exposure
    - raw_workspace_identity_exposure
    - raw_value_or_residual_magnitude_exposure
    - local_path_or_url_exposure
  raw_exposure_flags_all_false:
    - raw_operator_identity_exposed
    - raw_proxy_header_exposed
    - raw_workspace_identity_exposed
    - raw_value_exposed
    - residual_magnitude_exposed
```

## Runtime Admission (this freeze)

```yaml
runtime_admission:
  proxy_identity_read_only_projection_surface: true   # the one new live artifact
  route_level_auth_enforcement_change: false
  operator_permission_runtime_change: false
  owner_binding_persistence_change: false
  value_reveal_activation: false
  controlled_submit_activation: false
  default_on_posture_change: false
  e2e_integration_live: false
  multi_filing_gate_live: false
  model_migration_change: false
  arelle_invocation: false
  live_sec_network_access: false
  diagnostic_report_change: false
  proof_json_change: false
  source_acquisition_change: false
```

## Negative Invariants

- the new projection surface is read-only and non-enforcing; it never changes an
  existing route's admit/deny outcome;
- no route-level authorization, operator permission matrix, or tenant/session
  ownership enforcement change;
- no owner-binding persistence, schema, `models.py`, or Alembic change;
- no value reveal, controlled submit, or default-on runtime change;
- no live SEC network access, Arelle invocation, or source acquisition;
- no raw operator identity, raw proxy header value, raw workspace identity, raw
  value, residual magnitude, local path, or URL in any projection field, error
  body, or log;
- in `AUTH_OWNER=proxy` mode without `TRUSTED_PROXY_MODE=true`, or with a missing
  configured identity header, the projection fails closed (status `blocked_*`,
  hashes null) and never derives or echoes proxy header values;
- no committed diagnostic report or proof JSON byte change;
- no UI/theme control added in this freeze.

## Acceptance Criteria

```yaml
acceptance:
  - id: mode_selected
    check: doc 1351 selects exactly proxy_identity_read_only_projection; docs
      199/200 remain byte-stable.
  - id: projection_service
    check: build_proxy_identity_readonly_projection derives via
      _server_derived_principal and returns the response-safe contract above;
      fails closed (no raise, status blocked_*, hashes null) on untrusted proxy,
      missing identity header, or non-admitted AUTH_OWNER.
  - id: projection_route
    check: additive GET /api/v1/layer3/sec-xbrl/identity/projection returns the
      projection for the current request; no existing route handler is altered.
  - id: no_raw_leak
    check: projection output contains zero raw identity / proxy header value /
      raw value / residual magnitude / local path / URL across all modes.
  - id: behavior_preservation
    check: existing SEC XBRL route admit/deny behavior and existing
      test_layer3_api.py + test_sec_xbrl*.py expectations are unchanged.
  - id: gates_green
    check: full backend/tests/test_sec_xbrl*.py, backend/tests/test_layer3_api.py,
      tools/l3-progress-check.py, tools/l3-target-selection-validate.py
      --expect frozen, JSON validity of changed manifests, and git diff --check
      all pass.
```

## Verification

```powershell
python -m pytest backend/tests/test_sec_xbrl_proxy_identity_readonly_projection.py -q
python -m pytest backend/tests/test_sec_xbrl*.py -q
python -m pytest backend/tests/test_layer3_api.py -q
python tools/l3-progress-check.py
python tools/l3-target-selection-validate.py --expect frozen
python -m json.tool next_milestone_plans/layer3_progress_manifest.json > $null
git diff --check
```

## Next Posture

After this freeze: the next escalation freeze may select
`route_level_operator_identity_required` (turn the already-present
`authorize_sec_xbrl_route` admit/deny into an enforced route dependency under a
named auth mode), followed by a value-reveal activation freeze that sits behind
the enforced identity surface. Do not escalate enforcement or activate value
reveal in this freeze.
