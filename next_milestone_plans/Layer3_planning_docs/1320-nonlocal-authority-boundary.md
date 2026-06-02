# 1320 - SEC XBRL Nonlocal Authority Boundary

Milestone:
`sec_xbrl_nonlocal_deployment_authority_packet_or_in_app_auth_boundary_v1`

Base authority: `project6-origin/main` at
`e3a0792b6ee620cd0da5a0892d4c9769245ba3ff`

Prior milestone:
`sec_xbrl_default_on_nonlocal_production_readiness_gate_v1`

## Status

Branch-local docs-only Tier-2 design/pre-review entry.

This pass does not implement production readiness, in-app auth, proxy
integration, schema, persistence, API/UI, source acquisition, Arelle execution,
value reveal, export/delivery, provider dispatch, runtime defaults, or
redaction-posture changes. It defines the authority fork required after the
nonlocal production-readiness gate blocked on missing deployment-owned
authority.

## Current Authority

Repo-confirmed:

- `diagnostics/assessment/sec-xbrl-nonlocal-production-readiness-gate-report.json`
  emits `decision: nonlocal_production_readiness_blocked`.
- The only blocking reason is
  `nonlocal_production_readiness_authority_packet_missing`.
- The same report records clean inherited default-on runtime evidence:
  `decision: default_on_runtime_enabled`, `blocking_reasons_count: 0`.
- `backend/app/core/config.py` requires nonlocal deployments to use explicit
  HTTPS origins, `AUTH_OWNER=proxy`, `TRUSTED_PROXY_MODE=true`, a nonblank
  proxy identity header, safe storage exposure, and explicit Arelle nonlocal
  authorization when fact-authority cutover is enabled.
- `backend/tests/test_layer3_api.py` proves nonlocal proxy guardrails,
  fail-closed nonlocal configuration, local default-on behavior, and direct
  storage disabling in nonlocal mode.
- `next_milestone_plans/Layer3_planning_docs/116_SECURITY_SOURCE_DELIVERY_BOUNDARY_FREEZE.md`
  records the accepted security boundary: current repo code requires a
  proxy-owned trust posture for nonlocal configuration, but inspected local
  code does not itself authenticate individual inbound Layer 3 requests.

Reference-only:

- Prior deployment-hardening notes outside the repo describe the same
  proxy-owned nonlocal posture: explicit HTTPS origins, proxy-owned auth,
  trusted proxy mode, nonblank identity-header name, and disabled direct
  storage mount. Those notes are useful corroboration but are not admissible
  production authority by themselves.

Inference:

- The current repo can validate a redacted deployment authority packet for the
  external-proxy fork, but it cannot truthfully manufacture one. Repo-owned
  in-app auth is a separate fork and is not an admissible authority-packet
  mode; without explicit evidence from the selected fork, nonlocal
  production-readiness admission must remain blocked.

## Design Decision

The next admissible movement is a fork, not a single implementation:

1. **Authority-packet fork:** a deployment owner supplies a redacted
   server/deployment authority packet that the existing nonlocal readiness gate
   can validate without going live or changing runtime behavior.
2. **In-app auth fork:** if no external proxy authority can be proven, create a
   separate in-app auth/security design and later implementation lane before
   any nonlocal production-readiness admission.

This pass selects the fork and acceptance criteria only. It does not choose a
production host, identity provider, proxy product, domain, secret manager,
operator roster, retention policy, or live deployment.

## Fork A - Deployment Authority Packet

The authority-packet fork is admissible only when the packet is
server/deployment-owned, redacted, and validated by
`diagnostics/assessment/sec-xbrl-nonlocal-production-readiness-gate.py`.

Minimum packet fields are inherited from the gate:

- `deployment_mode`: must be `nonlocal`;
- `deployment_owner_ref`: redacted stable deployment owner reference;
- `approval_record_ref`: redacted stable approval reference;
- `approval_record_hash`: 64-character lowercase hex hash;
- `proxy_boundary_mode`: `trusted_external_proxy` only. Repo-owned in-app auth
  remains a separate fork and must not be admitted through the deployment
  authority-packet gate.
- `proxy_identity_header`: header name only, not an observed identity value;
- `allowed_origins_policy_hash`: 64-character lowercase hex hash;
- `storage_exposure_policy`: `auto` or `disabled`;
- `arelle_fact_authority_nonlocal_authorized`: must be `true`;
- `rollback_owner_ref`: redacted rollback owner reference;
- `incident_owner_ref`: redacted incident owner reference;
- `redaction_policy_id`: must match the gate redaction policy;
- `verification_run_ref`: redacted stable verification-run reference;
- `deployment_authority_provenance_ref`: redacted stable deployment-authority
  provenance reference;
- `deployment_authority_provenance_hash`: 64-character lowercase hex hash.

All `*_ref` authority fields must be reduced stable references matching the
gate-owned redacted reference shape, not raw operator names, issuer names,
deployment notes, paths, URLs, SEC identifiers, or local evidence labels. The
packet itself and the emitted report must not contain raw operator identity,
email, issuer identity, accession, labeled or bare CIK-like references, SEC URL,
local path in either Windows slash form, period date, raw sidecar payload, raw
value-store payload, raw value, or residual magnitude.

