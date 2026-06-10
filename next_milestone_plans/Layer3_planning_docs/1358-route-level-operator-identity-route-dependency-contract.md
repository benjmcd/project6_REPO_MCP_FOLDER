# 1358 Route-Level Operator Identity Route Dependency Contract

Status: planning-only contract. No runtime has been implemented. This doc is the
"explicit route contract" required by doc 200's stop-conditions block before any
implementation pass may wire a route-level operator-identity dependency onto
non-sec-xbrl mutating Layer 3 routes.

Doc 200 (`200_AUTH_SECURITY_ENTRY_CONTRACT.md`) stops any proposal that would
"change route dependencies without an explicit route contract". This doc IS that
explicit contract for a future implementation pass. It admits no runtime now.

## Authority Order

1. live `project6-origin/main` source files — `backend/app/api/layer3/handoff.py`,
   `backend/app/api/layer3/package.py`, `backend/app/api/layer3/source_ingestion.py`,
   `backend/app/services/layer3_sec_xbrl_in_app_auth_policy.py`,
   `backend/app/api/layer3/_shared.py`;
2. doc 200 `200_AUTH_SECURITY_ENTRY_CONTRACT.md` allowed-mode list and stop conditions;
3. doc 1352 `1352-sec-xbrl-route-level-operator-identity-required.md` as the
   already-wired reference implementation (sec_xbrl lane only);
4. this contract document.

Planning prose, browser state, proxy headers from untrusted clients, and
manually-supplied usernames are not authority for any future runtime implementation.

## Decision

```yaml
contract_status: authored
runtime_status: not_implemented
selected_future_mode: route_level_operator_identity_required
mode_source: doc 200 allowed-mode list
identity_semantics:
  AUTH_OWNER_none: local single-operator principal via _server_derived_principal;
    identity seam only, NOT an access gate; all admitted routes continue to
    succeed with the same response shape as today
  AUTH_OWNER_proxy_without_TRUSTED_PROXY_MODE: fail-closed HTTP 409,
    error_code sec_xbrl_in_app_auth_policy_untrusted_proxy_identity
  AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true: proxy identity derived
    server-side via configured header; fails 401 if required header absent
new_flags: none
default_on_changes: none
value_reveal_activation: false
controlled_submit_activation: false
model_migration_change: false
production_readiness_claim: false
```

The identity semantics directly reuse `_server_derived_principal` from
`backend/app/services/layer3_sec_xbrl_in_app_auth_policy.py` (lines 245-279)
via a to-be-authored public wrapper function. The seam is an identity stamp
recorded server-side; it does NOT gate access — admitted routes proceed regardless
of which operator profile is active under `AUTH_OWNER=none`.

## Scope: Excluded Routes

Routes in `backend/app/api/layer3/sec_xbrl.py` are EXCLUDED from this contract.
Those routes already enforce the imperative in-app auth policy via
`_sec_xbrl_policy_decision` + `_sec_xbrl_require_binding` (doc 1352). Wiring
them again under this contract would constitute a double-enforcement error.

Routes in `backend/app/api/layer3/source_ingestion.py` are NOT admitted by
this contract version (see source_ingestion section below).

## Route Enumeration: handoff.py

Source: `backend/app/api/layer3/handoff.py` — 19 POST routes confirmed by grep.

| Path | Handler | Classification |
|------|---------|----------------|
| `/handoff/export/prepare` | `post_handoff_export_prepare` | mutating_write |
| `/handoff/aps/dispatch` | `post_aps_handoff_dispatch` | mutating_write |
| `/handoff/export/download/readiness` | `post_mixed_source_external_export_download_readiness` | read_projection |
| `/handoff/export/download/prepare` | `post_external_export_download_prepare` | mutating_write |
| `/handoff/connector/record` | `post_connector_dispatch_record` | mutating_write |
| `/handoff/connector/local-destination/receipt` | `post_connector_local_destination_receipt` | mutating_write |
| `/handoff/connector/local-outbox/fake-target` | `post_server_owned_local_outbox_fake_target` | mutating_write |
| `/handoff/connector/local-outbox/write` | `post_server_owned_local_outbox_write` | mutating_write |
| `/handoff/connector/local-outbox/provider-private/prepare` | `post_local_outbox_provider_private_handoff_prepare` | mutating_write |
| `/handoff/connector/local-outbox/external-local-export/write` | `post_external_local_export_write` | mutating_write |
| `/handoff/export/internal-webhook/dispatch` | `post_internal_webhook_dispatch` | mutating_write |
| `/handoff/export/download/signed-reference/generate` | `post_external_export_download_signed_reference_generate` | mutating_write |
| `/handoff/export/download/provider-private-signed-url/prepare` | `post_provider_private_signed_url_prepare` | mutating_write |
| `/handoff/export/download/provider-private-signed-url/revoke` | `post_provider_private_signed_url_revoke` | mutating_write |
| `/handoff/export/download/provider-public-url/prepare` | `post_provider_public_url_prepare` | mutating_write |
| `/handoff/export/download/provider-public-url/revoke` | `post_provider_public_url_revoke` | mutating_write |
| `/handoff/export/download/provider-public-url/use` | `post_provider_public_url_delivery_use` | mutating_write |
| `/handoff/export/download/deliver` | `post_external_export_download_deliver` | needs_audit |
| `/handoff/export/download/signed-reference/use` | `post_external_export_download_signed_reference_use` | needs_audit |

