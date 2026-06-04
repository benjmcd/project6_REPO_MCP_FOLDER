# 1350 SEC XBRL Activation Lane Selection

Target: `sec_xbrl_activation_lane_selection_v1`.

## Purpose

The SEC XBRL consolidation series (planning docs 1345–1349, PRs #2128–#2173) completed the
prerequisite work: shared diagnostic framework, report leak guard, raw-value-key variants,
text-leak helpers, public authority guard (value-reveal, auth-binding families), custom guard
audit, exact unadmitted-key adapter, and resolved-fact redaction wrappers. All relevant
duplicate helpers are now consolidated into the shared modules.

The "activation lane" was explicitly parked throughout these consolidation PRs. This doc
makes the first governance decision about that parked lane.

## What the Activation Lane Covers

The activation lane refers to enabling the following behaviors, which have been built and
tested in validate-only or default-off postures:

1. **Default-on runtime posture**: `layer3_sec_xbrl_default_on_admission_restatement.py`
   - Currently in a `default_off` admission posture
   - Would make the SEC XBRL data flow available to operators without an explicit opt-in flag

2. **Value-reveal authorization**: `layer3_sec_xbrl_value_reveal_authority.py`
   - Currently validate-only; actual value reveal is blocked
   - Activation would allow operators to see redacted financial values

3. **Controlled value-reveal submit**: `layer3_sec_xbrl_controlled_value_reveal_submit.py`
   - Currently validate-only; submit path is blocked
   - Activation would allow submitting value-reveal requests to the controlled operator endpoint

4. **E2E integration runtime**: `layer3_sec_xbrl_e2e_integration.py` + `layer3_sec_xbrl_e2e_offline_orchestrator.py`
   - Currently offline/test-only; E2E integration is not live in the API
   - Activation would connect the offline orchestrator to live workbench sessions

5. **Multi-filing evidence authority gate**: `layer3_sec_xbrl_multi_filing_evidence_authority_gate.py`
   - Currently validate-only; multi-filing authority is not enforced at runtime
   - Activation would make this gate enforcement live

6. **In-app auth policy**: `layer3_sec_xbrl_in_app_auth_policy.py`
   - Currently planning/validate-only
   - Activation would make auth policy enforcement live for SEC XBRL routes

## Decision

```yaml
entry_decision: deferred_pending_auth_framework
selected_activation_mode: null
runtime_status: not_implemented
reason: |
  The activation lane requires:
  (1) A working auth/security framework at minimum proxy_identity_read_only_projection
      level (see 200_AUTH_SECURITY_ENTRY_CONTRACT.md). Without an identity surface,
      in-app auth policy enforcement (item 6) has no identity to enforce against.
  (2) A production operator acceptance criteria review — the value-reveal surface
      (items 2–3) has significant implications for data access. An operator acceptance
      criteria review must happen before value-reveal is activated.
  (3) A separate activation freeze for each sub-surface (items 1–6 must each have
      their own bounded freeze/contract/proof; they cannot all activate together).

  The consolidation work is complete. The activation is NOT blocked by code gaps —
  it is blocked by governance decisions that require product-authority input.

next_follow_up: |
  One of:
  (A) sec_xbrl_default_on_runtime_activation_freeze — authorize only item 1
      (default-on runtime) as a standalone activation without value-reveal or
      auth policy. This is the narrowest activation path.
  (B) sec_xbrl_auth_policy_activation_freeze — authorize only item 6
      (in-app auth policy) after auth mode is selected (doc 200 follow-up).
  (C) sec_xbrl_activation_lane_operator_review — schedule a product-authority
      review of the activation scope before selecting a freeze.
```

## Evidence Ledger

```yaml
evidence_ledger:
  consolidation_complete:
    status: verified
    evidence:
      - next_milestone_plans/Layer3_planning_docs/1349-sec-xbrl-custom-guard-audit.md
      - git log: PRs #2128-#2173 merged at a2775067
  current_test_state:
    status: verified
    evidence:
      - layer3_progress_board.md: "477 passed, 3 warnings" on full SEC XBRL suite
  default_on_admission_module:
    status: verified
    evidence:
      - backend/app/services/layer3_sec_xbrl_default_on_admission_restatement.py (exists)
  value_reveal_module:
    status: verified
    evidence:
      - backend/app/services/layer3_sec_xbrl_value_reveal_authority.py (exists, validate-only)
  controlled_submit_module:
    status: verified
    evidence:
      - backend/app/services/layer3_sec_xbrl_controlled_value_reveal_submit.py (exists, validate-only)
  e2e_integration_module:
    status: verified
    evidence:
      - backend/app/services/layer3_sec_xbrl_e2e_integration.py (exists, offline only)
  multi_filing_gate_module:
    status: verified
    evidence:
      - backend/app/services/layer3_sec_xbrl_multi_filing_evidence_authority_gate.py (exists)
  in_app_auth_policy_module:
    status: verified
    evidence:
      - backend/app/services/layer3_sec_xbrl_in_app_auth_policy.py (exists)
  auth_framework:
    status: open
    evidence: []
    blocker: "No auth/security implementation exists; AUTH_OWNER=none default; doc 200 deferred"
  operator_acceptance_criteria:
    status: open
    evidence: []
    blocker: "No product-authority acceptance criteria for value-reveal activation"
  activation_lane_isolation_plan:
    status: open
    evidence: []
    blocker: "Items 1-6 must each have a separate freeze before any can activate"
```

## Capability Isolation Matrix (this pass — docs only)

```yaml
capability_isolation_matrix:
  default_on_runtime_activation:
    planning_allowed_in_this_pass: true
    runtime_allowed_in_this_pass: false
  value_reveal_activation:
    planning_allowed_in_this_pass: true
    runtime_allowed_in_this_pass: false
  controlled_submit_activation:
    runtime_allowed_in_this_pass: false
  e2e_integration_live:
    runtime_allowed_in_this_pass: false
  multi_filing_gate_enforcement:
    runtime_allowed_in_this_pass: false
  in_app_auth_policy_enforcement:
    runtime_allowed_in_this_pass: false
  alembic_migration:
    runtime_allowed_in_this_pass: false
  live_arelle_invocation:
    runtime_allowed_in_this_pass: false
  live_sec_network_access:
    runtime_allowed_in_this_pass: false
  diagnostic_report_change:
    runtime_allowed_in_this_pass: false
  proof_json_change:
    runtime_allowed_in_this_pass: false
  activation_lane_authorization:
    status: explicitly_deferred
```

## Remaining Custom Guard Surfaces (do NOT migrate in this pass)

Per planning doc 1349, these wrappers remain custom (do NOT consolidate further):

- `layer3_sec_xbrl_projection_persistence._reject_raw_or_local_authority`
- `layer3_sec_xbrl_statement_packet_persistence._reject_raw_or_local_authority`
- `layer3_sec_xbrl_operator_review_workflow._reject_raw_or_local_authority`

These preserve service-local exception classes, error codes, messages, and `details.fields`
shape. They already delegate to the shared guard; consolidation would not add value and would
risk weakening service-local error contracts.

CIK/contact scan variants, auth-binding helpers, and residual-magnitude policy surfaces
in the SEC XBRL services also remain service-family-specific and must not be bulk-migrated.

## Runtime Non-Admission (this pass)

```yaml
runtime_admission:
  default_on_posture_change: false
  value_reveal_activation: false
  controlled_submit_activation: false
  e2e_integration_live: false
  multi_filing_gate_live: false
  in_app_auth_policy_live: false
  route_api_behavior_change: false
  model_migration_change: false
  arelle_invocation: false
  live_sec_network_access: false
  diagnostic_report_change: false
  proof_json_change: false
  source_acquisition_change: false
  activation_lane_authorization: false
```

## Negative Invariants

- no activation-lane authorization;
- no default-on runtime posture change;
- no value-reveal behavior change;
- no controlled-submit behavior change;
- no E2E integration live;
- no multi-filing gate enforcement change;
- no in-app auth policy enforcement change;
- no Alembic migration;
- no live Arelle invocation;
- no live SEC network access;
- no diagnostic report change;
- no proof JSON change;
- no source acquisition change;
- no route/API behavior change;
- no model change;
- no production service behavior change;
- no test behavior change.

## Stop Condition

Stop and return to planning before any activation code if:
- auth mode is still `null` in `200_AUTH_SECURITY_ENTRY_CONTRACT.md`;
- no operator acceptance criteria for value-reveal exist;
- activation items 1–6 have not each received a separate bounded freeze/contract/proof.

## Verification for This Planning Doc PR

```powershell
# Full SEC XBRL suite — no regression from docs-only change
python -m pytest backend/tests/test_sec_xbrl*.py -q

# Progress check
python tools/l3-progress-check.py

# JSON validity
python -m json.tool next_milestone_plans/layer3_progress_manifest.json > $null

# Clean diff
git diff --check
```

## Next Posture

After this doc merges: continue only with path (A), (B), or (C) from the `next_follow_up`
field above, in the order the product/operator authority selects. Do not begin activation
without an explicit `sec_xbrl_activation_freeze_v1` or equivalent doc that authorizes exactly
one activation surface.
