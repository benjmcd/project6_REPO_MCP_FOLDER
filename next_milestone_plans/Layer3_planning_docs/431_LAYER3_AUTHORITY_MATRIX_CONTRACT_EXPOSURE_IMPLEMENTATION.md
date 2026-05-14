# 431 - Layer 3 Authority Matrix Contract Exposure Implementation

## Status

Status: branch-local bounded implementation for `await_layer3_authority_matrix_contract_exposure_implementation_after_audit_sync`.

Doc: `431_LAYER3_AUTHORITY_MATRIX_CONTRACT_EXPOSURE_IMPLEMENTATION.md`.

This implementation follows current-main sync doc `430_LAYER3_AUTHORITY_MATRIX_CONTRACT_EXPOSURE_AUDIT_CURRENT_MAIN_SYNC.md`.

Current-main preflight commit: `647c6d64577f62ebe50d7b25be33edd000a49172`.

## Implementation Result

Result: `layer3_authority_matrix_contract_exposure_implemented_for_read_only_bootstrap_readiness`.

The implementation exposes an exposure-aware `authority_matrix_contract` payload only through existing read-only bootstrap and readiness response paths.

The response payload is built from `build_exposed_authority_matrix_contract()`, which derives from `build_authority_matrix_contract()` and preserves the pure source contract's schema id `layer3.authority_matrix_contract.v1`, contract definition id `layer3_authority_matrix_contract_definition_v1`, fail-closed result `blocked_no_runtime_authority`, and blocked runtime scope.

The exposed payload marks the admitted response-only slice with `exposure_context: read_only_bootstrap_readiness_response_paths`, `admitted_for_read_only_bootstrap_readiness_exposure`, `admitted_for_existing_bootstrap_readiness_openapi_schema`, and `admitted_for_bootstrap_readiness_response_model_shape`. It continues to block a separate authority-matrix route, schema/model/migration work, rendered UI, runtime behavior, and connector/provider behavior.

## Files Changed

- `backend/app/services/layer3_authority_matrix_contract.py` adds `build_exposed_authority_matrix_contract()` as the read-only bootstrap/readiness response variant while preserving the pure source builder.
- `backend/app/services/layer3_workbench.py` imports `build_exposed_authority_matrix_contract()` and passes `_workbench_authority_matrix_contract()` into existing bootstrap/readiness builders.
- `backend/app/services/layer3_bootstrap_contract.py` adds an `authority_matrix_contract` payload to `build_bootstrap_contract()`.
- `backend/app/services/layer3_readiness_contract.py` adds an `authority_matrix_contract` payload to `build_readiness_contract()`.
- `backend/app/api/layer3.py` adds explicit `authority_matrix_contract: dict[str, Any]` fields to `Layer3WorkbenchBootstrapResponse` and `Layer3ExecutionReadinessResponse`.
- `backend/tests/test_layer3_workbench.py` proves bootstrap/readiness bodies include the exposure-aware authority matrix contract and that separate route/runtime blocked rows remain fail-closed.
- `backend/tests/test_layer3_bootstrap_contract.py` proves direct bootstrap contract-builder parity includes `authority_matrix_contract`.
- `backend/tests/test_layer3_readiness_contract.py` proves direct readiness contract-builder parity includes `authority_matrix_contract`.
- `backend/tests/test_layer3_api.py` proves bootstrap/readiness OpenAPI schemas and response bodies include exposure-aware `authority_matrix_contract`, while no `/api/v1/layer3/authority-matrix` route is created.
- `backend/tests/test_layer3_authority_matrix_contract.py` proves the pure source builder remains fail-closed and the exposed builder marks only the admitted read-only response slice as exposed.

## Branch-Local Validation

- `python -m pytest .\backend\tests\test_layer3_workbench.py -k "bootstrap_is_explicit_about_first_slice_limits or state_action_contract_is_derived_from_state_model"`: `PASS`.
- `python -m pytest .\backend\tests\test_layer3_bootstrap_contract.py .\backend\tests\test_layer3_readiness_contract.py`: `PASS`.
- `python -m pytest .\backend\tests\test_layer3_api.py -k bootstrap_readiness_openapi_contracts`: `PASS`.
- `python -m pytest .\backend\tests\test_layer3_authority_matrix_contract.py`: `PASS`.
- PowerShell-expanded local equivalent of `python -m pytest ./backend/tests/test_layer3_*.py -q`: `PASS` (`525 passed`).

## Boundary

Entry decision: `read_only_bootstrap_readiness_exposure_implemented`.

Runtime status: `not_implemented`.

Existing bootstrap/readiness response shape changes are admitted by doc `429`; no new route is created.

No rendered operator panel, schema/model/migration change, runtime execution behavior, external connector invocation, destination write, connector-run creation, generic downstream dispatch, rendered connector action control, provider-public delivery/use, raw public URL display/use, public proxy runtime, package mutation, source expansion, RAG/vector behavior, auth/security behavior change, or frontend-only durable authority is admitted by this implementation.

The next required action after merge is `current_main_sync_layer3_authority_matrix_contract_exposure_implementation_after_merge`.

The next whole-project posture after sync is `await_layer3_next_governed_runtime_tranche_freeze_after_authority_matrix_exposure_sync`.
