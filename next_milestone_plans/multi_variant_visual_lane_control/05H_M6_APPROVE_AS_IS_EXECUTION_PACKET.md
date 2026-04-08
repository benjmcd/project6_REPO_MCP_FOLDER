# 05H M6 Approve-As-Is Execution Packet

## Purpose

Freeze the concrete execution packet for the bounded M6 controlled-admission / promotion lane.

## Status note

This packet is built on:

- achieved M3/M4 closure,
- achieved M5 coexistence / visibility barrier closure,
- and the exact M6 mechanism frozen in `03AA`.

This packet does **not** itself approve a non-baseline selector value.
It freezes the owner boundary, validation boundary, widening rules, and stop conditions for the M6 lane.

If the lane cannot name exactly one approved target under `03AA`, it must stop before code edits.

---

## Current milestone position

- M3 baseline-only selector bootstrap is merged and accepted.
- M4 acceptance closure is merged and recorded.
- M5 coexistence / visibility barrier is merged and recorded.
- The next milestone is M6: controlled admission / promotion of one explicitly approved non-baseline variant at a time.

What remains before direct M6 admission can be called approve-as-is is not more M5 barrier work.
It is a bounded direct-admission lane that:

1. records the exact approved target,
2. implements only the narrow owner changes required to admit that one value,
3. preserves the M5 barrier for every other non-approved value,
4. and proves no-drift on the already-achieved review/report/export/runtime surfaces.

---

## Canonical live authority chain for the M6 lane

The M6 lane must start from these live authority files:

- `backend/app/services/connectors_nrc_adams.py`
- `backend/app/services/nrc_aps_artifact_ingestion.py`
- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/review_nrc_aps_runtime.py`
- `backend/app/services/nrc_aps_promotion_gate.py`
- `backend/app/services/nrc_aps_promotion_tuning.py`

The M6 lane must also respect the already-frozen control docs:

- `00D_MULTI_VARIANT_PROGRAM_DECISION.md`
- `03E_VARIANT_IDENTITY_VISIBILITY_POLICY.md`
- `03F_REPLAY_PROMOTION_AND_REVIEW_COMPATIBILITY_POLICY.md`
- `03K_DIAGNOSTICS_REF_PERSISTENCE_POLICY.md`
- `03L_RUNTIME_DB_BINDING_AND_ISOLATION_POLICY.md`
- `03M_SELECTOR_ACTIVATION_SCOPE_AND_LIFETIME_POLICY.md`
- `03N_EXPERIMENT_ISOLATION_MECHANISM_POLICY.md`
- `03Y_REVIEW_REPORT_EXPORT_FIELD_SENSITIVITY_MAP.md`
- `03Z_EXACT_M5_BASELINE_VISIBILITY_AND_RUNTIME_ROOT_COEXISTENCE_MECHANISM.md`
- `03AA_EXACT_M6_CONTROLLED_ADMISSION_AND_PROMOTION_MECHANISM.md`
- `06C_ACTIVE_TEST_SURFACE_AND_COMMAND_MATRIX.md`
- `06E_BLOCKER_DECISION_TABLE.md`
- `06I_LOCAL_PERFORMANCE_BASELINE_AND_REGRESSION_CHECK_SPECIFICATION.md`
- `06J_CANONICAL_ACCEPTANCE_COMMAND_CONVENTION.md`
- `06K_SHELL_SPECIFIC_CANONICAL_ACCEPTANCE_COMMANDS.md`

---

## Exact pre-edit stop conditions

The M6 lane must stop before editing if any of the following is true:

1. no exact `approved_admission_target.selector_value` is recorded
2. no explicit approval record exists for that one selector value
3. no concrete comparison-evidence refs are recorded for the candidate
4. the needed implementation would admit more than one non-baseline value
5. the needed implementation would expose variant identity through new outward review/API/report/export fields
6. the needed implementation would reopen OCR / hybrid OCR / media-scope boundaries

If a stop condition is encountered, report it explicitly instead of widening by inference.

---

## Exact lane outcome required

The M6 lane must make all of the following true:

1. exactly one explicitly approved non-baseline selector value may be admitted through the integrated owner path
2. `baseline` remains the default for absent, invalid, unsupported, or unapproved values
3. every non-approved non-baseline value remains fail-closed to `baseline` in the owner path and experiment-hidden under the achieved M5 barrier
4. the admitted value can execute through the integrated PDF visual-lane seam without adding new outward variant-identity fields
5. repo-native promotion / comparison evidence and explicit approval are recorded for the admitted value
6. baseline diagnostics/runtime DB/review/report/export behavior remains correct
7. M5 barrier behavior remains intact for all non-approved values

If the implementation cannot make all seven true, it is not approve-as-is.

---

## Exact owner-file boundary

### Primary owner files expected to change

These are the only files that should be assumed editable at the start of the M6 lane:

- `backend/app/services/connectors_nrc_adams.py`
- `backend/app/services/nrc_aps_artifact_ingestion.py`
- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/review_nrc_aps_runtime.py`

### Expected test-edit files

- `backend/tests/test_nrc_aps_run_config.py`
- `tests/test_nrc_aps_document_processing.py`
- `tests/test_nrc_aps_artifact_ingestion.py`
- `tests/test_nrc_aps_artifact_ingestion_gate.py`

### Conditional owner promotion files

These are **not** part of the default owner set.
They may become editable only if the primary owner path proves insufficient and the widening is recorded explicitly:

- `backend/app/services/review_nrc_aps_catalog.py`
- `backend/app/api/review_nrc_aps.py`
- `backend/app/services/review_nrc_aps_document_trace.py`
- `backend/app/services/nrc_aps_evidence_report.py`
- `backend/app/services/nrc_aps_evidence_report_export.py`
- `backend/app/services/nrc_aps_evidence_report_export_package.py`

