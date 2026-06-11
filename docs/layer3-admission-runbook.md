# Layer 3 SEC/XBRL Nonlocal Production Admission Runbook

Single ordered operator runbook for SEC/XBRL Layer 3 nonlocal production admission.

---

## 1. What the gate is

There are two distinct gate mechanisms.  They serve different purposes and read
from different locations.

### 1a. Runtime evaluator (`evaluate_production_admission`)

Source: `backend/app/services/layer3_sec_xbrl_production_admission.py`

The runtime evaluator is called inside the running application.  It evaluates
seven ordered criteria against an `evidence` mapping provided by the calling
route handler.  It returns `production_admission_ready=True` if and only if:

1. `SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED` flag is explicitly `true`
   at call time (checked via `production_admission_flag_enabled()`), AND
2. Every one of the seven admission criteria returns `passed=True`.

**The seven criteria** (evaluated in order; first failing criterion determines
`production_admission_blocked_reason`):

| # | Criterion key | Evidence keys required | Failure token |
|---|---|---|---|
| 1 | `corpus_validation_passed_with_ownership` | `corpus_validation_passed=True`, `ownership_marker_present=True` | `corpus_validation_or_ownership_missing` |
| 2 | `companyfacts_oracle_coverage_quorum` | `companyfacts_oracle_supplied=True`, `oracle_mismatch_count=0`, `oracle_confirmed_count>=1`, `oracle_total_count>0`, confirmed/total >= 0.5 | `companyfacts_oracle_coverage_or_mismatch_failed` |
| 3 | `operator_decision_approved_ready_for_next_freeze` | `review_decision="approved"`, `decision_reason_code="ready_for_next_freeze"` | `operator_decision_not_approved_ready` |
| 4 | `value_reveal_authority_receipt_valid` | `value_reveal_authority_eligible=True`, `value_reveal_authority_receipt_id` nonempty str | `value_reveal_authority_not_valid` |
| 5 | `no_honesty_invariant_violation` | `honesty_invariant_violation=False`, `raw_leak_detected=False` (both keys must be present) | `honesty_invariant_unverified_or_violated` |
| 6 | `containment_invariants_held` | `production_database_touched=False`, `runtime_default_changed=False`, `value_reveal_performed=False`, `delivery_export_enabled=False` | `containment_invariants_not_held` |
| 7 | `review_exceptions_zero` | `review_exception_count=0` (int, not bool) | `review_exceptions_present` |

With the flag `OFF` (the default in all current deployments), the evaluator
returns `production_admission_ready=False` unconditionally.

**Current status**: `SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED` must
**never** be set in CI and is not present in the reference compose stack.  The
runtime evaluator is not activated in any current deployed configuration.

### 1b. Diagnostic packet check

Source: `diagnostics/assessment/sec-xbrl-nonlocal-admission-disposition.py`

The diagnostic script is an offline, read-only tool.  It does not change
runtime behaviour and does not activate the evaluator.  It validates two
operator-supplied JSON packet files and reports whether they are admissible for
operator review.

The script reads packets from one of two forms:

```sh
# Named files:
python diagnostics/assessment/sec-xbrl-nonlocal-admission-disposition.py \
    --admission-packet <admission-packet.json> \
    --backfill-disposition <backfill-disposition.json> \
    --output <report.json>

# Directory (canonical filenames):
python diagnostics/assessment/sec-xbrl-nonlocal-admission-disposition.py \
    --packet-dir <packet-directory> \
    --output <report.json>
```

When `--packet-dir` is used, the script expects exactly:
- `sec-xbrl-final-admission-packet.json`
- `sec-xbrl-backfill-disposition-packet.json`

Both files must be present in the directory.  `--packet-dir` cannot be combined
with `--admission-packet` or `--backfill-disposition`.

The script also reads a previously-generated readiness gate report:
`diagnostics/assessment/sec-xbrl-nonlocal-production-readiness-gate-report.json`.
That report must be current before packets can be admitted.

---

## 2. Pre-admission ordered steps

Complete these in order before preparing packets.

1. **Confirm the readiness gate is current.**  The nonlocal readiness gate
   report (`diagnostics/assessment/sec-xbrl-nonlocal-production-readiness-gate-report.json`)
   must have `decision="nonlocal_production_readiness_blocked"` with
   `blocking_reasons=["nonlocal_production_readiness_final_admission_missing"]`
   and `next_slice` equal to the admission target.  If the report is stale or
   absent, re-run the readiness diagnostic first.

2. **Confirm route atomicity evidence is current.**  The admission disposition
   script verifies that `backend/app/services/layer3_sec_xbrl_auth_binding.py`
   contains `require_sec_xbrl_owner_binding`, `sec_xbrl_auth_binding_missing`,
   `sec_xbrl_auth_binding_context_mismatch`, and `compatible_policy_hashes`;
   and that the API and tests contain the required atomicity/fail-closed
   evidence tokens.  These are read from the files at the time the script runs
   — no action needed if those files are current.

3. **Confirm standing non-admissions are preserved.**  The readiness gate report
   must carry all nine `non_goals_preserved` flags as `false` (no source
   acquisition, no Arelle subprocess, no value reveal, no export/delivery, no
   historical backfill performed, no production readiness claimed, etc.).

