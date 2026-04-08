# 00C Implementation Preparation and Execution Playbook

## Purpose

This document explains how the planning docs should be approached and used when the intent is:

- implementation preparation
- controlled code execution
- baseline-preserving integration work
- validation before, during, and after implementation

This is not the audit playbook.
Its job is to turn the planning pack into a practical implementation operating model.

### Authority note
This playbook is an operational workflow aid. It organizes access to the planning pack for implementation purposes but does not carry interpretive authority over foundational (`00F`, `00T`), control (`03*` series), or evidence (`06E`) docs. If this playbook appears to conflict with a stronger doc, the stronger doc governs. See `00U` Section 5 for the full strength hierarchy.

---

## 1. Core implementation principle

Do not start coding from the bootstrap plan alone.

The correct implementation sequence is:

1. establish the authoritative current state
2. freeze the exact allowed implementation surface
3. freeze the surrounding non-change surfaces
4. convert that into a concrete work sequence
5. validate against the command and performance gates

If you skip Stage 2 or Stage 3, implementation drift is likely.

### Current milestone note
The pack now distinguishes:

- **M6A**: achieved dedicated PageEvidence workbench construction under `03AB` + `05I`, recorded by `05J`
- **M6B target-definition**: frozen derivative record `05L` built from template `05K`
- **M6B direct admission**: achieved implementation of one approved selector value under `03AA` + `05H`, recorded by `05M`
- **M6B merged-main closure/handoff**: merged-main closure and next-scope handoff recorded by `05N`

Do not use `05K` by itself as approval. Treat `05J` as the evidence base, `05K` as the governing template, `05L` as the exact approved-target record, `05M` as the achieved implementation record for the lane that merged, and `05N` as the merged-main closure/handoff. Do not treat `05M` or `05N` as permission to widen into broader post-admission/defaulting scope.

---

## 2. Correct implementation-preparation order

### Stage 0 — establish implementation authority
Read:
1. `00T_STRICT_ADEQUACY_AUDIT_AND_PROCEED_DECISION.md`
2. `00F_LIVE_REPO_VERIFIED_FACTS_AND_OPEN_ITEMS.md`
3. `06E_BLOCKER_DECISION_TABLE.md`

Purpose:
- confirm that proceeding is justified
- know what remains bounded rather than solved
- know which blockers are truly closed vs merely residual

This stage prevents bad assumptions before coding starts.

### Stage 1 — freeze the exact implementation surface
Read:
1. `03U_CANONICAL_SELECTOR_CONFIG_KEY_AND_FAIL_CLOSED_POLICY.md`
2. `03V_SELECTOR_KEY_INSERTION_AND_CONSUMPTION_MAP.md`
3. `03W_EXACT_PROCESS_PDF_SEAM_FREEZE_SPECIFICATION.md`

Purpose:
- know the exact selector key
- know the exact propagation path
- know the exact first owner-path consumer zone
- know the exact seam boundary

This is the implementation-critical core.

### Stage 2 — freeze what surrounding surfaces must *not* drift
Read:
1. `03M_SELECTOR_ACTIVATION_SCOPE_AND_LIFETIME_POLICY.md`
2. `03N_EXPERIMENT_ISOLATION_MECHANISM_POLICY.md`
3. `03P_SELECTOR_CONTROL_KEY_AND_QUERY_PAYLOAD_LEAKAGE_POLICY.md`
4. `03Q_REVIEW_CATALOG_REPORT_VISIBILITY_BLOCKER_POLICY.md`
5. `03J_ARTIFACT_EQUIVALENCE_CONTROL_POLICY.md`
6. `03K_DIAGNOSTICS_REF_PERSISTENCE_POLICY.md`
7. `03L_RUNTIME_DB_BINDING_AND_ISOLATION_POLICY.md`

Purpose:
- freeze what surrounding behaviors must remain baseline-locked
- understand visibility, persistence, and leakage constraints
- prevent variant work from accidentally becoming runtime/report/review drift

### Stage 3 — translate into an actual coding sequence
Read:
1. `05D_SELECTOR_BOOTSTRAP_BASELINE_ONLY_PLAN.md`
2. `03G_IMPLEMENTATION_SEAM_FREEZE_CHECKLIST.md`
3. `06D_CRITICAL_BLOCKER_VALIDATION_SET.md`

Purpose:
- convert policy into execution order
- know what to verify before and after edits
- know what counts as implementation completion vs partial progress

### Stage 3A - if the current lane is M6A workbench work
Read:
1. `03AB_EXACT_M6A_PAGE_EVIDENCE_WORKBENCH_AND_OPTION2_BOUNDARY.md`
2. `05I_M6A_PAGE_EVIDENCE_WORKBENCH_EXECUTION_PACKET.md`
3. `03AA_EXACT_M6_CONTROLLED_ADMISSION_AND_PROMOTION_MECHANISM.md`
4. `05H_M6_APPROVE_AS_IS_EXECUTION_PACKET.md`

Purpose:
- distinguish workbench construction from direct admission
- keep Candidate A pre-admission until explicit later approval
- preserve the later M6B packet as a separate fail-closed lane

