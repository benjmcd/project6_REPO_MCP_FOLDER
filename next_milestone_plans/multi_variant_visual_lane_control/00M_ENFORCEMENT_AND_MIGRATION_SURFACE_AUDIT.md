# 00M Enforcement and Migration Surface Audit

## Purpose

Sharpen the bounded-uncertainty correction from v26 using direct repo-native workflow and migration evidence.

## Verified repo-native workflow surface

### Root workflow
`.github/workflows/playwright.yml`

Interpretation:
- there is a visible root CI/workflow surface
- it appears oriented to Playwright/UI concerns
- it does not, on current evidence, close the Python acceptance-path enforcement gap

## Verified migration surface

### Migration helpers
`backend/migration_compat.py`
- explicit Alembic/idempotent migration support exists in the live repo

### Database migration tool
`tools/migrate_sqlite_to_postgres.py`
- repo-native SQLite->Postgres migration tooling exists

### Alembic coverage for visual refs
`backend/alembic/versions/0010_visual_page_refs_json.py`
- adds `visual_page_refs_json` to `aps_content_document`

`backend/alembic/versions/0011_aps_retrieval_chunk_v1.py`
- includes `visual_page_refs_json` in retrieval-chunk schema evolution

## Correction to v26

v26 was right to reopen bounded uncertainty.
But it was slightly too broad about migration/schema risk.

The live repo evidence now supports this narrower statement:

- migration support for `visual_page_refs_json` is explicitly present
- therefore the residual uncertainty is **not** “does migration support exist?”
- it is instead about future drift, non-audited migration surfaces, and operational enforcement

## Revised bounded uncertainty statement

What still remains open is:

1. **Enforcement gap**
   - the pack defines the Python acceptance path
   - but the visible root workflow surface does not yet show that path being enforced

2. **Bounded future-drift risk**
   - additional surfaces may still exist outside the audited authority set
   - especially outside the app-heavy paths we focused on

3. **Residual schema/contract completeness drift risk**
   - still real in principle
   - but now narrower, because migration support for `visual_page_refs_json` is explicitly verified