Passing this fork proves only that the deployment authority packet is
admissible to the readiness gate. It still does not implement production
enablement, export/delivery, provider dispatch, value reveal default-on, source
acquisition, Arelle execution, or final-statement semantics.

## Fork B - In-App Auth/Security Boundary

The in-app auth fork is required when the external proxy boundary cannot be
proven with a redacted authority packet.

The first in-app auth design must specify, before implementation:

- authenticated principal source and trust model;
- anonymous-request denial for SEC XBRL nonlocal/default-on surfaces;
- operator role or permission vocabulary;
- identity projection rules for audit logs without raw identity leakage;
- interaction with existing proxy headers;
- request/response redaction policy;
- session, token, or header replay behavior;
- route allowlist for SEC XBRL surfaces;
- negative tests for absent, malformed, spoofed, and unauthorized identity;
- containment/rollback that returns to local-only or proxy-owned posture
  without deleting persisted SEC XBRL authority rows.

Any implementation of this fork is Tier 2 because it touches authorization
behavior and may affect operator workflow. It needs separate risk
documentation, focused negative tests, containment notes, and review according
to the softened SEC XBRL merge-gate policy.

## Shared Non-Admissions

Both forks keep the following blocked until a separate admitted lane:

- production-readiness claim;
- public/provider URL behavior;
- connector or destination dispatch;
- export/delivery beyond already-admitted same-origin boundaries;
- value reveal default-on or automatic value delivery;
- raw internal value-store default-on;
- source acquisition or live SEC network execution;
- Arelle subprocess invocation;
- schema, `models.py`, Alembic migration, or durable persistence changes;
- rendered operator workflow changes;
- raw runtime artifacts;
- final financial-statement semantics;
- cross-company comparability.

## Acceptance Criteria For The Next Turn

Next work must take exactly one fork.

Authority-packet fork acceptance:

- Provide a redacted packet outside committed source or commit only a redacted,
  non-secret authority artifact explicitly approved for repo inclusion.
- Run
  `python ./diagnostics/assessment/sec-xbrl-nonlocal-production-readiness-gate.py
  --authority-packet <packet> --output <temp report>`.
- Confirm the temp report has
  `decision: nonlocal_production_readiness_authority_admitted`,
  `blocking_reasons: []`, and `production_readiness_claimed: false`.
- Confirm the packet includes `deployment_authority_provenance_ref` and
  `deployment_authority_provenance_hash`, and that the ref is a reduced stable
  provenance reference rather than a local filename, operator name, issuer name,
  URL, path, accession, CIK, or free-text deployment note.
- Confirm no raw identity/path/SEC URL/accession/residual magnitude appears in
  the packet or the temp report.
- Do not commit secrets, production origins, raw identities, local paths, or
  unreduced deployment notes.

In-app auth fork acceptance:

- Add a design/pre-review doc naming the exact auth mode and SEC XBRL surfaces.
- Include negative test obligations for anonymous, spoofed, malformed, and
  unauthorized requests.
- Include redaction, audit, rollback, and proxy-interoperability boundaries.
- Do not implement runtime auth until the design is reviewed or the operator
  explicitly authorizes implementation.

Common verification before merge:

- focused nonlocal/default-on tests;
- full `backend/tests/test_sec_xbrl*.py` suite if any test/diagnostic changes;
- `python ./tools/l3-target-selection-validate.py --expect frozen`;
- `python ./tools/l3-progress-check.py`;
- JSON validation for changed manifests and any committed reports;
- redaction/residual scan over committed SEC XBRL reports;
- `git diff --check`.

## Stop Conditions

Stop if the next work would require:

- claiming nonlocal production readiness without an admitted authority packet
  or implemented in-app auth proof;
- committing secrets, production identities, raw origins, local paths, raw SEC
  identifiers, raw values, or raw deployment evidence;
- changing runtime defaults, API/UI, operator workflow, schema, persistence,
  source acquisition, Arelle execution, value reveal, export/delivery, provider
  dispatch, or redaction posture in the same pass;
- treating proxy-owned posture as equivalent to proof that a proxy is actually
  deployed and enforcing identity.

## Branch-Local Verification

Docs-only validation on branch `codex/secxbrl-nonlocal-auth-boundary`:

- Focused nonlocal/default-on API tests:
  `python -m pytest ./backend/tests/test_layer3_api.py -q -k
  "deployment_profile or default_arelle_cutover or arelle_sidecar or
  default_on or value_reveal"`
  - PASS: `27 passed, 249 deselected, 3 warnings`.
- `python ./tools/l3-target-selection-validate.py --expect frozen`
  - PASS.
- `python ./tools/l3-progress-check.py`
  - PASS.
- Changed JSON parse:
  - PASS.
- Committed SEC XBRL report redaction/residual scan:
  - PASS: `44` SEC-like reports; `0` raw identity/path/SEC URL/accession hits;
    `0` nonzero residual-magnitude hits.
- `git diff --check`
  - PASS.

No Python runtime, diagnostic, report, or test file was touched by this
docs-only pass, so full SEC XBRL suite and `py_compile` were not required for
the branch-local diff.
