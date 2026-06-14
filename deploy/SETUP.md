# Layer 3 Production Deploy — First-Run Operator Runbook

This runbook covers the one-time setup required before `docker compose up` will
succeed.  The compose stack (`deploy/docker-compose.production.yml`) mounts two
credential files — `deploy/proxy/htpasswd` and `deploy/proxy/roles.map` — that
are **not** committed to git (only `.example` versions are tracked).  Without
them the `proxy` service (nginx:1.27-alpine) fails immediately with a
file-not-found error.

---

## Prerequisites

- Docker Desktop (or Docker Engine + Compose plugin) installed and running.
- A Linux/macOS shell or Windows PowerShell.
- Read access to this repo.

---

## Step 1 — Copy and fill the environment file

```
cp deploy/.env.deploy.example deploy/.env
```

Open `deploy/.env` and supply every `<REPLACE>` value.  The two **required**
values are:

| Variable | Notes |
|---|---|
| `POSTGRES_PASSWORD` | Must use only URL-safe characters `[A-Za-z0-9_-]` (32+ hex chars is ideal). The compose file embeds this value directly in the SQLAlchemy DSN (`postgresql+psycopg://app:<password>@db:5432/layer3`); characters such as `@ : / ? # %` would misparse the URL even though PostgreSQL itself accepts them. If you must use such characters, set `DATABASE_URL` (percent-encoded) in `deploy/.env` instead — it takes precedence over the compose default. |
| `ALLOWED_ORIGINS` | Explicit HTTPS origin(s) for CORS, e.g. `https://layer3.example.com`. No wildcards. |

All other variables in `deploy/.env.deploy.example` are optional; their
compose defaults are documented inline.  See `deploy/.env.deploy.example` for
the complete reference, grouped by area.

> **Security note:** `deploy/.env` is listed in `deploy/.gitignore` and must
> never be committed.

---

## Step 2 — Create `deploy/proxy/roles.map` from the example

```
cp deploy/proxy/roles.map.example deploy/proxy/roles.map
```

Edit `deploy/proxy/roles.map` and replace the placeholder usernames with the
real operator usernames you will add to `deploy/proxy/htpasswd` in step 3.

**Format** — each line is a nginx map entry:

```
"<username>" "<role>";
```

- Both fields are double-quoted and separated by a single space, followed by a
  semicolon.  This file is included directly inside the nginx `map` block in
  `deploy/proxy/nginx.conf`.
- Valid role tokens are `owner` and `auditor`.  These must match the compose
  environment variables `LAYER3_OWNER_ROLE_TOKENS` (default `owner`) and
  `LAYER3_AUDITOR_ROLE_TOKENS` (default `auditor`).
- **Users absent from this file get an empty role string.**  The app operates
  under `LAYER3_ROUTE_AUTHORIZATION_MODE=role_enforcing` and rejects every
  protected route for users with no role, returning 401.

Example `deploy/proxy/roles.map`:

```
"alice" "owner";
"bob"   "auditor";
```

> **Security note:** `deploy/proxy/roles.map` is listed in
> `deploy/.gitignore` and must never be committed.

---

## Step 3 — Generate `deploy/proxy/htpasswd` with bcrypt entries

The nginx `auth_basic` gate (configured in `deploy/proxy/nginx.conf`) reads
`deploy/proxy/htpasswd`.  Each entry must be a bcrypt hash (`$2y$` prefix);
nginx rejects MD5 and SHA-1 hashes in `auth_basic_user_file` by default on
modern builds.

**Generate one entry per user** using the `httpd` image (no local Apache
install required):

```
docker run --rm httpd:2.4-alpine htpasswd -nbB <username> <password>
```

The command prints a single line in the form `username:$2y$…`.  Append it to
`deploy/proxy/htpasswd`:

```
# First user — creates the file
docker run --rm httpd:2.4-alpine htpasswd -nbB alice mysecretpassword >> deploy/proxy/htpasswd

# Additional users — append
docker run --rm httpd:2.4-alpine htpasswd -nbB bob anothersecretpassword >> deploy/proxy/htpasswd
```

On Windows PowerShell, write-redirect may insert a BOM or CRLF newlines, both
of which corrupt bcrypt hash matching in nginx.  Use the script helper from
`deploy/smoke.ps1` as a reference, or redirect via `cmd /c`:

```powershell
cmd /c "docker run --rm httpd:2.4-alpine htpasswd -nbB alice mysecretpassword >> deploy\proxy\htpasswd"
```

The file must contain one `username:$2y$<hash>` line per user, with Unix
line-endings (LF) and no BOM.  Username values must exactly match the entries
in `deploy/proxy/roles.map` — nginx compares `$remote_user` (from Basic Auth)
against the map keys verbatim.

> **Security note:** `deploy/proxy/htpasswd` is listed in
> `deploy/.gitignore` and must never be committed.

---

## Step 4 — Start the stack

From the **repository root** (one level above `deploy/`):

```
docker compose -f deploy/docker-compose.production.yml --env-file deploy/.env up -d --build
```

The `--build` flag ensures the `app` image is built from the local source.
Omit it on subsequent runs if the source has not changed.

**Start order enforced by compose health checks:**

1. `db` (postgres:16-alpine) starts first; the `app` service waits until
   `pg_isready -U app -d layer3` returns healthy.
2. `app` starts and runs `alembic upgrade head` in its entrypoint; the `proxy`
   service waits until the app's `/ready` endpoint (defined in
   `Dockerfile.app`) returns healthy.
3. `proxy` (nginx:1.27-alpine) starts last and exposes port
   `${PROXY_HTTP_PORT:-8080}` on the host.

> **Security note:** The `app` container has no host port mapping — port 8000
> is only reachable within the `internal` bridge network.  All traffic must
> flow through the `proxy` container.  TLS must terminate at or before the
> proxy; see `deploy/proxy/nginx.conf` for options.

---

## Step 5 — Verify with the smoke test

Run the included smoke script to confirm auth, role enforcement, and
spoof-rejection are all working:

```powershell
.\deploy\smoke.ps1
```

The script spins up a parallel ephemeral stack with randomly generated
credentials, runs a 7-assertion matrix, and tears down.  It does **not** touch
your production `deploy/proxy/htpasswd` or `deploy/proxy/roles.map` files —
it generates its own credentials in a temporary `.smoke/` directory.

Optional flags:

| Flag | What it does |
|---|---|
| `-Probe` | Also runs the product-flow probe (steps 1–4 via HTTP) |
| `-Durability` | Seeds a record, restarts the app, verifies the record survived |
| `-Full` | Equivalent to `-Probe -Durability` |
| `-BackupRestore` | Full volume backup/restore round-trip (~3 min, destroys volumes) |
| `-KeepUp` | Leaves the ephemeral stack running after the test |

---

## Reference: volume layout

| Volume | Mount path in container | Purpose |
|---|---|---|
| `db_data` | `/var/lib/postgresql/data` | PostgreSQL data directory |
| `app_storage` | `/app/app/storage` | Connector artifact storage (`STORAGE_DIR`) |
| `export_data` | `/app/export-outbox` | Export outbox (`LAYER3_EXTERNAL_LOCAL_EXPORT_DIR`) |

| Proxy bind-mount | Source path | Destination in container |
|---|---|---|
| nginx config | `deploy/proxy/nginx.conf` | `/etc/nginx/nginx.conf` (read-only) |
| htpasswd | `deploy/proxy/htpasswd` | `/etc/nginx/htpasswd` (read-only) |
| roles map | `deploy/proxy/roles.map` | `/etc/nginx/roles.map` (read-only) |
