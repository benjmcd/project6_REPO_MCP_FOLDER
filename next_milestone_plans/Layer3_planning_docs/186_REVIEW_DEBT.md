# 186 Review-Debt Reconciliation Plan

## Purpose

This note freezes the immediate post-PR `#746` corrective plan before any new
Layer 3 capability work. It records the merged-review debt found on current
`project6-origin/main` after PRs `#738` through `#746`, why the debt matters,
and the smallest acceptable next pass.

This note is planning/control only. It does not make runtime behavior live,
does not prove any issue fixed, and does not replace source, tests, GitHub
review threads, or `tools/l3-progress-check.py` as implementation authority.

## Authority Snapshot

As of the audit that created this note:

- `project6-origin/main` includes merge commit
  `337c734f5282d538bdc85447b9180cb7a939810b` from PR `#746`.
- PRs `#738`, `#739`, `#740`, `#741`, `#742`, `#743`, `#744`, `#745`, and
  `#746` are merged.
- No open PRs were reported by GitHub.
- `python .\tools\l3-progress-check.py` passed on the audited tree.
- The root checkout was not treated as implementation authority because it was
  on `codex/root-preserve`, behind `project6-origin/main`, and dirty with
  unrelated local/untracked files.

## Grounded Current Determinations

### PR `#738`: live behavior debt

Two unresolved review threads remain valid against current source:

1. Raw mixed materialization idempotency can fail for existing
   `DatasetVersion` rows if an older row stores an absolute `storage_ref` and a
   new manifest supplies the same server-owned file as a relative ref. Current
   source validates the file path/hash, but `_ensure_row()` still compares the
   stored and expected `storage_ref` values by raw equality through
   `_same_value()`.
2. The rendered raw mixed materialization UI clears materialization status when
   manifest authority inputs change, but it does not clear the downstream
   dataset/content ID text fields populated by the prior successful
   materialization. `runPreflightFlow()` can still consume those stale IDs.

Classification: live behavior risk. This should be handled before downstream
capability work.

### PR `#744`: rendered delivery proof debt

Three unresolved review threads remain valid against current Playwright proof:

1. The rendered same-origin delivery proof waits for the API response, but it
   does not wait for the browser download event or assert the suggested
   filename.
2. The proof checks delivery headers and record refs, but it does not assert
   that the rendered delivery panel still surfaces the delivered artifact hash.
3. The proof checks underscore-style forbidden URL headers, but it does not
   check hyphenated header names such as `download-url`, `public-url`, or
   `signed-url`.

Classification: proof gap. This is not currently a proven runtime defect, but
it weakens the rendered delivery proof boundary.

### PR `#745`: Playwright harness reliability debt

One unresolved review thread remains valid against current Playwright config:

- Local/non-CI `reuseExistingServer: !process.env.CI` can reuse an already
  running server on the configured port without applying
  `LAYER3_SIGNED_REFERENCE_SECRET`. Signed-reference browser proofs can then
  hit a server that lacks the required secret and fail for an environmental
  reason unrelated to the tested UI path.

Classification: test-harness reliability risk.

### PR `#746`: checker/proof structural debt

Two unresolved review threads remain valid against current checker behavior:

1. The post-745 future-pass list is checked by membership, not exact order.
   A future edit could reorder the frozen roadmap and still pass.
2. The checker does loose whole-file term searches for negative-invariant
   language, but does not structurally inspect
   `post_745_downstream_expansion_freeze_proof["negative_invariants"]`.

Classification: proof/checker debt. This matters because the checker is meant
to prevent future planning drift.

## Biggest Current Points of Failure

1. **Stale source authority in rendered raw mixed UI.**
   - Why critical: it can let an operator change manifest authority while the
     workbench still drives preflight with IDs produced by a previous
     materialization.
   - Required attention: clear applied source IDs or block preflight after raw
     mixed manifest authority changes until a fresh materialization succeeds.

2. **Upgrade idempotency mismatch for existing materialized rows.**
   - Why critical: deterministic materialization should remain idempotent when
     old and new refs point to the same server-owned file with the same hash.
   - Required attention: compare storage authority canonically for this field
     without weakening server-owned path/hash checks or broadening allowed refs.

3. **Rendered same-origin delivery proof can overclaim browser delivery.**
   - Why critical: API `200` with attachment headers is not the same proof as a
     browser-managed download event.
   - Required attention: add download-event and filename assertions while
     keeping provider/public/signed URL boundaries blocked.

