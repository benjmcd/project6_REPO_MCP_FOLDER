# 1361 SEC Live Source Matrix Transition

Target: `sec_live_network_egress_experimental_default_off_transition_v1`.

## Purpose

This pass updates the support-matrix classification for the already-landed SEC
EDGAR live source-artifact acquisition surface. The previous `unsupported`
classification no longer matched current source authority: the API, service,
bootstrap contract, rendered control, fake-client tests, redirect guard, and
progress verifier already prove a bounded operator-confirmed acquisition path.

This pass does not make live SEC network access default-on and does not claim
production readiness.

## Authority Check

```yaml
authoritative_main_before_this_pass: 39f1f5a3325de035b919b61ac666bc198a338bd6
current_runtime:
  service: backend/app/services/layer3_sec_edgar_live_source_artifact.py
  api: backend/app/api/layer3/source_sec_edgar.py
  bootstrap_contract: backend/app/services/layer3_bootstrap_contract.py
  rendered_control: backend/app/review_ui/static/layer3.html
  rendered_client: backend/app/review_ui/static/layer3.js
existing_planning_authority:
  - next_milestone_plans/Layer3_planning_docs/1140-sec-edgar-text-table-live-source-artifact-acquisition-selection.md
  - next_milestone_plans/Layer3_planning_docs/1141-sec-edgar-text-table-live-source-artifact-acquisition-runtime.md
  - next_milestone_plans/Layer3_planning_docs/1142-sec-edgar-text-table-live-source-artifact-acquisition-runtime-current-main-sync.md
  - next_milestone_plans/Layer3_planning_docs/1143-sec-edgar-text-table-live-source-artifact-acquisition-rendered-status-selection.md
  - next_milestone_plans/Layer3_planning_docs/1144-sec-edgar-text-table-live-source-artifact-acquisition-rendered-status-runtime.md
  - next_milestone_plans/Layer3_planning_docs/1146-sec-edgar-text-table-live-source-artifact-acquisition-rendered-status-review-remediation-current-main-sync.md
official_sec_policy_rechecked:
  developer_resources: https://www.sec.gov/about/developer-resources
  accessing_edgar_data: https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
  max_rate: no_more_than_10_requests_per_second_total_per_user
  repo_default_rate: one_request_per_second_until_operator_configured
  user_agent_model: server_configured_contact_identity_required
```

## Decision

```yaml
entry_decision: support_matrix_status_transition
capability: sec_live_network_egress
old_status: unsupported
new_status: experimental_default_off
config_default_change: false
LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED_default: false
support_matrix_change: true
runtime_behavior_change: false
redaction_posture_change: false
value_reveal_change: false
controlled_submit_change: false
production_readiness_claimed: false
live_sec_manual_smoke_in_this_pass: false
ci_real_network_access: false
proof_mode: default_off_guard_plus_fake_sec_client_contract_double
```

`unsupported` is no longer the coherent status because the runtime is armable by
explicit server configuration and already has fake-client proof. `supported` is
also not coherent because the selected local profile still pins
`LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED=false`, requires server-configured
User-Agent identity, disables real network access in CI, and has no
production-readiness or value-reveal claim. The consistent classification is
`experimental_default_off`.

## Runtime Contract

The support-matrix runtime-contract audit now proves:

- with `LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED=false`, acquisition fails closed
  before any fetch call;
- with the flag explicitly enabled and a server User-Agent configured, the
  fake SEC client can acquire one complete-submission text artifact and return a
  redacted receipt;
- the proof uses no real network;
- raw SEC URL, raw local path, server User-Agent, and artifact bytes remain
  unrendered/unexposed;
- the support matrix still pins `LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED` false
  for the selected profile.

## Tier And Rollback

This is Tier-2 because it changes a support-matrix capability status for a live
network surface. It does not touch ORM models, Alembic migrations, durable
persistence shape, value reveal, default-on behavior, redaction posture, route
semantics, or runtime defaults.

Rollback is narrow: revert the support-matrix status, the checker/audit expected
status, this doc, and the associated board/manifest entries. Runtime containment
does not depend on rollback because the default flag remains false and the real
HTTP client still blocks when the flag, server User-Agent, CI policy, redirect
guard, request field guard, or hash checks fail.

## Next Posture

The next production-readiness pass should not jump to value reveal. The coherent
sequence is:

1. operator-configured manual live SEC source-artifact smoke outside CI, using a
   small allowlisted filing and recording only hash/redacted receipt evidence;
2. Arelle/fact-authority invocation over server-owned acquired evidence;
3. multi-filing evidence authority enforcement;
4. delivery/export/status proof over the acquired-authority chain;
5. nonlocal operator auth hardening;
6. default-on/value-reveal graduation only after the preceding chain is proven.
