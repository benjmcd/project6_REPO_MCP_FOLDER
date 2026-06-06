# 1353 SEC XBRL Controlled Value-Reveal Activation

Target: `sec_xbrl_controlled_value_reveal_activation_freeze_v1`.

This is the value-reveal activation freeze anticipated by the "Next Posture" of doc
`1352-sec-xbrl-route-level-operator-identity-required.md`. It activates activation-lane
items 2-3 of doc `1350-sec-xbrl-activation-lane-selection.md` (value-reveal authority +
controlled value-reveal submit) by making the controlled value-reveal submit capability a
deployment-enabled production path behind the already-enforced operator-identity surface.

It selects `controlled_value_reveal_submit` as the activated surface and flips
`layer3_sec_xbrl_controlled_value_reveal_submit_enabled` from default-off to default-on.
Docs `199`/`200` stay byte-stable. The auth posture selected by `1352`
(`route_level_operator_identity_required`) is unchanged. The arelle governed-sibling
reveal flag (`layer3_sec_edgar_arelle_value_reveal_enabled`) is a separate surface and is
NOT changed by this freeze.

## Repo-Confirmed Starting State (the capability is already built and proven)

The controlled value-reveal path is fully implemented and proven end-to-end; it has only
been parked behind a default-off feature flag. Confirmed in the worktree:

```yaml
already_implemented:
  service_path: backend/app/services/layer3_sec_xbrl_controlled_value_reveal_submit.py
  gate_lines:
    feature_flag: ":101 (settings.layer3_sec_xbrl_controlled_value_reveal_submit_enabled)"
    operator_confirmation: ":106 (operator_reveal_confirmation is not True)"
  reveal_path: "_resolve_sidecar_and_value_store + _controlled_reveal_records -> layer3_sec_edgar_arelle_value_reveal._reveal_records (reads a pre-stored value store; no live network or arelle at submit time)"
  existing_proof:
    service_success: "backend/tests/test_sec_xbrl_operator_review_workflow.py::test_controlled_value_reveal_submit_returns_transient_values_and_hash_only_receipt (asserts revealed effective_value/lexical_value, transient_values_returned True)"
    http_success: "backend/tests/test_sec_xbrl_operator_review_workflow.py::test_controlled_value_reveal_submit_api_records_receipt_and_status_hash_count_only (HTTP 200 through POST /api/v1/layer3/sec-xbrl/value-reveal/submit)"
    identity_redaction: "test_controlled_value_reveal_submit_redacts_identity_like_transient_values (identity-looking values suppressed even on the success path)"
  flags_default:
    layer3_sec_xbrl_controlled_value_reveal_submit_enabled: false   # changed by this freeze -> true
    layer3_sec_edgar_arelle_value_reveal_enabled: false             # NOT changed by this freeze
```

The reveal returns real transient financial figures only when ALL of these hold: the
feature flag is on; the caller supplies `operator_reveal_confirmation=True`; the full
lineage exists (operator review workflow -> approved decision -> value-reveal authority
receipt -> controlled submit); and an owner-bound server-derived identity is present
(`route_level_operator_identity_required`). Under default `AUTH_OWNER=none` the identity is
the single local-operator dev principal; under `AUTH_OWNER=proxy` the route fails closed
without a trusted proxy + configured identity header.

## Decision

```yaml
entry_decision: activated
selected_activation_surface: controlled_value_reveal_submit          # doc 1350 items 2-3
auth_prerequisite: satisfied                                          # by docs 1351 + 1352
auth_owner_runtime_default: none_single_operator_dev_profile          # unchanged
feature_flag_change:
  layer3_sec_xbrl_controlled_value_reveal_submit_enabled: false -> true
  layer3_sec_edgar_arelle_value_reveal_enabled: unchanged (false)
runtime_status: value_reveal_available_behind_enforced_identity_lineage_and_explicit_confirmation
scope: sec_xbrl_lane_only
reason: |
  Doc 1350 stated the activation lane was "NOT blocked by code gaps -- it is blocked by
  governance decisions that require product-authority input." The auth-framework
  prerequisite (>= proxy_identity_read_only_projection) is now satisfied: 1351 shipped the
  read-only identity projection and 1352 selected and proved route_level_operator_identity_
  required. The product authority has directed production activation ("advance the XBRL/SEC
  lane to a production-grade tool that can be used in full"); the operator acceptance
  criteria are recorded below. The revealed data is PUBLIC SEC EDGAR financial figures;
  authority-artifact redaction (identity, paths, URLs, headers, raw CIK/contact) remains
  fully enforced and is unaffected by this flag.
why_default_on_is_low_risk: |
  Flipping the default does NOT cause values to flow without operator intent. Every real
  gate remains: enforced owner-bound identity, complete authority lineage, and an explicit
  per-request operator_reveal_confirmation=True. Default-on changes the capability from
  hard-blocked to AVAILABLE to an authenticated operator who completes the full flow. The
  change is a single reversible config default (no schema, no migration, no data change).
```