`needs_audit` note: `post_external_export_download_deliver` and
`post_external_export_download_signed_reference_use` stream `FileResponse` bytes
and record delivery state. Whether they are classified as mutating_write or
read_projection for operator-identity wiring purposes requires a follow-up audit
of the underlying delivery recording service calls before any implementation
targets them.

## Route Enumeration: package.py

Source: `backend/app/api/layer3/package.py` — 16 POST routes confirmed by grep.

| Path | Handler | Classification |
|------|---------|----------------|
| `/package/review/preview` | `post_package_review_preview` | read_projection |
| `/package/review/commit` | `post_package_review_commit` | mutating_write |
| `/package/review/submit` | `post_package_review_submit` | mutating_write |
| `/package/mutation/preview` | `post_package_mutation_preview` | read_projection |
| `/package/replacement-artifact/materialize` | `post_package_replacement_artifact_materialize` | mutating_write |
| `/package/replacement-set/record` | `post_package_replacement_set_record` | mutating_write |
| `/package/replacement-set/record-from-corrected-artifact-set` | `post_package_replacement_set_record_from_corrected_artifact_set` | mutating_write |
| `/package/supersession/commit` | `post_package_supersession_commit` | mutating_write |
| `/package/supersession/commit-from-corrected-artifact-set-authority` | `post_package_supersession_commit_from_corrected_artifact_set_authority` | mutating_write |
| `/package/replacement-artifact/manifest/record` | `post_package_replacement_artifact_manifest_record` | mutating_write |
| `/package/replacement-artifact/manifest/record-from-authority` | `post_package_replacement_artifact_manifest_record_from_authority` | mutating_write |
| `/package/replacement-artifact/manifest/record-from-corrected-artifact-set-authority` | `post_package_replacement_artifact_manifest_record_from_corrected_artifact_set_authority` | mutating_write |
| `/package/corrected-artifact-set/record` | `post_package_corrected_artifact_set_record` | mutating_write |
| `/package/replacement-namespace/record` | `post_package_replacement_namespace_record` | mutating_write |
| `/package/replacement-namespace/record-from-corrected-artifact-manifest-authority` | `post_package_replacement_namespace_record_from_corrected_artifact_manifest_authority` | mutating_write |
| `/package/replacement-activation/commit` | `post_package_replacement_activation_commit` | mutating_write |

## Route Enumeration: source_ingestion.py

Source: `backend/app/api/layer3/source_ingestion.py` — 83 POST routes confirmed by grep.

Per-route classification is deferred to a follow-up audit. This contract does NOT
admit wiring of source_ingestion routes until that audit lands.

Path-prefix inventory (from grep output):

| Path prefix | Approximate family |
|-------------|-------------------|
| `/source/intake/...` | source intake upload |
| `/source/ingestion/candidate-b/...` | candidate-b bundle, runtime, corpus workflow, repeatability, promotion (~50 routes) |
| `/source/ingestion/server-configured-directory/...` | scan, hybrid-authority, vector-retrieval, qualitative-analysis, handoff/export (~30 routes) |
| `/source/mixed-corpus/...` | mixed corpus seed and materialize |

Explicit statement: wiring source_ingestion routes under this contract is NOT
admitted. A separate audit doc must enumerate and classify all 83 routes before
any source_ingestion route may receive an operator-identity dependency under this
mode.

## Request/Response Contract

The future implementation dependency adds NO new request fields. Requests to
wired routes remain byte-identical to today.

Under `AUTH_OWNER=none` (local single-operator dev profile):
- the server derives the local-operator principal via `_server_derived_principal`
  (returning `auth_owner_mode = "AUTH_OWNER_none_single_operator_dev_profile"`);