4. **Prepare evidence files.**  Gather the physical evidence files that will be
   hashed into the packets.  See section 3 for the per-field breakdown.

5. **Fill admission packets.**  Use `tools/l3-admission-packet-hashes.py` to
   fill hash fields (section 4).  Human-only fields must be filled by the
   authorised operator directly.

6. **Run the diagnostic gate check.**  See section 4.

---

## 3. Per-field breakdown: agent/tooling-preparable vs HUMAN-ONLY

### 3a. Final admission packet
Template: `next_milestone_plans/Layer3_planning_docs/sec-xbrl-final-admission-packet-template.json`

| Field | Who fills it | Notes |
|---|---|---|
| `admission_mode` | Agent/tooling | Fixed value: `nonlocal_in_app_auth_final_admission` |
| `admission_owner_ref` | **HUMAN-ONLY** | Redacted kebab-case ref to the admission owner record |
| `approval_record_ref` | **HUMAN-ONLY** | Redacted kebab-case ref to the approval record artifact |
| `approval_record_hash` | `l3-admission-packet-hashes.py fill` | SHA-256 of approval record file bytes |
| `in_app_auth_evidence_ref` | **HUMAN-ONLY** | Redacted kebab-case ref to the in-app auth evidence artifact |
| `in_app_auth_evidence_hash` | `l3-admission-packet-hashes.py fill` | SHA-256 of in-app auth evidence file bytes |
| `auth_binding_evidence_ref` | **HUMAN-ONLY** | Redacted kebab-case ref to the auth binding evidence artifact |
| `auth_binding_evidence_hash` | `l3-admission-packet-hashes.py fill` | SHA-256 of auth binding evidence file bytes |
| `rollback_owner_ref` | **HUMAN-ONLY** | Redacted kebab-case ref to the rollback owner |
| `incident_owner_ref` | **HUMAN-ONLY** | Redacted kebab-case ref to the incident owner |
| `redaction_policy_id` | Agent/tooling | Fixed value: `sec_xbrl_nonlocal_admission_disposition_redaction_v1` |
| `verification_run_ref` | **HUMAN-ONLY** | Redacted kebab-case ref to the verification run record |
| `admission_provenance_ref` | **HUMAN-ONLY** | Redacted kebab-case ref to the admission provenance artifact |
| `admission_provenance_hash` | `l3-admission-packet-hashes.py fill` | SHA-256 of admission provenance file bytes |

**CRITICAL**: Fabricating human-only fields (writing placeholder refs without
corresponding real approval records, rollback owners, or incident owners)
invalidates admission.  The diagnostic script enforces the redacted-ref format
(`lowercase-kebab-case-ref-<token>`) and runs a full redaction scan — but format
compliance is not a substitute for real authority.

### 3b. Backfill disposition packet
Template: `next_milestone_plans/Layer3_planning_docs/sec-xbrl-backfill-disposition-packet-template.json`

| Field | Who fills it | Notes |
|---|---|---|
| `disposition_mode` | **HUMAN-ONLY** | One of three allowed modes; operator determines based on `unbound_receipt_count` |
| `disposition_owner_ref` | **HUMAN-ONLY** | Redacted kebab-case ref to the disposition owner record |
| `disposition_record_ref` | **HUMAN-ONLY** | Redacted kebab-case ref to the disposition record artifact |
| `disposition_record_hash` | `l3-admission-packet-hashes.py fill` | SHA-256 of disposition record file bytes |
| `historical_inventory_ref` | **HUMAN-ONLY** | Redacted kebab-case ref to the historical inventory artifact |
| `historical_inventory_hash` | `l3-admission-packet-hashes.py fill` | SHA-256 of historical inventory file bytes |
| `unbound_receipt_count` | **HUMAN-ONLY** | Integer count of historical unbound receipts; determines disposition mode |
| `backfill_required` | **HUMAN-ONLY** | Boolean; must be consistent with `disposition_mode` and `unbound_receipt_count` |
| `backfill_authority_ref` | **HUMAN-ONLY** | Redacted kebab-case ref to backfill authority (required even when no backfill needed) |
| `backfill_authority_hash` | `l3-admission-packet-hashes.py fill` | SHA-256 of backfill authority file bytes |
| `containment_policy_ref` | **HUMAN-ONLY** | Redacted kebab-case ref to containment policy artifact |
| `containment_policy_hash` | `l3-admission-packet-hashes.py fill` | SHA-256 of containment policy file bytes |
| `redaction_policy_id` | Agent/tooling | Fixed value: `sec_xbrl_nonlocal_admission_disposition_redaction_v1` |
| `verification_run_ref` | **HUMAN-ONLY** | Redacted kebab-case ref to the verification run record |
| `disposition_provenance_ref` | **HUMAN-ONLY** | Redacted kebab-case ref to the disposition provenance artifact |
| `disposition_provenance_hash` | `l3-admission-packet-hashes.py fill` | SHA-256 of disposition provenance file bytes |

