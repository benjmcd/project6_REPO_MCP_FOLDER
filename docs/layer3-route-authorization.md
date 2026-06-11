# Layer 3 Route Authorization

## Scope

Read/write access classes atop identity presence, with owner and auditor roles.

The authorization layer adds an *access class* (`read` or `write`) and a *role*
(`owner` or `auditor`) on top of the existing operator-identity seam
(`route_level_operator_identity_required`). The mode flag
`LAYER3_ROUTE_AUTHORIZATION_MODE` controls whether enforcement is active.

## Mode flag semantics

| Mode | Behavior |
|---|---|
| `identity_presence` (default) | Existing behavior preserved exactly. Role derivation is not attempted. `role` is `null` in the result. No new exception class can be raised. |
| `role_enforcing` | Derives role from the configured roles header CSV. Auditor on a write access class is rejected. Missing or unrecognized header tokens are rejected. |

## Header contract

- `PROXY_ROLES_HEADER` (default `X-Forwarded-Roles`): comma-separated role
  tokens supplied by the trusted reverse proxy.
- The reverse proxy **must** strip or overwrite any client-supplied value for
  this header before forwarding. Claude has no way to verify client-supplied
  header values.
- Token matching is case-insensitive. Custom token strings are configured via
  `LAYER3_OWNER_ROLE_TOKENS` and `LAYER3_AUDITOR_ROLE_TOKENS` (CSV, defaults
  `owner` and `auditor`).

## Access classes and role mapping

| Access class | Allowed roles |
|---|---|
| `read` | `owner`, `auditor` |
| `write` | `owner` |

## Non-goals

- No session or cookie-based authentication.
- No per-resource ACLs.
- No UI authentication layer.
- No cross-request state or role caching.
