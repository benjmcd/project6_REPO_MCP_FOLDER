# 1308 - SEC XBRL Controlled Submit Post-Merge Audit Closure

Milestone: `sec_xbrl_controlled_value_reveal_submit_post_merge_audit_closure_v1`

Base authority: `project6-origin/main` at `52c4e5915f75fffdc76fcff711e911efcf332c4c`

Prior milestone: `next_milestone_plans/Layer3_planning_docs/1307-submit-status-ref-hardening.md`

Merged authority: PR `#2051` at `96613b00fa9034e2b17d8842b542a3e7d8d93e84`

## Status

Merged current-main Tier-1 documentation/proof closure over already-merged
Tier-2 controlled value-reveal submit surfaces, verified after merge.

This closure records the post-merge audit outcome for the controlled value-reveal
submit path after the implementation and follow-up hardening records landed on
current main. It does not add or change runtime behavior.

## Evidence Reviewed

- PR `#2043` landed the controlled value-reveal submit boundary at
  `d9e55ceebf87de8a42bfe3475debbd0ff452a19f`.
- PR `#2045` landed authority receipt-id raw-reference hardening at
  `64c8957cdf7dcad26eb92c4cf7d146b4a7c15f3b`.
- PR `#2047` landed local-reference review-thread hardening at
  `1012f65d09b6d5922377086c362d2c45df47d13c`.
- PR `#2049` landed submit-status receipt-id raw/local-reference hardening at
  `b5eee6b03104c8294144c21fec2c573ef2a50c24`.
- PR `#2050` reconciled the status-reference hardening record as merged at
  `52c4e5915f75fffdc76fcff711e911efcf332c4c`.

The current GitHub state has no open PRs, and the PR `#2041` through `#2050`
thread audit has zero active unresolved review threads. This is not treated as
proof that every merged PR had independent review; reviewless merged PRs remain
reviewless historical evidence rather than clean-review evidence.

## Closure Finding

The controlled-submit path is closed for the current bounded server-side submit
boundary:

- browser-supplied request ids, authority receipt ids, and status receipt ids
  reject raw or local authority references before lookup;
- failed raw/local validation creates no partial controlled-submit receipt;
- submit receipts persist ids, hashes, counts, policy/state, inventory hashes,
  summary metadata, and invariant flags only;
- the status path returns no revealed facts and no lower-level lineage ids;
- feature flags/defaults remain off;
- no export/delivery, rendered value UI, default-on behavior, production
  readiness, or final financial-statement semantics are admitted by this
  closure.

## Scope

This slice changes only:

- this planning document;
- `next_milestone_plans/layer3_progress_board.md`;
- `next_milestone_plans/layer3_progress_manifest.json`;
- `next_milestone_plans/layer3_workbench_proof_manifest.json`.

It does not touch `models.py`, Alembic migrations, schema, durable persistence,
backend API behavior, services, tests, rendered UI, value-reveal response
semantics, default-on behavior, source acquisition, live SEC network, Arelle
subprocess invocation, delivery/export, provider dispatch, raw runtime
artifacts, production readiness, or final financial-statement semantics.

## Verification

PR and post-merge current-main docs-only closure verification:

- `python .\tools\l3-target-selection-validate.py --expect frozen`
  - PASS
- `python .\tools\l3-progress-check.py`
  - PASS
- JSON parse with `utf-8-sig`
  - PASS for `next_milestone_plans/layer3_progress_manifest.json` and
    `next_milestone_plans/layer3_workbench_proof_manifest.json`
- `git diff --check`
  - PASS

The runtime proof for the controlled-submit hardening remains the post-merge
current-main verification recorded in 1304 through 1307, most recently focused
operator-review workflow tests with `72 passed, 3 warnings`, the full SEC XBRL
suite with `299 passed, 4 warnings`, py_compile, target/progress, JSON,
redaction, residual-magnitude, and diff checks on current main.

## Next Posture

The next admissible work is a separate design/admission-selection pass for
rendered value UI, default-on behavior, export/delivery, or production readiness.
Those gates must remain separate from this closure and must define authority,
operator authorization, containment, rollback, redaction, audit logging, and
targeted verification before any implementation.
