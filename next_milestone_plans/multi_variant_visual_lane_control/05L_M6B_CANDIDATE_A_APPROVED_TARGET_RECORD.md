# 05L M6B Candidate A Approved Target Record

## Purpose

Freeze the exact approved Candidate A target record required by `03AA` and `05H` before any direct M6B admission code begins.

This document is the frozen derivative record contemplated by `05K`.
It closes the exact target-definition gap.
It does **not** itself change integrated runtime behavior.

Governed by:

- `03AA_EXACT_M6_CONTROLLED_ADMISSION_AND_PROMOTION_MECHANISM.md`
- `05H_M6_APPROVE_AS_IS_EXECUTION_PACKET.md`
- `05J_M6A_PAGE_EVIDENCE_WORKBENCH_IMPLEMENTATION_RECORD.md`
- `05K_M6B_CANDIDATE_A_TARGET_RECORD_TEMPLATE.md`

---

## Status note

Candidate A is now explicitly named and approved for the later M6B direct-admission lane under the narrow scope recorded below.

All other non-`baseline` values remain fail-closed unless separately approved later.

---

## Exact approved target record

```yaml
approved_admission_target:
  selector_value: "candidate_a_page_evidence_v1"
  candidate_id: "candidate_a"
  candidate_label: "Candidate A"
  admission_scope: "direct_m6b_admission"
  target_status: "approved_for_direct_admission"

provenance:
  source_workbench_branch: "codex/mvvlc-candidate-a-evidence-next"
  source_workbench_commit: "2188baf9"
  source_workbench_record_ref: "next_milestone_plans/multi_variant_visual_lane_control/05J_M6A_PAGE_EVIDENCE_WORKBENCH_IMPLEMENTATION_RECORD.md"
  source_workbench_report_ref: "tests/reports/mvvlc_candidate_a_page_evidence_workbench_report_v1.json"
  source_runner_ref: "tools/run_nrc_aps_page_evidence_workbench.py"
  source_service_ref: "backend/app/services/nrc_aps_page_evidence.py"

approved_behavior_delta:
  summary: "Candidate A may change only seam-local PDF visual significance and preservation decisions by using deterministic PageEvidence geometry/text signals inside the already-frozen visual-preservation seam for the one admitted selector value."
  exact_changes:
    - "Candidate A may preserve and execute the exact selector value `candidate_a_page_evidence_v1` through the integrated owner path instead of fail-closing it to `baseline`."
    - "Candidate A may use PageEvidence-derived deterministic per-page signals to decide seam-local visual-preservation eligibility and visual-ref emission behavior inside the frozen PDF visual lane."
  exact_non_goals:
    - "No document-class replacement, no whole-document classification redesign, and no change to baseline-facing document_class semantics."
    - "No OCR-routing change, no OCR or hybrid OCR reopening, no media-scope expansion, and no new outward review/API/report/export identity fields."
  exact_boundaries_of_change:
    - "Integrated PDF visual-lane seam only, first consumed inside the already-frozen `_process_pdf(...)` owner path."
    - "The one admitted selector value only; every other non-`baseline` value remains fail-closed and experiment-hidden unless separately approved later."

required_invariants:
  baseline_remains_default: true
  unapproved_values_fail_closed: true
  no_new_outward_variant_identity_fields: true
  no_ocr_hybrid_media_scope_reopen: true
  no_report_export_schema_widening: true
  no_runtime_root_allowlist_redesign: true

evidence_refs:
  canonical_workbench_report_refs:
    - "tests/reports/mvvlc_candidate_a_page_evidence_workbench_report_v1.json"
  workbench_validation_refs:
    - "next_milestone_plans/multi_variant_visual_lane_control/05J_M6A_PAGE_EVIDENCE_WORKBENCH_IMPLEMENTATION_RECORD.md"
    - "backend/tests/test_nrc_aps_page_evidence.py"
    - "tests/test_nrc_aps_page_evidence_workbench.py"
  comparison_refs:
    - "tests/fixtures/nrc_aps_docs/v1/manifest.json"
    - "tests/reports/mvvlc_candidate_a_page_evidence_workbench_report_v1.json"
  promotion_gate_refs:
    - "tests/test_nrc_aps_promotion_gate.py"
    - "tests/reports/nrc_aps_promotion_validation_report.json"
  promotion_tuning_refs:
    - "not_applicable_no_policy_tuning_used_for_candidate_a_first_admission"
  supporting_repo_docs:
    - "00D_MULTI_VARIANT_PROGRAM_DECISION.md"
    - "03AA_EXACT_M6_CONTROLLED_ADMISSION_AND_PROMOTION_MECHANISM.md"
    - "03Y_REVIEW_REPORT_EXPORT_FIELD_SENSITIVITY_MAP.md"
    - "03Z_EXACT_M5_BASELINE_VISIBILITY_AND_RUNTIME_ROOT_COEXISTENCE_MECHANISM.md"
    - "05H_M6_APPROVE_AS_IS_EXECUTION_PACKET.md"
    - "05J_M6A_PAGE_EVIDENCE_WORKBENCH_IMPLEMENTATION_RECORD.md"
    - "05K_M6B_CANDIDATE_A_TARGET_RECORD_TEMPLATE.md"

visibility_and_exposure_expectations:
  integrated_runtime_visibility: "The integrated owner path may recognize and preserve `candidate_a_page_evidence_v1` as the one admitted non-`baseline` value through the PDF visual-lane seam."
  baseline_facing_visibility: "Baseline remains the default for missing, invalid, unsupported, or unapproved values, and no new outward public-facing variant label or identity field is introduced."
  review_runtime_report_export_expectations:
    - "Review/catalog/API/report/export/package surfaces remain free of new outward variant-identity fields."
    - "M5 barrier behavior remains intact for every non-approved value, and baseline-facing visibility rules remain unchanged for absent, invalid, or unapproved selector values."
    - "Diagnostics-ref persistence, runtime DB binding, and baseline review-root resolution remain governed by the already-frozen M5/M6 no-drift rules."

approval_record:
  approval_statement: "The selector value `candidate_a_page_evidence_v1` is approved as the only non-`baseline` `visual_lane_mode` value for the later M6B Candidate A direct-admission lane. This approval is limited to seam-local PDF visual significance and preservation behavior derived from the M6A PageEvidence workbench evidence. All other non-`baseline` selector values remain fail-closed to `baseline` and remain experiment-hidden unless separately approved later."
  approval_basis_summary: "Candidate A is approved first because the achieved M6A workbench provides deterministic PageEvidence signals across the representative fixture set and a pinned canonical report artifact, while the fixture-manifest comparison also shows Candidate A should be admitted narrowly as a seam-local visual-preservation mechanism rather than as a document-class replacement. For that reason the first admission excludes OCR-routing changes, policy tuning, outward identity expansion, and broader classification redesign."
  approved_by: "repository owner (explicit user approval in Codex session)"
  approval_date_utc: "2026-04-08T06:44:36Z"

admission_acceptance_bar:
  required_validation_bundles:
    - "05H required owner-path bundle"
    - "05H required governance bundle"
    - "05H required M5 no-drift backend bundle"
    - "05H required root-side report/export/context bundle"
    - "06I local performance baseline/regression check"
  must_be_true_after_m6b:
    - "The exact selector value `candidate_a_page_evidence_v1` survives normalization, forwarding, and seam consumption as the one admitted non-`baseline` value."
    - "Baseline remains the default for absent, invalid, unsupported, or unapproved values, and all other non-`baseline` values remain fail-closed and experiment-hidden."
    - "Candidate A changes only seam-local PDF visual significance and preservation behavior; it does not reopen OCR-routing, media-scope behavior, or outward identity/schema surfaces."
    - "Review/runtime/report/export/package behavior, diagnostics-ref persistence, runtime DB binding, and baseline review-root resolution remain correct."
    - "The achieved M5 coexistence and visibility barrier remains intact for all non-approved values."

stop_if_any_field_unfilled: true
```

---

## Interpretation

This record intentionally approves less than the raw PageEvidence workbench could imply.

The pinned workbench report shows that Candidate A produces useful deterministic visual-page signals across the representative fixture set, but it also shows that those signals do not map cleanly onto the repo's broader document-class semantics for every fixture. That is why this approval is limited to seam-local PDF visual-preservation behavior rather than promoted as a general document-class or OCR-routing replacement.

---

## Next step

At the time this approved-target record was frozen, the next justified MVVLC step was the later M6B direct-admission implementation lane under `03AA` + `05H`, using this record as the exact approved target contract.

That later direct-admission step has since been achieved in the current clean worktree and recorded in `05M`.
Merged-main closure and the next-scope handoff are now recorded in `05N`.
This document remains the exact approved target contract for that achieved lane, but it should no longer be read in isolation as meaning the M6B implementation has not yet happened anywhere.
