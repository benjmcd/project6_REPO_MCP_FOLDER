# P24 Mixed-Source Product-Authority Checkpoint Closeout

Status: branch-local read-only product-authority checkpoint. Not current-main until merged and post-merge proof is recorded.

## Scope

This pass adds a rendered `/review/layer3` checkpoint that lets an operator
inspect whether the mixed-source product-flow authority chain is complete from
P17 through P18/P19/P21/P22:

- P17 mixed-source handoff/export prepare material authority.
- P18 mixed-source APS handoff dispatch authority.
- P19 mixed-source external export/download readiness authority.
- P21 same-origin external export/download delivery authority.
- P22 same-origin signed-reference authority.

The checkpoint is read-only. It derives from existing loaded `State` and
`State.sessionSummary` authority helpers and renders status rows plus blocked
boundary flags. It does not add a new backend route, payload builder, submit
handler, persisted state, or transport path.

## Runtime Boundary

No backend route, service, schema, model, migration, durable persistence,
parser, source-shape, provider, connector, destination, local outbox, package
payload, package row, download URL, signed-reference status/revocation,
external export, or dispatch behavior is added. The checkpoint only summarizes
already-loaded server-owned authority and existing branch-local rendered
controls.

## Fail-Closed And Redaction

The checkpoint renders `mixed_source_product_authority_checkpoint_blocked`
unless every required authority step is present. Its rendered blocked-boundary
flags keep real export/dispatch, provider public/private URL, connector
dispatch, destination write, local outbox, package payload rewrite,
schema-runtime source widening, and production readiness explicitly false.

## Non-Goals

- No real export or external dispatch.
- No provider/public URL behavior.
- No connector, destination, local outbox, credential, network, or external
  dispatch behavior.
- No signed-reference status or revocation UI/API.
- No schema/model/migration change.
- No parser behavior change.
- No source-shape expansion.
- No package payload rewrite, mutation, reconstruction, replacement, or
  supersession.
- No SEC XBRL surface.
- No value reveal, default-on behavior, or production-readiness activation.

## Verification

Branch-local verification passed:

- `node --check ./backend/app/review_ui/static/layer3.js`
- `Get-Content -Raw ./e2e/layer3-workbench.spec.js | node --input-type=module --check`
- `python -B -m py_compile ./backend/tests/test_layer3_page.py`
- `python -B -m pytest ./backend/tests/test_layer3_page.py -q -k "product_authority_checkpoint"`
  (`1 passed, 24 deselected, 3 warnings`)
- `python -B -m pytest ./backend/tests/test_layer3_page.py -q`
  (`25 passed, 3 warnings`)
- `python -B -m pytest ./backend/tests/test_layer3_api.py -q -k "mixed_source_external_export_download"`
  (`5 passed, 292 deselected, 3 warnings`)
- `npx playwright test ./e2e/layer3-workbench.spec.js -g "P18/P19 mixed-source readiness controls" --project=chromium`
  (`1 passed`)
- `npx playwright test ./e2e/layer3-workbench.spec.js -g "P18/P19 mixed-source readiness controls" --project=chromium --headed`
  (`1 passed`)
- `npx playwright test ./e2e/layer3-workbench.spec.js -g "P18/P19 mixed-source readiness controls|P21 mixed-source external export download delivery control|P22 mixed-source signed-reference controls|raw mixed rendered external export download signed reference" --project=chromium`
  (`4 passed`)
- `npx playwright test ./e2e/layer3-workbench.spec.js -g "P18/P19 mixed-source readiness controls|P21 mixed-source external export download delivery control|P22 mixed-source signed-reference controls|raw mixed rendered external export download signed reference" --project=chromium --headed`
  (`4 passed`)

## Next Posture

Merge-review and current-main sync the branch-local P22/P23/P24 work before
selecting another downstream surface. Provider/public URL governance,
connector/destination/local-outbox dispatch, durable revocation UI/API,
schema/source-shape expansion, and production readiness remain separate future
freezes.
