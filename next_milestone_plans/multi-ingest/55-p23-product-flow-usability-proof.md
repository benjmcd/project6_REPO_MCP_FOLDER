# P23 Mixed-Source Product-Flow Usability Proof Closeout

Status: current-main. Content present on main tip 1f9a4ec6. The P23 rendered product-flow usability proof is on current main after the 2026-06-06 history rebuild. Post-merge proof recorded 2026-06-11.

## Scope

This pass proves the rendered mixed-source downstream flow can proceed through
the already-admitted server-authoritative chain without synthetic P19 readiness:

- P17 mixed-source handoff/export prepare material authority.
- P18 mixed-source APS handoff dispatch rendered control.
- P19 mixed-source external export/download readiness rendered control.
- P22 mixed-source same-origin signed-reference generation control.

The implementation adds rendered UI authority derivation and payload branching
only. P18 still posts to the existing `/handoff/aps/dispatch` route with mixed
material fields, so the backend selects the existing mixed APS validator. P19
posts to the existing `/handoff/export/download/readiness` route and no longer
falls through to the legacy `/handoff/export/download/prepare` path when mixed
P18 authority is present.

## Runtime Boundary

No backend route, service, schema, model, migration, durable persistence,
parser, source-shape, provider, connector, destination, local outbox, package
payload, package row, or external dispatch behavior is added. The browser only
submits the already-admitted mixed P18/P19/P22 decisions when complete
server-owned material authority is present.

## Fail-Closed And Redaction

The rendered controls remain disabled when the relevant authority packet is
incomplete, when mixed P19 readiness is already recorded, or when prior
downstream pending state is active. Mixed P18/P19 payloads omit legacy
analysis/pass/result fields, payload refs, download URLs, public/provider URLs,
connector refs, destination refs, local paths, package bytes, schema migration
fields, and source expansion fields.

## Non-Goals

- No download URL generation or exposure.
- No provider/public URL behavior.
- No connector, destination, local outbox, credential, network, or external
  dispatch behavior.
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
- `python -B -m pytest ./backend/tests/test_layer3_page.py -q`
  (`24 passed, 3 warnings`)
- `npx playwright test ./e2e/layer3-workbench.spec.js -g "P18/P19 mixed-source readiness controls" --project=chromium`
  (`1 passed`)
- `npx playwright test ./e2e/layer3-workbench.spec.js -g "P18/P19 mixed-source readiness controls|P21 mixed-source external export download delivery control|P22 mixed-source signed-reference controls|raw mixed rendered external export download signed reference" --project=chromium`
  (`4 passed`)
- `npx playwright test ./e2e/layer3-workbench.spec.js -g "P18/P19 mixed-source readiness controls|P21 mixed-source external export download delivery control|P22 mixed-source signed-reference controls|raw mixed rendered external export download signed reference" --project=chromium --headed`
  (`4 passed`)
- `npx playwright test ./e2e/layer3-workbench.spec.js -g "provider-private signed URL prepare status revoke" --project=chromium`
  (`1 passed`)
- `npx playwright test ./e2e/layer3-workbench.spec.js -g "provider-private signed URL prepare status revoke" --project=chromium --headed`
  (`1 passed`)

The provider-private/provider-public rendered canary remains green as a
non-regression check. It does not admit mixed-source provider/public URL
behavior; it only proves this P23 rendered mixed-source authority branching did
not break the existing separately-governed provider route family.

## Post-Merge Proof (2026-06-11)

Signed-reference backend test slice run against main tip 1f9a4ec6:

```
python -m pytest backend/tests -q -k "signed_reference"
```

Result: **8 passed, 9 skipped, 3180 deselected** (4 warnings, no failures).

The P23 rendered authority branching (P18/P19/P22 mixed-source payloads) is
confirmed not to have broken the signed-reference or delivery test surface.

## Next Posture

P22/P23/P24 are on current main. Durable revocation UI/API remains separate
and is still safer than provider/public URL governance or
connector/destination/local-outbox dispatch. The next downstream surface must
be selected by a separate freeze before implementation.
