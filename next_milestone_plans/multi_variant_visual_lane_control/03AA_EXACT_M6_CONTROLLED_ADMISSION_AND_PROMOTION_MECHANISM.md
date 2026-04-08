# 03AA Exact M6 Controlled Admission and Promotion Mechanism

## Purpose

Freeze the exact M6 controlled-admission / promotion mechanism before implementation.

## Status note

This is a planning/freeze input for the bounded M6 lane.

If the chosen candidate architecture uses a dedicated pre-admission workbench surface, that workbench must be frozen separately and does not itself count as integrated admission.

It does **not** itself approve any specific non-baseline selector value.
Instead, it freezes:

- what must be true before one value can be admitted,
- how that approval must be evidenced,
- how admission interacts with the achieved M5 visibility barrier,
- and what remains fail-closed until explicit approval exists.

If a later M6 code lane cannot name exactly one approved target under the rules below, it must stop before editing.

---

## Verified live anchors this mechanism is built on

1. `connectors_nrc_adams._normalize_request_config(...)` currently persists `visual_lane_mode` into `ConnectorRun.request_config_json`, but fail-closes every non-`baseline` value back to `baseline`.
2. `nrc_aps_artifact_ingestion.processing_config_from_run_config(...)` forwards `visual_lane_mode` into processing config.
3. `nrc_aps_document_processing._normalize_visual_lane_mode(...)` currently fail-closes every non-`baseline` value back to `baseline`, and `_process_pdf(...)` only executes the baseline visual lane helper.
4. `review_nrc_aps_runtime.request_config_is_baseline_visible(...)` currently treats only `baseline` or missing `visual_lane_mode` as baseline-visible; every other explicit value is experiment-hidden.
5. `nrc_aps_promotion_gate.validate_promotion_gate(...)` already provides repo-native evaluation of a finalized live-validation batch against a canonical promotion policy and emits `aps.promotion_governance.v2`.
6. `nrc_aps_promotion_tuning.compare_promotion_policies(...)` already provides repo-native baseline-vs-tuned comparison with explicit rationale requirements and leaves even a passing tuned candidate in `experimental_pass_not_promoted`, not implicitly admitted.
7. T3 already contains the repo-native governance validation surfaces most relevant to admission/promotion: replay, promotion gate, promotion tuning, safeguards, sync drift, live batch, and live validation.

---

## Rejected mechanisms

### 1. Admitting arbitrary non-baseline selector values

Rejected.

The M6 lane must not convert `visual_lane_mode` from a bounded control into an open registry.
Only one explicitly approved non-baseline value may be admitted at a time.

### 2. Admitting multiple non-baseline values concurrently

Rejected.

The program decision remains:
- baseline first,
- then one approved variant at a time,
- not baseline + A + B + C simultaneously in integrated runtime.

### 3. Inferring approval from passing tests alone

Rejected.

Passing validation is necessary but insufficient.
Repo-native promotion/tuning evidence plus an explicit approval record are both required.

### 4. Public variant-identity exposure as the admission mechanism

Rejected.

M6 may widen integrated runtime behavior for one approved value, but it does not authorize new outward review/API/report/export identity fields for that value.

### 5. Treating M5 hidden/visible classification as obsolete

Rejected.

M5 remains the default barrier for all non-approved non-baseline values.
M6 only carves out one approved integrated exception.

---

## Exact approved-target rule

No non-baseline selector value is approved by default by this document.

Before any M6 code edits begin, the lane must freeze exactly one:

- `approved_admission_target.selector_value`

And must record, in the lane report or equivalent freeze artifact:

- the exact selector string,
- the source worktree / branch / commit or other concrete provenance for the candidate,
- the comparison-evidence refs used to justify the candidate,
- and the explicit approval statement that this one value, and only this one value, is being admitted.

If that record does not exist, the M6 code lane must stop before editing.

Integrated runtime rule after approval:

