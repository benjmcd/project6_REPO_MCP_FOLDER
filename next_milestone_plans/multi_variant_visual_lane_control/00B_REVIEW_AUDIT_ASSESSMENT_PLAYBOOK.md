# 00B Review / Audit / Assessment Playbook

## Purpose

This document tells a reviewer exactly how to use the planning pack when the goal is:

- verification
- auditing
- assessment
- challenge review
- adequacy review
- whole-pack conceptualization

This is not the implementation playbook.

### Authority note
This playbook is an operational workflow aid. It organizes the review process but does not carry interpretive authority over foundational (`00F`, `00T`), control (`03*` series), or evidence (`06E`) docs. If this playbook appears to conflict with a stronger doc, the stronger doc governs. See `00U` Section 5 for the full strength hierarchy.

Its job is to help a reviewer determine:

1. what the pack is actually claiming
2. how strong those claims are
3. what is foundational vs derivative
4. what is frozen vs still bounded
5. whether the pack is strong enough to proceed

---

## 1. Core review principle

Do not read the pack as a flat list of files.

The pack has three different document roles:

### A. Foundational control docs
These define the core model and should dominate interpretation.

### B. Evidence / closure / narrowing docs
These verify, refine, narrow, or correct the foundational picture.

### C. Execution / validation docs
These tell you how the model is supposed to be applied and checked.

A correct audit moves in that order.
If you reverse it, you will misread the pack.

---

## 2. Review modes

There are three valid audit modes.

### Mode 1 — individual-doc review
Use this when one specific document is under scrutiny.

### Mode 2 — cluster review
Use this when a question crosses a boundary class, for example:
- selector policy
- experiment isolation
- visibility leakage
- validation

### Mode 3 — full-pack review
Use this when you need to assess:
- adequacy
- internal consistency
- readiness to proceed
- whether the pack is overclaiming

Each mode uses a different order.

---

## 3. Mandatory starting documents for any audit

Before auditing anything else, read:

1. `README_INDEX.md`
2. `00A_MASTER_NAVIGATION_AND_REVIEW_MAP.md`
3. `00F_LIVE_REPO_VERIFIED_FACTS_AND_OPEN_ITEMS.md`
4. `00T_STRICT_ADEQUACY_AUDIT_AND_PROCEED_DECISION.md`

Why:
- `README_INDEX` tells you what is in the pack
- `00A` tells you how the pack is meant to be traversed
- `00F` tells you the current evidence/closure state
- `00T` tells you the current proceed/no-proceed interpretation

Without those four, later documents are easy to overread.

---

## 4. Correct order for whole-pack review

If the goal is to audit the planning docs as a whole, use this order.

### Pass 1 — authority and current position
Read:
1. `README_INDEX.md`
2. `00A_MASTER_NAVIGATION_AND_REVIEW_MAP.md`
3. `00F_LIVE_REPO_VERIFIED_FACTS_AND_OPEN_ITEMS.md`
4. `00D_MULTI_VARIANT_PROGRAM_DECISION.md`
5. `06E_BLOCKER_DECISION_TABLE.md`
6. `00T_STRICT_ADEQUACY_AUDIT_AND_PROCEED_DECISION.md`

Goal:
- understand the pack’s current claim set
- understand what remains bounded
- understand whether proceeding is justified

### Pass 2 — frozen control boundaries
Read:
1. `03M_SELECTOR_ACTIVATION_SCOPE_AND_LIFETIME_POLICY.md`
2. `03N_EXPERIMENT_ISOLATION_MECHANISM_POLICY.md`
3. `03U_CANONICAL_SELECTOR_CONFIG_KEY_AND_FAIL_CLOSED_POLICY.md`
4. `03V_SELECTOR_KEY_INSERTION_AND_CONSUMPTION_MAP.md`
5. `03W_EXACT_PROCESS_PDF_SEAM_FREEZE_SPECIFICATION.md`
6. `03P_SELECTOR_CONTROL_KEY_AND_QUERY_PAYLOAD_LEAKAGE_POLICY.md`

