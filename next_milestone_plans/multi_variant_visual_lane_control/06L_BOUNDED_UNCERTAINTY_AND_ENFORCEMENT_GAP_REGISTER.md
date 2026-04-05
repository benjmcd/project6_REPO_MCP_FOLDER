# 06L Bounded Uncertainty and Enforcement Gap Register

## Purpose

Keep the remaining uncertainty explicit and bounded, instead of pretending it is zero.

## Bounded uncertainty items

### U1 — Non-audited repo surfaces
The control pack is based primarily on audited live app surfaces and selected active tests.
Residual uncertainty remains for:
- non-app surfaces
- non-Python surfaces
- future drift outside the audited authority set

### U2 — Enforcement vs specification
The pack now specifies:
- canonical acceptance commands
- local performance regression gate

But those are still control-pack specifications.
They are not yet verified as repo-native enforcement mechanisms such as:
- CI checks
- repo-managed runner scripts
- repo-native benchmark harnesses

### U3 — Schema/contract completeness risk
The re-audit found an additional review schema surface:
- `backend/app/schemas/review_nrc_aps.py`
- `NrcApsReviewVisualArtifactItemOut.visual_page_class`

This demonstrates that “surface closure” should be treated as materially strong but still bounded.

## Practical interpretation

These are no longer major structural blockers.
But they are real enough that the pack should not claim absolute closure.


## Narrowing after this revision

### Migration support is explicitly present
Verified:
- `backend/migration_compat.py`
- `tools/migrate_sqlite_to_postgres.py`
- `backend/alembic/versions/0010_visual_page_refs_json.py`
- `backend/alembic/versions/0011_aps_retrieval_chunk_v1.py`

So the residual uncertainty is no longer about whether `visual_page_refs_json` has any migration support at all.

### Enforcement gap is more concrete
Verified visible root workflow:
- `.github/workflows/playwright.yml`

This sharpens the remaining enforcement gap:
the Python acceptance path is specified by the pack, but not yet visibly enforced by the root workflow surface we found.


## Further narrowing after direct workflow/hook/config check

Verified:
- exactly one root workflow: `.github/workflows/playwright.yml`
- no repo-native pre-commit surface found
- no `pytest` references in the checked repo-native workflow/config/hook files

So the enforcement gap is now best stated as:

**the Python acceptance path is pack-specified but not visibly repo-enforced in the root workflow/hook/config surfaces checked.**


## Further narrowing after schema/contract check

Direct schema/contract evidence now shows:

- `visual_page_refs` is broadly represented across the checked schema/contract surfaces
- `visual_page_class` is narrower and concentrated in review-oriented schema/trace surfaces

So the residual schema/contract item is now best stated as:

**localized asymmetry in `visual_page_class` representation, not broad absence of visual-surface schema/contract coverage.**


## Correction after visual_page_class roundtrip check

The prior schema/contract item is now downgraded:

- `visual_page_class` remains narrower in direct production-file search
- but test-backed roundtrip and evidence-group acceptance show it is already supported as a nested field

So this is no longer a remaining open item.
It is only a narrower watch-note.


## Further narrowing after non-app live-surface check

Checked live non-app repo-native surfaces:
- `tools/**/*.py`
- root helper scripts
- `README.md`
- `REPO_INDEX.md`
- `docs/**/*`

No `visual_page_refs` or `visual_page_class` consumers were found there.

So the remaining bounded uncertainty is now more concentrated on:
- archive/worktree content,
- non-audited/generated surfaces,
- and future drift,
rather than active repo-native non-app consumers visible in the checked live root/tools/docs surfaces.


## Further narrowing after archive/worktree duplication check

Observed archive/worktree matches are dominated by duplicated copies of the same NRC APS service/test/tool paths.

So the remaining outside-scope uncertainty is now more specifically:
- duplicated historical/worktree state,
- generated/non-audited surfaces,
- future drift,

not observed new active consumer categories.
