# 05P Post-Admission Retain Baseline Default Decision Record

## Purpose

Freeze the exact current-horizon decision that follows the merged M6B Candidate A admission and the later post-admission/defaulting planning freeze.

This is a decision record, not an implementation packet and not a program-decision amendment.

Merged `main` now contains this decision as authority, and its merged-main closure/handoff is recorded in:

- `05Q_POST_ADMISSION_RETAIN_BASELINE_MERGED_MAIN_CLOSURE_AND_HANDOFF.md`

---

## Governing basis

Read together:

1. `00D_MULTI_VARIANT_PROGRAM_DECISION.md`
2. `00F_LIVE_REPO_VERIFIED_FACTS_AND_OPEN_ITEMS.md`
3. `03AC_EXACT_POST_ADMISSION_DEFAULTING_SCOPE_AND_DECISION_BOUNDARY.md`
4. `05L_M6B_CANDIDATE_A_APPROVED_TARGET_RECORD.md`
5. `05M_M6B_CANDIDATE_A_ADMISSION_IMPLEMENTATION_RECORD.md`
6. `05N_M6B_MERGED_MAIN_CLOSURE_AND_POST_ADMISSION_HANDOFF.md`
7. `05O_POST_ADMISSION_DEFAULTING_PLANNING_FREEZE_PACKET.md`
8. `06E_BLOCKER_DECISION_TABLE.md`
9. `06I_LOCAL_PERFORMANCE_BASELINE_AND_REGRESSION_CHECK_SPECIFICATION.md`

---

## Exact decision

For the current horizon:

1. `baseline` remains the default.
2. `candidate_a_page_evidence_v1` remains admitted but non-default.
3. Candidate B and Candidate C remain non-admitted.
4. OCR-routing, media scope, policy tuning, threshold retuning, and outward variant-identity expansion remain locked.
5. No default-promotion target-definition lane opens from this decision.

---

## Why this is the correct current-horizon outcome

1. `00D` still carries the hard program rule that baseline remains default, and no explicit amendment to that rule exists.
2. `05M` and `05N` prove that the one approved Candidate A value is admitted and validated on merged `main`, but they do not provide authority to change the program-default rule.
3. `05O` explicitly allows a retain-baseline-default decision as one of only three valid planning outcomes.
4. No additional evidence packet has been frozen that would justify opening a program-decision amendment or default-promotion target-definition lane now.
5. The downstream review/document-trace/retrieval/evidence/report/export surfaces remain no-drift-sensitive and should not be widened by inference from successful Candidate A admission alone.

---

## What remains true after this decision

1. Missing, invalid, unsupported, and unapproved `visual_lane_mode` values still resolve to `baseline`.
2. `candidate_a_page_evidence_v1` remains the only admitted non-`baseline` selector value on merged `main`.
3. Candidate A remains review-visible under the already-admitted rules, but not default.
4. Every other explicit non-`baseline` value remains fail-closed and experiment-hidden.
5. The governing direct-admission boundary remains `03AA` + `05H`.
6. The accepted validation basis remains `05M` + `06I`.

---

## What this decision does not authorize

This decision does **not** authorize:

1. Candidate A default-promotion code
2. Candidate B or Candidate C admission
3. OCR-routing or media-scope widening
4. policy tuning or threshold retuning
5. new libraries, packages, schema surfaces, model changes, or migrations
6. outward variant-identity field expansion
7. any new implementation lane by implication

---

## Reopen rule

If a future proposal wants any outcome other than the retained current-horizon default posture above, it must first:

1. explicitly reopen the current `00D` baseline-default program rule
2. freeze a separate exact program-decision amendment record
3. freeze a separate exact later target-definition lane before any code begins

No later implementation lane should start from this record alone.

---

## Current next-step posture

At the time this decision record was frozen, the following was the correct next-step posture:

For the primary MVVLC milestone path, there is no additional implementation move justified by this record.

The only justified future moves are:

1. keep the retained-default state in place
2. later open an explicit program-decision amendment plus exact target-definition lane if new evidence or new goals justify it
3. pursue repo-native enforcement hardening as a separate parallel lane

This record closes the current-horizon post-admission/defaulting decision question without reopening scope.
That retained-default state has since been merged and handed off explicitly by `05Q`.