### Stage 3B - if the current lane is M6B direct-admission implementation after target-definition closure
Read:
1. `03AA_EXACT_M6_CONTROLLED_ADMISSION_AND_PROMOTION_MECHANISM.md`
2. `05H_M6_APPROVE_AS_IS_EXECUTION_PACKET.md`
3. `05J_M6A_PAGE_EVIDENCE_WORKBENCH_IMPLEMENTATION_RECORD.md`
4. `05K_M6B_CANDIDATE_A_TARGET_RECORD_TEMPLATE.md`
5. `05L_M6B_CANDIDATE_A_APPROVED_TARGET_RECORD.md`

Purpose:
- implement only the one exact approved selector value already frozen in `05L`
- keep the admitted behavior delta narrow and evidence-backed rather than widening by inference
- preserve `05H` as the current direct-admission execution packet while keeping every other non-approved value fail-closed
- after validation, freeze a separate achieved-lane implementation record rather than treating raw code edits as the lane closure

### Stage 4 — prepare the concrete validation surface
Read:
1. `06J_CANONICAL_ACCEPTANCE_COMMAND_CONVENTION.md`
2. `06K_SHELL_SPECIFIC_CANONICAL_ACCEPTANCE_COMMANDS.md`
3. `06I_LOCAL_PERFORMANCE_BASELINE_AND_REGRESSION_CHECK_SPECIFICATION.md`
4. `06C_ACTIVE_TEST_SURFACE_AND_COMMAND_MATRIX.md`

Purpose:
- know how to run the validation path correctly
- know what performance gate applies
- avoid “passing” with the wrong command or wrong scope

---

## 3. Correct implementation usage modes

There are three valid ways to use the planning docs during implementation.

### Mode 1 — use docs individually
Use this when one coding action maps to one specific rule.

Examples:
- need selector key semantics -> `03U`
- need exact insertion point -> `03V`
- need exact seam boundary -> `03W`
- need shell command -> `06K`
- need performance gate -> `06I`

This is the most efficient mode during active edits.

### Mode 2 — use a cluster of docs together
Use this when a coding task crosses a control boundary.

Examples:

#### Task: implement selector propagation safely
Use together:
- `03U`
- `03V`
- `03P`
- `03M`
- `03W`

#### Task: ensure experiment work does not leak into review/report surfaces
Use together:
- `03I`
- `03N`
- `03Q`
- `03S`
- `03T`
- `03L`

#### Task: preserve output/persistence contract stability
Use together:
- `03J`
- `03K`
- `03L`
- `03X`
- `00E`
- `00F`

This is the best mode for nontrivial implementation work.

### Mode 3 — use the pack as a whole
Use this only at major checkpoints:
- before starting implementation
- before declaring a slice complete
- before handing off to another implementer
- before deciding to reopen scope

Whole-pack use is for control moments, not daily coding.

---

## 4. Minimal implementation packet

If someone needs the smallest credible subset required to start controlled implementation, it is this:

1. `03U_CANONICAL_SELECTOR_CONFIG_KEY_AND_FAIL_CLOSED_POLICY.md`
2. `03V_SELECTOR_KEY_INSERTION_AND_CONSUMPTION_MAP.md`
3. `03W_EXACT_PROCESS_PDF_SEAM_FREEZE_SPECIFICATION.md`
4. `03M_SELECTOR_ACTIVATION_SCOPE_AND_LIFETIME_POLICY.md`
5. `03N_EXPERIMENT_ISOLATION_MECHANISM_POLICY.md`
6. `03P_SELECTOR_CONTROL_KEY_AND_QUERY_PAYLOAD_LEAKAGE_POLICY.md`
7. `05D_SELECTOR_BOOTSTRAP_BASELINE_ONLY_PLAN.md`
8. `03G_IMPLEMENTATION_SEAM_FREEZE_CHECKLIST.md`
9. `06D_CRITICAL_BLOCKER_VALIDATION_SET.md`
10. `06J_CANONICAL_ACCEPTANCE_COMMAND_CONVENTION.md`
11. `06I_LOCAL_PERFORMANCE_BASELINE_AND_REGRESSION_CHECK_SPECIFICATION.md`

If implementation begins without these eleven, the setup is too loose.

Note: `03G` and `06D` are required because Stage 3 of the implementation workflow depends on them for execution-order conversion and blocker verification. Omitting them from the minimal packet would create an inconsistency with the staged workflow above.

If the current lane is the dedicated PageEvidence workbench lane, additionally require:
12. `03AB_EXACT_M6A_PAGE_EVIDENCE_WORKBENCH_AND_OPTION2_BOUNDARY.md`
13. `05I_M6A_PAGE_EVIDENCE_WORKBENCH_EXECUTION_PACKET.md`
14. `03AA_EXACT_M6_CONTROLLED_ADMISSION_AND_PROMOTION_MECHANISM.md`
15. `05H_M6_APPROVE_AS_IS_EXECUTION_PACKET.md`

---

## 5. Full implementation packet

For a full controlled implementation cycle, use:

