# 1321 - SEC XBRL Nonlocal In-App Auth Design

Milestone: `sec_xbrl_nonlocal_in_app_auth_design_v1`

Base authority: `project6-origin/main` at
`236bd1a2d78f637d40a0d31fd46d2f3d410441be`

Prior milestone:
`sec_xbrl_nonlocal_deployment_authority_packet_or_in_app_auth_boundary_v1`

## Status

Branch-local docs-only Tier-2 design/pre-review entry.

This pass selects the in-app auth fork because no admissible redacted
deployment authority packet was found in the repo or the inspected operator
sandbox. It does not implement auth, middleware, API dependencies, schema,
`models.py`, Alembic migrations, durable persistence, UI, operator workflow,
source acquisition, Arelle execution, value reveal, export/delivery, runtime
defaults, provider dispatch, raw artifacts, redaction-posture changes, or a
production-readiness claim.

## Claim Ledger

Repo-confirmed:

- `diagnostics/assessment/sec-xbrl-nonlocal-production-readiness-gate-report.json`
  emits `decision: nonlocal_production_readiness_blocked` with
  `blocking_reasons: [nonlocal_production_readiness_authority_packet_missing]`.
- `backend/app/core/config.py` requires nonlocal deployments to use explicit
  HTTPS origins, `AUTH_OWNER=proxy`, `TRUSTED_PROXY_MODE=true`, a nonblank
  proxy identity header, safe storage exposure, and explicit Arelle nonlocal
  authorization when fact-authority cutover is enabled.
- `backend/tests/test_layer3_api.py` proves those nonlocal configuration
  guardrails fail closed and that direct storage is not mounted in nonlocal
  mode.
- `next_milestone_plans/Layer3_planning_docs/116_SECURITY_SOURCE_DELIVERY_BOUNDARY_FREEZE.md`
  records that repo-live configuration expects a proxy-owned trust posture,
  but inspected code does not itself prove request-level operator
  authentication for Layer 3.
- Existing Candidate B workflow code provides a useful local precedent:
  `backend/app/services/layer3_candidate_b_operator_workflow_access_policy.py`
  derives hash-only actor/workspace refs from server request context, rejects
  caller-supplied auth/security/raw identity fields, checks role-to-route
  allowlists, enforces owner bindings, and emits redacted audit events.
- Current SEC XBRL protected surfaces in `backend/app/api/layer3.py` include
  operator-review workflow status, decision submit/status, value-reveal
  authority prepare, controlled value-reveal submit, and controlled value-reveal
  submit status.

Carried-forward and still current unless a later implementation changes it:

- value reveal remains explicit and controlled, not default-on;
- export/delivery is a separate exfiltration-class gate;
- source acquisition, corpus-validation Arelle execution, and provider
  dispatch remain separately blocked;
- final financial-statement semantics and cross-company comparability remain
  non-admitted.

Inference:

- A proxy-header-only policy is not enough to admit nonlocal production
  readiness unless a deployment authority packet also proves direct FastAPI
  bypass prevention and trusted header injection. Without that packet, the next
  admissible path is repo-owned in-app auth design and later implementation
  proof.

## Branch Selection Evidence

The authority-packet fork was checked first. The operator-provided
`sandbox_temp` directory exists outside the repo, but a targeted search for
`sec_xbrl_nonlocal_deployment_authority`,
`deployment_owner_ref`, `approval_record_hash`, `verification_run_ref`,
`arelle_fact_authority_nonlocal_authorized`, `repo_owned_in_app_auth`, and
`trusted_external_proxy` found no JSON, Markdown, or text authority packet
matching the readiness gate fields.

Therefore this pass selects the in-app auth fork. That selection is not a
production-readiness admission; it is the next governance/design artifact
needed before implementation.

## Selected Auth Mode

Selected mode:
`sec_xbrl_repo_owned_in_app_operator_auth_boundary_v1`.

The future runtime contract is:

- derive an operator principal from server-owned in-app auth context, not from
  JSON payload fields or browser-local state;
- reduce principal identity to stable hash-only actor and workspace refs before
  it enters SEC XBRL services, receipts, reports, or logs;
- reject caller-supplied auth, security, raw identity, proxy header, local path,
  URL, token, secret, value-store, source-acquisition, default-on, or
  export/delivery override fields;
- check a role-to-route allowlist before any SEC XBRL protected surface
  performs a read or write;
- bind mutating authority receipts to the hash-only owner/workspace identity
  that admitted the action, or explicitly stop if existing receipt tables cannot
  represent that binding without a separate schema/persistence pass;
- emit only redacted policy decisions and audit refs, never raw names, emails,
  tokens, headers, local paths, SEC identifiers, raw values, or residual
  magnitudes;
- keep value reveal, export/delivery, source acquisition, Arelle execution, and
  production readiness as separate gates even after auth exists.

This selected mode may interoperate with an external proxy later, but proxy
headers are only trusted when either a deployment authority packet proves the
proxy boundary or a repo-owned in-app verifier normalizes the identity before
SEC XBRL code sees it. A future implementation must not treat arbitrary
client-supplied `X-Forwarded-*` headers as authentication.

## Protected SEC XBRL Route Families

The future policy should protect these route families as one central map rather
than per-route ad hoc checks:

