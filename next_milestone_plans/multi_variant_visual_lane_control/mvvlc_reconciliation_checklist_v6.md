# MVVLC Reconciliation Checklist v5
_Last updated: 2026-04-05_

## Purpose

This checklist is the controlling reconciliation and execution-order gate for the
`next_milestone_plans/multi_variant_visual_lane_control` pack.

It exists to prevent:
- planning-closure being mistaken for implemented state,
- navigation/workflow docs being mistaken for technical authority,
- sidecar/session artifacts contaminating the control spine,
- stale open/closed language drifting across related docs,
- and implementation starting before the planning pack is strict enough.

---

## 0. Authority boundary

Before any planning-doc edit or implementation-preparation work:

- Treat active planning docs as the only candidates for implementation-control baseline.
- Treat `99_CLAUDE_CODE_AUDIT_NOTES_AND_RECOMMENDATIONS.md` as non-authoritative audit commentary.
- Treat exported sessions as tertiary evidence only.
- Treat `multi_variant_visual_lane_program_spec_v2.md` as non-governing unless explicitly re-adopted.
- Treat narrowing/candidate/support docs as subordinate to foundational/evidence/control docs.

### Required explicit status outcome
At minimum, the pack should clearly distinguish:
- authoritative active docs,
- workflow/navigation aids,
- historical narrowing/support docs,
- candidate-only notes,
- sidecars,
- archival/legacy artifacts.

---

## 1. Tier-1 must-fix docs before using the pack as implementation-control baseline

### 1. `06D_CRITICAL_BLOCKER_VALIDATION_SET.md`
**Why**
- Duplicate/ambiguous blocker numbering.
- Gate rule does not clearly govern the full blocker set.

**Required outcome**
- One clean blocker set.
- One clean numbering scheme.
- One gate rule covering the full set.

### 2. `00F_LIVE_REPO_VERIFIED_FACTS_AND_OPEN_ITEMS.md`
**Why**
- Reused numbering across sections.
- Fact / implication / closure-state / open-item categories are mixed too loosely.
- Stale acceptance-command open/closed wording still present.

**Required outcome**
- Namespaced identifiers or equivalent unambiguous item scheme.
- Distinct sections for verified facts, inferred implications, closure state, and bounded residuals.
- Synchronize command-convention state with `06K`.

### 3. `06E_BLOCKER_DECISION_TABLE.md`
**Why**
- Several rows, especially selector-path closure, read too much like implemented-state closure.

**Required outcome**
Each row must distinguish:
- planning/control closure,
- implementation work still required,
- true closure,
- bounded residual.

### 4. `00U_ASSERTION_JUSTIFICATION_AND_EVIDENTIARY_STANDARD.md`
**Why**
- Workflow/navigation docs still carry too much interpretive force.

**Required outcome**
- Explicit non-override rule.
- Explicit category discipline.
- Explicit treatment of non-authoritative sidecars / legacy docs.

### 5. `00C_IMPLEMENTATION_PREPARATION_AND_EXECUTION_PLAYBOOK.md`
**Why**
- Stage 3 requires `05D`, `03G`, `06D`.
- Minimal implementation packet omits `03G` and `06D`.

**Required outcome**
- Internal consistency between staged workflow and minimal packet.
- Explicit statement that workflow docs do not override stronger technical authority.

### 6. `05D_SELECTOR_BOOTSTRAP_BASELINE_ONLY_PLAN.md`
**Why**
- Preconditions are still too implicit.
- Seam-checklist dependency is not explicit enough.

**Required outcome**
- Explicit linkage to `03G` and `03W`.
- Preconditions stated as condition + governing doc(s), where practical.

### 7. `06C_ACTIVE_TEST_SURFACE_AND_COMMAND_MATRIX.md`
**Why**
- Mixes verified tests, grouped bundles, candidate forms, and acceptance gates.

**Required outcome**
Split into:
- verified file-level tests,
- command bundles,
- acceptance-gating requirements,
- interpretation rule.

### 8. `03H_SELECTOR_CONFIG_INSERTION_POLICY.md`
**Why**
- Internally contradictory: unresolved selector key vs canonical `visual_lane_mode`.

**Required outcome**
- Remove stale unresolved wording or clearly frame it as chronology.
- Synchronize with `03U` and `03V`.

### 9. `06J_CANONICAL_ACCEPTANCE_COMMAND_CONVENTION.md`
**Why**
- Stale “still open” wording coexists with shell realization closure.

**Required outcome**
- Synchronize closure language to `06K`.
- Distinguish conceptual convention, shell realization, and repo-native enforcement.

### 10. `00A_MASTER_NAVIGATION_AND_REVIEW_MAP.md`
**Why**
- Needs stronger implementation-packet consistency and directory-level authority hygiene.

**Required outcome**
- Clarify active implementation packet.
- Clarify non-authoritative same-directory artifacts.
- Clarify that navigation does not override stronger docs.

