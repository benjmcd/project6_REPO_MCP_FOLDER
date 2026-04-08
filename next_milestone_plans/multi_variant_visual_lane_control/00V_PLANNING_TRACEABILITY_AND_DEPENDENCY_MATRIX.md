# 00V Planning Traceability and Dependency Matrix

## Purpose

This document makes the pack easier to verify and safer to use.

Instead of forcing the reader to infer which documents justify which others, this matrix shows:

- which docs are foundational
- which docs depend on them
- what each document is for
- what evidence/governing docs support it
- how the document should be used

This is a reasoning/traceability layer, not a replacement for the documents themselves.

---

## 1. Foundational control spine

| Document | Primary role | Why it matters | Must be read with |
|---|---|---|---|
| `00F_LIVE_REPO_VERIFIED_FACTS_AND_OPEN_ITEMS.md` | evidence authority state | establishes what is actually verified, bounded, or still residual | `06E`, `00T` |
| `00D_MULTI_VARIANT_PROGRAM_DECISION.md` | macro program decision | states the high-level multi-variant intent and why the pack exists | `00F`, `06E` |
| `06E_BLOCKER_DECISION_TABLE.md` | blocker/status synthesis | compresses the control model into decision-ready blocker language | `00F`, `00T` |
| `00T_STRICT_ADEQUACY_AUDIT_AND_PROCEED_DECISION.md` | proceed judgment | states why proceeding is justified and what is still bounded | `00F`, `06L` |
| `03M_SELECTOR_ACTIVATION_SCOPE_AND_LIFETIME_POLICY.md` | selector activation control | constrains when/how selector behavior is allowed to matter | `03U`, `03V`, `03W` |
| `03N_EXPERIMENT_ISOLATION_MECHANISM_POLICY.md` | isolation control model | prevents false assumptions about experiment isolation | `03Q`, `03S`, `03T`, `03L` |
| `03AA_EXACT_M6_CONTROLLED_ADMISSION_AND_PROMOTION_MECHANISM.md` | target-definition and later direct-admission control | constrains the one-target admission lane and the exact record that must exist before code | `05K`, `05L`, `05H`, `03AB`, `05I`, `05J` |
| `03AB_EXACT_M6A_PAGE_EVIDENCE_WORKBENCH_AND_OPTION2_BOUNDARY.md` | achieved workbench control | constrains the dedicated PageEvidence / Option 2 workbench lane that now serves as precursor evidence for later direct admission | `05I`, `05J`, `03AA`, `05K`, `05L`, `05H` |
| `03AC_EXACT_POST_ADMISSION_DEFAULTING_SCOPE_AND_DECISION_BOUNDARY.md` | post-admission/defaulting planning boundary | constrains the later-scope planning phase after merged M6B closure, including the core owner path, review/document-trace, retrieval/evidence/report/export downstream surfaces, and dependency posture, and prevents default-promotion or wider variant work from starting by inference | `05O`, `05N`, `06E`, `00D`, `00F` |
| `03U_CANONICAL_SELECTOR_CONFIG_KEY_AND_FAIL_CLOSED_POLICY.md` | selector identity and fail behavior | defines the selector key and its safe interpretation | `03V`, `03P` |
| `03V_SELECTOR_KEY_INSERTION_AND_CONSUMPTION_MAP.md` | selector propagation path | defines where the key is normalized, forwarded, defaulted, and first consumed | `03U`, `03W` |
| `03W_EXACT_PROCESS_PDF_SEAM_FREEZE_SPECIFICATION.md` | seam freeze | defines the exact implementation surface allowed to vary | `03V`, `05D`, `06D` |

Interpretation:
- if someone does not understand these documents, they do not yet understand the pack

---

## 2. Implementation-constraining policy layer

