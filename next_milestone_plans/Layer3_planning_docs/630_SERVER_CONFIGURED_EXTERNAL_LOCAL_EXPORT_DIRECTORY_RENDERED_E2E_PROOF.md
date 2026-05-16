# 630 - Server-Configured External Local Export Directory Rendered E2E Proof

## Status

Status: rendered E2E proof for `server_configured_external_local_export_directory`.

Doc: `630_SERVER_CONFIGURED_EXTERNAL_LOCAL_EXPORT_DIRECTORY_RENDERED_E2E_PROOF.md`.

Runtime current-main sync: `629_SERVER_CONFIGURED_EXTERNAL_LOCAL_EXPORT_DIRECTORY_RUNTIME_CURRENT_MAIN_SYNC.md`.

Branch: `codex/l3-external-local-export-e2e-proof`.

Current-main checkpoint before proof: `884fc16ecde50db4ebf0a0c459796fb7fdfcdc47`.

Selected next external surface: `server_configured_external_local_export_directory`.

Selected next external surface class: `server_configured_external_destination_write`.

Selected proof action: `prove_server_configured_external_local_export_directory_rendered_status_history`.

Proof status: `server_configured_external_local_export_directory_rendered_e2e_proven_branch_local`.

Layer 3 placement: Data Structuring & Processing export/write boundary.

Runtime behavior change: false.

Rendered UI behavior change: true, limited to a read-only status/history panel for existing server summary authority.

## Owner Scope

This pass does not re-implement the external local export runtime. It proves the already-merged runtime with a rendered operator-visible read-only surface:

- rendered panel `#external-local-export-panel`;
- rendered mode `rendered_external_local_export_read_only_status_surface`;
- response authority `State.sessionSummary.external_local_export`;
- status surface mode `read_only_external_local_export_status_history`;
- Playwright owner proof `e2e/layer3-handoff.spec.js`;
- review-browser harness setting `LAYER3_EXTERNAL_LOCAL_EXPORT_DIR` to a temp server-owned directory outside app-owned storage;
- static page sentinel coverage in `backend/tests/test_layer3_page.py`.

The panel exposes status, durable receipt id, authority chain refs, redacted `external-local-export://` artifact and manifest refs, lifecycle policy, history, audit history, guardrail projection, and blocked adjacent surfaces. It does not expose raw local paths, server environment variable values, caller-supplied destination paths, path editing controls, or writable browser authority.

## Proof Coverage

The focused E2E path performs the existing end-to-end authority chain:

```yaml
source_flow: existing Layer 3 executed session
package_flow: result review + package review + handoff/export + APS handoff + external export/download readiness
local_receipt_flow: connector-local receipt + server-owned local outbox target + server-owned local outbox write
provider_private_flow: local-outbox provider-private handoff prepare/status
external_local_export_flow: server-configured external local export write/status
rendered_surface: read-only status/history panel
```

The proof validates:

- `external_local_export_ready` before write;
- `external_local_export_written` after write;
- same `client_request_id` plus same basis returns the same receipt as `external_local_export_replay`;
- status route returns `layer3.external_local_export.status.v1`;
- session summary projects `read_only_external_local_export_status_history`;
- durable history authority is `durable_external_local_export_receipt_rows`;
- durable audit authority is `durable_external_local_export_audit_event_rows`;
- idempotency terms include `external_local_export_client_request_conflict`, `return_existing_status`, and `external_local_export_existing_output_conflict`;
- guardrail projection includes stale authority, same-key conflict, and target write conflict;
- rendered panel has no `button`, `input`, `select`, or `textarea`;
- rendered panel does not show `C:\`, `LAYER3_EXTERNAL_LOCAL_EXPORT_DIR`, or `destination_path`;
- real connector invocation, ConnectorRun creation, ConnectorRunTarget creation, credentials, network egress, provider-public delivery/use, raw public URL, raw token, package mutation, source expansion, RAG/vector, and frontend-durable authority remain blocked.

## Validation

These validations passed in this branch-local proof pass:

```powershell
node --check .\backend\app\review_ui\static\layer3.js
python -m py_compile .\backend\tests\review_browser_server.py .\backend\tests\test_layer3_page.py
python -m pytest .\backend\tests\test_layer3_page.py -q
npx playwright test e2e/layer3-handoff.spec.js --grep "renders external local export lifecycle" --project=chromium
npx playwright test e2e/layer3-handoff.spec.js --grep "renders external local export lifecycle" --project=chromium --headed
```

The first Playwright attempt used a Windows path-shaped test argument and returned `No tests found`; it was not accepted as validation. The accepted proof uses the repo-relative path `e2e/layer3-handoff.spec.js`, matching the fixed-port harness convention.

This branch must also pass before merge:

```powershell
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
git diff --check
```

## Non-Admission Boundary

This proof admits no new runtime behavior beyond the already-selected external local export surface. It does not add real connector invocation, ConnectorRun creation, ConnectorRunTarget creation, credentials, network egress, provider-public delivery/use, raw public URL exposure, raw token exposure, caller-supplied destination paths or URLs, package mutation/reconstruction, source expansion/ingestion, RAG/vector behavior, qualitative-hybrid analysis runtime, broad auth/security behavior, full mockup activation, frontend-durable authority, or generic downstream dispatch.

## Next Posture

The next whole-project posture after this proof merges is `await_current_main_sync_for_server_configured_external_local_export_directory_rendered_e2e_proof`.

After current-main sync, if no external local export guardrail gap is found, the next selected implementation-entry decision should move to the highest-priority remaining user-desired surface: package mutation/reconstruction, with one named operator action frozen before runtime.
