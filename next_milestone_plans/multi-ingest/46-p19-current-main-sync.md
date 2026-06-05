# P19 Mixed-Source External Export/Download Readiness Current-Main Sync

Status: docs/control current-main sync only.

Live `project6-origin/main` includes PR #2220 at merge commit
`9e4451cb710c0185a64f1788b9e0d848be7dbc8b`.

## Scope

This sync records that the P19 mixed-source external export/download readiness
runtime is current-main behavior after PR #2220. The runtime admits exactly one
reference-only readiness state over the recorded P18 mixed-source APS handoff
dispatch state and keeps delivery/download behavior blocked.

No runtime code changes in this sync.

## Current-Main Runtime Boundary

The P19 runtime records:

- response schema `layer3.mixed_source_external_export_download_readiness.v1`
- status schema `layer3.mixed_source_external_export_download_readiness_state.v1`
- readiness state `mixed_source_external_export_download_ready`
- operator decision `record_mixed_source_external_export_download_readiness`

The runtime verifies committed Gate B material authority, recomputes the P14
mixed-source preview, reloads the P15 reconciliation and package rows, verifies
P16 package-review submit authority, verifies P17 handoff/export prepare
authority, and verifies P18 APS handoff dispatch authority before recording the
readiness state.

The recorded state remains reference-only. It emits public
`layer3://mixed-source-package/...` package refs and a public
`layer3://mixed-source-external-export/...` readiness ref while keeping
`external_export_enabled`, `download_enabled`, `download_url_enabled`,
`signed_reference_enabled`, `provider_public_url_enabled`,
`provider_private_signed_url_enabled`, `connector_dispatch_enabled`,
`delivery_enabled`, and `external_export_download_enabled` false.

## Non-Goals

- No backend runtime change in this sync.
- No rendered UI/static behavior change.
- No external export/download delivery.
- No browser download or download URL.
- No signed-reference, public URL, provider URL, or provider dispatch behavior.
- No connector, destination, local outbox, credential, network, or file delivery
  behavior.
- No schema/model/migration change.
- No parser behavior change.
- No source-shape expansion.
- No package payload rewrite.
- No package reconstruction or mutation.
- No legacy CSV bridge deprecation.
- No excluded-tool behavior.
- No production-readiness activation.

## Proof

PR #2220 CI passed all required backend Layer 3 API and test shards. The PR had
clean merge state, zero reviews, and zero review threads before merge.

Detached post-merge proof from current main
`9e4451cb710c0185a64f1788b9e0d848be7dbc8b` passed:

- touched-file `py_compile`
- focused P19/API contract and error-envelope slice
  (`28 passed, 267 deselected, 3 warnings`)
- full `backend/tests/test_layer3_api.py`
  (`295 passed, 4 warnings`)
- affected external export response helper tests
  (`6 passed, 2 warnings`)
- manifest JSON syntax
- authority-index validation
- frozen target-selection validation
- progress check
- `git diff --check`

## Next Posture

The next mixed-source downstream step is a separate external export/download
delivery freeze over the recorded P19 readiness state. That freeze must choose
the exact delivery surface before implementation and must keep download URLs,
signed references, public/provider URLs, connector/provider/destination
behavior, schema/model/migration changes, parser/source-shape expansion,
package payload rewrite, excluded-tool behavior, and production readiness
blocked unless explicitly selected and proved.