### Inspect-only hidden-consumer / governance files

These must be inspected for compatibility, but should remain edit-free unless a repo-confirmed blocker forces widening:

- `backend/app/services/nrc_aps_promotion_gate.py`
- `backend/app/services/nrc_aps_promotion_tuning.py`
- `backend/app/services/review_nrc_aps_runtime_roots.py`
- `backend/app/services/review_nrc_aps_runtime_db.py`
- `backend/app/services/nrc_aps_content_index.py`
- `backend/app/services/connectors_sciencebase.py`
- `backend/app/services/aps_retrieval_plane.py`
- `backend/app/services/aps_retrieval_plane_read.py`

### Exact scope exclusion

The default M6 lane does **not** authorize:

- admission of more than one non-baseline selector value
- replacement of the baseline default
- new outward identity fields
- replay/promotion/safeguard redesign
- report/export schema widening
- runtime-root allowlist redesign

---

## Exact validation boundary

### Required owner-path bundle

- `backend/tests/test_nrc_aps_run_config.py`
- `tests/test_nrc_aps_document_processing.py`
- `tests/test_nrc_aps_artifact_ingestion.py`
- `tests/test_nrc_aps_artifact_ingestion_gate.py`

### Required governance bundle

- `tests/test_nrc_aps_replay_gate.py`
- `tests/test_nrc_aps_promotion_gate.py`
- `tests/test_nrc_aps_promotion_tuning.py`
- `tests/test_nrc_aps_safeguard_gate.py`
- `tests/test_nrc_aps_safeguards.py`
- `tests/test_nrc_aps_sync_drift.py`
- `tests/test_nrc_aps_live_batch.py`
- `tests/test_nrc_aps_live_validation.py`

### Required M5 no-drift backend bundle

- `backend/tests/test_review_nrc_aps_catalog.py`
- `backend/tests/test_review_nrc_aps_api.py`
- `backend/tests/test_review_nrc_aps_details.py`
- `backend/tests/test_review_nrc_aps_tree.py`
- `backend/tests/test_review_nrc_aps_graph.py`
- `backend/tests/test_review_nrc_aps_document_trace_api.py`
- `backend/tests/test_review_nrc_aps_document_trace_service.py`
- `backend/tests/test_review_nrc_aps_document_trace_page.py`
- `backend/tests/test_review_nrc_aps_runtime_db.py`
- `backend/tests/test_diagnostics_ref_persistence.py`

### Required root-side report/export/context bundle

- `tests/test_nrc_aps_evidence_report.py`
- `tests/test_nrc_aps_evidence_report_contract.py`
- `tests/test_nrc_aps_evidence_report_gate.py`
- `tests/test_nrc_aps_evidence_report_export.py`
- `tests/test_nrc_aps_evidence_report_export_contract.py`
- `tests/test_nrc_aps_evidence_report_export_gate.py`
- `tests/test_nrc_aps_evidence_report_export_package.py`
- `tests/test_nrc_aps_evidence_report_export_package_contract.py`
- `tests/test_nrc_aps_evidence_report_export_package_gate.py`
- `tests/test_api.py`
- `tests/test_nrc_aps_document_corpus.py`

### Performance posture

Rerun `06I`.

For M6 this is not optional, because the lane is expected to touch:

- connector/processing owner behavior,
- review/runtime visibility classification,
- and potentially admitted-run operational paths that can affect aggregate runtime cost.

---

## Exact widening rules

The M6 lane must not widen casually.

Allowed widening trigger classes are only:

1. the admitted value cannot become baseline-visible operationally without promoting a review/catalog/API/report/export owner file
2. the admitted value cannot preserve baseline document-trace/runtime semantics without promoting a conditional owner file
3. an inspect-only governance / hidden-consumer file proves to be a real outward leak or normalization surface under execution evidence

Every widening decision must be recorded explicitly in the final report as:

- file widened into
- reason class
- why the default owner set was insufficient
- what new risk the widening introduced

---

## Exact no-drift assertions the lane must prove

The M6 lane must prove all of the following:

- baseline remains default
- the one admitted value is the only non-baseline integrated value
- unapproved non-baseline values remain hidden or fail-closed by explicit design
- no new outward review/API/report/export identity fields were introduced
- baseline review/runtime/report/export/package behavior remains correct
- baseline diagnostics-ref persistence remains correct
- baseline runtime DB read-only access and review-root resolution remain correct
- M5 coexistence / visibility barrier behavior remains correct for non-approved values

---

## Exact status language allowed at the end of the lane

The next lane may be described as approve-as-is only if it provides:

1. one explicitly named approved selector value
2. explicit promotion/comparison evidence refs for that value
3. explicit approval record for that value
4. passing execution evidence for the required validation bundles
5. explicit no-drift findings for review/runtime/report-export surfaces
6. a refreshed `06I` result

Do not use softer overclaim language such as:

- effectively complete
- done pending minor validation
- ready for promotion
- functionally closed

unless the formal evidence above actually exists.

---

## Immediate next action after this packet

The next justified move is:

1. if the chosen architecture is a dedicated pre-admission workbench, freeze and execute that workbench lane first under `03AB` + `05I`
2. otherwise keep working on a fresh merged-main direct-admission lane
3. record the exact approved target and evidence refs before direct-admission code edits
4. re-audit the canonical authority files above
5. implement only within the packet frozen here
6. run the required validation bundles
7. freeze that lane separately

The direct-admission M6 lane remains prepared enough to proceed later,
but it is intentionally fail-closed until one approved target is explicitly named and any separate pre-admission workbench choice is resolved.
