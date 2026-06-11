"""Deployment smoke suite — W2-S10.

Covers:
1. Production-profile settings validation: parses .env.production.example and
   asserts every var is accepted by Settings, pinning the example file against
   drift (uses a placeholder postgres URL so the nonlocal validator passes).
2. Fail-closed asserts (parametrized): the six nonlocal rejection cases.
3. Boot smoke with DB_INIT_MODE=migrate: fresh tmp SQLite DB, import the app,
   assert /health 200, /ready 200, and alembic_version table populated.
4. create_all guard: production example must set DB_INIT_MODE=migrate (or
   default is migrate); production must never silently use create_all.
5. Results reported via pytest pass/fail (run with -q from repo root).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Path / env bootstrap — must happen before any app import.
# DB_INIT_MODE=none prevents _initialize_database() from touching disk when
# main.py is imported for the TestClient smoke test.  Task 3 overrides this
# per-test via monkeypatch + importlib.reload.
# ---------------------------------------------------------------------------
os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import Settings  # noqa: E402

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

PRODUCTION_EXAMPLE = BACKEND / ".env.production.example"
_POSTGRES_PLACEHOLDER = (
    "postgresql+psycopg://placeholder:placeholder@localhost:5432/placeholder_db"
)

# Minimal kwargs that satisfy all nonlocal validator requirements.
_NONLOCAL_VALID_KWARGS: dict[str, str] = {
    "DEPLOYMENT_MODE": "nonlocal",
    "ALLOWED_ORIGINS": "https://app.example.com",
    "AUTH_OWNER": "proxy",
    "TRUSTED_PROXY_MODE": "true",
    "PROXY_IDENTITY_HEADER": "X-Forwarded-User",
    "STORAGE_EXPOSURE": "disabled",
    "DB_INIT_MODE": "migrate",
    "DATABASE_URL": _POSTGRES_PLACEHOLDER,
    "LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_NONLOCAL_AUTHORIZED": "true",
}


def _build_nonlocal(**overrides: str) -> Settings:
    kwargs = {**_NONLOCAL_VALID_KWARGS, **overrides}
    return Settings(_env_file=None, **kwargs)


# ===========================================================================
# Task 1 — Production-profile example file parses and constructs OK
# ===========================================================================


def _parse_env_example(path: Path) -> dict[str, str]:
    """Parse KEY=value lines from an env example file; skip comments and blanks."""
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        result[key.strip()] = value.strip()
    return result


def test_production_example_exists() -> None:
    """The production example file must be present."""
    assert PRODUCTION_EXAMPLE.exists(), (
        f"Missing production example: {PRODUCTION_EXAMPLE}"
    )


def test_production_example_all_vars_accepted_by_settings() -> None:
    """Every var in .env.production.example is accepted by Settings (no UnusedVars).

    Replace placeholder DATABASE_URL and ALLOWED_ORIGINS so the nonlocal
    validator does not reject them outright, keeping the test focused on
    field acceptance rather than URL reachability.
    """
    parsed = _parse_env_example(PRODUCTION_EXAMPLE)
    assert parsed, "env.production.example parsed no key=value pairs"

    overrides: dict[str, str] = {}
    # Swap placeholders with syntactically valid substitutes so validators pass.
    if "DATABASE_URL" in parsed and "<REPLACE" in parsed["DATABASE_URL"]:
        overrides["DATABASE_URL"] = _POSTGRES_PLACEHOLDER
    if "ALLOWED_ORIGINS" in parsed and "<REPLACE" in parsed["ALLOWED_ORIGINS"]:
        overrides["ALLOWED_ORIGINS"] = "https://app.example.com"
    if "LAYER3_SEC_EDGAR_USER_AGENT" in parsed and "<REPLACE" in parsed.get(
        "LAYER3_SEC_EDGAR_USER_AGENT", ""
    ):
        overrides["LAYER3_SEC_EDGAR_USER_AGENT"] = "TestOrg test@example.com"
    if "NRC_ADAMS_APS_SUBSCRIPTION_KEY" in parsed and "<REPLACE" in parsed.get(
        "NRC_ADAMS_APS_SUBSCRIPTION_KEY", ""
    ):
        overrides["NRC_ADAMS_APS_SUBSCRIPTION_KEY"] = "placeholder-key"

    kwargs = {**parsed, **overrides}

    # Build the full set of recognized keys:
    # (a) fields that declare an alias (most fields)
    alias_to_field = {
        field_info.alias: name
        for name, field_info in Settings.model_fields.items()
        if field_info.alias
    }
    recognized: set[str] = set(alias_to_field.keys())

    # (b) fields WITHOUT an alias — pydantic-settings resolves them
    # case-insensitively from the uppercased field name (e.g. app_name →
    # APP_NAME, api_prefix → API_PREFIX).
    for field_name in Settings.model_fields:
        if not Settings.model_fields[field_name].alias:
            recognized.add(field_name.upper())

    # (c) env vars that are intentionally NOT Settings fields but are
    # legitimately documented in the production example (consumed elsewhere).
    # LAYER3_LOG_FORMAT is read directly by observability.py via os.environ.
    recognized.add("LAYER3_LOG_FORMAT")

    unknown_keys = [k for k in parsed if k not in recognized]
    assert not unknown_keys, (
        f"Keys in .env.production.example have no matching Settings alias or "
        f"known external env var: {unknown_keys}\n"
        "Either add a Settings field with the matching alias, document the var "
        "in the recognized set above, or remove the key from the example file."
    )

    # Now construct Settings — this must not raise.
    profile = Settings(_env_file=None, **kwargs)
    assert profile.deployment_mode == "nonlocal"
    assert "postgres" in profile.database_url
    origins = profile.allowed_origin_list
    assert origins and all(o.startswith("https://") for o in origins)


# ===========================================================================
# Task 2 — Fail-closed asserts (parametrized)
# ===========================================================================


@pytest.mark.parametrize(
    "overrides, match_fragment",
    [
        # nonlocal + sqlite rejected
        (
            {"DATABASE_URL": "sqlite:///some.db"},
            "sqlite",
        ),
        # nonlocal + http origin rejected
        (
            {"ALLOWED_ORIGINS": "http://insecure.example.com"},
            "[Hh][Tt][Tt][Pp][Ss]",
        ),
        # nonlocal + AUTH_OWNER=none rejected
        (
            {"AUTH_OWNER": "none"},
            "[Aa][Uu][Tt][Hh]_[Oo][Ww][Nn][Ee][Rr]",
        ),
        # nonlocal + untrusted proxy rejected (TRUSTED_PROXY_MODE=false)
        (
            {"TRUSTED_PROXY_MODE": "false"},
            "[Tt][Rr][Uu][Ss][Tt][Ee][Dd]",
        ),
        # nonlocal + armed value-reveal flag rejected
        (
            {"LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED": "true"},
            "[Vv]alue.reveal",
        ),
        # role_enforcing without roles header rejected
        (
            {
                "LAYER3_ROUTE_AUTHORIZATION_MODE": "role_enforcing",
                "PROXY_ROLES_HEADER": "",
            },
            "(?i)PROXY_ROLES_HEADER",
        ),
    ],
    ids=[
        "sqlite_rejected",
        "http_origin_rejected",
        "auth_owner_none_rejected",
        "untrusted_proxy_rejected",
        "armed_value_reveal_rejected",
        "role_enforcing_without_roles_header_rejected",
    ],
)
def test_nonlocal_fail_closed(overrides: dict[str, str], match_fragment: str) -> None:
    with pytest.raises((ValidationError, ValueError), match=match_fragment):
        _build_nonlocal(**overrides)


# ===========================================================================
# Task 3 — Boot smoke with DB_INIT_MODE=migrate
# ===========================================================================


def test_boot_smoke_migrate_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Start the app with migrate mode against a fresh tmp SQLite DB.

    Verifies:
    - /health returns 200 {"status": "ok"}
    - /ready returns 200 {"status": "ready"}
    - alembic_version table exists (proves the migrate path ran, not create_all)

    Strategy mirrors test_layer3_observability.py but uses a real file-based
    SQLite DB (not :memory:) so alembic can inspect it and the alembic_version
    table persists across connections.
    """
    import importlib

    from sqlalchemy import create_engine, inspect as sa_inspect, text
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from fastapi.testclient import TestClient

    db_file = tmp_path / "smoke.db"
    db_url = f"sqlite:///{db_file.as_posix()}"
    storage_dir = tmp_path / "storage"

    # Point the app at the tmp DB before importing main.
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("DB_INIT_MODE", "migrate")
    monkeypatch.setenv("STORAGE_DIR", str(storage_dir))

    # Re-import app modules so the patched env is picked up.
    # We must reload in reverse-dependency order.
    import app.db.session as _db_session_mod
    import app.core.config as _config_mod
    import main as _main_mod

    importlib.reload(_config_mod)
    importlib.reload(_db_session_mod)
    importlib.reload(_main_mod)

    reloaded_app = _main_mod.app

    # After reload, _initialize_database() has already run (migrate mode).
    # Verify alembic_version exists before exercising HTTP endpoints.
    engine = create_engine(
        db_url,
        future=True,
        connect_args={"check_same_thread": False},
    )
    inspector = sa_inspect(engine)
    live_tables = set(inspector.get_table_names())
    assert "alembic_version" in live_tables, (
        "alembic_version table not found after DB_INIT_MODE=migrate boot — "
        "migrate path did not run or was skipped."
    )

    # Wire TestClient; override get_db so /ready hits the same tmp DB.
    from app.api.deps import get_db as _get_db
    from app.core.config import bootstrap_storage_tree, settings as _settings

    monkeypatch.setattr(_settings, "storage_dir", str(storage_dir))
    bootstrap_storage_tree(storage_dir)

    SessionLocal = sessionmaker(
        bind=engine, autocommit=False, autoflush=False, future=True
    )

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    reloaded_app.dependency_overrides[_get_db] = override_get_db
    try:
        client = TestClient(reloaded_app, raise_server_exceptions=False)

        health_resp = client.get("/health")
        assert health_resp.status_code == 200, (
            f"/health returned {health_resp.status_code}: {health_resp.text}"
        )
        assert health_resp.json().get("status") == "ok"

        # /ready needs the engine to point at our tmp DB; _db_session_mod.engine
        # was reloaded, so it should already target db_url.
        ready_resp = client.get("/ready")
        assert ready_resp.status_code == 200, (
            f"/ready returned {ready_resp.status_code}: {ready_resp.text}"
        )
        assert ready_resp.json().get("status") == "ready"
    finally:
        reloaded_app.dependency_overrides.pop(_get_db, None)
        engine.dispose()


# ===========================================================================
# Task 4 — create_all guard: production example must specify DB_INIT_MODE=migrate
# ===========================================================================


def test_production_example_db_init_mode_is_migrate() -> None:
    """Production example must set DB_INIT_MODE=migrate, not create_all.

    If the key is absent entirely, the Settings default is 'migrate'
    (config.py Field default='migrate') — which is acceptable because the
    app will never silently use create_all.  If the key IS present, it
    must not be 'create_all'.
    """
    parsed = _parse_env_example(PRODUCTION_EXAMPLE)
    db_init_mode = parsed.get("DB_INIT_MODE")

    if db_init_mode is None:
        # Key absent: verify Settings default is migrate, not create_all.
        default_profile = Settings(_env_file=None)
        assert default_profile.db_init_mode == "migrate", (
            "DB_INIT_MODE is absent from .env.production.example and the "
            f"Settings default is '{default_profile.db_init_mode}', not "
            "'migrate'. Production deployments would silently use create_all."
        )
    else:
        assert db_init_mode.lower() == "migrate", (
            f"DB_INIT_MODE in .env.production.example is '{db_init_mode}', "
            "expected 'migrate'. Production must not use create_all or none."
        )