| Document | Primary role | Governing basis | Implementation consequence |
|---|---|---|---|
| `03P_SELECTOR_CONTROL_KEY_AND_QUERY_PAYLOAD_LEAKAGE_POLICY.md` | prevent control-key leakage | `03U`, `03V`, live request normalization facts | selector cannot be treated like normal payload data |
| `03I_RUNTIME_ROOT_AND_RUN_NAMESPACE_POLICY.md` | runtime/root control | repo runtime discovery and visibility evidence | runtime separation must be reasoned about structurally |
| `03J_ARTIFACT_EQUIVALENCE_CONTROL_POLICY.md` | artifact contract stability | visual output/persistence surfaces | pass-1 work cannot casually change artifact semantics |
| `03K_DIAGNOSTICS_REF_PERSISTENCE_POLICY.md` | diagnostics persistence stability | diagnostics/runtime evidence | diagnostic references must remain stable unless explicitly reopened |
| `03L_RUNTIME_DB_BINDING_AND_ISOLATION_POLICY.md` | runtime DB isolation limits | review/runtime/run-binding evidence | DB binding remains a major leakage/control surface |
| `03Q_REVIEW_CATALOG_REPORT_VISIBILITY_BLOCKER_POLICY.md` | review/report visibility blocker | verified review/catalog/API/report/export evidence | root separation is insufficient by itself |
| `03S_REVIEW_API_ENDPOINT_EXPOSURE_MATRIX.md` | review API exposure detail | review API evidence | run-bound review surfaces remain critical |
| `03T_REPORT_EXPORT_RUN_VISIBILITY_MATRIX.md` | report/export exposure detail | report/export evidence | report/export persistence remains critical |

Interpretation:
- these docs should be used whenever implementation might affect downstream visibility, runtime, persistence, or artifact behavior

---

## 3. Execution and validation layer

| Document | Primary role | Governing basis | Use stage |
|---|---|---|---|
| `05D_SELECTOR_BOOTSTRAP_BASELINE_ONLY_PLAN.md` | implementation path sequencing | control spine + boundary docs | pre-implementation / active execution |
| `05H_M6_APPROVE_AS_IS_EXECUTION_PACKET.md` | later direct-admission execution packet | `03AA` + `05L` + achieved M5 barrier | later direct-admission execution |
| `05I_M6A_PAGE_EVIDENCE_WORKBENCH_EXECUTION_PACKET.md` | achieved workbench execution packet | `03AB` + achieved M5 barrier | achieved M6A execution reference |
| `05J_M6A_PAGE_EVIDENCE_WORKBENCH_IMPLEMENTATION_RECORD.md` | achieved workbench implementation record | `03AB` + `05I` + completed M6A validation | immediate evidence base for the frozen approved-target record and later direct admission |
| `05K_M6B_CANDIDATE_A_TARGET_RECORD_TEMPLATE.md` | governing target-record template | `03AA` + `05J` + achieved M5 barrier | exact shape for current and future approved-target records |
| `05L_M6B_CANDIDATE_A_APPROVED_TARGET_RECORD.md` | frozen approved Candidate A target record | `03AA` + `05J` + `05K` + achieved M5 barrier | immediate bridge into later direct-admission execution |
| `05M_M6B_CANDIDATE_A_ADMISSION_IMPLEMENTATION_RECORD.md` | achieved direct-admission implementation record | `03AA` + `05H` + `05L` + completed M6B validation | implementation-lane record for the admitted Candidate A lane that later merged |
| `05N_M6B_MERGED_MAIN_CLOSURE_AND_POST_ADMISSION_HANDOFF.md` | merged-main closure and next-scope handoff record | `05M` + merged PR `#21` + `06E` | reconciles the active pack to merged-main M6B closure and hands the pack forward into the now-frozen post-admission/defaulting planning phase |
| `05O_POST_ADMISSION_DEFAULTING_PLANNING_FREEZE_PACKET.md` | exact post-admission/defaulting planning packet | `03AC` + `05N` + `06E` | turns the next step from vague future scope into one bounded planning packet with explicit allowed outcomes, stop conditions, and downstream module/endpoint classes that must be reconsidered before any later widening |
| `05P_POST_ADMISSION_RETAIN_BASELINE_DEFAULT_DECISION_RECORD.md` | exact current-horizon default decision record | `00D` + `03AC` + `05O` + `05M` + `05N` + `06E` | records that the current horizon explicitly retains `baseline` as the default and prevents later default-promotion or additional-candidate work from being inferred without a new explicit amendment |
| `06C_ACTIVE_TEST_SURFACE_AND_COMMAND_MATRIX.md` | active test surface map | repo test evidence | validation preparation |
| `06D_CRITICAL_BLOCKER_VALIDATION_SET.md` | required validation gates | `06E` + policy docs | pre-claim-complete validation |
| `06I_LOCAL_PERFORMANCE_BASELINE_AND_REGRESSION_CHECK_SPECIFICATION.md` | performance gate | repo-native fixture sources + local policy | validation/performance |
| `06J_CANONICAL_ACCEPTANCE_COMMAND_CONVENTION.md` | conceptual acceptance path | test surface evidence | validation |
| `06K_SHELL_SPECIFIC_CANONICAL_ACCEPTANCE_COMMANDS.md` | concrete acceptance commands | `06J` + shell expression | validation/execution |

