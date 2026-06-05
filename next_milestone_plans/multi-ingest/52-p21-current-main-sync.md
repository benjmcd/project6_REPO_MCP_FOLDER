# P21 Mixed-Source Rendered Delivery Controls Current-Main Sync

Status: docs/control current-main sync only.

Live `project6-origin/main` includes PR #2226 at merge commit
`dcd0e159b5bb0ac7eb1c6af6b6609e4c9b31b48d`.

## Scope

This sync records that the P21 rendered `/review/layer3` mixed-source external
export/download delivery control is current-main behavior after PR #2226. The
runtime admits exactly one rendered operator control over the existing P20
same-origin artifact-stream delivery route and server-owned P19/P20 readiness
authority.

No runtime code changes in this sync.

## Current-Main Runtime Boundary

The rendered P21 control:

- reads `State.sessionSummary.external_export_download_readiness`;
- selects only the `review_facing` mixed package;
- submits the existing `POST /api/v1/layer3/handoff/export/download/deliver`
  route;
- sends `delivery_mode: same_origin_artifact_stream`;
- sends `operator_decision: deliver_mixed_source_external_export_download`;
- prefers refreshed server-delivered state over optimistic local submitted
  state;
- keeps stale source-directory prepare state from taking over mixed-source
  status or delivery routes;
- keeps signed-reference controls blocked while mixed-source readiness is the
  active delivery authority.

## Non-Goals

- No runtime code change in this sync.
- No backend route or API behavior change in this sync.
- No schema, DTO, model, or migration change.
- No parser behavior change.
- No source-shape expansion.
- No package payload rewrite, mutation, reconstruction, replacement, or
  supersession.
- No download URL generation or exposure.
- No signed-reference generation, use, status, or revocation.
- No public URL, provider URL, provider dispatch, connector dispatch,
  destination, credential, local outbox, network, or external file delivery
  behavior.
- No SEC XBRL surface.
- No source acquisition or Arelle behavior.
- No excluded-tool behavior.
- No value reveal, default-on behavior, or production-readiness activation.

## Proof

PR #2226 CI passed all required backend Layer 3 API and test shards. The PR had
clean merge state before merge. Two review threads were addressed and resolved
before merge.

Detached post-merge proof from current main
`dcd0e159b5bb0ac7eb1c6af6b6609e4c9b31b48d` passed:

- `node --check ./backend/app/review_ui/static/layer3.js`;
- `python -B -m pytest ./backend/tests/test_layer3_page.py -q`
  (`23 passed, 3 warnings`);
- `python -B -m pytest ./backend/tests/test_layer3_api.py -q -k
  "mixed_source_external_export_download_readiness or
  mixed_source_external_export_download_deliver"`
  (`4 passed, 292 deselected, 3 warnings`);
- `python -B -m pytest
  ./backend/tests/test_layer3_external_export_response.py::test_mixed_external_export_delivery_response_helper_is_shared_with_workbench
  -q` (`1 passed, 2 warnings`);
- `npm run test:e2e -- --grep "P21 mixed-source"`
  (`1 passed`);
- `npm run test:e2e:headed -- --grep "P21 mixed-source"`
  (`1 passed`);
- manifest JSON syntax;
- authority-index validation;
- frozen target-selection validation;
- progress check;
- `git diff --check`.

## Next Posture

Freeze exactly one next mixed-source downstream surface before implementation:
signed-reference governance, provider/public URL governance,
connector/destination dispatch, durable audit or revocation behavior,
product-flow usability proof, or a product-authority checkpoint.

Download URLs, signed references, public/provider URLs, connector/provider/
destination behavior, schema/model/migration changes, parser/source-shape
expansion, package payload rewrite, excluded-tool behavior, value reveal,
default-on behavior, and production readiness remain blocked unless a later
freeze selects and proves them.
