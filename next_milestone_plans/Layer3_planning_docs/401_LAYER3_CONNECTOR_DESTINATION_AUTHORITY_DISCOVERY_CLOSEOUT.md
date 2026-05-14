# 401 - Layer 3 Connector Destination Authority Discovery Closeout

## Status

Status: planning/control closeout for `connector_destination_dispatch_authority_discovery`; `entry_decision: no_runtime_now`.

This closeout executes the next allowed action from `400_LAYER3_CONNECTOR_DESTINATION_AUTHORITY_DISCOVERY_FREEZE_CURRENT_MAIN_SYNC.md`: `conduct_connector_destination_dispatch_authority_discovery`.

This governing artifact is `401_LAYER3_CONNECTOR_DESTINATION_AUTHORITY_DISCOVERY_CLOSEOUT.md`.

The selected exact named Layer 3 product/use-case requirement remains `operator_reviews_connector_destination_dispatch_authority_gap_without_external_invocation`.

The selected runtime mode is `null`.

The runtime status is `not_implemented`.

The stop condition is `no_runtime_now_connector_destination_named_target_absent`.

## Source Evidence

The current Layer 3 connector/destination handoff surface remains `internal_dispatch_record_only`.

Repo-confirmed Layer 3 evidence:

- `backend/app/services/layer3_connector_dispatch_entry.py` defines `CONNECTOR_DISPATCH_RECORD_MODE = "internal_dispatch_record_only"`.
- `backend/app/services/layer3_connector_dispatch_entry.py` forbids `connector_key`, `connector_run_id`, `connector_secret`, `destination_id`, `destination_secret`, `destination_url`, provider URL fields, package mutation fields, source expansion fields, RAG fields, retry/rerun fields, and hidden LLM fields.
- `backend/app/services/layer3_connector_dispatch_entry.py` returns `external_connector_invocation_enabled: False`, `destination_write_enabled: False`, and `connector_run_created: False`.
- `backend/app/api/layer3.py` exposes only `POST /api/v1/layer3/handoff/connector/record` for the Layer 3 connector boundary and routes it to `record_internal_connector_dispatch`.
- `backend/app/api/layer3.py` marks connector keys, connector run IDs, destination IDs, destination secrets, and destination URLs as known but non-admitted fields in the connector record schema.
- `backend/app/services/layer3_state_action_contract.py` admits only `internal_dispatch_record_only` and keeps `connector_destination_dispatch` deferred.
- `backend/app/services/layer3_state_model_contract.py` allows only `inspect_internal_connector_dispatch_record` after `connector_dispatch_recorded` and forbids `external_connector_invocation`, `destination_write`, and `connector_run_creation`.
- `backend/tests/test_layer3_api.py` proves the connector record endpoint creates an internal receipt without external side effects, rejects forbidden connector/destination fields, records `dispatch_mode: internal_dispatch_record_only`, and reports `external_connector_invocation_enabled`, `destination_write_enabled`, and `connector_run_created` as false.

Repo-confirmed adjacent connector evidence:

- `backend/app/api/router.py` exposes general source/retrieval connector run APIs for `sciencebase_public`, `sciencebase_mcs`, `nrc_adams_aps`, and `senate_lda`.
- `backend/app/models/models.py` contains generic `ConnectorRun`, `ConnectorRunSubmission`, `ConnectorRunTarget`, checkpoint, policy, event, and artifact-alias rows for source/retrieval connector runs.
- `backend/app/services/connectors_nrc_adams.py`, `backend/app/services/connectors_sciencebase.py`, and `backend/app/services/connectors_senate_lda.py` own source/retrieval connector submission and execution behavior.
- Those source/retrieval connector surfaces do not provide a Layer 3 downstream destination target, Layer 3 destination write, Layer 3 connector dispatch route, or Layer 3 delivery side-effect contract.

## Discovery Answers

- Exact named connector selected for Layer 3 runtime dispatch: not identified.
- Exact named destination target selected for Layer 3 runtime dispatch: not identified.
- Destination writes allowed: no; current Layer 3 responses and contracts keep destination writes disabled or forbidden.
- Existing `internal_dispatch_record_only` substrate: sufficient only as an inspection/intent record, not as runtime dispatch authority.
- Owner service for later runtime dispatch: not identified; the current owner service owns only internal record creation.
- Route/request/response/model/migration/idempotency/replay/audit/failure contract for runtime dispatch: not admitted.
- Credential, secret, tenant/session-owner, auth/security, and leak-control policy: not identified for Layer 3 downstream dispatch.
- Required negative-test matrix for runtime dispatch: not admitted because the runtime target and side-effect policy are absent.
- Rendered action controls: not admitted; current rendered surfaces may only display blocked/read-only connector status.
- Headed/headless browser proof: not required for this closeout because no rendered UI behavior changes in this pass.

## Decision

The discovery result is `insufficient_authority_for_layer3_connector_destination_runtime`.

This pass must stop as `no_runtime_now_connector_destination_named_target_absent`.

No implementation-entry freeze is justified from current main because the discovery did not identify a named Layer 3 connector, named destination, owner runtime service, credential/security model, and fail-closed side-effect policy.

## Non-Admission Boundary

This closeout admits no runtime behavior, no external connector invocation, no destination write, no connector-run creation, no generic downstream dispatch, no rendered connector action control, no provider-public delivery/use, no raw public URL display/use, no public proxy runtime, no package mutation, no source expansion, no RAG/vector behavior, no auth/security behavior change, no model or migration change, and no frontend-only durable authority.

The existing `/api/v1/layer3/handoff/connector/record` surface remains internal record-only.

The general `/api/v1/connectors/.../runs` source/retrieval APIs remain adjacent infrastructure, not Layer 3 downstream delivery authority.

## Next Whole-Project Posture

The next whole-project posture is `await_next_exact_named_layer3_product_use_case_requirement_after_connector_destination_no_runtime_closeout`.

A future connector/destination implementation-entry freeze may only start after a new exact named Layer 3 product/use-case requirement identifies:

- a named connector;
- a named destination;
- the runtime owner service;
- the credential/security model;
- the fail-closed side-effect policy;
- the receipt/audit/idempotency/replay contract;
- the required negative-test matrix.
