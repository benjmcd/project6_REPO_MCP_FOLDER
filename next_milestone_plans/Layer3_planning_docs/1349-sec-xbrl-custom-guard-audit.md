# 1349 SEC XBRL custom guard and redaction audit

Target: `sec_xbrl_custom_guard_redaction_audit_v1`.

Progress registration:

- `next_milestone_plans/layer3_progress_manifest.json` records the audit target
  as a docs-only SEC XBRL guard/redaction tracking milestone;
- `next_milestone_plans/layer3_workbench_proof_manifest.json` records the
  corresponding proof posture and verification gates;
- `next_milestone_plans/layer3_progress_board.md` records the current board
  status and next-posture constraint.

This slice records the post-framework, post-public-authority-guard state of the
remaining SEC XBRL guard and redaction helpers. It landed as design/audit only
in PR #2138, and PR #2168 later landed the exact diagnostic redaction
pass-through cleanup recorded below. The unadmitted-key adapter slice then
extracts the exact service-local `_reject_unadmitted_keys` seam recorded below.
These changes do not migrate custom runtime wrappers, change report bytes,
alter runtime defaults, or authorize the parked activation lane.

## Purpose

Recent consolidation slices migrated the exact-match diagnostic framework,
report leak, raw-value-key, and text-leak helper shapes. The remaining surfaces
are not exact-match duplicates. They combine shared raw/local authority scanning
with service-specific error contracts, blocked-key details, CIK/contact scan
variants, residual-magnitude policy, or diagnostic-only redaction evidence.

Bulk-migrating those surfaces would risk weakening the validate-only,
default-off, redacted-public-output posture. This audit defines the safe
classification and sequencing before further changes.

## Current shared authority surfaces

The current shared surfaces are:

- `diagnostics/assessment/sec_xbrl_diagnostic_framework.py` for diagnostic
  criteria, blocking reasons, decisions, and report/control envelope helpers;
- `backend/app/services/layer3_sec_xbrl_public_authority_guard.py` for
  raw/local authority violation detection and service-local rejection helpers;
- `backend/app/services/layer3_sec_xbrl_report_leak_guard.py` for public report
  object leak flags, text leak flags, raw-value-key flags, and report-leak
  rejection;
- `backend/app/services/layer3_sec_xbrl_canonical_concepts.py` for canonical
  report redaction scan payloads;
- `diagnostics/assessment/sec_xbrl_report_redaction.py` for diagnostic residual
  magnitude stripping.

These shared modules are the authority for further consolidation. New helpers
should extend them only when the existing call-site semantics can be represented
without changing public error shape, report bytes, default posture, or
validate-only behavior.

## Remaining service-family inventory

### Already-delegating service-local wrappers

These wrappers already delegate to the shared public authority guard while
preserving service-local exception classes, error codes, messages, and details:

- `layer3_sec_xbrl_projection_persistence._reject_raw_or_local_authority`;
- `layer3_sec_xbrl_statement_packet_persistence._reject_raw_or_local_authority`;
- `layer3_sec_xbrl_operator_review_workflow._reject_raw_or_local_authority`.

Future work here should not replace the wrappers blindly. Their value is the
service-local public error contract. Only small follow-ups that reduce repeated
wrapper construction without changing those contracts are acceptable.
Projection and statement-packet persistence now opt into exact/contextual CIK
raw-reference detection through the shared guard; operator review workflow keeps
its broader CIK scan. The wrappers remain service-local so their exception
classes, error codes, messages, and details stay stable.

Projection and statement-packet persistence now delegate their common
exact/contextual CIK public-authority scan posture through the shared
`reject_persistence_public_authority` adapter. The adapter does not own service
exception classes, error codes, messages, raw-key sets, or residual-magnitude
policy; those remain caller-owned so persistence behavior stays
service-specific and behavior-preserving.

A separate exact adapter seam in these same service families is now extracted:
`_reject_unadmitted_keys` delegates to the shared `unadmitted_keys` predicate
and raises the service-local exception with `details={"fields": unknown}` via
`layer3_sec_xbrl_public_authority_guard.reject_unadmitted_keys`. The migrated
services are projection persistence, statement-packet persistence, and
operator-review workflow. The slice preserves each service exception class,
error code, message, and details shape; because it touches
persistence/operator workflow services, treat it as Tier-2-shaped even though
it is behavior-preserving.

### Exact unadmitted-key service adapter migrated

The unadmitted-key adapter migration removes only the repeated local
`_reject_unadmitted_keys` helper bodies from:

- `layer3_sec_xbrl_projection_persistence.py`;
- `layer3_sec_xbrl_statement_packet_persistence.py`;
- `layer3_sec_xbrl_operator_review_workflow.py`.

