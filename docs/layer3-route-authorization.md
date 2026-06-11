# Layer 3 Route Authorization

## Scope

Route-level identity-presence gating and role-based access control on top of
the existing operator-identity seam, covering the Layer 3 core workbench,
handoff, package, source-ingestion, source/sec-edgar, NRC APS review API, legacy
dataset/connector surface, and sec-xbrl runtime posture route. The sec-xbrl
route family uses the stricter `authorize_sec_xbrl_route` /
`_sec_xbrl_policy_decision` / `derive_sec_xbrl_evidence_owner` mechanism for
all POST and the value-reveal status GET; this authorization layer adds an
access class (`read` or `write`) and a role (`owner` or `auditor`) on top of
that seam.

The mode flag `LAYER3_ROUTE_AUTHORIZATION_MODE` controls whether role
enforcement is active. The default mode (`identity_presence`) is inert and
bit-identical to prior behavior.

The canonical policy owner is
`backend/app/services/layer3_sec_xbrl_in_app_auth_policy.py`. The authority
matrix row `auth_security_posture` cites this file as
`layer3.sec_xbrl.repo_owned_in_app_operator_auth_policy.v1` and records
admission result `admitted_by_route_level_role_authorization_phase1`.

## Role Model

Two roles are admitted:

| Role | Permitted access classes |
|---|---|
| `owner` | `read`, `write` |
| `auditor` | `read` only |

## Access Classes

| Access class | Allowed roles |
|---|---|
| `read` | `owner`, `auditor` |
| `write` | `owner` |

Every gated route declares one of these access classes explicitly at the call
site. A declaration drift guard (AST-level) enforces that no gated route omits
the `access=` argument. The sec_xbrl module is enrolled in the drift guard with
stricter-mechanism recognition.

## Mode Flag Semantics

| Mode | Behavior |
|---|---|
| `identity_presence` (default) | Existing identity-presence behavior preserved exactly. Role derivation is not attempted. `role` is `null` in the result. No new exception class can be raised. This mode is the active default and the only mode enforced in production today. |
| `role_enforcing` | Derives role from the configured roles header CSV. Owner is granted when any token matches the owner token set. Auditor is granted when any token matches the auditor token set and owner is not present. An auditor on a `write` access class is rejected (403). A missing or unrecognized roles header is rejected (401). |

The nonlocal validator rejects `role_enforcing` combined with a blank
`PROXY_ROLES_HEADER`.

## Role Derivation: AUTH_OWNER=none

Under `AUTH_OWNER=none` (the local/dev default), `_server_derived_role` returns
`owner` unconditionally, regardless of mode. This preserves single-operator
local proof behavior.

## Header Contract

- `PROXY_ROLES_HEADER` (default `X-Forwarded-Roles`): comma-separated role
  tokens supplied by the trusted reverse proxy. Used only under `role_enforcing`
  mode.
- The reverse proxy **must** strip or overwrite any client-supplied values for
  the identity header, groups header, and roles header before forwarding. The
  app has no way to verify client-supplied header values.
- `proxy_roles_header` is listed in `FORBIDDEN_REQUEST_FIELDS` and is included
  in the readonly projection exposed by `/sec-xbrl/identity/projection`.
- Token matching is case-insensitive. Custom token strings are configured via
  `LAYER3_OWNER_ROLE_TOKENS` and `LAYER3_AUDITOR_ROLE_TOKENS` (CSV; defaults
  are `owner` and `auditor` respectively).

## Configuration Reference

| Env var | Default | Purpose |
|---|---|---|
| `LAYER3_ROUTE_AUTHORIZATION_MODE` | `identity_presence` | `identity_presence` (inert default) or `role_enforcing` (active role check) |
| `PROXY_ROLES_HEADER` | `X-Forwarded-Roles` | Request header name carrying role tokens from the reverse proxy |
| `LAYER3_OWNER_ROLE_TOKENS` | `owner` | CSV of header token strings that map to the owner role |
| `LAYER3_AUDITOR_ROLE_TOKENS` | `auditor` | CSV of header token strings that map to the auditor role |

## Coverage

Routes gated by `route_level_operator_authorization_required`:

- **Layer 3 core workbench** (`backend/app/api/layer3/__init__.py`): all
  call sites declared with `access="read"` or `access="write"` per route
  semantics.
- **Layer 3 handoff** (`backend/app/api/layer3/handoff.py`): same.
- **Layer 3 package** (`backend/app/api/layer3/package.py`): same.
- **Layer 3 source ingestion** (`backend/app/api/layer3/source_ingestion.py`):
  same; `/api/v1/layer3/source/intake/upload` is also enrolled in the
  pre-body identity middleware.
- **Layer 3 source/sec-edgar** (`backend/app/api/layer3/source_sec_edgar.py`):
  same.
- **NRC APS review API** (`backend/app/api/review_nrc_aps.py`): all 23 GET
  routes gated with `access="read"`. Module-local helpers; no import from
  `layer3._shared`.
- **Legacy dataset/connector surface** (`backend/app/api/router.py`): all 45
  routes gated (read/write per route semantics). `/api/v1/sources/upload` is
  also enrolled in the pre-body identity middleware in `backend/main.py`.
- **Sec-xbrl runtime posture** (`GET /api/v1/layer3/sec-xbrl/runtime/posture`):
  gated with `access="read"`. The sec_xbrl module uses the stricter
  `authorize_sec_xbrl_route` mechanism for all other routes; the drift guard
  recognizes both mechanisms.

All ~207 layer3 seam call sites declare `access=` explicitly, enforced by the
declaration drift guard.

## Explicitly Public Surfaces

The following routes are intentionally ungated and must remain so:

- `GET /api/layer3/bootstrap` — public metadata
- `GET /readiness` — health/readiness probe
- `GET /api/layer3/authority-matrix` — governance read-only exposure
- `GET /health` — health probe
- `GET /` — root
- `GET /api/v1/layer3/sec-xbrl/identity/projection` — **fail-soft; ungated by
  design** (doc-1351 diagnostic contract). Returns a readonly projection of the
  current identity and authorization configuration. Never raises an auth error;
  always returns 200.

FastAPI `/docs` and `/openapi.json` remain open. Locking them down is a
deployment-owned decision (reverse proxy or network policy), not an in-app
decision.

## Non-Goals

- No session or cookie-based authentication.
- No per-resource or object-level ACLs.
- No UI or static-asset authentication (reverse-proxy-owned).
- No cross-request role state or caching.
- Capping the sec_xbrl payload-claimed `operator_role` at the server-derived
  role under `role_enforcing` is deferred.
- Requiring `role_enforcing` in nonlocal mode is deferred (currently opt-in).
- `egress_write` and `decision_write` access classes are deferred.

## Deferred Follow-Ups

1. Cap the sec_xbrl payload-claimed `operator_role` at the server-derived role
   when `LAYER3_ROUTE_AUTHORIZATION_MODE=role_enforcing` — currently the
   payload field is accepted as-is under role_enforcing.
2. Consider requiring `role_enforcing` in nonlocal mode once reverse proxies
   provision the roles header reliably.
3. Consider `egress_write` / `decision_write` access classes for export and
   decision routes.
