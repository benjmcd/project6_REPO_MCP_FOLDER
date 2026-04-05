# Multi-Variant Visual Lane Control Pack

## Current state

This is the planning and control pack for baseline-preserving integrated selector bootstrap, scoped to the PDF visual-lane only.

The pack is materially closed at the planning/control level. That does **not** mean implementation is done. It means the planning layer no longer has a major unresolved structural blocker.

### What is closed

- Selector config key: `visual_lane_mode`, normalized, forwarded, defaulted, fail-closed to `baseline` (`03U`, `03V`)
- Exact seam boundary: helper-contract freeze at the visual-preservation lane (`03W`)
- Acceptance command convention: conceptual + shell-specific realizations for PowerShell, CMD, POSIX (`06J`, `06K`)
- Residual consumer/visibility closure: app-surface consumers explicitly enumerated (`00K`, `03X`)
- Local performance gate: defined (`06I`), execution pending on applying frozen command convention

### What requires implementation

- Seam-internal branch behavior within the frozen seam
- Control-key / query-payload exclusion behavior
- Runtime-root coexistence mechanism for experiments
- Review/catalog/report/API/export visibility controls for experiment runs
- Diagnostics persistence and runtime DB binding no-change rules
- Artifact equivalence acceptance procedure

### What is bounded residual

- Repo-native Python acceptance-path enforcement (pack-specified, not CI-enforced)
- Future drift outside audited authority surface

---

## How to use this pack

### First time
1. `00A_MASTER_NAVIGATION_AND_REVIEW_MAP.md` — front-door navigation
2. `00F_LIVE_REPO_VERIFIED_FACTS_AND_OPEN_ITEMS.md` — factual backbone

### For review / audit
- `00B_REVIEW_AUDIT_ASSESSMENT_PLAYBOOK.md`

### For implementation
- `00C_IMPLEMENTATION_PREPARATION_AND_EXECUTION_PLAYBOOK.md`

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
- **v8–v9:** Tightened selector-config guidance, control-key leakage policy, runner-convention evidence
- **v10–v11:** Incorporated session-origin evidence, tightened experiment-isolation model, added review API exposure matrix
- **v12–v13:** Verified report/export visibility blocker, tightened direct backend caller closure
- **v14–v15:** Narrowed runner-convention and consumer-closure uncertainties
- **v16–v17:** Closed framework-choice question, narrowed acceptance-command convention
- **v18–v19:** Defined local performance gate, closed acceptance-command conceptual convention
- **v20–v21:** Froze canonical selector key (`visual_lane_mode`), mapped insertion/consumption points
- **v22:** Closed acceptance-command item with shell-specific realizations
- **v23:** Froze exact seam boundary via helper-contract specification
- **v24–v25:** Closed residual consumer/visibility item
- **v26–v29:** Bounded uncertainty corrections, enforcement gap narrowing, schema/contract evidence
- **v30–v32:** Non-app surface checks, worktree/archive narrowing, stop rule

### Important correction (v26)
The v25 claim of "no remaining open items" was too strong. The evidence supports material strength for the audited live app authority surface, but not total project closure or repo-native operational enforcement. A bounded uncertainty set was reopened and is now explicitly tracked in `06L`.

---

## Use rule

This remains a control pack.
Do not convert candidate control ideas into code without explicit freeze.
Do not treat planning closure as proof that implementation already exists.