Interpretation:
- these docs become operational only after the control spine is understood

---

## 4. Navigation / workflow layer

| Document | Primary role | Why it exists | Best use |
|---|---|---|---|
| `00A_MASTER_NAVIGATION_AND_REVIEW_MAP.md` | pack traversal map | the pack is too large for flat reading | first re-entry / orientation |
| `00B_REVIEW_AUDIT_ASSESSMENT_PLAYBOOK.md` | review workflow | tells reviewers how to audit docs correctly | audit / challenge / adequacy review |
| `00C_IMPLEMENTATION_PREPARATION_AND_EXECUTION_PLAYBOOK.md` | implementation workflow | tells implementers how to use docs during real work | pre-implementation / implementation |
| `00S_NARROWING_STOP_RULE_AND_RECOMMENDATION.md` | stop-rule for narrowing | prevents endless low-value narrowing | process control / scope control |

Interpretation:
- these docs are meta-operational
- they guide how to use the pack, not what the selector architecture is

---

## 5. Narrowing / correction / residual layer

| Document | Primary role | What it narrows or corrects | How to read it |
|---|---|---|---|
| `00L_CLOSURE_CLAIM_RETRACTION_AND_BOUNDED_UNCERTAINTY.md` | retract over-strong closure claims | v25-style overclaim risk | read after `00F`, not before |
| `00M_ENFORCEMENT_AND_MIGRATION_SURFACE_AUDIT.md` | clarify enforcement/migration surfaces | too-broad residual risk framing | read as corrective narrowing |
| `00N_REPO_NATIVE_ENFORCEMENT_SURFACE_NARROWING.md` | narrow enforcement gap | vague enforcement residual | read with `06L` |
| `00O_SCHEMA_AND_CONTRACT_DRIFT_RISK_NARROWING.md` | narrow schema/contract residual | overly broad schema concern | read with `00P` |
| `00P_VISUAL_PAGE_CLASS_ROUNDTRIP_SUPPORT_NOTE.md` | downgrade a residual risk | `visual_page_class` pessimism | read as a correction |
| `00Q_NON_APP_LIVE_SURFACE_NARROWING.md` | narrow non-app residuals | broad non-app uncertainty | read after `00N` |
| `00R_ARCHIVE_AND_WORKTREE_DUPLICATION_NARROWING.md` | characterize archive/worktree residuals | vague outside-scope uncertainty | read as bounded residual refinement |
| `06L_BOUNDED_UNCERTAINTY_AND_ENFORCEMENT_GAP_REGISTER.md` | current residual register | where uncertainty still lives | read after `00L` / `00T` |

Interpretation:
- these docs are not the architecture
- they refine the confidence model around the architecture

---

## 6. “What justifies what?” quick matrix

### Selector control
- `03U` justified by:
  - live config normalization pattern
  - explicit processing-config forwarding pattern
  - fail-closed repo style
- `03V` justified by:
  - `03U`
  - exact function-path evidence
- `03W` justified by:
  - live helper decomposition inside `_process_pdf(...)`
  - `03V`
  - baseline-lock intent

### Isolation/visibility model
- `03N` justified by:
  - runtime/root evidence
  - review/catalog/API evidence
  - report/export/package evidence
