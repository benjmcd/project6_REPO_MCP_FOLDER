"""CI contract test for the reference production compose deployment.

Asserts structural invariants of the deploy/ directory without running docker
or importing yaml.  Uses only stdlib (pathlib + re).

Collected by pytest via the test_layer3_*.py glob.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Root paths
# ---------------------------------------------------------------------------
BACKEND = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND.parent
DEPLOY_DIR = REPO_ROOT / "deploy"

COMPOSE_FILE = DEPLOY_DIR / "docker-compose.production.yml"
NGINX_CONF = DEPLOY_DIR / "proxy" / "nginx.conf"
HTPASSWD_EXAMPLE = DEPLOY_DIR / "proxy" / "htpasswd.example"
ROLES_MAP_EXAMPLE = DEPLOY_DIR / "proxy" / "roles.map.example"
ENV_DEPLOY_EXAMPLE = DEPLOY_DIR / ".env.deploy.example"
GITIGNORE = REPO_ROOT / ".gitignore"

# The five permanently-gated value-reveal flags that must never be true under deploy/
VALUE_REVEAL_FLAGS = [
    "LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED",
    "LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED",
    "LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED",
    "LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compose_text() -> str:
    return COMPOSE_FILE.read_text(encoding="utf-8")


def _nginx_text() -> str:
    return NGINX_CONF.read_text(encoding="utf-8")


def _gitignore_text() -> str:
    return GITIGNORE.read_text(encoding="utf-8")


def _all_deploy_texts() -> list[tuple[str, str]]:
    """Return (filename, text) for every text file under deploy/."""
    results = []
    for f in DEPLOY_DIR.rglob("*"):
        if f.is_file():
            try:
                results.append((str(f.relative_to(REPO_ROOT)), f.read_text(encoding="utf-8")))
            except UnicodeDecodeError:
                pass
    return results


# ===========================================================================
# Existence checks
# ===========================================================================


def test_compose_file_exists() -> None:
    assert COMPOSE_FILE.exists(), (
        f"deploy/docker-compose.production.yml missing (expected at {COMPOSE_FILE})"
    )


def test_nginx_conf_exists() -> None:
    assert NGINX_CONF.exists(), (
        f"deploy/proxy/nginx.conf missing (expected at {NGINX_CONF})"
    )


def test_htpasswd_example_exists() -> None:
    assert HTPASSWD_EXAMPLE.exists(), (
        f"deploy/proxy/htpasswd.example missing (expected at {HTPASSWD_EXAMPLE})"
    )


def test_roles_map_example_exists() -> None:
    assert ROLES_MAP_EXAMPLE.exists(), (
        f"deploy/proxy/roles.map.example missing (expected at {ROLES_MAP_EXAMPLE})"
    )


def test_env_deploy_example_exists() -> None:
    assert ENV_DEPLOY_EXAMPLE.exists(), (
        f"deploy/.env.deploy.example missing (expected at {ENV_DEPLOY_EXAMPLE})"
    )


# ===========================================================================
# Compose: app service has no host port mapping
# ===========================================================================


def test_app_service_has_no_host_ports() -> None:
    """The app service must not publish a host port (traffic must go through proxy)."""
    text = _compose_text()

    # Find the app service block (from "  app:" to the next top-level key or EOF)
    app_section_match = re.search(
        r"^\s{2}app\s*:\s*\n(.*?)(?=^\s{2}\w|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    assert app_section_match, (
        "Could not locate 'app:' service block in docker-compose.production.yml"
    )
    app_section = app_section_match.group(1)

    # 'ports:' under the app service would expose a host port — must not be present
    assert not re.search(r"^\s+ports\s*:", app_section, re.MULTILINE), (
        "The 'app' service must not have a 'ports:' mapping — "
        "host must access the app only through the proxy"
    )


# ===========================================================================
# Compose: required env vars present
# ===========================================================================


def test_compose_deployment_mode_nonlocal() -> None:
    text = _compose_text()
    assert re.search(r"DEPLOYMENT_MODE\s*:\s*nonlocal", text), (
        "DEPLOYMENT_MODE: nonlocal not found in docker-compose.production.yml"
    )


def test_compose_auth_owner_proxy() -> None:
    text = _compose_text()
    assert re.search(r"AUTH_OWNER\s*:\s*proxy", text), (
        "AUTH_OWNER: proxy not found in docker-compose.production.yml"
    )


def test_compose_trusted_proxy_mode_true() -> None:
    text = _compose_text()
    assert re.search(r'TRUSTED_PROXY_MODE\s*:\s*["\']?true["\']?', text, re.IGNORECASE), (
        "TRUSTED_PROXY_MODE: true not found in docker-compose.production.yml"
    )


def test_compose_role_enforcing_present() -> None:
    text = _compose_text()
    assert re.search(r"LAYER3_ROUTE_AUTHORIZATION_MODE\s*:\s*role_enforcing", text), (
        "LAYER3_ROUTE_AUTHORIZATION_MODE: role_enforcing not found in "
        "docker-compose.production.yml"
    )


def test_compose_database_url_uses_psycopg() -> None:
    text = _compose_text()
    assert re.search(r"DATABASE_URL.*postgresql\+psycopg", text), (
        "DATABASE_URL in docker-compose.production.yml must use postgresql+psycopg driver"
    )


def test_compose_no_sqlite_anywhere_in_deploy() -> None:
    for filename, text in _all_deploy_texts():
        assert "sqlite" not in text.lower(), (
            f"'sqlite' found in deploy/{filename} — "
            "SQLite is forbidden in nonlocal deployments"
        )


# ===========================================================================
# nginx.conf: security requirements
# ===========================================================================


def test_nginx_conf_sets_x_forwarded_user() -> None:
    text = _nginx_text()
    assert re.search(r"proxy_set_header\s+X-Forwarded-User", text), (
        "nginx.conf must set proxy_set_header X-Forwarded-User"
    )


def test_nginx_conf_sets_x_forwarded_email() -> None:
    text = _nginx_text()
    assert re.search(r"proxy_set_header\s+X-Forwarded-Email", text), (
        "nginx.conf must set proxy_set_header X-Forwarded-Email"
    )


def test_nginx_conf_sets_x_forwarded_groups() -> None:
    text = _nginx_text()
    assert re.search(r"proxy_set_header\s+X-Forwarded-Groups", text), (
        "nginx.conf must set proxy_set_header X-Forwarded-Groups"
    )


def test_nginx_conf_sets_x_forwarded_roles() -> None:
    text = _nginx_text()
    assert re.search(r"proxy_set_header\s+X-Forwarded-Roles", text), (
        "nginx.conf must set proxy_set_header X-Forwarded-Roles"
    )


def test_nginx_conf_no_http_x_forwarded_passthrough() -> None:
    """nginx.conf must not reference $http_x_forwarded_* variables.

    Passing $http_x_forwarded_user (or similar) would forward client-supplied
    headers, enabling identity spoofing.  All identity headers must be derived
    server-side (e.g. $remote_user).
    """
    text = _nginx_text()
    assert not re.search(r"\$http_x_forwarded_", text), (
        "nginx.conf must not reference $http_x_forwarded_* variables — "
        "doing so would allow clients to spoof identity headers"
    )


def test_nginx_conf_has_auth_basic() -> None:
    text = _nginx_text()
    assert re.search(r"\bauth_basic\b", text), (
        "nginx.conf must configure auth_basic for HTTP Basic Authentication"
    )


# ===========================================================================
# Value-reveal flags: must not appear as true in any deploy/ file
# ===========================================================================


def test_value_reveal_flags_not_true_in_deploy() -> None:
    """None of the permanently-gated value-reveal flags may be assigned true in deploy/.

    Comment lines (starting with # after optional whitespace) are excluded —
    comments that document the flags for operator guidance are acceptable.
    """
    deploy_texts = _all_deploy_texts()
    for flag in VALUE_REVEAL_FLAGS:
        # Match actual assignments (env KEY=true or yaml KEY: true) on non-comment lines.
        assignment_true_pattern = re.compile(
            r"^[^#]*" + re.escape(flag) + r"\s*[=:]\s*['\"]?true['\"]?",
            re.MULTILINE | re.IGNORECASE,
        )
        for filename, text in deploy_texts:
            match = assignment_true_pattern.search(text)
            assert not match, (
                f"Permanently-gated flag {flag} found set to true in {filename}. "
                "This flag must remain false in all deploy/ configuration."
            )


def test_admission_evaluator_not_set_in_deploy() -> None:
    """SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED must not be set (assigned) in deploy/.

    Comments mentioning the flag for documentation purposes are acceptable.
    Only actual KEY=value or KEY: value assignments are rejected.
    """
    flag = "SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED"
    # Match lines where the flag is actually assigned (env or yaml syntax),
    # ignoring lines that are comments (start with # after optional whitespace).
    assignment_pattern = re.compile(
        r"^[^#]*" + re.escape(flag) + r"\s*[=:]",
        re.MULTILINE,
    )
    for filename, text in _all_deploy_texts():
        match = assignment_pattern.search(text)
        assert not match, (
            f"{flag} is assigned a value in {filename}. "
            "This flag must never be set in the reference compose stack or CI."
        )


# ===========================================================================
# .gitignore: runtime/secret files must be gitignored
# ===========================================================================


def test_gitignore_deploy_env() -> None:
    text = _gitignore_text()
    assert re.search(r"deploy/\.env\b", text), (
        ".gitignore must ignore deploy/.env (operator secrets must not be committed)"
    )


def test_gitignore_deploy_smoke_dir() -> None:
    text = _gitignore_text()
    assert re.search(r"deploy/\.smoke/", text), (
        ".gitignore must ignore deploy/.smoke/ (ephemeral smoke artifacts)"
    )


def test_gitignore_deploy_proxy_htpasswd() -> None:
    text = _gitignore_text()
    assert re.search(r"deploy/proxy/htpasswd\b", text), (
        ".gitignore must ignore deploy/proxy/htpasswd (password hashes are secrets)"
    )


def test_gitignore_deploy_proxy_roles_map() -> None:
    text = _gitignore_text()
    assert re.search(r"deploy/proxy/roles\.map\b", text), (
        ".gitignore must ignore deploy/proxy/roles.map (username->role mapping)"
    )
