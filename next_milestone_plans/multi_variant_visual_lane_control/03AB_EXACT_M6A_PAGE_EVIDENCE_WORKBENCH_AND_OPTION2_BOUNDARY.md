# 03AB Exact M6A PageEvidence Workbench and Option 2 Boundary

## Purpose

Freeze the exact pre-admission workbench boundary for the dedicated PageEvidence / Candidate surface under Option 2.

This document exists because the chosen next step is no longer direct integrated admission alone.
The chosen next step is:

- build a dedicated PageEvidence workbench surface,
- use it to develop and compare Candidate A first,
- and keep direct integrated admission under the separate M6 packet fail-closed until one exact approved target is later named.

---

## Status note

This is a planning/freeze input for **M6A**, not direct integrated admission.

It does **not**:

- approve any non-`baseline` selector value,
- widen integrated runtime behavior,
- or authorize simultaneous baseline + A + B + C runtime support.

It freezes:

- the exact role of the dedicated PageEvidence workbench,
- the boundary between workbench work and later M6 direct admission,
- the allowed structure for Option 2 while Candidate A is still the only active candidate,
- and the anti-scaffolding rules needed to avoid a premature multi-variant framework.

Direct integrated admission remains governed by `03AA` + `05H`.

---

## Verified live anchors this mechanism is built on

1. `_process_pdf(...)` already contains a decomposed visual-preservation lane with helper-level boundaries frozen by `03W`.
2. `visual_lane_mode` already exists as the canonical selector key and currently fail-closes every non-`baseline` value back to `baseline` in the integrated owner path.
3. `review_nrc_aps_runtime.py` and the achieved M5 barrier already keep explicit non-`baseline` runs experiment-hidden by default.
4. `nrc_aps_promotion_gate.py`, `nrc_aps_promotion_tuning.py`, and their matching repo-native tool/test surfaces already establish a live pattern for dedicated evaluation surfaces that remain separate from default integrated runtime.
5. `visual_page_refs` and `visual_page_class` already persist through models, schemas, retrieval, evidence bundles, and review surfaces; that outward binary contract is part of the live baseline surface and must not be widened casually.
6. The strongest reviewed secondary-evidence set in `next_milestone_plans/sessions_to_be_reviewed` converges on a PyMuPDF-native PageEvidence direction for Candidate A, but those files remain secondary evidence only and do not override live repo authority.

---

## Exact M6A role

M6A is a **pre-admission workbench lane**.

Its job is to create one dedicated internal surface where Candidate A can be constructed, tuned, and compared without silently becoming integrated runtime behavior.

The M6A workbench may:

- define an internal PageEvidence schema and deterministic evidence derivation path,
- provide a standalone runner or workbench tool for isolated analysis,
- emit isolated comparison artifacts and evidence refs,
- and prepare a later exact approval record for one admitted selector value.

The M6A workbench may **not** by itself:

- make Candidate A a default integrated path,
- make Candidate A baseline-visible on outward surfaces,
- or convert Option 2 into a broad A/B/C runtime registry.

---

## Exact separation between workbench mode and admission mode

Three roles must remain distinct:

1. **Standalone workbench mode**
   - explicit, out-of-band, isolated, and non-default
2. **Optional companion-run mode**
   - only if later explicitly widened and recorded
   - not the default starting mode for M6A
3. **Integrated admission mode**
   - still governed by `03AA` + `05H`
   - still blocked until one exact approved target is named

Interpretation rule:

- workbench construction is not admission
- companion-run experimentation is not admission
- passing workbench experiments are not approval
- only an explicit later M6 admission record can authorize integrated runtime widening

---

## Exact Option 2 boundary for Candidate A-C

Option 2 is accepted only in this constrained form:

- one **shared** dedicated PageEvidence/Candidate workbench surface is allowed,
- Candidate A is the only active candidate in the first workbench lane,
- Candidate B and Candidate C remain conceptual later candidates only,
- and no per-candidate runtime framework should be introduced yet.

This means the first dedicated surface is:

- shared by design,
- immediately used by Candidate A,
- and not allowed to become dormant A/B/C scaffolding.

Rejected forms of Option 2:

- separate empty `candidate_a`, `candidate_b`, `candidate_c` code trees
- a generic registry for unlimited variant plug-ins
- placeholder enums or selector values for B/C with no immediate live use
- workbench logic that also silently becomes the integrated default path

---

## Exact filesystem and ownership rule

The workbench should be realized using existing repo-native surfaces, not a brand-new top-level subsystem.

Default filesystem roles:

- `backend/app/services/` for shared PageEvidence logic
- `tools/` for explicit standalone workbench runners
- `backend/tests/` for unit/service-level workbench tests
- `tests/` for root-side functional runner/workbench tests

The M6A workbench does **not** require:

- a new top-level repo directory
- candidate-specific A/B/C folders
- baseline-specific folder duplication
- or any edits in the dirty root workspace

Worktree role rule:

- current planning/freeze work happens in `worktrees/mvvlc-candidate-a-freeze-next`
- later workbench implementation should start from a fresh merged-`main` worktree, recommended name `worktrees/mvvlc-page-evidence-workbench-next`
- later direct admission should start from a separate fresh merged-`main` worktree, recommended name `worktrees/mvvlc-candidate-a-admission-next`

If equivalent fresh merged-`main` worktrees are used with different names, that is acceptable.
The root dirty workspace is not acceptable.

---

## Exact outward-contract rule

The first M6A workbench lane must preserve the outward binary baseline contract unless a later stronger freeze explicitly reopens it.

That means:

- no new outward variant-identity fields
- no review/API/report/export schema widening for candidate identity
- no direct change to the public meaning of `visual_page_class`
- no default integrated behavior change

Internal PageEvidence richness is allowed.
Outward binary compatibility remains the default requirement.

---

## Exact non-goals of M6A

This workbench freeze does **not** authorize:

- direct admission of Candidate A into integrated runtime
- any admitted selector value beyond `baseline`
- simultaneous A/B/C implementation
- OCR / hybrid OCR / media-scope redesign
- ML-heavy default-path replacement of the current visual lane
- shared seeded runtime data generation
- or new outward review/runtime/report/export identity surfaces

---

## Result

The pack is now allowed to split M6 into two bounded steps:

- **M6A** - Candidate A PageEvidence workbench construction and isolated evidence capture
- **M6B** - later controlled admission of one explicitly approved selector value under `03AA` + `05H`

This closes the planning ambiguity introduced by choosing Option 2.
It does not yet authorize code.
