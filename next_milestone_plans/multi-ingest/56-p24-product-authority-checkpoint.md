# P24 Mixed-Source Product-Authority Checkpoint Closeout

Status: current-main. Content present on main tip 1f9a4ec6. The P24 read-only product-authority checkpoint rendered controls are on current main after the 2026-06-06 history rebuild. Post-merge proof recorded 2026-06-11.

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
boundary flags. The rendered card is scoped with overflow containment so long
authority labels cannot widen the page on mobile. It does not add a new backend
route, payload builder, submit handler, persisted state, or transport path.

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
- `npx playwright test ./e2e/layer3-workbench.spec.js -g "responsive live-state sublayer|mockup workbench theme exposes|Sublayer 3C execution lanes projection" --project=chromium`
  (`3 passed`)
- `npx playwright test ./e2e/layer3-workbench.spec.js -g "query/source setup projection|output review package handoff projection|Sublayers AB projection" --project=chromium`
  (`3 passed`)

## Post-Merge Proof (2026-06-11)

Signed-reference backend test slice run against main tip 1f9a4ec6:

```
python -m pytest backend/tests -q -k "signed_reference"
```

Result: **8 passed, 9 skipped, 3180 deselected** (4 warnings, no failures).

The P24 read-only checkpoint renders over already-loaded server-authoritative
state without new routes. The signed-reference test surface confirms the P22
authority chain underlying the checkpoint remains intact on current main.

## Next Posture

P22/P23/P24 are on current main. Provider/public URL governance,
connector/destination/local-outbox dispatch, durable revocation UI/API,
schema/source-shape expansion, and production readiness remain separate future
freezes. The next downstream surface must be selected by a separate freeze
before implementation.