- `03Q` / `03S` / `03T` justified by:
  - direct endpoint/service evidence
  - run-bound persistence/exposure evidence

### M6A achieved / M6B target-definition closure / later direct-admission split
- `03AB` justified by:
  - achieved M5 barrier closure
  - live dedicated evaluation-surface patterns in promotion/tuning tools and services
  - the explicit Option 2, Candidate A first decision
- `05I` justified by:
  - `03AB`
  - the need to keep workbench construction separate from direct integrated admission
  - the existing fresh-worktree execution pattern already used by MVVLC lanes
- `05J` justified by:
  - completed M6A workbench implementation and bounded validation
  - the need to carry forward exact repo-native evidence rather than only the earlier execution packet
- `05K` justified by:
  - `03AA`
  - `05J`
  - the need to define one exact approved target before direct-admission code begins
- `05L` justified by:
  - `05K`
  - the pinned canonical Candidate A report artifact in `05J`
  - the fixture-manifest comparison basis used to keep Candidate A scoped as seam-local visual-preservation behavior rather than document-class replacement
  - explicit user approval of the recommended Candidate A selector value, delta, and invariants
- `05M` justified by:
  - completed M6B owner-path implementation in the current clean worktree
  - full `05H` validation-bundle execution
  - rerun `06I` evidence within the frozen thresholds
  - the need to record the achieved lane explicitly rather than treating raw code diffs as closure by implication
- `05N` justified by:
  - PR `#21` merged the achieved M6B lane into `main`
  - the need to reconcile the active pack from pre-merge branch review language to merged-main closure
  - the need to name the next separate post-admission/defaulting planning freeze explicitly instead of leaving it implied
- `03AC` justified by:
  - merged `main` already admits Candidate A but still leaves broader defaulting/deferred scope unresolved
  - the need to enumerate exactly which modules, endpoints, dependencies, and widening classes belong to later-scope planning versus separate freezes
  - the need to keep later-scope questions bounded without treating merged M6B closure as implicit permission
- `05O` justified by:
  - `03AC`
  - the need to convert the post-admission/defaulting phase from a general note into a concrete decision packet
  - the need to constrain later outcomes to explicit no-code decisions before any future target-definition or implementation lane begins

### Proceed judgment
- `00T` justified by:
  - `00F`
  - `06E`
  - narrowing/correction docs
  - bounded residual framing

### Validation model
- `06J` / `06K` justified by:
  - active test surface evidence
  - import-path behavior
- `06I` justified by:
  - active fixture sources
  - absence of repo-native benchmark harness
  - explicit local gate policy

---

## 7. How to use this matrix

### If you are reviewing a doc
Use this matrix to identify:
- whether the doc is foundational or derivative
- which stronger docs constrain it
- which evidence docs justify it
- whether you are reading it too strongly

### If you are implementing
Use this matrix to identify:
- which docs are mandatory before edits
- which docs only matter at validation time
- which docs are residual/narrowing docs rather than implementation control docs

For the current milestone position:
- `03AB` + `05I` define the achieved M6A workbench lane
- `05J` is the achieved evidence record produced by that lane
- `03AA` + `05K` define the governing target-record shape
- `05L` is the achieved approved-target record for Candidate A
- `03AA` + `05H` are the governing direct-admission execution pair
- `05M` is now the achieved implementation record for the admitted Candidate A lane that merged into `main`
- `05N` is now the merged-main closure/handoff record for that achieved lane
- `03AC` + `05O` now freeze the exact post-admission/defaulting planning boundary and decision packet
- `05P` now freezes the current-horizon retain-`baseline` decision under that packet
- no further MVVLC implementation or default-promotion lane is justified by inference from the retained-default state

### If you are challenging adequacy
Use this matrix to ask:
- is this claim grounded in evidence?
- is it a policy conclusion or just a convenience statement?
- has a later narrowing doc reduced its force?

---

## 8. Final traceability rule

For any important planning claim, the reader should be able to identify:

1. the governing doc
2. the evidence doc or repo fact behind it
3. the neighboring docs that limit how it should be used

If that cannot be done, the claim is not adequately traceable yet.

This document exists so that standard can actually be met.
