# 1302 - SEC XBRL Value-Reveal Authority Receipt

Milestone: `sec_xbrl_value_reveal_authority_receipt_v1`

Base authority: `project6-origin/main` at `ad1b2e3e1e5ee94feda0c409d2e35776fca20f32`

Merged authority: `project6-origin/main` at `0ce24f713fd3453e97810d56cfdad4d0176abbed`

Prior milestone: `next_milestone_plans/Layer3_planning_docs/1301-value-reveal-authority-design.md`

## Status

Merged current-main Tier-2 implementation entry.

This slice implements only a server-owned authority receipt that bridges an approved SEC
XBRL operator-review decision to a later explicit value-reveal submit. It does not reveal
values.

## Tier-2 Surfaces

Touched Tier-2 surfaces:

- `backend/app/models/models.py`: adds `L3SecXbrlValueRevealAuthorityReceipt`.
- `backend/alembic/versions/0044_layer3_sec_xbrl_value_reveal_authority_receipt.py`:
  adds one additive authority-receipt table and indexes.
- `backend/app/api/layer3.py`: adds
  `POST /api/v1/layer3/sec-xbrl/value-reveal/authority/prepare`.

Supporting Tier-1/Tier-2-adjacent surfaces:

- `backend/app/services/layer3_sec_xbrl_value_reveal_authority.py`: owns the
  decision-to-authority eligibility predicate.
- `backend/tests/test_sec_xbrl_operator_review_workflow.py`: adds focused model,
  service, API, fail-closed, idempotency, metadata, and migration proof.
- `next_milestone_plans/layer3_progress_manifest.json` and
  `next_milestone_plans/layer3_workbench_proof_manifest.json`: record this branch-local
  implementation boundary.

## Authority Boundary

The browser supplies only:

- `client_request_id`;
- `authority_mode=sec_xbrl_value_reveal_authority_receipt_v1`;
- `operator_decision=prepare_sec_xbrl_value_reveal_authority`;
- `sec_xbrl_operator_review_decision_id`;
- `decision_basis_hash`;
- optional bounded `operator_attestation`, stored only as a hash when present.

The server resolves:

- decision/workflow/statement-packet/projection lineage;
- dataset version hash from `DatasetVersion`;
- sidecar receipt by projection-bound `sidecar_receipt_hash`;
- internal value-store hash from the sidecar receipt.

The receipt stores `sidecar_receipt_id_hash`, not the raw sidecar receipt id. The raw id
is reconstructed only transiently from the server-owned sidecar hash in the authority
service so a later reveal-submit slice can remain server-resolved.

## Eligibility Predicate

The authority receipt requires:

- existing matching operator-review decision;
- `review_decision == "approved"`;
- `decision_reason_code == "ready_for_next_freeze"`;
- clean decision status projection from the existing operator-review workflow service;
- complete decision, workflow, packet, and projection lineage;
- zero workflow, packet, and packet-row review exceptions;
- materialized/redacted packet and projection;
- every projection fact and packet row still value-redacted;
- one projection-bound sidecar hash and one projection-bound value-store hash;
- existing dataset-version authority;
- a READY sidecar receipt with `resolved_fact_projection`;
- matching sidecar-bound internal value-store hash.

Failures create no authority receipt row.

## Rollback And Containment

The migration is additive. Downgrade removes only the new authority receipt indexes and
table.

The receipt is immutable by `client_request_id`, `authority_basis_hash`, and one receipt
per operator-review decision. Replaying the same basis returns the existing receipt.

This slice does not add controlled reveal submit, rendered value UI, default-on behavior,
source acquisition, Arelle invocation, delivery/export, raw runtime artifacts, production
readiness, or financial-statement semantics claims.

If a later slice persists raw sidecar receipt IDs, returns values, stores revealed values,
changes authorization, renders values, or changes defaults, that later slice needs a
separate design and containment plan.

## Verification

Current-main post-merge results:

- `python -m pytest .\backend\tests\test_sec_xbrl_operator_review_workflow.py -q`
  - `61 passed, 3 warnings`
- `$files = (Get-ChildItem -Path .\backend\tests -Filter 'test_sec_xbrl*.py').FullName; python -m pytest $files -q`
  - `288 passed, 4 warnings`
- `python ./tools/l3-target-selection-validate.py --expect frozen`
  - `Layer 3 target-selection validation: PASS (frozen)`
- `python ./tools/l3-progress-check.py`
  - `Layer 3 progress state check: PASS`
- `python -m py_compile` on touched Python files
  - PASS
- JSON validation with `utf-8-sig`
  - changed manifests parse; 53 committed SEC XBRL report JSON files parse
- redaction scan over committed SEC XBRL report JSON files
  - PASS over 53 reports; no raw accession, local path, SEC URL, or email hits
- residual-magnitude scan over committed SEC XBRL report JSON files
  - PASS over 53 reports; no nonzero residual-magnitude hits
- `git diff --check`
  - PASS

## Next Slice

`sec_xbrl_controlled_value_reveal_submit_v1` is the next possible implementation only
after this authority-receipt branch lands and current-main verification is clean. That
future slice must remain explicit, feature-flagged/default-off, server-resolved from the
authority receipt, and separate from rendered value UI or default-on admission.
