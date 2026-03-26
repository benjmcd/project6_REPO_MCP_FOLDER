# PostgreSQL Status Handoff

## Summary

The PostgreSQL lane is complete through the Tier1 operator-default cutover. PostgreSQL is now the supported default **Tier1 operator** database, while the repo still intentionally retains a SQLite no-env runtime default in [config.py](C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\core\config.py).

This document is the authoritative PostgreSQL status surface for the live repo. Historical planning files were used to arrive here, but they are not the ongoing authority.

## Current state

Current split-default semantics:

- Tier1 operator default in [project6.ps1](C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\project6.ps1) is PostgreSQL.
- No-env runtime default in [config.py](C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\core\config.py) remains SQLite.
- Explicit Tier1 SQLite fallback remains supported through `-Tier1DatabaseBackend sqlite`.
- Tier2 and Tier3 remain intentionally SQLite-shaped.

Operationally, the supported Tier1 flow is now:

1. Provide a PostgreSQL `DATABASE_URL` through process env, `backend/.env`, or `-Tier1PostgresUrl`.
2. Run [project6.ps1](C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\project6.ps1) Tier1 actions against PostgreSQL by default.
3. Use explicit SQLite fallback only when intentionally needed.

## Completed lane map

- PostgreSQL compatibility foundation -> `f356c44`
  - added driver/runtime compatibility
  - made Alembic/environment support PostgreSQL
  - removed the initial PostgreSQL migration blockers
- Tier1 PostgreSQL migration tooling -> `9daacd8`
  - added Tier1 PostgreSQL operator support
  - added the SQLite-to-PostgreSQL migration utility in [migrate_sqlite_to_postgres.py](C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\tools\migrate_sqlite_to_postgres.py)
- Tier1 operator default cutover -> `5019239`
  - made PostgreSQL the default Tier1 operator backend in [project6.ps1](C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\project6.ps1)
  - updated [backend/.env.example](C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\.env.example) and [README.md](C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\README.md) to PostgreSQL-first Tier1 guidance

## Verification basis already established

The completed PostgreSQL lane established all of the following in the live workspace:

- fresh SQLite `alembic upgrade head` succeeded
- fresh PostgreSQL `alembic upgrade head` succeeded
- the SQLite-to-PostgreSQL Tier1 migration utility succeeded against the canonical [backend/method_aware.db](C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\method_aware.db)
- PostgreSQL-default Tier1 smoke succeeded:
  - Tier1 migrate
  - Tier1 data migration into PostgreSQL
  - API startup
  - health/status
  - `GET /api/v1/datasets`
- explicit Tier1 SQLite fallback smoke also succeeded after the PostgreSQL-default cutover

This means the current repo supports both:

- PostgreSQL-first Tier1 operator use
- intentional SQLite Tier1 fallback

## Intentional deferred tech debt

The following are deferred by design and are not missing work from the completed PostgreSQL lane:

- runtime default in [config.py](C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\core\config.py) remains SQLite
- SQLite-heavy tests remain deferred, especially [tests/test_api.py](C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\tests\test_api.py)
- Tier2/Tier3 remain SQLite-shaped for speed and isolation
- checked-in proof/report refresh is not part of the completed PostgreSQL lane
- SQLite retirement has not been decided

The repo therefore has a deliberate split-brain default model:

- operator default: PostgreSQL
- bare runtime default with no env: SQLite

That split is temporary tech debt, but it is currently intentional and documented.

## What is not authoritative for PostgreSQL status

These are not the ongoing live authority for PostgreSQL state:

- root planning/strategy drafts
- session logs
- anything under [handoff](C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\handoff)

Use live code, current docs, and the commit chain above instead.

## Next possible lanes

If PostgreSQL work continues, the next reasonable lanes are:

1. runtime default flip in [config.py](C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\core\config.py)
2. SQLite-heavy test and proof refresh, including [tests/test_api.py](C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\tests\test_api.py)
3. explicit SQLite retirement or legacy-support decision

Until one of those lanes is intentionally opened, the current PostgreSQL state should be treated as stable and complete for Tier1 operator use.