### 11. `README_INDEX.md` (Tier-1 if another agent will use it as entry point)
**Why**
- Historically layered front door.
- Stale unresolved-state language near the top.
- No sufficiently explicit classification of same-directory artifacts.

**Required outcome**
- Current-state front door, not accumulated revision narrative.
- Explicit status classification for active vs historical vs sidecar vs archival docs.

---

## 2. Tier-2 strong recommended synchronization/hardening

### `06F_RUNNER_CONVENTION_EVIDENCE_AND_REMAINING_UNCERTAINTY.md`
- Historical narrowing doc with stale closure drift.
- Should be synchronized to `06K` or marked superseded operationally.

### `06H_ACCEPTANCE_COMMAND_CONVENTION_NARROWING_REPORT.md`
- Same stale “what remains open” vs “concept now frozen” structure.
- Should be synchronized to `06K` or explicitly marked historical.

### `03V_SELECTOR_KEY_INSERTION_AND_CONSUMPTION_MAP.md`
- Needs current mechanism vs required addition vs target-state structure.

### `03Q_REVIEW_CATALOG_REPORT_VISIBILITY_BLOCKER_POLICY.md`
- Keep blocker posture, but reduce universal-sounding overstatement.

### `00V_PLANNING_TRACEABILITY_AND_DEPENDENCY_MATRIX.md`
- Replace abstract “justified by” phrases with exact doc references where possible.

### `00T_STRICT_ADEQUACY_AUDIT_AND_PROCEED_DECISION.md`
- Add explicit distinction between planning adequacy and implemented-state proof.


### `00B_REVIEW_AUDIT_ASSESSMENT_PLAYBOOK.md`
- Conditional synchronization surface.
- Not a Tier-1 blocker on its own, but once `README_INDEX.md`, `00A`, `00F`, `00T`, and `06E` are corrected, `00B` should be updated so reviewer workflow does not preserve stale authority/currentness assumptions.
- In particular, its mandatory starting-doc and whole-pack review order should remain aligned with the corrected front-door and proceed/closure documents.

### `06L_BOUNDED_UNCERTAINTY_AND_ENFORCEMENT_GAP_REGISTER.md`
- Keep synchronized with actual residuals.
- Do not absorb late-session alarms without bounded live-code recheck.

---

## 3. Archive / status hygiene

### `99_CLAUDE_CODE_AUDIT_NOTES_AND_RECOMMENDATIONS.md`
Required banner:
- non-authoritative sidecar,
- commentary/work product,
- not part of active control spine unless promoted later.

### `multi_variant_visual_lane_program_spec_v2.md`
Required action:
- move out of active pack directory, or
- mark clearly as legacy / archival / non-governing unless re-adopted.

### `06G_PERFORMANCE_BUDGET_EVIDENCE_AND_REMAINING_UNCERTAINTY.md`
- Mark as supporting evidence / narrowing support, not primary execution authority.

### `03R_DOCUMENT_TYPE_THREADING_CANDIDATE_POLICY.md`
- Keep explicitly candidate-only and non-governing.

---

## 4. Command-convention cluster rule

Treat `06K_SHELL_SPECIFIC_CANONICAL_ACCEPTANCE_COMMANDS.md` as the anchor for the command-convention cluster.

That means:
- `06J`
- `06F`
- `06H`

must all be synchronized to `06K` rather than each carrying independent closure narratives.

### Required interpretation
- `06K` anchors shell-level canonical realization.
- `06J` should anchor conceptual convention.
- `06F` / `06H` should either:
  - be synchronized support docs, or
  - be explicitly marked historical/superseded.

---

## 5. Bounded live-code verification pass (after Tier-1 doc hardening, before implementation)

Do one bounded recheck only.

### Questions
1. What is the exact selector-path implementation gap?
2. Which T2–T6 bundles are truly current/active versus historical/provisional?
3. Do the late memory/storage-risk claims hold up enough to promote into the pack?
4. Are there any materially relevant hidden consumers outside the already-audited app-surface chain?

### Output format
Only:
- verified repo fact,
- planning implication,
- bounded residual.

No broad new audit rhetoric.

---

## 6. Proceed gate

### Do not proceed to implementation if:
- Tier-1 doc hardening is incomplete, or
- the bounded live-code pass finds a new architecture blocker severe enough to widen scope.

### Proceed to controlled implementation only if:
- Tier-1 docs are hardened,
- command-convention cluster is synchronized to `06K`,
- reviewer/entry-point workflow docs that will actually be used (`README_INDEX.md`, `00A`, and conditionally `00B`) are synchronized to the corrected authority model,
- sidecar / session / legacy authority contamination is neutralized,
- and bounded live-code recheck does not reveal a new blocker-level architecture issue.

---

## 7. Immediate next action

The next agent should be assigned a **doc-only hardening pass** against Tier-1, with no code edits.

Only after that should the bounded live-code verification pass run.