### Control core
- `03M`
- `03N`
- `03U`
- `03V`
- `03W`
- `03P`

### Persistence / isolation / downstream protection
- `03I`
- `03J`
- `03K`
- `03L`
- `03Q`
- `03S`
- `03T`

### Execution and validation
- `05D`
- `05H`
- `05I`
- `05J`
- `05K`
- `05L`
- `06C`
- `06D`
- `06E`
- `06I`
- `06J`
- `06K`

### Current authority / residual state
- `00F`
- `00T`

For the current next lane, `05J` is the achieved evidence base, `05K` is the governing template, `05L` is the frozen approved-target record, and `05H` is the immediate direct-admission execution packet.

This is the most reliable working set for actual execution.

---

## 6. Correct implementation workflow

### Step 1 — restate the permitted change
Before coding, explicitly restate:
- selector key
- selector propagation path
- exact seam
- non-change surfaces

Use:
- `03U`
- `03V`
- `03W`
- `03M`
- `03N`

### Step 2 — identify regression-sensitive neighbors
Before coding, explicitly identify:
- review/report/runtime surfaces
- artifact-equivalence expectations
- diagnostics/runtime DB baseline locks

Use:
- `03Q`
- `03S`
- `03T`
- `03J`
- `03K`
- `03L`

### Step 3 — execute the smallest coherent implementation slice
Use:
- `05D`
- `03G`
- `06D`

The goal is not to edit broadly.
The goal is to preserve the frozen seam and keep surrounding surfaces stable.

### Step 4 — validate with the pack-defined command path
Use:
- `06J`
- `06K`
- `06C`

### Step 5 — validate with the pack-defined performance gate
Use:
- `06I`

### Step 6 — re-check against the blocker table
Use:
- `06E`

This workflow should be repeated for every meaningful slice.

---

## 7. What should be re-read repeatedly during implementation

Some docs are “read once.”
Some are “keep open while working.”

### Keep open while coding
- `03U`
- `03V`
- `03W`
- `03P`
- `03N`
- `05D`
- `06D`

### Re-read at validation time
- `06E`
- `06I`
- `06J`
- `06K`

### Re-read only when challenged or scope changes
- `00L`
- `00M`
- `00N`
- `00Q`
- `00R`
- `00S`
- `06L`

This distinction matters for practical use.

---

## 8. Implementation anti-patterns

Do not do any of these:

### Anti-pattern 1
Start from `05D` without first reading:
- `03U`
- `03V`
- `03W`

This causes sloppy seam assumptions.

### Anti-pattern 2
Treat `03U` as enough without `03P`
This causes selector leakage risk.

### Anti-pattern 3
Treat runtime-root separation as sufficient without reading:
- `03N`
- `03Q`
- `03S`
- `03T`

This causes false isolation assumptions.

### Anti-pattern 4
Treat validation as only command execution without `06I`
This removes the performance gate.

### Anti-pattern 5
Treat bounded residuals as permission to improvise
Residuals are bounded, not invitations to widen scope.

---

## 9. Best implementation review checkpoints

### Checkpoint A — before first code edit
Read:
- `00T`
- `03U`
- `03V`
- `03W`
- `03N`

Question:
- do I know exactly what I am allowed to change?

### Checkpoint B — before opening broader scope
Read:
- `03Q`
- `03S`
- `03T`
- `03L`
- `06E`

Question:
- would this wider change destabilize visibility/runtime/report surfaces?

### Checkpoint C — before claiming completion
Read:
- `06D`
- `06E`
- `06I`
- `06J`
- `06K`

Question:
- has the implementation been validated in the way the pack actually requires?

---

## 10. How to use the planning docs together during execution

### During design within implementation
Use:
- `03U`
- `03V`
- `03W`
- `03M`

### During safe coding
Use:
- `05D`
- `03G`
- `03P`
- `03N`

### During downstream impact checking
Use:
- `03Q`
- `03S`
- `03T`
- `03J`
- `03K`
- `03L`

### During acceptance
Use:
- `06C`
- `06D`
- `06E`
- `06I`
- `06J`
- `06K`

That is the correct cluster usage model.

---

## 11. Final implementation recommendation

If the intent is implementation preparation and execution:

1. begin with authority (`00T`, `00F`, `06E`)
2. freeze the exact implementation zone (`03U`, `03V`, `03W`)
3. freeze surrounding non-change surfaces (`03M`, `03N`, `03P`, `03Q`, `03J`, `03K`, `03L`)
4. use the bootstrap plan only after that (`05D`)
5. validate using the pack-defined command and performance surfaces (`06J`, `06K`, `06I`)

This is the strictest and most reliable implementation approach the current pack supports.


## 12. Reasoning / justification check before proceeding

Before implementation begins, also confirm against:

- `00U_ASSERTION_JUSTIFICATION_AND_EVIDENTIARY_STANDARD.md`
- `00V_PLANNING_TRACEABILITY_AND_DEPENDENCY_MATRIX.md`

Purpose:
- ensure that no implementation-critical rule is being followed only because it “sounds right”
- ensure that each critical planning assertion has a governing doc and evidence basis