Each service imports the shared helper under the same local
`_reject_unadmitted_keys` name and supplies its service-local exception class,
error code, and message. The shared helper remains a small adapter over
`unadmitted_keys`; it does not alter admitted-field sets, raw/local authority
scans, persistence writes, operator decisions, runtime defaults, or public API
contracts.

The proof obligation for this slice is exact error-shape preservation:
unknown-field failures must continue to raise the service-specific exception
with the same code/message and `details={"fields": [...]}`. It is not a
general service-wrapper consolidation and it does not migrate value-reveal,
E2E, multi-filing, auth-binding, or diagnostic hit-class policies.

### Exact default report-leak service adapter migrated

The offline evidence loader and CompanyFacts oracle packet report guards share
one exact default report-leak posture: `reject_report_leaks` with
`include_raw_value_keys=False`, preserving service-specific error class, code,
and message. That construction now delegates through
`layer3_sec_xbrl_report_leak_guard.reject_report_leaks_with_error`.

This adapter does not migrate proof-capability report leak checks because that
surface enables `include_raw_value_keys=True`. It also does not migrate the
multi-filing response leak check because that surface uses public-text-only
scanning with raw period dates disabled.

### Value-reveal authority family

The value-reveal authority and controlled-submit helpers remain custom because
they split two policies:

- blocked raw authority/value keys reported as `blocked_keys`;
- raw reference text scanned with value-key scans disabled and CIK/operator
  contact variants enabled.

Affected surfaces:

- `layer3_sec_xbrl_value_reveal_authority._reject_raw_or_local_authority`;
- `layer3_sec_xbrl_controlled_value_reveal_submit._reject_raw_or_local_authority`;
- `layer3_sec_xbrl_controlled_value_reveal_submit._value_text_requires_redaction`;
- `layer3_sec_xbrl_controlled_value_reveal_submit._response_has_forbidden_reference`.

Safe next slice, if pursued: extract a value-reveal-family adapter that wraps
the shared guard while preserving `blocked_keys`, HTTP status, exact error
codes, CIK/contact scan variants, and response traversal behavior. Do not merge
it with persistence or E2E guard work.
The value-reveal-family raw/local authority adapter is now extracted in the
shared guard. The authority and controlled-submit services still own their
service-specific exception classes, error codes, messages, and blocked-key
sets, while the shared adapter owns the common CIK/contextual-CIK/operator
contact scan posture.

### E2E output family

The E2E offline orchestrator and integration helpers remain custom because they
protect public output shape, not just raw/local authority text. Their policies
are related but not identical:

- `layer3_sec_xbrl_e2e_offline_orchestrator.py` rejects raw public keys,
  recursively scans nested output, and applies public text-pattern checks;
- `layer3_sec_xbrl_e2e_integration.py` rejects residual magnitude keys,
  projection-private keys, raw reference/public keys, recursively scans nested
  output, and applies public text-pattern checks.

Affected surfaces:

- `layer3_sec_xbrl_e2e_offline_orchestrator._reject_public_raw_or_local_authority`;
- `layer3_sec_xbrl_e2e_offline_orchestrator._reject_public_text_patterns`;
- `layer3_sec_xbrl_e2e_integration._reject_output_raw_or_local_authority`;
- `layer3_sec_xbrl_e2e_integration._reject_public_text_patterns`.

Safe next slice, if pursued: design an output-policy adapter that keeps each
service's existing exception class, error code, field detail, residual policy,
and recursive traversal behavior. Do not route this through a generic
report-leak helper unless field-level errors remain byte/shape-equivalent.
The output-policy helper now exposes default-off exact/contextual CIK scan
options, and the E2E offline/integration wrappers opt into those scans while
preserving their service-specific public-output, residual, period-date, and
field-detail behavior.
The E2E-family public output/text adapters are now extracted in the shared
guard. The offline orchestrator and integration services still own their
exception classes, error codes, messages, raw-output key sets, residual policy,
and period-date scan posture, while the shared adapters own the common
exact/contextual CIK scan posture for E2E public outputs and public text.

### Multi-filing evidence authority gate

The multi-filing gate remains custom because it intentionally scans public
response JSON text with raw period-date scanning disabled and raises a plain
`ValueError` for response leaks.

Affected surface:

- `layer3_sec_xbrl_multi_filing_evidence_authority_gate._reject_response_leaks`.

Safe next slice, if pursued: either keep this local or add a very small
`report_text_leak_flags(..., scan_raw_period_dates=False)` variant only if the
shared helper can preserve the exact current scan set and exception behavior.

### Auth-binding text reference family

Auth binding already uses shared raw/local authority detection but keeps a
narrow receipt-reference policy:

- raw period dates disabled;
- operator contact enabled;
- bare `sec.gov`, Windows paths anywhere, and local segment scans enabled;
- standard local reference scans disabled.

Affected surface:

- `layer3_sec_xbrl_auth_binding._reject_raw_reference`.

No immediate migration is required. Any future change should be limited to
documentation or test strengthening unless a repeated variant emerges.

