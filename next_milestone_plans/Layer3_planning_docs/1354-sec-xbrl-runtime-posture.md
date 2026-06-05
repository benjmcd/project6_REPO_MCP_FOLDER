# 1354 SEC XBRL Runtime Posture Projection

Target: `sec_xbrl_runtime_posture_projection_v1`.

This slice adds the top-level operator posture surface needed after the controlled
value-reveal activation in doc `1353-sec-xbrl-value-reveal-activation.md`. It does not
activate a new live path. It makes the current SEC XBRL runtime state inspectable before
future activation freezes touch live SEC network access, Arelle invocation, governed-sibling
value reveal, export, or default-on production readiness.

## Decision

```yaml
entry_decision: implemented
selected_surface: read_only_runtime_posture_projection
api_route: GET /api/v1/layer3/sec-xbrl/runtime/posture
canonical_service: backend/app/services/layer3_sec_xbrl_posture.py
authorities_read:
  - app.core.config.settings
  - app.services.layer3_sec_xbrl_in_app_auth_policy.PROTECTED_ROUTE_FAMILIES
runtime_state_reported:
  - controlled_value_reveal_submit_enabled
  - arelle_fact_authority_cutover_enabled
  - arelle_fact_authority_nonlocal_authorized
  - live_sec_edgar_network_enabled
  - arelle_internal_value_store_enabled
  - arelle_corpus_validation_enabled
  - arelle_governed_sibling_value_reveal_enabled
  - auth_owner
  - trusted_proxy_mode
```

The response reports activated capabilities, gated capabilities, protected route-family
metadata, identity-authority posture, operator next actions, and negative boundaries. It
sets `production_readiness_claimed: false` because this is observability/readiness
infrastructure, not a production-readiness declaration.

## Runtime Admission

```yaml
runtime_admission:
  route_added: true
  service_added: true
  db_or_storage_dependency: false
  db_or_storage_write: false
  request_body_admitted: false
  source_acquisition_performed: false
  live_sec_network_access: false
  arelle_invocation: false
  value_reveal_performed: false
  delivery_export_enabled: false
  rendered_ui_legacy_value_reveal_enabled: false
  production_readiness_claimed: false
```

## Negative Invariants

- no raw operator identity, proxy header value, workspace identity, raw value, residual
  magnitude, local path, or URL is exposed;
- no SEC EDGAR network request, Arelle subprocess invocation, source acquisition, value
  reveal, delivery export, database write, storage write, schema change, model change, or
  migration is introduced;
- no route-family policy is changed; the route only reads the existing protected-route-family
  metadata;
- the governed-sibling Arelle value-reveal rendered UI remains disabled/replaced by the
  controlled submit surface from doc 1353.

## Acceptance Criteria

```yaml
acceptance:
  - id: default_posture
    check: default settings report controlled value reveal available, live SEC network gated,
      governed-sibling reveal gated, nonlocal Arelle cutover gated, and production readiness
      still blocked.
  - id: fail_closed_controlled_submit_flag
    check: with controlled submit disabled, the posture changes to
      sec_xbrl_controlled_value_reveal_submit_blocked_by_feature_flag and lists the capability
      as gated.
  - id: runtime_flags_reflected
    check: enabling live/Arelle-related flags changes only the reported posture while side-effect
      booleans stay false and production readiness remains unclaimed.
  - id: redacted_endpoint
    check: proxy-mode request headers are not echoed by the endpoint.
```

## Verification

```powershell
..\..\.venvs\project6-py312\Scripts\python.exe -m pytest .\backend\tests\test_sec_xbrl_runtime_posture.py -q
..\..\.venvs\project6-py312\Scripts\python.exe -m pytest .\backend\tests\test_sec_xbrl_proxy_identity_readonly_projection.py -q
..\..\.venvs\project6-py312\Scripts\python.exe -m pytest .\backend\tests\test_sec_xbrl_operator_review_workflow.py -k "controlled_value_reveal_submit" -q
..\..\.venvs\project6-py312\Scripts\python.exe -m pytest .\backend\tests\test_layer3_api.py -k "sec_edgar_arelle_value_reveal" -q
git diff --check
```

## Next Posture

The next bounded production pass should either render this posture in `/review/layer3` as
the operator-facing readiness/status panel, or use the posture response as the prerequisite
audit surface for a live SEC source-acquisition/Arelle invocation activation freeze. Do not
claim full production readiness until live source acquisition, Arelle invocation, multi-filing
gate enforcement, export/package/status delivery, and nonlocal operator auth are all proven.
