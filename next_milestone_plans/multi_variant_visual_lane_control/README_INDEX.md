# Multi-Variant Visual Lane Control Pack

## Current state

This is the planning and control pack for the MVVLC program, still bounded to the PDF visual-lane seam.

Merged `main` now contains the baseline-only selector/bootstrap implementation, the recorded M4 acceptance closure for that baseline path, and the bounded M5 coexistence / visibility barrier implementation. The pack's current job is to preserve those closures, carry the bounded residuals honestly, and define the next later-scope lane explicitly.

### What is closed

- Selector config key: `visual_lane_mode`, normalized, forwarded, defaulted, fail-closed to `baseline` (`03U`, `03V`)
- Exact seam boundary: helper-contract freeze at the visual-preservation lane (`03W`)
- M3 selector path: baseline-preserving seam consumption is implemented in the frozen owner path (`05D`, `06E`)
- M4 baseline-only acceptance gate: T1-T8 and the local `06I` performance gate were executed and recorded for the merged baseline path (`05D`, `06C`, `06E`, `06I`)
- Review/report/export field-sensitivity map: standalone later-scope exposure inventory is now frozen (`03Y`)
- M5 execution packet boundary: exact owner/test/widening boundary is now frozen (`05F`)
- M5 coexistence / visibility mechanism: exact baseline-facing classification and runtime-root coexistence design is frozen and implemented on merged `main` (`03Z`, `05G`)
- M5 barrier implementation record and handoff: exact owner files, validations, `06I` rerun, and no-drift judgment are recorded (`05G`)
- Artifact equivalence acceptance surface: operational and green under the canonical grouped T7 bundle (`03J`, `06C`, `06D`, `06E`)
- Review/runtime acceptance surface: operational and green under the canonical grouped T8 bundle (`03L`, `06C`, `06D`, `06E`)
- Acceptance command convention: conceptual + shell-specific realizations for PowerShell, CMD, POSIX (`06J`, `06K`)
- Residual consumer/visibility closure: app-surface consumers explicitly enumerated (`00K`, `03X`)

### Current milestone position

- M3 baseline-only selector/bootstrap is implemented and accepted on merged `main`
- M4 acceptance gate is passed for the baseline-only bootstrap path
- M5 later-scope coexistence / visibility barrier is implemented and locally validated on merged `main` under the frozen `03Z` + `05F` packet (`05G`, `06E`)
- M6 planning/freeze packet is now frozen on the current clean branch as `03AA` + `05H`
- The next justified MVVLC milestone step is bounded M6 admission implementation only after one approved target is explicitly named, not more M5 mechanism implementation

### Next lane to execute

- Record one exact approved non-baseline selector value before any M6 code edits
- Implement only the frozen M6 admission boundary under `03AA` + `05H`
- Keep M5 barrier closure intact for all non-approved values
- Do not treat the M6 packet as permission for uncontrolled multi-variant integrated rollout

### What is bounded residual

- Repo-native Python acceptance-path enforcement (pack-specified, not CI-enforced)
- Tier 2 performance capture breadth: the recorded artifact-aware comparison uses the declared-root handoff fallback sample because the preferred real-ADAMS timed capture did not complete within practical session budget
- Future drift outside audited authority surface
- Exact approved M6 target is not yet named in the pack; implementation remains fail-closed until that record exists

---

## How to use this pack

### First time
1. `00A_MASTER_NAVIGATION_AND_REVIEW_MAP.md` - front-door navigation
2. `00F_LIVE_REPO_VERIFIED_FACTS_AND_OPEN_ITEMS.md` - factual backbone

### For review / audit
- `00B_REVIEW_AUDIT_ASSESSMENT_PLAYBOOK.md`

### For implementation
- `00C_IMPLEMENTATION_PREPARATION_AND_EXECUTION_PLAYBOOK.md`
- `05E_POST_M4_APPROVAL_READY_NEXT_LANE_PLAN.md`
- `03Z_EXACT_M5_BASELINE_VISIBILITY_AND_RUNTIME_ROOT_COEXISTENCE_MECHANISM.md`
- `05F_M5_APPROVE_AS_IS_EXECUTION_PACKET.md`
- `05G_M5_BARRIER_IMPLEMENTATION_RECORD_AND_M6_HANDOFF.md`
- `03AA_EXACT_M6_CONTROLLED_ADMISSION_AND_PROMOTION_MECHANISM.md`
- `05H_M6_APPROVE_AS_IS_EXECUTION_PACKET.md`

### For "can we proceed?"
- `00T_STRICT_ADEQUACY_AUDIT_AND_PROCEED_DECISION.md`

### For reasoning / traceability
- `00U_ASSERTION_JUSTIFICATION_AND_EVIDENTIARY_STANDARD.md`
- `00V_PLANNING_TRACEABILITY_AND_DEPENDENCY_MATRIX.md`

---

## Directory artifact classification

### Active planning docs (control spine)
All `00*`, `03*`, `05*`, `06*` docs listed in `00A` are active planning docs forming the implementation-control baseline.

### Non-authoritative same-directory artifacts
| Artifact | Status | Role |
|---|---|---|
| `99_CLAUDE_CODE_AUDIT_NOTES_AND_RECOMMENDATIONS.md` | Non-authoritative | Commentary/work product |
| `mvvlc_reconciliation_checklist_v6.md` | Working artifact | Hardening task control, not architecture authority |
| `multi_variant_visual_lane_program_spec_v2.md` | Legacy | Non-governing unless explicitly re-adopted |
| `claude_code_hardening_task.txt` | Task input | Hardening task specification |
| `MANIFEST.json` | Metadata | Pack manifest |

Do not treat non-authoritative artifacts as active planning authority. See `00U` Section 5 for the strength hierarchy.

---

## Pack evolution history

This pack evolved through 32+ revisions. Key milestones:

- **v7:** Added selector activation scope/lifetime policy, experiment isolation mechanism, critical blocker validation set
- **v8-v9:** Tightened selector-config guidance, control-key leakage policy, runner-convention evidence
- **v10-v11:** Incorporated session-origin evidence, tightened experiment-isolation model, added review API exposure matrix
- **v12-v13:** Verified report/export visibility blocker, tightened direct backend caller closure
- **v14-v15:** Narrowed runner-convention and consumer-closure uncertainties
- **v16-v17:** Closed framework-choice question, narrowed acceptance-command convention
- **v18-v19:** Defined local performance gate, closed acceptance-command conceptual convention
- **v20-v21:** Froze canonical selector key (`visual_lane_mode`), mapped insertion/consumption points
- **v22:** Closed acceptance-command item with shell-specific realizations
- **v23:** Froze exact seam boundary via helper-contract specification
- **v24-v25:** Closed residual consumer/visibility item
- **v26-v29:** Bounded uncertainty corrections, enforcement gap narrowing, schema/contract evidence
- **v30-v32:** Non-app surface checks, worktree/archive narrowing, stop rule

### Important correction (v26)
The v25 claim of "no remaining open items" was too strong. The evidence supports material strength for the audited live app authority surface, but not total project closure or repo-native operational enforcement. A bounded uncertainty set was reopened and is now explicitly tracked in `06L`.

---

## Use rule

This remains a control pack.
Do not convert candidate control ideas into code without explicit freeze.
Do not reopen merged M3/M4 closure without live contradictory evidence.
Do not treat achieved M5 barrier closure as permission to admit approved non-baseline integrated runs without a separate frozen M6 packet.
Do not treat the frozen M6 packet as permission to start code before one exact approved target is explicitly named.