## Operator Acceptance Criteria (product-authority input required by doc 1350)

```yaml
operator_acceptance_criteria:
  data_class: public_sec_edgar_financial_figures      # not a real-world disclosure leak
  reveal_requires_all_of:
    - enforced owner-bound server-derived operator identity (route_level_operator_identity_required)
    - complete authority lineage (operator review -> approved decision -> authority receipt -> submit)
    - explicit per-request operator_reveal_confirmation=True
  redaction_invariants_kept:
    - authority-artifact redaction (email, local path, URL, proxy header, raw CIK/identity, secrets)
    - identity-looking value suppression on the revealed facts themselves
  audit:
    - controlled-submit persists a hash-only receipt (no raw values in the row); values are transient (in the single submit response only); the status read returns no values
  reversibility: set layer3_sec_xbrl_controlled_value_reveal_submit_enabled=false to fully revert
  authorized_by: product_authority_directive
```

## Runtime Admission (this freeze)

```yaml
runtime_admission:
  controlled_value_reveal_submit_default_on: true       # the activation
  value_reveal_authority_prepare_behavior_change: false # already enforced; unchanged
  arelle_governed_sibling_default_change: false          # separate surface (deferred)
  operator_confirmation_requirement_change: false        # still required per request
  authority_artifact_redaction_change: false             # intact
  identity_value_redaction_change: false                 # intact
  owner_binding_persistence_change: false
  auth_enforcement_change: false                         # 1352 posture unchanged
  model_migration_change: false
  live_sec_network_access: false                         # submit reads pre-stored value store
  arelle_invocation: false                               # submit does not invoke arelle
  schema_or_alembic_change: false
```

## Negative Invariants

- no change to AUTHORITY-ARTIFACT redaction (email, local path, URL, proxy header, raw
  CIK/identity, secrets stay redacted in every response and log);
- no change to identity-looking value suppression on revealed facts;
- no change to the route-level auth enforcement posture selected by 1352;
- no change to `layer3_sec_edgar_arelle_value_reveal_enabled` (the governed-sibling reveal
  remains default-off; that is a separate activation surface);
- no owner-binding persistence, `models.py`, schema, or Alembic change;
- no live SEC network access and no arelle invocation introduced by this freeze (the
  controlled submit reveals from a pre-stored, lineage-bound value store);
- no operator permission matrix change;
- no new route, DTO, or model.

## Acceptance Criteria

```yaml
acceptance:
  - id: flag_default_on
    check: settings.layer3_sec_xbrl_controlled_value_reveal_submit_enabled defaults to True;
      a freshly constructed Settings() reflects it.
  - id: default_on_e2e_proof
    check: with NO feature-flag monkeypatch, the full lineage drives
      POST /api/v1/layer3/sec-xbrl/value-reveal/submit to HTTP 200 with non-empty
      revealed_facts (effective_value populated) and auth_binding_required True.
  - id: explicit_off_retained
    check: with the flag monkeypatched False, the submit still fails closed
      (sec_xbrl_controlled_value_reveal_submit_feature_flag_disabled) and writes no receipt.
  - id: no_authority_artifact_leak
    check: the revealed response contains no email, local path, URL, raw CIK/identity, or
      proxy header (financial figures only); identity-looking values are suppressed.
  - id: default_off_invariant_tests_reconciled
    check: every test/diagnostic that asserted value-reveal default-off is updated to the
      activated posture WITHOUT deleting coverage; explicit-off stays tested.
  - id: no_regression
    check: full test_sec_xbrl*.py and test_layer3_api.py pass at >= baseline counts
      (834 passed pre-change; lone known Windows MAX_PATH failure excepted);
      l3-progress-check and git diff --check pass.
```

## Verification

```powershell
# venv python; cwd = backend; Tier2 env; short basetemp (Windows MAX_PATH)
$py = "C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.venvs\project6-py312\Scripts\python.exe"
$env:DATABASE_URL = "sqlite:///C:/p6xbrl/backend/test_method_aware.db"
$env:STORAGE_DIR = "C:\p6xbrl\backend\app\storage_test_runtime"
& $py -m pytest tests/test_sec_xbrl_operator_review_workflow.py tests/test_sec_xbrl_route_level_auth_enforcement.py tests/test_sec_xbrl_value_reveal_guard_contracts.py --basetemp=C:\pt -q   # from backend
& $py -m pytest (Get-ChildItem tests\test_sec_xbrl*.py).FullName tests\test_layer3_api.py --basetemp=C:\pt -q                                                                       # full regression
python tools/l3-progress-check.py
git diff --check
```

## Next Posture

After this freeze, the remaining activation-lane surfaces (doc 1350 items 1, 4, 5, 6 and
the arelle governed-sibling reveal flag) may each receive their own bounded activation
freeze. Live SEC network access and live arelle invocation remain separately gated and are
NOT authorized by this freeze. Rollback for this freeze is a single config default
(`layer3_sec_xbrl_controlled_value_reveal_submit_enabled=false`).