Disposition mode rules enforced by the diagnostic script:
- `no_historical_unbound_receipts`: requires `unbound_receipt_count=0` and `backfill_required=false`
- `historical_unbound_receipts_fail_closed_pending_backfill`: requires `unbound_receipt_count>0` and `backfill_required=true`
- `historical_unbound_receipts_backfill_authorized`: requires `unbound_receipt_count>0` and `backfill_required=true`

### 3c. Ref format

All `*_ref` fields must match the redacted-ref pattern:
`<lowercase-word>[-<word>]*-ref-<token>[-<token>]*`

They must not contain: operator email addresses, issuer identities, accession
numbers, CIK values, SEC URLs, local file paths, period dates, raw decimal
values, or raw financial payload data.

---

## 4. Hash tool usage

```sh
# Step 1: compute hashes to preview (optional sanity check):
python tools/l3-admission-packet-hashes.py compute \
    path/to/approval_record.pdf \
    path/to/auth_evidence.json

# Step 2: fill hash fields in the admission template:
python tools/l3-admission-packet-hashes.py fill \
    --packet next_milestone_plans/Layer3_planning_docs/sec-xbrl-final-admission-packet-template.json \
    --out sec-xbrl-final-admission-packet.json \
    --field approval_record_hash:path/to/approval_record.pdf \
    --field in_app_auth_evidence_hash:path/to/auth_evidence.json \
    --field auth_binding_evidence_hash:path/to/binding_evidence.json \
    --field admission_provenance_hash:path/to/provenance.json

# Step 3: manually fill remaining human-only fields in sec-xbrl-final-admission-packet.json

# Step 4: verify hashes after editing:
python tools/l3-admission-packet-hashes.py verify \
    --packet sec-xbrl-final-admission-packet.json \
    --field approval_record_hash:path/to/approval_record.pdf \
    --field in_app_auth_evidence_hash:path/to/auth_evidence.json \
    --field auth_binding_evidence_hash:path/to/binding_evidence.json \
    --field admission_provenance_hash:path/to/provenance.json
```

The `fill` command:
- Removes `_template_note` (the diagnostic script reports it as `unexpected_packet_field`).
- Refuses to overwrite an existing output file.
- Leaves all non-hash fields untouched.

---

## 5. Packet placement and gate re-run

Completed packets must be placed either:

- At named paths passed directly to the diagnostic script via `--admission-packet`
  and `--backfill-disposition`, or
- In a directory passed via `--packet-dir`, using the canonical filenames:
  `sec-xbrl-final-admission-packet.json` and
  `sec-xbrl-backfill-disposition-packet.json`.

Packets are operator-supplied and are **not committed to the repository**.

### Re-run the gate check:

```sh
# Using --packet-dir:
python diagnostics/assessment/sec-xbrl-nonlocal-admission-disposition.py \
    --packet-dir <packet-directory> \
    --output diagnostics/assessment/sec-xbrl-nonlocal-admission-disposition-report.json

# Or with explicit file paths:
python diagnostics/assessment/sec-xbrl-nonlocal-admission-disposition.py \
    --admission-packet sec-xbrl-final-admission-packet.json \
    --backfill-disposition sec-xbrl-backfill-disposition-packet.json \
    --output diagnostics/assessment/sec-xbrl-nonlocal-admission-disposition-report.json
```

A successful run produces a report with:
```json
"decision": "nonlocal_production_admission_disposition_ready_for_operator_review"
```

A blocked run produces:
```json
"decision": "nonlocal_production_admission_disposition_blocked"
```

with `blocking_reasons` listing the failing criteria.  Address each blocker
and re-run until the decision is `ready_for_operator_review`.

---

## 6. Corpus validation receipt dependency

The runtime evaluator criterion `corpus_validation_passed_with_ownership`
(criterion 1) requires corpus validation receipts to exist in the running
container's storage volume.

Receipt storage location (within the container):
```
<STORAGE_DIR>/layer3-sec-edgar-real-company-corpus-validation/receipts/*.json
```

Source constant: `RECEIPT_DIR = "layer3-sec-edgar-real-company-corpus-validation"`
(defined in `backend/app/services/layer3_sec_edgar_real_company_corpus_validation.py`).

`STORAGE_DIR` defaults to `/app/app/storage` in-container
(from `Dockerfile.app`: `WORKDIR /app`, default storage resolves to `/app/app/storage`).

**Current state**: The reference compose stack persists app storage in the
`app_storage` named volume (mounted at `/app/app/storage` in the container).
Named volumes inherit image-side content and ownership on first mount — the
image creates and chowns `/app/app/storage` to uid 1001 (`appuser`) during the
build.  Because the volume is named (not a bind-mount), it survives container
restarts and upgrades.

**Implication for admission**: Corpus validation receipts generated during a
prior validation run inside the container are preserved in `app_storage` across
restarts.  A fresh deploy with an empty `app_storage` volume has no receipts;
corpus validation must be run inside the deployed container before the runtime
evaluator can satisfy criterion 1.

The diagnostic packet check does not read or verify receipt presence — it is
purely a document/authority check.  Receipt presence is only required at the
moment the runtime evaluator is called (when the evaluator flag is enabled).
