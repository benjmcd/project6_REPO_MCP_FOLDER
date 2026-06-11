"""Tests for deployment-profile validation rules in Settings."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings

_NONLOCAL_VALID_KWARGS = {
    "DEPLOYMENT_MODE": "nonlocal",
    "ALLOWED_ORIGINS": "https://app.example.com",
    "AUTH_OWNER": "proxy",
    "TRUSTED_PROXY_MODE": "true",
    "PROXY_IDENTITY_HEADER": "X-Forwarded-User",
    "STORAGE_EXPOSURE": "disabled",
    "DB_INIT_MODE": "migrate",
    "LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_NONLOCAL_AUTHORIZED": "true",
}

_POSTGRES_URL = "postgresql+psycopg://placeholder:placeholder@localhost:5432/placeholder_db"


def _build(**overrides) -> Settings:
    kwargs = {**_NONLOCAL_VALID_KWARGS, **overrides}
    return Settings(_env_file=None, **kwargs)


# (a) nonlocal + sqlite URL + db_init_mode=migrate -> raises referencing sqlite
def test_nonlocal_sqlite_url_migrate_raises() -> None:
    with pytest.raises((ValidationError, ValueError), match="sqlite"):
        _build(DATABASE_URL="sqlite:///some.db", DB_INIT_MODE="migrate")


# (b) nonlocal + sqlite URL + db_init_mode=none -> still raises. Nonlocal
# deployments must not retain a sqlite URL even when startup DB init is disabled.
def test_nonlocal_sqlite_url_none_raises() -> None:
    with pytest.raises((ValidationError, ValueError), match="sqlite"):
        _build(DATABASE_URL="sqlite:///some.db", DB_INIT_MODE="none")


# (c) local defaults construct OK (no nonlocal rules apply)
def test_local_defaults_construct_ok() -> None:
    profile = Settings(_env_file=None)
    assert profile.deployment_mode == "local"


# (d) nonlocal + postgres URL + valid kwargs constructs OK
def test_nonlocal_postgres_url_constructs_ok() -> None:
    profile = _build(DATABASE_URL=_POSTGRES_URL)
    assert profile.deployment_mode == "nonlocal"
    assert profile.database_url == _POSTGRES_URL


def test_nonlocal_postgres_url_with_db_init_none_constructs_ok() -> None:
    profile = _build(DATABASE_URL=_POSTGRES_URL, DB_INIT_MODE="none")
    assert profile.deployment_mode == "nonlocal"
    assert profile.database_url == _POSTGRES_URL
