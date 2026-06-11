# P22 Mixed-Source Signed-Reference Runtime And Rendered Controls Closeout

Status: current-main. Content present on main tip 1f9a4ec6. The P22 runtime and rendered controls are on current main after the 2026-06-06 history rebuild. Post-merge proof recorded 2026-06-11.

## Scope

This pass implements the P22 freeze by admitting mixed-source same-origin
signed-reference generation and use over the existing P20 mixed-source delivery
route family and by rendering the corresponding `/review/layer3` controls when
server-owned P19 mixed-source readiness is present:

- `POST /api/v1/layer3/handoff/export/download/signed-reference/generate`
- `POST /api/v1/layer3/handoff/export/download/signed-reference/use`

The runtime accepts `mixed_dataset_document` only when the server revalidates
the existing P20 delivery authority over the P14/P15/P16/P17/P18/P19 chain and
the current `review_facing` package row. The public signed-reference response
uses the existing generic schema id while exposing mixed-source authority fields
and:

- `server_authority:
  mixed_source_external_export_download_signed_reference_gate`
- `operator_decision:
  generate_mixed_source_external_export_download_signed_reference`
- `use_operator_decision:
  use_mixed_source_external_export_download_signed_reference`
- `signed_reference_delivery_mode: same_origin_signed_delivery_reference`

The rendered control uses `State.sessionSummary.external_export_download_readiness`
as the source of truth, selects only the `review_facing` package, submits
`generate_mixed_source_external_export_download_signed_reference`, and enables
the Use button only after the server returns one same-origin signed reference.

## Runtime Boundary

The implementation reuses the existing durable signed-reference token, receipt,
and audit state family. It adds no table, migration, provider object, connector
run, local outbox, package row, package payload write, parser behavior, source
shape, or production-readiness behavior.

Mixed-source generation must use the P22 signed-reference operator decision.
The service internally converts that request to the already-admitted P20
delivery decision only for server-side delivery revalidation. Token use
revalidates current delivery authority before consuming durable single-use
state.

## Fail-Closed And Redaction

The runtime fails closed for missing signing secret, wrong mixed-source
operator decision, stale or mismatched delivery authority, malformed/expired/
replayed tokens, extra fields on token use, and non-admitted delivery fields
such as download URLs, provider/public URLs, connector refs, destination refs,
local outbox fields, package bytes, or package rewrite inputs.

Status and durable receipt surfaces expose only response-safe refs, hashes,
token ids/prefixes, expiry, replay policy, and receipt/audit ids. They do not
expose local package paths, raw package bytes, raw signed-reference tokens in
durable state, public/provider URLs, connector targets, destination ids,
credentials, or local outbox targets.

## Non-Goals

- No download URL generation or exposure.
- No public/provider URL or provider dispatch behavior.
- No connector, destination, local outbox, credential, network, or external
  file delivery behavior.
- No schema/model/migration change.
- No parser behavior change.
- No source-shape expansion.
- No package payload rewrite, mutation, reconstruction, replacement, or
  supersession.
- No SEC XBRL surface.
- No source acquisition or Arelle behavior.
- No excluded-tool behavior.
- No value reveal, default-on behavior, or production-readiness activation.

## Verification

Branch-local verification passed:

- `python -B -m py_compile ./backend/app/api/layer3.py
  ./backend/app/services/layer3_workbench.py ./backend/tests/test_layer3_api.py
  ./backend/tests/test_layer3_page.py`
- `python -B -m pytest ./backend/tests/test_layer3_api.py -q -k
  "mixed_source_external_export_download_signed_reference"`
  (`1 passed, 296 deselected, 3 warnings`)
- `python -B -m pytest ./backend/tests/test_layer3_api.py -q -k
  "special_route_openapi_contracts or
  mixed_source_external_export_download_signed_reference"`
  (`2 passed, 295 deselected, 3 warnings`)
- `python -B -m pytest ./backend/tests/test_layer3_page.py -q -k
  "mixed_source_rendered_delivery_uses_p19_material_authority"`
  (`1 passed, 22 deselected, 3 warnings`)
- `Get-Content -Raw ./e2e/layer3-workbench.spec.js | node
  --input-type=module --check`
- `python -B -m pytest ./backend/tests/test_layer3_api.py -q -k
  "signed_reference or mixed_source_external_export_download_deliver_streams_package_artifact"`
  (`3 passed, 294 deselected, 3 warnings`)
- `python -B -m pytest ./backend/tests/test_layer3_api.py -q -k
  "mixed_source_external_export_download"`
  (`5 passed, 292 deselected, 3 warnings`)
- `python -B -m pytest ./backend/tests/test_layer3_api.py -q -k
  "openapi or signed_reference or mixed_source_external_export_download"`
  (`20 passed, 277 deselected, 3 warnings`)
- `python -B -m pytest ./backend/tests/test_layer3_signed_reference_state.py -q`
  (`5 passed`)
- `python -B -m pytest ./backend/tests/test_layer3_api.py -q`
  (`297 passed, 4 warnings`)
- `python -B -m pytest ./backend/tests/test_layer3_page.py -q`
  (`23 passed, 3 warnings`)
- `npx playwright test ./e2e/layer3-workbench.spec.js -g
  "P21 mixed-source external export download delivery control|P22
  mixed-source signed-reference controls|raw mixed rendered external export
  download signed reference" --project=chromium`
  (`3 passed`)
- `npx playwright test ./e2e/layer3-workbench.spec.js -g
  "P21 mixed-source external export download delivery control|P22
  mixed-source signed-reference controls|raw mixed rendered external export
  download signed reference" --project=chromium --headed`
  (`3 passed`)
- Layer 3 authority-index validation
- Layer 3 target-selection frozen validation
- Layer 3 progress check
- `git diff --check`

## Post-Merge Proof (2026-06-11)

Signed-reference backend test slice run against main tip 1f9a4ec6:

```
python -m pytest backend/tests -q -k "signed_reference"
```

Result: **8 passed, 9 skipped, 3180 deselected** (4 warnings, no failures).

Test nodes collected:
- `backend/tests/test_layer3_api.py::test_layer3_api_json_or_error_call_sites_return_workbench_error_envelope[external_export_download_generate_signed_reference-...]`
- `backend/tests/test_layer3_api.py::test_layer3_api_mixed_source_external_export_download_signed_reference_uses_delivery_authority`
- `backend/tests/test_layer3_api.py::test_layer3_api_mixed_source_signed_reference_rejected_after_direct_delivery`
- `backend/tests/test_layer3_signed_reference_state.py::test_record_generated_signed_reference_persists_sanitized_durable_state`
- `backend/tests/test_layer3_signed_reference_state.py::test_single_use_reference_records_one_delivery_and_rejects_replay`
- `backend/tests/test_layer3_signed_reference_state.py::test_revoked_reference_fails_closed_and_records_rejected_audit`
- `backend/tests/test_layer3_signed_reference_state.py::test_expired_reference_fails_closed_and_marks_token_expired`
- `backend/tests/test_layer3_signed_reference_state.py::test_concurrent_single_use_reference_does_not_double_deliver`

## Next Posture

P22/P23/P24 are on current main. Provider/public URL governance,
connector/destination/local-outbox dispatch, durable revocation UI or a
product-authority checkpoint, schema/source-shape expansion, and production
readiness remain separate future freezes.
