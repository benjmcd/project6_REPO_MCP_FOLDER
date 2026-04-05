# 00U Assertion, Justification, and Evidentiary Standard

## Purpose

This document exists to make the pack stricter.

The pack now contains many planning assertions, determinations, scope decisions, and bounded assumptions.
Those are not all equal, and they should not be treated as if they are all grounded in the same way.

This document defines the standard that should be used when reading, reviewing, applying, or extending the pack.

---

## 1. Core rule

No material assertion in the planning pack should be treated as valid merely because it appears in a planning document.

Every material assertion should be interpreted through four questions:

1. **What kind of statement is this?**
2. **What evidence or reasoning supports it?**
3. **What stronger or governing document constrains it?**
4. **How hard is the statement allowed to be read?**

This rule applies even to small-sounding claims.

---

## 2. Statement classes

### Class A — Verified repo fact
A statement grounded directly in live repo evidence.

Examples:
- a function exists
- a caller chain exists
- a field is persisted
- an endpoint returns a run-bound payload
- a workflow file exists
- a migration file references a field

These are the strongest statements in the pack.

Primary authority:
- `00F_LIVE_REPO_VERIFIED_FACTS_AND_OPEN_ITEMS.md`
- direct evidence docs that fed into it

### Class B — Control policy / normative rule
A statement about what must be treated as allowed, disallowed, frozen, baseline-locked, or fail-closed.

Examples:
- selector must fail closed to baseline
- only the visual-preservation seam is allowed to vary in pass 1
- root separation alone is not sufficient isolation
- control keys must not leak into query payloads

These are not repo facts by themselves.
They are policy conclusions grounded in verified facts plus intent.

Primary authority:
- `03*` docs
- especially `03M`, `03N`, `03U`, `03V`, `03W`

### Class C — Derived planning conclusion
A statement that combines multiple verified facts into a broader planning judgment.

Examples:
- proceeding is justified
- narrowing should stop by default
- current residual uncertainty is non-blocking
- whole-pack review should happen in a particular order

These are justified conclusions, not raw evidence.

Primary authority:
- `00T`
- `00S`
- `06E`
- `00A`
- `00B`
- `00C`

### Class D — Bounded residual / non-closure statement
A statement that explicitly keeps uncertainty alive.

Examples:
- Python acceptance path is pack-specified but not visibly repo-enforced
- duplicated archive/worktree state remains outside the audited authority surface
- future drift remains possible

These are not weaknesses in the pack.
They are honesty constraints.

Primary authority:
- `00L`
- `00N`
- `00R`
- `06L`

---

## 3. Required support pattern for any material assertion

For a material assertion to be treated as adequate, the reviewer should be able to identify:

### A. Evidence basis
At least one of:
- direct repo fact
- explicit cross-doc reasoning
- explicit bounding statement

### B. Governing context
At least one stronger or controlling doc that tells you how far the assertion is allowed to go.

### C. Non-overclaim boundary
A point at which the assertion stops being safe to read more broadly.

If any of these are missing, the assertion is under-justified.

---

## 4. How to read small assertions correctly

Small assertions are where sloppy packs usually fail.

Examples of small assertions:
- “this document is foundational”
- “this path is implementation-critical”
- “this residual is non-blocking”
- “this doc should be read later”
- “this policy is baseline-locked”
- “this is only a watch-note, not an open blocker”

These still require justification.

The justification may be compact, but it must exist.

### Correct interpretation rule
A small assertion is only adequate if it can be traced to one of:
- explicit repo evidence
- a stronger governing control document
- an explicit narrowing/correction document
- an explicit stop-rule / proceed-rule

---

## 5. Strength hierarchy

When multiple docs seem to speak to the same issue, use this hierarchy.

### Highest interpretive weight
- `00F`
- `00T`
- `06E`
- foundational `03*` control docs
- direct evidence docs referenced by them

### Medium interpretive weight
- `05D`
- `06I`
- `06J`
- `06K`
- `00A`
- `00B`
- `00C`

### Narrowing/correction weight
- `00L`
- `00M`
- `00N`
- `00O`
- `00P`
- `00Q`
- `00R`
- `00S`
- `06L`

Rules:
- A later narrowing/correction doc can reduce the force of an earlier broader claim.
- A derivative doc should not be read as the core architecture unless it explicitly replaces it.
- **Non-override rule:** Medium-weight docs (navigation, workflow, playbook — `00A`, `00B`, `00C`) are operational aids. They organize and facilitate access to the pack but do not carry interpretive authority over highest-weight foundational, evidence, or control docs (`00F`, `00T`, `06E`, `03*` series). If a navigation/workflow doc appears to conflict with a foundational or control doc, the foundational or control doc governs.

### Non-authoritative same-directory artifacts

The following artifacts exist in the same directory as the active planning docs but are **not** part of the active control spine. They carry no interpretive authority unless explicitly promoted:

- `99_CLAUDE_CODE_AUDIT_NOTES_AND_RECOMMENDATIONS.md` — commentary/work product, not planning authority
- `mvvlc_reconciliation_checklist_v6.md` — working reconciliation artifact for hardening tasks, not architecture authority
- `multi_variant_visual_lane_program_spec_v2.md` — legacy/non-governing unless explicitly re-adopted

Do not let these artifacts override or reinterpret active planning docs.

---

## 6. Acceptable reasoning forms in this pack

### Strongest
Direct repo evidence + explicit policy conclusion.

### Strong
Multiple repo facts synthesized into a planning rule, with explicit boundaries.

### Acceptable
Operational/document-navigation guidance derived from already-settled policy and authority structure.

### Weak / not acceptable
Statements that rely on:
- tone
- repetition
- implication alone
- optimistic closure language
- undocumented extrapolation

The pack should reject the weak form wherever possible.

---

## 7. What to challenge when reviewing a doc

When reviewing any planning doc, ask:

1. Does this document distinguish evidence from policy from conclusion?
2. Does it rely on a stronger doc or direct evidence?
3. Does it overstate closure?
4. Does it silently expand scope beyond the frozen control model?
5. Does it assume repo-native enforcement where only pack-defined convention exists?
6. Does it leave small assertions unjustified?

If yes to 3–6, the doc needs tightening.

---

## 8. Practical adequacy rule

A planning doc in this pack is adequate when:

- its role is clear
- its scope is clear
- its claims can be traced
- its boundaries are explicit
- it does not overclaim beyond the evidence or stronger controlling docs

That is the standard to use before proceeding.

---

## 9. How this should affect future passes

Any future pass that adds or modifies planning content should make sure:

1. the new assertion class is obvious
2. the evidence basis is visible or cross-referenced
3. the governing doc is named
4. the boundary of the claim is explicit

If not, the new doc or edit is not strict enough.