4. **Signed-reference Playwright setup can reuse an invalid server.**
   - Why critical: local proofs can fail or pass against an environment that is
     not the configured proof environment.
   - Required attention: disable reuse for this suite or fail closed when the
     reused server does not expose the required signed-reference secret posture.

5. **Post-745 roadmap guard is under-specified structurally.**
   - Why critical: the written freeze claims a ranked future order and required
     negative invariants, but the checker does not fully enforce those
     structures.
   - Required attention: compare exact ranked order and inspect the proof
     manifest's negative-invariant list directly.

## Next Required Pass

Before any provider/public URL, connector/destination, package mutation,
source expansion, RAG/vector, mockup, auth/security, or other new Layer 3
capability work, run exactly one review-debt reconciliation pass.

Recommended pass name:

`post_746_review_debt_reconciliation`

Recommended order:

1. Start from clean live `project6-origin/main`.
2. Reconfirm no open PRs and re-read unresolved review threads for PRs `#738`,
   `#744`, `#745`, and `#746`.
3. Fix PR `#738` live behavior debt first.
4. Harden PR `#744` delivery proof.
5. Harden PR `#745` Playwright signed-reference server setup.
6. Harden PR `#746` progress-check structural enforcement.
7. Run focused tests plus `python .\tools\l3-progress-check.py` and
   `git diff --check`.
8. Open at most one PR if the changes stay within this reconciliation scope.
9. Merge only after checks pass and review threads/comments are clean.
10. Stop; do not start the next capability pass in the same run.

## Validation Requirements For That Pass

Minimum validation should include:

- `python .\tools\l3-progress-check.py`
- focused raw mixed materialization tests covering canonical storage-ref
  idempotency and stale UI source invalidation behavior
- focused Playwright delivery proof for the same-origin download event,
  suggested filename, rendered artifact hash, and forbidden URL headers
- focused signed-reference Playwright setup validation
- `python -m pytest .\backend\tests -k layer3 -q`, if feasible
- `git diff --check`

If headed/headless browser behavior is touched, the pass must prove both
headed and headless Chromium behavior or report the exact infeasibility.

## Negative Scope

The reconciliation pass must not admit:

- provider/public URL behavior;
- connector or destination dispatch;
- package mutation, reconstruction, replacement, or supersession;
- source-family expansion beyond `dataset_version` and `aps_content_document`;
- source adapter registry;
- local upload or local-directory ingestion;
- web connector retrieval;
- RAG/vector retrieval;
- hidden LLM planning;
- full mockup activation;
- auth/security behavior changes;
- new rendered controls except the smallest correction required for stale
  source-authority invalidation;
- model or migration changes unless a directly proven blocker makes them
  unavoidable and the run stops for review first.

## UI Theme Obligations

If the reconciliation touches rendered workbench behavior, it must preserve the
existing theme posture from docs `184`/`185`:

- `light` remains valid for status, preview, and review inspection;
- `dark` remains valid for execution and package construction surfaces;
- `workbench` remains valid for package submit, handoff/export, APS handoff,
  external export/download, signed-reference, and operation-dock flows;
- no text overlap, hidden target controls, or target-state mockup controls may
  be introduced.

## Roadmap After Reconciliation

Only after the review-debt reconciliation is merged and verified should the
future roadmap resume:

1. provider/public URL entry freeze;
2. provider/public URL implementation, if admitted by that freeze;
3. connector/destination dispatch entry freeze;
4. connector/destination dispatch implementation, if admitted;
5. rendered package mutation/reconstruction entry freeze;
6. package mutation/reconstruction implementation, if admitted;
7. source breadth entry freeze;
8. source-family/source-adapter expansion, if admitted;
9. qualitative/hybrid/RAG/vector entry freeze;
10. qualitative/hybrid/RAG/vector implementation, if admitted;
11. browser/full mockup activation freeze;
12. full mockup activation, if admitted;
13. auth/security entry freeze and hardening;
14. CI, performance, observability, provenance, and audit hardening.

## Stop Condition

The next implementation run is complete only when:

- all currently unresolved PR `#738`, `#744`, `#745`, and `#746` review debts
  are fixed, disproven, or explicitly reclassified with current-main evidence;
- any PR opened for the reconciliation is green and has no actionable review
  debt;
- `project6-origin/main` is reverified after merge;
- no new Layer 3 capability work has started.