| Route family | Current route | Required role posture |
| --- | --- | --- |
| `sec_xbrl_operator_review_workflow_status_read` | `POST /api/v1/layer3/sec-xbrl/operator-review/workflow/status` | owner or auditor, redacted read only |
| `sec_xbrl_operator_review_decision_submit_write` | `POST /api/v1/layer3/sec-xbrl/operator-review/workflow/decision/submit` | owner only, receipt-bound |
| `sec_xbrl_operator_review_decision_status_read` | `POST /api/v1/layer3/sec-xbrl/operator-review/workflow/decision/status` | owner or auditor, redacted read only |
| `sec_xbrl_value_reveal_authority_prepare_write` | `POST /api/v1/layer3/sec-xbrl/value-reveal/authority/prepare` | owner only, explicit value-reveal authority intent |
| `sec_xbrl_controlled_value_reveal_submit_write` | `POST /api/v1/layer3/sec-xbrl/value-reveal/submit` | owner only, explicit reveal confirmation, authority receipt bound |
| `sec_xbrl_controlled_value_reveal_submit_status_read` | `GET /api/v1/layer3/sec-xbrl/value-reveal/submit/status/{id}` | owner only if the response can include revealed value payload; otherwise auditor read may be admitted only for redacted status metadata |

Future default-on, nonlocal-readiness, source-acquisition, Arelle execution,
export/delivery, provider dispatch, and production-readiness surfaces remain
outside this route-family map until separate gates admit them.

## Owner Binding And Persistence Boundary

Repo-confirmed current SEC XBRL routes already create and inspect durable
operator-review, value-reveal authority, and controlled-submit receipts. This
design does not modify those tables.

The next implementation must choose one of two owner-binding strategies before
claiming route-level authorization:

1. Add hash-only owner/workspace binding fields to the relevant SEC XBRL
   receipt tables through additive Tier-2 migrations; or
2. Add a separate hash-only auth binding receipt/table keyed by existing SEC
   XBRL receipt ids and basis hashes.

Either strategy requires schema/persistence work and therefore cannot be
implemented under this docs-only pass. Until one strategy lands, auth design can
prove role gating and request-field rejection, but it cannot claim complete
cross-owner isolation for already-persisted SEC XBRL receipts.

## Negative Test Obligations

A later implementation or validate-only policy harness must include focused
negative proof for:

- anonymous request denied on every protected SEC XBRL family;
- missing, empty, malformed, or stale auth context denied;
- spoofed JSON auth/security/raw identity fields denied;
- direct proxy-header spoofing denied unless a trusted boundary is proven;
- unauthorized role denied per route family;
- auditor role denied for mutating decision, value-reveal authority, and
  controlled-submit routes;
- cross-owner receipt id or basis hash denied when owner binding exists;
- stale policy hash or contradictory receipt authority denied;
- value-reveal submit status does not leak raw values to auditor-only status
  access if auditor status is ever admitted;
- auth audit output contains only hashes, policy ids, status codes, and refs.

## Verification Plan

The next safest pass is
`sec_xbrl_nonlocal_in_app_auth_policy_validation_v1`: a validate-only
diagnostic/test harness that proves the selected policy map, forbidden fields,
negative cases, and redaction outputs without wiring runtime dependencies into
SEC XBRL routes yet.

Only after that validation pass should a separate Tier-2 implementation decide
whether to add API dependencies, middleware, config expansion, owner-binding
schema, audit persistence, or route enforcement.

Minimum verification for any implementation:

- focused SEC XBRL auth-policy unit tests over the central policy service;
- API tests for all protected route families under anonymous, malformed,
  spoofed, unauthorized, and authorized contexts;
- migration upgrade/downgrade or containment notes if owner binding touches
  schema/persistence;
- full `backend/tests/test_sec_xbrl*.py` suite if runtime/test files change;
- `python ./tools/l3-target-selection-validate.py --expect frozen`;
- `python ./tools/l3-progress-check.py`;
- JSON/report validation for changed manifests and committed reports;
- redaction and residual-magnitude scan over committed SEC XBRL reports;
- `git diff --check`.

## Stop Conditions

Stop before implementation if the next pass would require any of the following
without a separate explicit implementation instruction:

- runtime auth dependency or middleware changes;
- `AUTH_OWNER` value expansion or nonlocal deployment config changes;
- SEC XBRL route behavior changes;
- schema, `models.py`, Alembic, owner-binding persistence, or audit persistence;
- value reveal default-on, automatic value delivery, or raw value-store
  default-on;
- source acquisition, live SEC network execution, or Arelle subprocess
  invocation;
- export/delivery, provider dispatch, public URL, or destination selection;
- production-readiness claim;
- raw identity, accessions, SEC URLs, local paths, raw values, or residual
  magnitude artifacts.

## Branch-Local Verification

Docs-only verification on branch `codex/secxbrl-in-app-auth-design`:

- Focused nonlocal/default-on API tests:
  `python -m pytest ./backend/tests/test_layer3_api.py -q -k
  "deployment_profile or default_arelle_cutover or arelle_sidecar or
  default_on or value_reveal"`
  - PASS: `27 passed, 249 deselected, 3 warnings`.
- Full SEC XBRL suite:
  `python -m pytest <28 backend/tests/test_sec_xbrl*.py files> -q`
  - PASS: `322 passed, 4 warnings`.
- `python ./tools/l3-target-selection-validate.py --expect frozen`
  - PASS.
- `python ./tools/l3-progress-check.py`
  - PASS.
- Changed JSON parse:
  - PASS.
- Committed SEC XBRL report redaction/residual scan:
  - PASS: `56` SEC-like reports; `0` raw identity/path/SEC URL/accession
    hits; `0` nonzero residual-magnitude hits.
- `git diff --check`
  - PASS.
- `py_compile`
  - Not applicable: no Python runtime, diagnostic, report, or test file was
    touched by this docs-only pass.