Goal:
- determine what is actually allowed to vary
- determine how selector control is constrained
- determine the exact frozen seam and propagation path

### Pass 3 — downstream visibility / persistence / leakage
Read:
1. `03I_RUNTIME_ROOT_AND_RUN_NAMESPACE_POLICY.md`
2. `03Q_REVIEW_CATALOG_REPORT_VISIBILITY_BLOCKER_POLICY.md`
3. `03S_REVIEW_API_ENDPOINT_EXPOSURE_MATRIX.md`
4. `03T_REPORT_EXPORT_RUN_VISIBILITY_MATRIX.md`
5. `03J_ARTIFACT_EQUIVALENCE_CONTROL_POLICY.md`
6. `03K_DIAGNOSTICS_REF_PERSISTENCE_POLICY.md`
7. `03L_RUNTIME_DB_BINDING_AND_ISOLATION_POLICY.md`

Goal:
- verify that experiment isolation is not overstated
- verify that review/runtime/report leakage is handled correctly
- verify that artifact/persistence contracts are treated as first-class control surfaces

### Pass 4 ? validation / acceptance / operationalization
Read:
1. `05D_SELECTOR_BOOTSTRAP_BASELINE_ONLY_PLAN.md`
2. `05H_M6_APPROVE_AS_IS_EXECUTION_PACKET.md`
3. `05I_M6A_PAGE_EVIDENCE_WORKBENCH_EXECUTION_PACKET.md`
4. `05J_M6A_PAGE_EVIDENCE_WORKBENCH_IMPLEMENTATION_RECORD.md`
5. `05K_M6B_CANDIDATE_A_TARGET_RECORD_TEMPLATE.md`
6. `05L_M6B_CANDIDATE_A_APPROVED_TARGET_RECORD.md`
7. `05M_M6B_CANDIDATE_A_ADMISSION_IMPLEMENTATION_RECORD.md`
8. `05N_M6B_MERGED_MAIN_CLOSURE_AND_POST_ADMISSION_HANDOFF.md`
9. `03AC_EXACT_POST_ADMISSION_DEFAULTING_SCOPE_AND_DECISION_BOUNDARY.md`
10. `05O_POST_ADMISSION_DEFAULTING_PLANNING_FREEZE_PACKET.md`
11. `05P_POST_ADMISSION_RETAIN_BASELINE_DEFAULT_DECISION_RECORD.md`
12. `06C_ACTIVE_TEST_SURFACE_AND_COMMAND_MATRIX.md`
13. `06D_CRITICAL_BLOCKER_VALIDATION_SET.md`
14. `06I_LOCAL_PERFORMANCE_BASELINE_AND_REGRESSION_CHECK_SPECIFICATION.md`
15. `06J_CANONICAL_ACCEPTANCE_COMMAND_CONVENTION.md`
16. `06K_SHELL_SPECIFIC_CANONICAL_ACCEPTANCE_COMMANDS.md`

Goal:
- determine whether the pack translates into a real validation path
- assess whether implementation can be checked in practice
- determine whether the pack now closes the exact M6B implementation gap with a real achieved-lane record plus merged-main closure/handoff and points to the correct bounded post-admission/defaulting decision packet

### Pass 5 — challenge, narrowing, residuals
Read:
1. `00L_CLOSURE_CLAIM_RETRACTION_AND_BOUNDED_UNCERTAINTY.md`
2. `00M_ENFORCEMENT_AND_MIGRATION_SURFACE_AUDIT.md`
3. `00N_REPO_NATIVE_ENFORCEMENT_SURFACE_NARROWING.md`
4. `00O_SCHEMA_AND_CONTRACT_DRIFT_RISK_NARROWING.md`
5. `00P_VISUAL_PAGE_CLASS_ROUNDTRIP_SUPPORT_NOTE.md`
6. `00Q_NON_APP_LIVE_SURFACE_NARROWING.md`
7. `00R_ARCHIVE_AND_WORKTREE_DUPLICATION_NARROWING.md`
8. `00S_NARROWING_STOP_RULE_AND_RECOMMENDATION.md`
9. `06L_BOUNDED_UNCERTAINTY_AND_ENFORCEMENT_GAP_REGISTER.md`