- the route proceeds; the response is byte-identical to today's response;
- no identity value appears in the response body.

Under `AUTH_OWNER=proxy` + `TRUSTED_PROXY_MODE=false` (or unset):
- the server raises `SecXbrlInAppAuthPolicyError` with
  `code = "sec_xbrl_in_app_auth_policy_untrusted_proxy_identity"`, `http_status = 409`;
- the error is rendered through a helper consistent with `_sec_xbrl_auth_policy_error_response`
  in `backend/app/api/layer3/_shared.py` (lines 3887-3911): a `JSONResponse` whose
  body is `workbench_error_response(Layer3WorkbenchError(...))` with
  `status="blocked"`, `blocked_fields` list from `exc.details`, and
  `next_allowed_actions` naming the relevant diagnostic action;
- no raw proxy header value, identity value, or local path appears in the error body.

Under `AUTH_OWNER=proxy` + `TRUSTED_PROXY_MODE=true` + missing configured header:
- the server raises `SecXbrlInAppAuthPolicyError` with
  `code = "sec_xbrl_in_app_auth_policy_missing_identity_authority"`, `http_status = 401`;
- same error rendering as above; fail-closed.

## Test Contract (Future Implementation Pass)

The implementation pass must supply tests satisfying all of the following before
merge is admitted:

```yaml
test_slices:
  - id: inertness_proof_none
    requirement: for every wired mutating_write and read_projection route in
      handoff.py and package.py, under AUTH_OWNER=none, responses are
      byte-identical to baseline (same status code, same body schema, no new
      fields). Verified via parametrized test comparing pre- and post-wiring
      response payloads for each route family.

  - id: fail_closed_proxy_untrusted
    requirement: under AUTH_OWNER=proxy with TRUSTED_PROXY_MODE unset or false,
      each wired route returns HTTP 409, body contains error_code
      sec_xbrl_in_app_auth_policy_untrusted_proxy_identity, no raw header or
      identity value in body.

  - id: fail_closed_proxy_missing_header
    requirement: under AUTH_OWNER=proxy with TRUSTED_PROXY_MODE=true but
      configured identity header absent, each wired route returns HTTP 401,
      error_code sec_xbrl_in_app_auth_policy_missing_identity_authority.

  - id: no_leak
    requirement: no raw proxy header value, no raw identity string, no local
      filesystem path, no credential appears in any response body for any wired
      route under any operator profile.

  - id: regression_slice
    requirement: full backend/tests/test_layer3_api.py and
      backend/tests/test_layer3_handoff*.py / test_layer3_package*.py pass at
      >= prior counts after wiring.

  - id: needs_audit_routes_excluded
    requirement: post_external_export_download_deliver and
      post_external_export_download_signed_reference_use are NOT wired until
      the needs_audit classification is resolved by a follow-up doc.
```

## Negative Invariants / No-Go

- no value-reveal activation; `layer3_sec_xbrl_controlled_value_reveal_submit_enabled`
  and `layer3_sec_edgar_arelle_value_reveal_enabled` remain off by default;
- no controlled-submit activation;
- no live network request during any test or validation;
- no default-on behavior change (AUTH_OWNER=none local profile is the unchanged default);
- no browser-state identity; no durable frontend identity authority;
- no untrusted proxy headers accepted as identity under any condition;
- no source_ingestion route wired under this contract version;
- no sec_xbrl.py route re-wired (those enforce via 1352 imperative path);
- no raw header value, identity string, path, credential, or permission-internal
  exposed in any response or error body;
- no new DTO, model, migration, config default, or feature flag introduced;
- no production-readiness claim; nonlocal readiness gate remains blocked pending
  its deployment authority packet.

## Stop Conditions

Stop and return to planning if a future implementation proposal attempts to:
- wire source_ingestion routes before the per-route classification audit lands;
- re-wire sec_xbrl.py routes (double-enforcement);
- use browser state, local storage, or manually-supplied usernames as identity;
- accept untrusted proxy headers outside TRUSTED_PROXY_MODE=true;
- expose any raw identity, proxy header, path, or credential in a response body;
- flip any feature-flag default or claim production readiness;
- change any route behavior under AUTH_OWNER=none beyond recording the
  local-operator principal seam;
- activate more than one auth/security mode (this contract selects exactly
  route_level_operator_identity_required and admits no simultaneous mode);
- skip the needs_audit delivery-route classification before wiring those routes.