- `baseline` remains the default when the selector is absent, invalid, unsupported, or unapproved.
- the one named approved selector value may survive integrated normalization / forwarding / seam consumption.
- every other non-`baseline` value must continue to fail closed to `baseline` in the connector/processing owner path and remain experiment-hidden under the achieved M5 barrier.

---

## Exact baseline-comparison and explicit-approval rule

Baseline remains the control and comparison anchor.

An M6 admission decision is only valid if it is backed by all of the following:

1. A finalized candidate batch manifest or equivalent concrete candidate-evidence reference.
2. Repo-native promotion-governance evidence from `nrc_aps_promotion_gate.validate_promotion_gate(...)`.
3. Repo-native baseline-vs-candidate comparison evidence from `nrc_aps_promotion_tuning.compare_promotion_policies(...)` if any policy tuning is involved.
4. Explicit rationale entries for every tuned policy key if policy tuning is used.
5. An explicit human approval record naming the admitted selector value.

Additional interpretation rules:

- A passing tuned comparison is **not** itself promotion.
- `experimental_pass_not_promoted` is still not admitted.
- Approval must be explicit and recorded; do not infer it from `tuned_passed=True`, from green tests, or from local preference.

---

## Exact runtime and visibility rule after admission

M6 widens integrated runtime in a controlled way:

- exactly one approved non-baseline selector value may become integrated-runtime-admissible,
- baseline remains the default,
- variant identity remains internal-only on outward surfaces,
- and the achieved M5 barrier remains active for every non-approved non-baseline value.

This means:

1. The approved value may be allowed through the connector/processing owner path.
2. The approved value may become baseline-visible operationally where an admitted integrated run must be reviewable or reportable.
3. That visibility widening must apply only to the one approved selector value.
4. Unapproved non-baseline values must still be treated as absent on baseline-facing discovery and run-bound surfaces.
5. No new outward field may advertise variant identity merely because the admitted value is now integrated.

---

## Exact owner-boundary implication

Unlike M5, M6 is expected to widen into both:

- the connector/processing owner path, and
- the visibility-classification path.

### Default owner files expected to change

- `backend/app/services/connectors_nrc_adams.py`
- `backend/app/services/nrc_aps_artifact_ingestion.py`
- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/review_nrc_aps_runtime.py`

### Conditional owner promotion files

These are not part of the default owner set.
They may become editable only if the default owner path proves insufficient and the widening is recorded explicitly:

- `backend/app/services/review_nrc_aps_catalog.py`
- `backend/app/api/review_nrc_aps.py`
- `backend/app/services/review_nrc_aps_document_trace.py`
- `backend/app/services/nrc_aps_evidence_report.py`
- `backend/app/services/nrc_aps_evidence_report_export.py`
- `backend/app/services/nrc_aps_evidence_report_export_package.py`

### Inspect-only governance / compatibility files

These should normally remain edit-free:

- `backend/app/services/nrc_aps_promotion_gate.py`
- `backend/app/services/nrc_aps_promotion_tuning.py`
- `backend/app/services/review_nrc_aps_runtime_roots.py`
- `backend/app/services/review_nrc_aps_runtime_db.py`
- `backend/app/services/nrc_aps_content_index.py`
- `backend/app/services/connectors_sciencebase.py`

---

## Exact non-goals of this mechanism freeze

This document does **not** authorize:

- admitting more than one non-baseline value,
- changing the canonical selector key,
- making a non-baseline value the new default,
- exposing variant identity through new outward fields,
- reopening OCR / hybrid OCR / media-scope boundaries,
- bypassing repo-native promotion evidence with ad hoc judgment,
- or replacing the achieved M5 barrier with a broader multi-variant registry.

---

## Result

The exact M6 admission / promotion mechanism is now frozen enough to proceed,
but it is intentionally fail-closed on one point:

the exact admitted non-baseline target must still be named explicitly before direct integrated-admission code begins.

That is now an explicit stop condition, not a hidden assumption.
