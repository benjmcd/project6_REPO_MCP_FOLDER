# P20 Mixed-Source External Export/Download Delivery Current-Main Sync

Status: docs/control current-main sync only.

Live `project6-origin/main` includes PR #2223 at merge commit
`6ca7835c6d8724715c9ac2d7a92ca34de2898ef2`.

## Scope

This sync records that the P20 mixed-source external export/download delivery
runtime is current-main behavior after PR #2223. The runtime admits exactly one
same-origin artifact-stream delivery surface over recorded P19 readiness and
current mixed-source package rows.

No runtime code changes in this sync.

## Current-Main Runtime Boundary

The P20 runtime records:

- response schema `layer3.mixed_source_external_export_download_delivery.v1`
- status schema `layer3.mixed_source_external_export_download_delivery_state.v1`
- delivery state `mixed_source_external_export_download_delivered`
- delivery mode `same_origin_artifact_stream`
- operator decision `deliver_mixed_source_external_export_download`

The runtime verifies committed Gate B material authority, recomputes/replays the
P14 package-review preview and P19 readiness chain, reloads the P15
reconciliation and package rows, verifies P16 package-review submit authority,
verifies P17 handoff/export prepare authority, verifies P18 APS handoff
dispatch authority, verifies P19 external export/download readiness authority,
and validates the selected package artifact hash before streaming.

The recorded delivery state remains reference-only in reconciliation/session
JSON. It contains public refs, package identity, hashes, negative authority
flags, and delivery metadata. It does not expose local package paths or
`payload_ref` status fields.

## Non-Goals

- No runtime code change in this sync.
- No rendered UI/static behavior change.
- No browser download control.
- No download URL generation or exposure.
- No signed-reference generation, use, status, or revocation.
- No public URL, provider URL, or provider dispatch behavior.
- No connector, destination, local outbox, credential, network, or external file
  delivery behavior.
- No schema/model/migration change.
- No parser behavior change.
- No source-shape expansion.
- No package payload rewrite.
- No package reconstruction or mutation.
- No legacy CSV bridge deprecation.
- No excluded-tool behavior.
- No SEC XBRL surface.
- No production-readiness activation.

## Proof

PR #2223 CI passed all required backend Layer 3 API and test shards. The PR had
clean merge state, zero reviews, and zero review threads before merge.

Detached post-merge proof from current main
`6ca7835c6d8724715c9ac2d7a92ca34de2898ef2` passed:

- touched-file `py_compile`
- focused P20/API delivery and OpenAPI slice
  (`23 passed, 273 deselected, 4 warnings`)
- affected external export contract and response helper tests
  (`11 passed, 2 warnings`)
- bounded external export/download E2E slice
  (`1 passed, 3 deselected, 4 warnings`)
- full `backend/tests/test_layer3_api.py`
  (`296 passed, 4 warnings`)
- manifest JSON syntax
- authority-index validation
- frozen target-selection validation
- progress check
- `git diff --check`

## Next Posture

The next mixed-source downstream step is a separate freeze for exactly one
surface: rendered delivery controls, signed-reference governance,
provider/public URL governance, connector/destination dispatch, or a
stop-for-product-authority checkpoint.

Download URLs, signed references, public/provider URLs, connector/provider/
destination behavior, schema/model/migration changes, parser/source-shape
expansion, package payload rewrite, excluded-tool behavior, and production
readiness remain blocked unless a later freeze selects and proves them.
