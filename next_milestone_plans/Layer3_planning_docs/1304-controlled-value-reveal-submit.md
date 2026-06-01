# 1304 - SEC XBRL Controlled Value-Reveal Submit

Milestone: `sec_xbrl_controlled_value_reveal_submit_v1_tier2_risk_assessed_implementation`

Base authority: `project6-origin/main` at `ddcab8771ebecfdd33b78a077bc461a37edc7d90`

Merged authority: `project6-origin/main` at `d9e55ceebf87de8a42bfe3475debbd0ff452a19f`

Prior milestone: `next_milestone_plans/Layer3_planning_docs/1303-controlled-value-reveal-submit-design.md`

## Status

Merged current-main Tier-2 risk-assessed implementation entry.

This slice implements only a server-owned controlled reveal-submit boundary
behind a default-off feature flag. It returns controlled values transiently from
an already-prepared SEC XBRL value-reveal authority receipt and records only a
hash/count audit receipt. It does not add rendered value UI, default-on
behavior, source acquisition, live SEC network, Arelle subprocess invocation,
delivery/export, provider dispatch, raw runtime artifacts, production readiness,
or final financial-statement semantics.

## Tier-2 Surfaces

Touched Tier-2 surfaces:

- `backend/app/models/models.py`: adds
  `L3SecXbrlControlledValueRevealSubmitReceipt`.
- `backend/alembic/versions/0045_layer3_sec_xbrl_controlled_value_reveal_submit.py`:
  adds one additive hash/count submit receipt table and indexes.
- `backend/app/api/layer3.py`: adds
  `POST /api/v1/layer3/sec-xbrl/value-reveal/submit` and a hash/count-only
  submit-status route.
- `backend/app/services/layer3_sec_xbrl_controlled_value_reveal_submit.py`:
  owns authority-receipt-bound reveal submit and status projection.
- `backend/app/core/config.py`: adds the default-off
  `LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED` flag.

Supporting surfaces:

- `backend/tests/test_sec_xbrl_operator_review_workflow.py`: adds focused
  service/API/model/migration/fail-closed proof.
- Layer 3 progress/proof manifests and board record the implementation
  boundary.

## Authority Boundary

The browser supplies only:

- `client_request_id`;
- `submit_mode=sec_xbrl_controlled_value_reveal_submit_v1`;
- `operator_decision=submit_explicit_sec_xbrl_value_reveal_from_authority_receipt`;
- `sec_xbrl_value_reveal_authority_receipt_id`;
- `authority_basis_hash`;
- `operator_reveal_confirmation=true`;
- optional `max_records`, capped by the server.

The browser cannot supply raw sidecar receipt ids, sidecar hashes, dataset ids
or hashes, value-store hashes, paths, URLs, accessions, CIKs, tickers, contacts,
source acquisition fields, Arelle fields, delivery/export fields, UI authority,
or default-on fields.

The server resolves:

- the authority receipt by id and authority basis hash;
- decision/workflow/statement-packet/projection/dataset lineage;
- sidecar receipt and internal value store from persisted authority hashes;
- transient reveal records from the sidecar-bound internal value store.

## Persistence And Containment

The submit receipt stores only ids, hashes, counts, policy/state, inventory
hashes, summary metadata, and negative-invariant flags. It does not persist raw
values, raw identity values, raw sidecar receipt ids, local paths, accessions,
CIKs, operator contacts, SEC URLs, delivery locations, or revealed fact payloads.

The submit response may return controlled values transiently. Identity-like
values, accessions, SEC URLs, emails, local paths, CIK-like values, and
period-date-like values are redacted before response. The status route returns
no revealed facts and omits lower-level sidecar/dataset/projection lineage ids.

Rollback/containment:

- migration is additive;
- downgrade removes only the new submit receipt indexes and table;
- failed authority, sidecar, value-store, redaction, cap, or receipt-write
  checks create no partial submit receipt;
- replay by the same authority basis returns the existing receipt metadata and
  recomputed transient response;
- conflicting request or authority basis fails closed;
- feature flag remains default-off and default-on admission is not claimed.

## Verification

Branch-local results:

- `python -m pytest .\backend\tests\test_sec_xbrl_operator_review_workflow.py -q`
  - `68 passed, 3 warnings`
- `python -m py_compile` on touched Python and migration files
  - PASS
- `python -m pytest` over `backend/tests/test_sec_xbrl*.py`
  - `295 passed, 4 warnings`
- `python .\tools\l3-target-selection-validate.py --expect frozen`
  - PASS
- `python .\tools\l3-progress-check.py`
  - PASS
- JSON validation with `utf-8-sig` for progress/proof manifests plus SEC XBRL
  report JSON
  - PASS
- Redaction scan across committed SEC XBRL report JSON
  - PASS
- Residual-magnitude regression scan against `project6-origin/main`
  - PASS; no committed SEC XBRL report JSON changed in this branch
- `git diff --check`
  - PASS

Post-merge current-main results at `d9e55ceebf87de8a42bfe3475debbd0ff452a19f`:

- focused operator-review workflow test
  - `68 passed, 3 warnings`
- full SEC XBRL suite
  - `295 passed, 4 warnings`
- target-selection frozen check, progress check, touched-file `py_compile`,
  manifest/report JSON validation, redaction scan, residual-magnitude
  regression scan, and `git diff --check`
  - PASS

## Next Posture

After this implementation has landed and current-main verification remains clean, the
next safe posture is a read-only post-merge audit and then a separate rendered
value UI or default-on design only if explicitly admitted. This slice does not
admit rendered values or default-on behavior.
