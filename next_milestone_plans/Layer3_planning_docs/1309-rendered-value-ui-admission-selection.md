# 1309 - SEC XBRL Rendered Value UI Admission Selection

Milestone: `sec_xbrl_rendered_controlled_value_reveal_ui_admission_selection_v1`

Base authority: `project6-origin/main` at `45e5a087b83b092e70abf3b4ee7dc6da41f77f64`

Prior milestone: `next_milestone_plans/Layer3_planning_docs/1308-controlled-submit-post-merge-audit-closure.md`

Merged authority: PR `#2053` at `23189d47abf9d7f20e98075e29ea9f3df69683d6`

## Status

Merged current-main Tier-2 risk-assessed design/admission-selection entry,
verified after merge. This pass changes no runtime behavior.

## Selection

Select rendered controlled value-reveal UI as the next admissible SEC XBRL
implementation boundary.

Do not select default-on behavior, export/delivery, or production readiness as
the next implementation boundary. Those gates remain downstream because they
either broaden the reveal beyond an explicit operator interaction, create an
exfiltration/delivery surface, or require system-level auth, retention,
monitoring, rollback, and operating policy that this slice does not implement.

## Evidence

Current main already contains the server-side controlled value-reveal sequence:

- `POST /api/v1/layer3/sec-xbrl/value-reveal/authority/prepare` creates a
  server-owned value-reveal authority receipt from an approved operator-review
  decision and returns no values.
- `POST /api/v1/layer3/sec-xbrl/value-reveal/submit` accepts only authority
  receipt id, authority basis hash, explicit operator reveal confirmation, and
  an optional server-capped `max_records`.
- `GET /api/v1/layer3/sec-xbrl/value-reveal/submit/status/{...}` returns the
  submit receipt/status surface without revealed facts.
- 1304 through 1308 record post-merge verification and hardening for authority
  ids, status ids, raw/local reference rejection, no partial receipts after
  failed validation, default-off posture, and non-admission of rendered value UI,
  export/delivery, default-on behavior, and production readiness.

Current rendered workbench proof still blocks value reveal:

- `e2e/layer3-workbench.spec.js` asserts
  `#sec-xbrl-value-reveal-submit` has count `0` on the existing SEC XBRL
  operator-review status and decision controls.
- The same rendered decision proof asserts `data-value-reveal-enabled="false"`,
  `data-delivery-export-enabled="false"`, and
  `data-runtime-default-enabled="false"`.

That means the next value-producing movement should be a bounded rendered
operator control over the already-admitted server sequence, not default-on or
export.

## Future Implementation Boundary

The next code-bearing slice may add a rendered SEC XBRL value-reveal panel to
`/review/layer3` over existing APIs only:

1. prepare value-reveal authority from:
   - `client_request_id`;
   - `authority_mode=sec_xbrl_value_reveal_authority_receipt_v1`;
   - `operator_decision=prepare_sec_xbrl_value_reveal_authority`;
   - `sec_xbrl_operator_review_decision_id`;
   - `decision_basis_hash`;
   - optional bounded operator attestation that the backend hashes and rejects
     if raw contact/value/reference-like text is supplied;
2. submit explicit controlled value reveal from:
   - `client_request_id`;
   - `submit_mode=sec_xbrl_controlled_value_reveal_submit_v1`;
   - `operator_decision=submit_explicit_sec_xbrl_value_reveal_from_authority_receipt`;
   - `sec_xbrl_value_reveal_authority_receipt_id`;
   - `authority_basis_hash`;
   - `operator_reveal_confirmation=true`;
   - optional `max_records`, still server-capped;
3. inspect submit status from:
   - `sec_xbrl_controlled_value_reveal_submit_receipt_id` only.

The browser must not supply sidecar receipt ids, sidecar hashes, dataset ids,
dataset hashes, value-store hashes, raw values, raw resolved fact authorities,
accessions, CIKs, issuer identities, period dates, local paths, SEC URLs,
source-acquisition fields, Arelle fields, export/delivery fields, default-on
fields, or production-readiness fields.

The panel may render transient controlled values returned by the submit
response only after the backend returns them. It must keep the status projection
read-only and value-free.

## Stop Conditions

Stop before implementation if any proposed slice requires:

- new `models.py`, Alembic, schema, or durable persistence;
- API changes outside the existing authority prepare, controlled submit, and
  submit-status routes;
- frontend durable authority or browser-side reconstruction of server authority;
- default-on behavior, automatic reveal, batch reveal, pagination, export,
  delivery, source acquisition, Arelle invocation, provider/connector dispatch,
  raw runtime artifacts, or production-readiness claims;
- value rendering from local browser state rather than the backend response;
- operator identity/authentication claims that are not implemented and tested.

## Required Future Proof

The later implementation PR must prove:

- controls stay disabled until required ids/hashes and explicit confirmation are
  present;
- request payloads include only the admitted fields above;
- authority prepare errors clear or withhold raw operator attestation text;
- controlled submit renders only backend-returned controlled values and does
  not render accessions, CIKs, issuer identity, period dates, SEC URLs, local
  paths, operator contacts, sidecar ids, value-store ids, residual magnitudes,
  export fields, default-on fields, source-acquisition fields, or Arelle fields;
- status inspection renders no revealed facts;
- feature flags/defaults remain off;
- no export/delivery, default-on behavior, source acquisition, Arelle invocation,
  production-readiness, or final financial-statement semantics are admitted;
- focused backend/API tests and headed/headless Playwright proof pass;
- committed reports/manifests pass JSON validation, redaction scan,
  residual-magnitude scan, target-selection frozen check, progress check, and
  `git diff --check`.

## Verification

PR and post-merge current-main docs-only admission-selection verification:

- `python .\tools\l3-target-selection-validate.py --expect frozen`
  - PASS
- `python .\tools\l3-progress-check.py`
  - PASS
- JSON parse with `utf-8-sig`
  - PASS for `next_milestone_plans/layer3_progress_manifest.json` and
    `next_milestone_plans/layer3_workbench_proof_manifest.json`
- `git diff --check`
  - PASS

## Next Posture

Implement the bounded rendered controlled value-reveal UI proof over the
existing backend authority/submit/status APIs. Keep default-on behavior,
export/delivery, and production readiness deferred until after rendered
operator proof is landed and verified.