## Remaining diagnostic redaction inventory

### Exact resolved-fact diagnostic redaction wrappers migrated

The canonical retained-coherence and statement-organization diagnostics now
bind the shared `diagnostic_resolved_fact_redaction_scan_payload` helper
directly under the local `_redaction_scan_payload` name instead of retaining
local wrapper functions:

- `sec-xbrl-canonical-retained-coherence.py` binds the shared helper with the
  retained/total fact-count extra pattern;
- `sec-xbrl-canonical-statement-organization.py` binds the shared helper with
  its resolved-fact ID pattern.

The migration is behavior-preserving: both affected committed reports remain
covered by the data-driven framework byte-stability test and regenerate
byte-identically. It does not migrate diagnostic text/hit-class policies,
service runtime wrappers, value-reveal, E2E, multi-filing, auth-binding,
default-on, or production-readiness behavior.

### Exact pass-through diagnostic wrappers migrated

The following diagnostics now import the shared diagnostic redaction scanner
directly under the local `_redaction_scan_payload` name instead of retaining a
one-line local pass-through wrapper:

- `sec-xbrl-multi-period-projection.py`;
- `sec-xbrl-statement-assembly.py`;
- `sec-xbrl-sector-family-coverage.py`.

The migration is behavior-preserving: the affected committed reports regenerate
byte-identically and no report JSON is changed. This does not migrate any
custom resolved-fact, value-reveal, nonlocal, default-on, or runtime/public
error-surface guard semantics.

Safe next slice, if pursued: keep exact pass-through cleanup separate from
diagnostic-specific policy extraction. If a helper requires custom flags,
blocked-key semantics, exception shape, or report-byte changes, treat it as a
design/audit-first surface rather than an exact-match migration.

### Default-on admission restatement and real corpus runner

These diagnostics use text-level redaction scans over historical or imported
report text:

- `sec-xbrl-default-on-admission-restatement.py`;
- `sec-xbrl-real-corpus-product-runner.py`.

They scan accessions, CIKs, SEC URLs, local paths, operator contact, and raw
decimal magnitude evidence. They should not be migrated into canonical report
redaction without a design that preserves their historical-report semantics.

Safe next slice, if pursued: create a diagnostic text-redaction helper that
accepts explicit regex classes and proves byte-identical committed reports.

### Nonlocal admission/readiness gates

These diagnostics produce redaction hit classes, not boolean report-leak flags:

- `sec-xbrl-nonlocal-admission-disposition.py`;
- `sec-xbrl-nonlocal-production-readiness-gate.py`.

They also inspect `_ref` fields and raw/local authority keys. Their output shape
is part of diagnostic evidence and must remain stable.

Safe next slice, if pursued: only extract a shared hit-class helper if the
ordered hit list remains identical and committed reports are byte-stable.

## Sequencing

Recommended future order:

1. Keep planning/proof authority synchronized with current main before
   starting another migration slice.
2. After the exact `_reject_unadmitted_keys` adapter, continue only with
   service-family-specific guard/redaction migrations when service-local error
   shape can be proven unchanged.
3. Value-reveal-family adapter design and tests, if repeated wrapper risk
   justifies the churn.
4. E2E output-policy adapter design and tests, separately from value reveal.
5. Multi-filing response leak scan variant, only if a text helper can preserve
   `scan_raw_period_dates=False`.
6. Diagnostic text/hit-class helper extraction in byte-stable batches;
   resolved-fact diagnostic redaction wrappers are already migrated.
7. Reassess activation-lane readiness only after the guard/redaction
   consolidation debt is either retired or explicitly accepted.

## Acceptance for future migration slices

Every future slice must prove:

- exact service-local error class, code, message, HTTP status, and details
  shape are preserved;
- validate-only/default-off boundaries remain unchanged;
- no proof JSON, committed report JSON, config, models, Alembic, API, UI, or
  persistence schema changes occur unless explicitly scoped;
- diagnostic report migrations regenerate committed reports byte-identically or
  are explicitly documented as historical runtime-bound artifacts;
- full `backend/tests/test_sec_xbrl*.py`, Layer 3 progress check, frozen
  target-selection validation, and `git diff --check` pass;
- GitHub closeout uses CI green, review-settle window, thread-aware GraphQL
  `reviewThreads`, merge if authorized, detached post-merge proof, and final
  thread scan.

## Explicit non-scope

This audit and its bounded follow-up traces do not:

- migrate any remaining custom service wrapper beyond the exact
  `_reject_unadmitted_keys` adapter recorded above;
- change runtime behavior, route behavior, persistence, schema, UI, config, or
  models;
- regenerate or edit proof JSONs or committed diagnostic reports;
- seed or generate runtime evidence;
- enable live SEC network access, Arelle invocation, value reveal, or runtime
  default-on behavior;
- authorize the activation lane.