Goal:
- determine whether the pack overstates closure
- understand bounded residuals without confusing them with unresolved core blockers

---

## 5. How to audit one document properly

Never audit a single planning doc in isolation.

For any target document:

### Step 1
Read `00F_LIVE_REPO_VERIFIED_FACTS_AND_OPEN_ITEMS.md`

### Step 2
Read the target document

### Step 3
Read the target’s nearest governing docs
Examples:
- if target is `03V`, also read `03U` and `03W`
- if target is `03Q`, also read `03N`, `03S`, and `03T`
- if target is `06I`, also read `06E`, `06J`, and `05D`

### Step 4
Read `06E_BLOCKER_DECISION_TABLE.md`

### Step 5
Answer:
1. Is the document foundational or derivative?
2. Does it overclaim beyond verified evidence?
3. Does it silently conflict with a controlling document?
4. Is it still current, or has a later narrowing doc modified its force?
5. If it uses general `M6` or post-admission language, does it hide an important `M6A`, `05L` approved-target, later `M6B` direct-admission, `03AC` + `05O` planning-only distinction, or the achieved `05P` retain-default decision?

If you skip Step 3 or Step 5, the audit is not strict enough.

## 6. Recommended review clusters

### Cluster A — selector/control architecture
Read together:
- `03H_SELECTOR_CONFIG_INSERTION_POLICY.md`
- `03M_SELECTOR_ACTIVATION_SCOPE_AND_LIFETIME_POLICY.md`
- `03P_SELECTOR_CONTROL_KEY_AND_QUERY_PAYLOAD_LEAKAGE_POLICY.md`
- `03U_CANONICAL_SELECTOR_CONFIG_KEY_AND_FAIL_CLOSED_POLICY.md`
- `03V_SELECTOR_KEY_INSERTION_AND_CONSUMPTION_MAP.md`
- `03W_EXACT_PROCESS_PDF_SEAM_FREEZE_SPECIFICATION.md`

Audit focus:
- selector semantics
- fail-closed behavior
- propagation correctness
- exact seam boundary
- leakage prevention

### Cluster B — experiment isolation / visibility architecture
Read together:
- `03I_RUNTIME_ROOT_AND_RUN_NAMESPACE_POLICY.md`
- `03N_EXPERIMENT_ISOLATION_MECHANISM_POLICY.md`
- `03Q_REVIEW_CATALOG_REPORT_VISIBILITY_BLOCKER_POLICY.md`
- `03S_REVIEW_API_ENDPOINT_EXPOSURE_MATRIX.md`
- `03T_REPORT_EXPORT_RUN_VISIBILITY_MATRIX.md`
- `03L_RUNTIME_DB_BINDING_AND_ISOLATION_POLICY.md`
- `03K_DIAGNOSTICS_REF_PERSISTENCE_POLICY.md`

Audit focus:
- whether isolation is being overstated
- which surfaces remain baseline-visible
- which persistence/runtime behaviors are baseline-locked

### Cluster C — evidence / closure / adequacy
Read together:
- `00E_REPO_CONSUMER_AND_INVARIANT_MAP.md`
- `00F_LIVE_REPO_VERIFIED_FACTS_AND_OPEN_ITEMS.md`
- `00L_CLOSURE_CLAIM_RETRACTION_AND_BOUNDED_UNCERTAINTY.md`
- `00S_NARROWING_STOP_RULE_AND_RECOMMENDATION.md`
- `00T_STRICT_ADEQUACY_AUDIT_AND_PROCEED_DECISION.md`
- `06L_BOUNDED_UNCERTAINTY_AND_ENFORCEMENT_GAP_REGISTER.md`

