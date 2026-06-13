# Layer 3 Backup / Restore Runbook

Covers all three named Docker volumes: `db_data`, `app_storage`, and `export_data`.

---

## 1. Volume Inventory

| Volume | Mount path in container | Contents | Consistency note |
|---|---|---|---|
| `db_data` | `/var/lib/postgresql/data` | Postgres 16 cluster (all tables, alembic_version, sequences) | **Atomic unit with app_storage** |
| `app_storage` | `/app/app/storage` | Uploaded source bytes (content-addressed; path stored as `storage_ref` in DB) | **Atomic unit with db_data** |
| `export_data` | `/app/export-outbox` | Export outbox artifacts produced by the app | Independent; loss causes re-generation work only |

**Critical**: `db_data` and `app_storage` are ONE atomic consistency unit. Each `L3SourceIntakeRecord` row holds a `storage_ref` that points into `app_storage` and a `content_sha256` that the preview endpoint re-verifies against the on-disk bytes. If these volumes are backed up at different points in time, records uploaded in the gap will yield `409 source_intake_preview_hash_mismatch` (if the file is present but hash disagrees) or `404 source_intake_preview_storage_missing` (if the DB row exists but the file was not yet on disk). Either condition is permanent — there is no repair path short of restore. **Never run independent cron jobs that dump the DB and tar the file volumes at separate times.**

---

## 2. Project-Name Derivation

Volume names are `<project>_db_data`, `<project>_app_storage`, `<project>_export_data`. The prefix is the **compose project name**, not the worktree directory name.

The compose file at `deploy/docker-compose.production.yml` has no `name:` key, so Docker Compose derives the project name from the directory that `docker compose` is invoked in — or from the `COMPOSE_PROJECT_NAME` environment variable, or the `-p` flag.

**Always derive it programmatically before backup or restore:**

```bash
# From the repo root or any directory with compose access:
docker compose -f deploy/docker-compose.production.yml config --format json \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['name'])"
```

Or explicitly force it:

```bash
export COMPOSE_PROJECT_NAME=layer3
# or pass -p layer3 to every compose command
```

> **Warning**: `p6deploy` is the worktree directory name on the developer machine. It is NOT necessarily the compose project name. Do not hardcode volume prefixes.

---

## 3. POSTGRES_PASSWORD URL Safety

`DATABASE_URL` is interpolated as:

```
postgresql+psycopg://app:${POSTGRES_PASSWORD}@db:5432/layer3
```

The password is embedded literally in a URL. Characters `@ : / ? # %` break DSN parsing even though Postgres itself accepts them. Use only `[A-Za-z0-9_-]` characters (hex is ideal).

Escape hatch: set the full percent-encoded `DATABASE_URL` directly in `deploy/.env` — it takes precedence over the default expansion.

---

## 4. Backup Procedure

All three volumes are backed up in a **single quiesced window**. Independent cron jobs that dump the DB and tar the file volumes at different times manufacture cross-volume skew and will permanently corrupt the source-intake records that were uploaded between the two jobs. Do not do this.

### Pre-check

```bash
docker compose -f deploy/docker-compose.production.yml --env-file deploy/.env \
  exec db pg_isready -U app -d layer3
# Must exit 0 before proceeding.
```

### Step 1 — Quiesce (stop app only; db stays up)

```bash
docker compose -f deploy/docker-compose.production.yml --env-file deploy/.env \
  stop app
```

This single quiesce covers both the Postgres dump and both file-volume tars. The db container stays running so `pg_dump` can connect to it.

> **RPO note**: This quiesce window means zero new uploads are accepted during backup. RPO is 24 h with daily backups; losing `app_storage` is NOT acceptable (it would orphan every DB row uploaded since the last backup permanently). Retain backups for 30 days. Supplement with weekly physical cold-copies (see §7).

### Step 2 — Dump db_data

Use a shell-level redirect (`>`) for binary fidelity. Never pipe through PowerShell — PowerShell pipelines re-encode bytes and corrupt binary formats.

```bash
# Linux / bash (run from host or a helper container with pg_dump):
docker compose -f deploy/docker-compose.production.yml --env-file deploy/.env \
  exec -T db pg_dump -U app -d layer3 \
  --format=custom --compress=9 --no-owner --no-privileges \
  > backups/TIMESTAMP/db.pgdump
```

Also capture the alembic revision set:

```bash
docker compose -f deploy/docker-compose.production.yml --env-file deploy/.env \
  exec -T db psql -U app -d layer3 -Atc \
  "SELECT version_num FROM alembic_version ORDER BY version_num" \
  > backups/TIMESTAMP/alembic_versions.txt
```

Capture the full SET (not just a count). An empty result is a FAIL.

### Step 3 — Tar file volumes

Use a GNU-tar image (`debian:bookworm-slim`) mounted against the named volumes. The `python:3.11-slim` app image uses GNU tar but invoking tar through a dedicated helper image avoids dependency drift.

```bash
# app_storage
docker run --rm \
  -v <project>_app_storage:/data:ro \
  -v "$(pwd)/backups/TIMESTAMP":/out \
  debian:bookworm-slim \
  tar czf /out/app_storage.tar.gz -C /data . --numeric-owner

# export_data
docker run --rm \
  -v <project>_export_data:/data:ro \
  -v "$(pwd)/backups/TIMESTAMP":/out \
  debian:bookworm-slim \
  tar czf /out/export_data.tar.gz -C /data . --numeric-owner
```

Verify archive integrity immediately:

```bash
docker run --rm \
  -v "$(pwd)/backups/TIMESTAMP":/out \
  debian:bookworm-slim \
  tar -tzf /out/app_storage.tar.gz > /dev/null  # exit 0 = intact
```

