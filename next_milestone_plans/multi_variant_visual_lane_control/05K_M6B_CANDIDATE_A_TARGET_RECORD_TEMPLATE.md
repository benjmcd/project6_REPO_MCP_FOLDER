# 05K M6B Candidate A Target Record Template

## Purpose

Provide the exact record shape that must be filled before direct M6B Candidate A admission code begins.

This document is a template and execution aid.
It is not itself an approval record.
It must be filled with concrete values and evidence refs before the later direct-admission lane starts.

This template is governed by:

- `03AA_EXACT_M6_CONTROLLED_ADMISSION_AND_PROMOTION_MECHANISM.md`
- `05H_M6_APPROVE_AS_IS_EXECUTION_PACKET.md`
- `05J_M6A_PAGE_EVIDENCE_WORKBENCH_IMPLEMENTATION_RECORD.md`

---

## Status note

The pack is intentionally fail-closed until one exact non-`baseline` selector value is recorded here with explicit approval and evidence refs.

If any required field below cannot be filled with concrete repo-backed evidence, do not start M6B code.

---

## Exact use rule

Before any direct-admission M6B code edits:

1. copy this template into the active lane report or replace the placeholders in a frozen derivative record
2. fill every required field with exact values
3. attach the required evidence refs
4. record the explicit approval statement
5. only then begin the later direct-admission lane under `03AA` + `05H`

Do not treat partial completion of this template as approval.

---

## Required target record

Use the following exact structure.

```yaml
approved_admission_target:
  selector_value: "<exact non-baseline visual_lane_mode value>"
  candidate_id: "candidate_a"
  candidate_label: "Candidate A"
  admission_scope: "direct_m6b_admission"
  target_status: "approved_for_direct_admission"

provenance:
  source_workbench_branch: "<branch name>"
  source_workbench_commit: "<commit sha>"
  source_workbench_record_ref: "<doc path or artifact ref>"
  source_workbench_report_ref: "<exact durable canonical workbench report ref>"
  source_runner_ref: "<tool path>"
  source_service_ref: "<service path>"

approved_behavior_delta:
  summary: "<one-paragraph statement of what changes vs baseline>"
  exact_changes:
    - "<change 1>"
    - "<change 2>"
  exact_non_goals:
    - "<non-goal 1>"
    - "<non-goal 2>"
  exact_boundaries_of_change:
    - "<boundary 1>"
    - "<boundary 2>"

required_invariants:
  baseline_remains_default: true
  unapproved_values_fail_closed: true
  no_new_outward_variant_identity_fields: true
  no_ocr_hybrid_media_scope_reopen: true
  no_report_export_schema_widening: true
  no_runtime_root_allowlist_redesign: true

evidence_refs:
  canonical_workbench_report_refs:
    - "<exact durable workbench report json ref>"
  workbench_validation_refs:
    - "<test/doc/artifact ref>"
  comparison_refs:
    - "<comparison artifact ref>"
  promotion_gate_refs:
    - "<promotion gate artifact ref>"
  promotion_tuning_refs:
    - "<promotion tuning artifact ref or explicit not_applicable note>"
  supporting_repo_docs:
    - "03AA_EXACT_M6_CONTROLLED_ADMISSION_AND_PROMOTION_MECHANISM.md"
    - "05H_M6_APPROVE_AS_IS_EXECUTION_PACKET.md"
    - "05J_M6A_PAGE_EVIDENCE_WORKBENCH_IMPLEMENTATION_RECORD.md"

visibility_and_exposure_expectations:
  integrated_runtime_visibility: "<what becomes integrated>"
  baseline_facing_visibility: "<what must remain hidden or unchanged>"
  review_runtime_report_export_expectations:
    - "<expectation 1>"
    - "<expectation 2>"

approval_record:
  approval_statement: "<explicit statement that this one selector value is approved>"
  approval_basis_summary: "<why Candidate A is approved first>"
  approved_by: "<human approver>"
  approval_date_utc: "<YYYY-MM-DDTHH:MM:SSZ>"

admission_acceptance_bar:
  required_validation_bundles:
    - "05H required owner-path bundle"
    - "05H required governance bundle"
    - "05H required M5 no-drift backend bundle"
    - "05H required root-side report/export/context bundle"
    - "06I local performance baseline/regression check"
  must_be_true_after_m6b:
    - "<post-admission truth 1>"
    - "<post-admission truth 2>"

stop_if_any_field_unfilled: true
```

---

## Field rules

### `approved_admission_target.selector_value`

This must be:

- one exact literal selector string
- non-`baseline`
- the only non-`baseline` value approved for admission in the lane

This must not be:

- a wildcard
- a family name
- a prose description
- a list of future values

### `provenance`

The provenance block must point to the concrete Candidate A workbench result being promoted from pre-admission evaluation into direct-admission consideration.

At minimum it must identify:

- the workbench branch
- the exact commit
- the M6A implementation record or equivalent frozen artifact
- the exact durable canonical workbench report artifact being promoted as evidence
- the actual runner and service refs used to produce the candidate evidence

### `approved_behavior_delta`

This block must describe what Candidate A is allowed to do differently from baseline.

Be exact.
Do not write:

- "better classification"
- "improved visual handling"
- "more accurate"

Instead record:

- what signals or decisions differ
- where those differences are allowed to act
- what remains baseline-identical

### `required_invariants`

Every invariant listed above must remain true after admission.
If the candidate would break any invariant, do not proceed under `05H`.

### `evidence_refs`

Evidence refs must be concrete.
Acceptable refs include:

- exact planning-doc paths
- exact test files
- exact JSON artifact paths
- exact batch-manifest paths
- exact commit SHAs

At least one exact durable canonical workbench report JSON ref is required for Candidate A.
Do not rely only on tests and prose if a pinned workbench report artifact exists.

Unacceptable refs include:

- "see earlier discussion"
- "covered in sessions"
- "same as Candidate A workbench"

### `approval_record`

The approval statement must explicitly say that:

- this one selector value is approved
- it is the only approved non-`baseline` value for this lane
- all other non-`baseline` values remain fail-closed

### `admission_acceptance_bar`

This block is the bridge into the later direct-admission lane.
It must name the validation bundles and the exact post-admission truths the lane is expected to prove.

---

## Fill-first checklist

Before starting M6B code, confirm all of the following are answered:

1. What exact selector string will represent Candidate A?
2. Which exact workbench commit and durable canonical report artifact justify Candidate A?
3. What exact behavior is allowed to differ from baseline?
4. What exact behavior must remain unchanged?
5. What exact evidence proves Candidate A is the one approved first?
6. What exact outward surfaces must remain free of new variant identity fields?
7. What exact validation bundles will prove the direct-admission lane correct?

If any answer is still vague, remain in target-definition mode and do not start code.

---

## Minimal example shape

This is illustrative only.
Do not treat it as approval.

```yaml
approved_admission_target:
  selector_value: "candidate_a_page_evidence_v1"
  candidate_id: "candidate_a"
  candidate_label: "Candidate A"
  admission_scope: "direct_m6b_admission"
  target_status: "approved_for_direct_admission"
```

The real record must fill the entire template, not only the selector field.