Audit focus:
- whether closure claims are honest
- whether residuals are explicit
- whether proceeding is justified without overclaim

### Cluster D — validation / operational adequacy
Read together:
- `06C_ACTIVE_TEST_SURFACE_AND_COMMAND_MATRIX.md`
- `06D_CRITICAL_BLOCKER_VALIDATION_SET.md`
- `06E_BLOCKER_DECISION_TABLE.md`
- `06I_LOCAL_PERFORMANCE_BASELINE_AND_REGRESSION_CHECK_SPECIFICATION.md`
- `06J_CANONICAL_ACCEPTANCE_COMMAND_CONVENTION.md`
- `06K_SHELL_SPECIFIC_CANONICAL_ACCEPTANCE_COMMANDS.md`

Audit focus:
- validation realism
- command adequacy
- performance-gate seriousness
- operational completeness

---

## 7. Foundational vs derivative review rule

### Foundational docs
These should carry the highest interpretive weight:

- `00D`
- `00E`
- `00F`
- `00T`
- `03M`
- `03N`
- `03U`
- `03V`
- `03W`
- `06E`

### Execution / validation docs
These are operationally critical, but they do not carry the same interpretive weight as the foundational control/evidence spine:

- `05D`
- `06C`
- `06D`
- `06I`
- `06J`
- `06K`

Use them to determine how the frozen model is applied, validated, and accepted; do not let them override stronger foundational/control docs.

### Derivative/narrowing docs
These refine or narrow earlier claims:

- `00G`
- `00H`
- `00L`
- `00M`
- `00N`
- `00O`
- `00P`
- `00Q`
- `00R`
- `00S`
- `06L`

Rule:
- later narrowing/correction docs can reduce the force of earlier claims
- but derivative docs do not replace the control spine unless they explicitly correct it

This distinction is mandatory for correct audit reading.

---

## 8. What a reviewer should be able to state after a successful audit

After a strict audit, the reviewer should be able to answer all of the following without ambiguity:

1. What exact code-path zone is allowed to vary?
2. What exact selector control exists, and how does it fail closed?
3. Why is runtime-root separation insufficient by itself?
4. Which review/report/runtime surfaces remain leakage-sensitive?
5. What validation path is expected?
6. What residual uncertainty remains, and why is it non-blocking?

If those answers are not possible, the review is incomplete.

---

## 9. Best minimal audit packets

### Minimal packet — “Is the pack credible?”
Read:
1. `00A`
2. `00F`
3. `00D`
4. `06E`
5. `00T`

### Minimal packet — “Is the control model internally coherent?”
Read:
1. `03M`
2. `03N`
3. `03U`
4. `03V`
5. `03W`
6. `03Q`

### Minimal packet — “Is it overclaiming?”
Read:
1. `00F`
2. `00L`
3. `00N`
4. `06L`
5. `00S`
6. `00T`

---

## 10. Audit anti-patterns

Do not do any of these:

- read only the narrowing docs first
- treat `README_INDEX` as a sufficient substitute for the actual control docs
- audit implementation docs before understanding the frozen seam and selector path
- treat bounded residuals as evidence that the whole pack is still immature
- treat derivative docs as if they are the architecture itself

Those are the main ways to misread the pack.

---

## 11. Final review recommendation

If the objective is rigorous assessment of the planning docs:

- use whole-pack review when deciding whether to proceed
- use thematic cluster review when challenging a specific aspect
- use individual-doc review only after the reviewer has already internalized `00F`, `06E`, and the relevant governing docs

That is the strictest and most reliable review approach the current pack supports.


## 12. Reasoning / justification cross-check

Before concluding that a planning doc is adequate, also use:

- `00U_ASSERTION_JUSTIFICATION_AND_EVIDENTIARY_STANDARD.md`
- `00V_PLANNING_TRACEABILITY_AND_DEPENDENCY_MATRIX.md`

These are the fastest way to test whether even small assertions are:
- adequately justified
- properly scoped
- tied to stronger governing docs
- not being read too strongly
