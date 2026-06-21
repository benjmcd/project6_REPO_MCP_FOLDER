# 1360 SEC XBRL Current Posture Reconciliation

Target: `sec_xbrl_current_posture_reconciliation_v1`.

## Purpose

This pass reconciles the SEC XBRL activation-planning record with current
`project6-origin/main` runtime truth after the RC3 support-matrix hardening lane.
It is a docs/test honesty pass only. It does not change any runtime flag,
capability status, redaction posture, route behavior, model, migration, or
operator workflow.

## Authority Check

Current live authority at this pass:

```yaml
authoritative_main: 6b83cd0b80e2f17f82f1c58c466e7163480be0d3
config_default:
  LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED: false
support_matrix:
  sec_controlled_value_reveal_submit: experimental_default_off
  sec_value_reveal: experimental_default_off
  sec_live_network_egress: unsupported
  real_provider_delivery: unsupported
readme_front_door:
  selected_profile: local_expert + public_connectors + sec_xbrl_offline
  production_ready_sec_value_reveal: false
```

Docs `1350-sec-xbrl-activation-lane-selection.md` and
`1353-sec-xbrl-value-reveal-activation.md` contain historical activation/default-on
language. That language is not current runtime authority. Current config, support
matrix, README, and support-matrix runtime-contract tests reassert the conservative
posture: controlled value reveal remains experimental/default-off unless explicitly
enabled in runtime configuration.

## Decision

```yaml
entry_decision: reconciled_to_current_main
controlled_value_reveal_default_on_current_main: false
controlled_value_reveal_submit_status: experimental_default_off
support_matrix_change: false
config_default_change: false
runtime_behavior_change: false
redaction_posture_change: false
production_readiness_claimed: false
historical_docs_reinterpreted:
  - 1350-sec-xbrl-activation-lane-selection.md activation update
  - 1353-sec-xbrl-value-reveal-activation.md default-on freeze language
current_authority:
  - backend/app/core/config.py
  - config/support_matrix.yaml
  - README.md
  - scripts/support_matrix_runtime_contract_audit.py
  - backend/tests/test_layer3_support_matrix_runtime_contract_exhaustive.py
```

## Test Correction

`backend/tests/test_sec_xbrl_runtime_posture.py` now treats the default posture as
feature-flag gated:

- the default fixture keeps
  `settings.layer3_sec_xbrl_controlled_value_reveal_submit_enabled = False`;
- the default posture test expects
  `sec_xbrl_controlled_value_reveal_submit_blocked_by_feature_flag`;
- a separate explicit-enabled test proves the posture still reports controlled
  value reveal as available when the flag is intentionally enabled.

This prevents future posture tests from masking a drift between config defaults
and the operator-facing posture projection.

## Negative Invariants

- no support-matrix capability status change;
- no config default or `.env` default change;
- no value reveal activation;
- no controlled-submit activation;
- no live SEC network access;
- no Arelle invocation;
- no multi-filing enforcement;
- no delivery/export/provider behavior;
- no model, migration, persistence, or schema change;
- no redaction-posture change;
- no production-readiness claim.

## Next Posture

The next implementation-entry freeze should select exactly one production-readiness
surface from the runtime posture map. The recommended dependency order is:

1. live SEC source acquisition, because source acquisition authority precedes
   live Arelle/fact authority and multi-filing evidence;
2. Arelle invocation/fact authority over server-owned acquired evidence;
3. multi-filing evidence authority gate enforcement;
4. delivery/export/package status;
5. nonlocal operator-auth hardening and deployment readiness;
6. default-on/value-reveal graduation only after the preceding authority chain is
   proven and support-matrix status is intentionally changed.

Any future pass that changes value reveal, default-on behavior, persistence,
redaction posture, or production readiness is Tier-2 under the active SEC XBRL
merge-gate policy and must record the touched surfaces, rollback/containment,
targeted verification, and review/coherence check evidence.