### Step 4 — Manifest

Write `backups/TIMESTAMP/manifest.json`:

```json
{
  "backup_timestamp": "TIMESTAMP",
  "compose_project": "<project>",
  "alembic_version_set": ["<rev1>", ...],
  "archives": {
    "db.pgdump": "<bytes>",
    "app_storage.tar.gz": "<bytes>",
    "export_data.tar.gz": "<bytes>"
  }
}
```

### Step 5 — Resume

```bash
docker compose -f deploy/docker-compose.production.yml --env-file deploy/.env \
  start app
# Then wait for /ready -> 200 before declaring backup complete.
```

**RTO**: ~30 min for a full restore on standard hardware.

---

## 5. Restore Procedure

### Ordering rule

> db up (no app) → restore db_data → verify alembic set → restore file volumes → full up

`DB_INIT_MODE=none` means `alembic upgrade head` runs only from the app container CMD. A stopped app cannot migrate. Never restore file volumes before the DB is verified — a healthy preview endpoint requires both to be consistent.

### Step 1 — Total destroy

```bash
docker compose -f deploy/docker-compose.production.yml --env-file deploy/.env \
  down -v
# All three volumes are deleted. This is intentional — stale data must not survive.
```

### Step 2 — Start db only

```bash
docker compose -f deploy/docker-compose.production.yml --env-file deploy/.env \
  up -d db
# Wait for pg_isready:
docker compose -f deploy/docker-compose.production.yml --env-file deploy/.env \
  exec db pg_isready -U app -d layer3
```

**Assert app container is NOT running** before restoring:

```bash
docker compose -f deploy/docker-compose.production.yml --env-file deploy/.env \
  ps -q app
# Output must be empty (no container).
```

### Step 3 — Restore db_data

Use a shell-level redirect (`<`) for binary fidelity. Never pipe through PowerShell.

```bash
docker compose -f deploy/docker-compose.production.yml --env-file deploy/.env \
  exec -T db pg_restore -U app -d layer3 \
  --no-owner --role=app --clean --if-exists --exit-on-error --format=custom \
  < backups/TIMESTAMP/db.pgdump
```

### Step 4 — Verify alembic revision set

```bash
docker compose -f deploy/docker-compose.production.yml --env-file deploy/.env \
  exec -T db psql -U app -d layer3 -Atc \
  "SELECT version_num FROM alembic_version ORDER BY version_num"
```

**The restored set must equal the set captured during backup.** A count mismatch (e.g. count=1 when backup had 3 rows) is a FAIL. If it does not match, **DO NOT start the app**. Never hand-edit `alembic_version`. Investigate whether the correct dump was used or whether the Postgres cluster was actually restored.

### Step 5 — Recreate empty file volumes and restore

```bash
# Recreate volumes without starting containers:
docker compose -f deploy/docker-compose.production.yml --env-file deploy/.env \
  up --no-start

# Restore app_storage:
docker run --rm \
  -v <project>_app_storage:/data \
  -v "$(pwd)/backups/TIMESTAMP":/backup:ro \
  debian:bookworm-slim \
  sh -c "tar xzf /backup/app_storage.tar.gz -C /data --numeric-owner && chown -R 1001:1001 /data"

# Restore export_data:
docker run --rm \
  -v <project>_export_data:/data \
  -v "$(pwd)/backups/TIMESTAMP":/backup:ro \
  debian:bookworm-slim \
  sh -c "tar xzf /backup/export_data.tar.gz -C /data --numeric-owner && chown -R 1001:1001 /data"
```

The explicit `chown -R 1001:1001 /data` is required even when `--numeric-owner` is used. The helper image's uid/gid table may remap numeric owners during extraction; `chown` guarantees the non-root `appuser` (uid/gid 1001) can read and write the restored tree.

### Step 6 — Full stack up

```bash
docker compose -f deploy/docker-compose.production.yml --env-file deploy/.env \
  up -d
# The proxy depends_on app with condition: service_healthy — it will wait
# for /ready -> 200 before accepting traffic.
```

### Step 7 — Validate

```bash
# Readiness probe:
curl -s -o /dev/null -w "%{http_code}" http://localhost:<PROXY_PORT>/ready
# Expected: 200

# Operator identity (use real credentials):
curl -u owner:<password> http://localhost:<PROXY_PORT>/api/v1/layer3/operator/identity
# Expected: 200

# Source intake preview for a known pre-backup record:
curl -u owner:<password> \
  http://localhost:<PROXY_PORT>/api/v1/layer3/source/intake/<known_id>/preview
# Expected: 200 (proves db row + file bytes both survived the round-trip)
```

---

## 6. alembic_version Handling

`pg_dump --format=custom` captures the full alembic_version table. `pg_restore` restores it exactly. `alembic upgrade head` on the next app start is a no-op when the DB is already at HEAD, or runs the delta migrations from an intermediate revision. Never hand-edit `alembic_version`.

---

## 7. Physical-tar DR (Cold Copy)

For a weekly DR supplement, take a physical cold copy of the Postgres data directory:

1. Bring the **entire stack down** (`down`, not `down -v` — do NOT delete volumes).
2. Pin the exact image digest for both the backup and the restore so tar interpretation is identical.
3. `docker run --rm -v <project>_db_data:/data:ro debian:bookworm-slim@sha256:<digest> tar czf /out/db_data.tar.gz -C /data . --numeric-owner`
4. Restore in reverse with the same pinned digest.

`pg_dump` (logical) is the only cross-version-safe method for database migration across Postgres major versions. Physical tar requires the same Postgres major version on restore.
