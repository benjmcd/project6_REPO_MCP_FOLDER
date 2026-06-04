# P17A Current-Main Sync

Status: docs/control current-main sync only. Live `project6-origin/main` is
`313d516c4766851110598dc16dc9c60270016dc9`.

## Scope

This sync records that the P17A rendered material-authority handoff/export
prepare control is current-main behavior after PR #2210 and review-debt
follow-up PR #2211.

PR #2210 implemented only the `/review/layer3` rendered control for the
already-live P17 mixed-source handoff/export prepare API. PR #2211 fixed the
rendered decision controls so a complete mixed-source material-authority packet
enables the decision select and notes textarea under the same lifecycle
blockers as the submit button.

## Authority

- P17A freeze: `38-p17a-rendered-status-freeze.md`
- P17A runtime closeout: `39-p17a-rendered-runtime-closeout.md`
- Runtime merge: PR #2210 at
  `5dad54d2bf32cdcff9c0a1d35a6e23acf4b61680`
- Review-debt merge: PR #2211 at
  `86ecc1fa168c605004bfdfabe08fa6cb054d17c1`

## Non-Goals

- No runtime code change.
- No backend route, DTO, schema, model, or migration change.
- No parser behavior or source-shape expansion.
- No package construction, package-review submit, or handoff/export
  persistence change.
- No APS handoff behavior.
- No external export/download behavior.
- No connector, provider, local outbox, destination, network, or credential
  behavior.
- No package payload rewrite, reconstruction, or mutation.
- No excluded-tool behavior.
- No production-readiness activation.

## Verification

Post-merge proof from detached current main passed:

- `node --check ./backend/app/review_ui/static/layer3.js`
- `python -B -m pytest ./backend/tests/test_layer3_page.py -q`
  (`22 passed, 3 warnings`)
- `python -B -m pytest ./backend/tests/test_layer3_api.py -q -k
  "mixed_source_handoff_export_prepare or package_family_handoff_export_prepare"`
  (`1 passed, 290 deselected, 3 warnings`)
- JSON syntax for shared manifests
- `python -B ./tools/l3-authority-index-validate.py`
- `python -B ./tools/l3-target-selection-validate.py --expect frozen`
- `python -B ./tools/l3-progress-check.py`
- `git diff --check`

GitHub proof:

- PR #2210 merged, one review thread resolved.
- PR #2211 merged, zero review threads.

## Next Posture

The next mixed-source pass must freeze exactly one downstream surface before
runtime. The likely candidates are APS handoff or external export/download
readiness, but this sync does not select either. Connector/provider behavior,
schema/model/migration changes, parser/source-shape expansion, payload rewrite,
excluded-tool behavior, and production-readiness claims remain blocked until a
later freeze admits one exact surface.
