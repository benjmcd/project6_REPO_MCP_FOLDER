# Multi-Variant Visual Lane Program Spec v2

## 1. Purpose

This spec defines how to preserve the current visual-lane baseline while enabling three separate baseline-derived experimental tracks without breaking the repo’s existing behavior, contracts, artifact semantics, or adjacent APS flows.

This is **not** a generic redesign spec. It is a contract-sensitive program spec for a repo whose current live implementation is broader and more interconnected than a single file-level lane swap.

## 2. Live-repo facts verified before this revision

From the live repo:

- Primary owner file remains `backend/app/services/nrc_aps_document_processing.py`.
- `process_document(...)` is a single entry point routing by content type:
  - `text/plain`
  - `application/pdf`
  - image content types
  - `application/zip`
- The visual lane is currently embedded inside `_process_pdf(...)`.
- Active visual classes are binary:
  - `diagram_or_visual`
  - `text_heavy_or_empty`
- `_has_significant_visual_content(page)` returns true if:
  - any `page.get_images()` entry has width and height `>= 100`, or
  - `len(page.get_drawings()) >= 20`
- OCR fallback inside `_process_pdf(...)` separately uses `has_significant_image` based only on `page.get_images()` and the same `>=100x100` rule.
- Visual artifact writing remains conditional on `artifact_storage_dir`.
- `default_processing_config(...)` exists and is the natural first config insertion point, but it currently does not contain a variant selector.

## 3. Why the earlier spec was not closed enough

The earlier multi-variant plan was directionally right, but under-scoped in several ways:

1. It treated this too much like a local lane swap.
2. It did not explicitly freeze media-type scope.
3. It did not define where variant identity may appear.
4. It was not strict enough about OCR-vs-visual shared evidence boundaries.
5. It implied integration of three variants too early.
6. It did not explicitly baseline-lock replay/promotion/safeguard/review/report surfaces.
7. It did not fully require live active test-surface closure before implementation.

## 4. New repo-wide constraints discovered

The repo has a broader APS ecosystem than the earlier plan captured. Adjacent live modules include:

- `nrc_aps_contract.py`
- `nrc_aps_artifact_ingestion.py` and gate module
- `nrc_aps_evidence_bundle*`
- `nrc_aps_evidence_report*`
- `nrc_aps_evidence_report_export*`
- `nrc_aps_evidence_citation_pack*`
- `nrc_aps_replay_gate.py`
- `nrc_aps_promotion_gate.py`
- `nrc_aps_promotion_tuning.py`
- `nrc_aps_safeguards*`
- `nrc_aps_live_batch.py`
- `review_nrc_aps_*`

Therefore, any multi-variant architecture must be designed as a repo-level controlled program, not as a free local duplication exercise.

## 5. Program goals

### 5.1 Primary goals
1. Preserve one frozen baseline as the default and reference truth.
2. Create three baseline-derived experimental tracks for independent work.
3. Allow controlled comparison and bakeoff across baseline and approved variants.
4. Prevent contract drift and unrelated repo breakage.
5. Make rollback to the frozen baseline immediate and reliable.
6. Avoid permanently hardcoding the repo to one inseparable implementation.

### 5.2 Secondary goals
1. Support stricter vs looser strategies.
2. Support both implementation variants and tuning-profile variants.
3. Support human-only, AI-assisted, or AI-led experimental work.
4. Preserve auditability and evidence-based promotion.

## 6. Non-goals for current scope

Do not assume, for current scope:

1. outward taxonomy changes
2. artifact writer byte/path/hash changes
3. DB/API/report/review contract redesign
4. plugin-first generalization of the whole ingestion plane
5. all four implementations running in normal runtime immediately
6. model/layout-system default-path integration
7. full OCR subsystem redesign

## 7. The key architectural determination

## 7.1 Best overall structure
Use a **hybrid model**:

- one frozen baseline
- three experimental variant worktrees/branches
- one bounded in-repo selector seam
- baseline integrated first as default
- experimental variants stay worktree-only until they meet integration criteria

This is still the best overall direction.

## 7.2 Critical correction
Do **not** first introduce a selector and wire in baseline + A + B + C simultaneously.

Correct staged rule:

1. integrate selector seam with **baseline only**
2. verify no contract/consumer breakage
3. only then allow one approved experimental variant at a time into the integrated registry

## 8. First-scope selector boundary

### 8.1 Media-type scope
The first selector seam must be **PDF visual-lane only**.

It must **not** initially change:
- plain-text processing
- image processing
- ZIP processing
- generic `process_document(...)` media routing semantics

### 8.2 Functional scope
The first swappable boundary should cover only:

- shared page evidence derivation for PDF pages
- visual-preservation decision logic
- provenance / comparison hooks
- optional deterministic rule derivation inputs

It should **not** initially own:

- artifact writer semantics
- API/report/export/review contract shapes
- persistence schema
- replay/promotion/safeguard policy
- top-level media routing
- the entire PDF pipeline as one swappable block

## 9. Variant identity policy

Variant identity must **not** leak into public or contract-sensitive surfaces in the first scope.

### 9.1 Allowed initially
- internal telemetry
- bakeoff outputs
- controlled diagnostics
- local comparison artifacts
- explicit experiment manifests

### 9.2 Forbidden initially
- public API contract fields
- report/export/review payloads
- persistence surfaces unless explicitly approved later
- artifact ref/path/hash behavior
- default user-facing output surfaces

## 10. OCR vs visual split

Current live code has two related but non-identical signal consumers:

- OCR fallback uses image significance only
- visual preservation uses broader visual significance (image or drawings)

So the first seam must introduce:

- a shared evidence layer
- separate consumer decisions for OCR and visual preservation

It must **not** first replace the whole `_process_pdf(...)` logic with one large monolithic variant swap.

## 11. Required invariants in current scope

Unless re-scoped later, all integrated variants must preserve:

1. outward binary visual contract
2. existing artifact writer semantics
3. existing persistence / downstream contract assumptions
4. baseline default selection behavior
5. no hidden dependency inflation in default path
6. explicit provenance in internal telemetry
7. immediate rollback to baseline

## 12. Variant types

### Type A — Baseline replay variant
- exact reference behavior
- default integrated implementation
- contract-stable
- artifact-stable

### Type B — Deterministic contract-stable experimental variant
- new evidence/routing logic
- same outward contract
- eligible for promotion later

### Type C — Experiment-only research variant
- worktree/manual/bakeoff only
- not integrated into normal runtime at first
- can diverge more internally
- cannot become default without promotion

### Type D — Ambiguity-only extension variant
- bounded extra logic for uncertain cases only
- stricter runtime controls
- not a first-pass requirement

## 13. Variant vs tuning profile

Not every “strict vs loose” idea needs a full variant.

We need two separate concepts:

### Implementation variant
Different architecture or evidence/routing approach.

### Tuning profile
Same implementation shape, different thresholds or strictness.

Default rule:
- use tuning profiles first where possible
- reserve full variant tracks for materially different logic structures

## 14. Selector model

## 14.1 First integrated selector
The selector should be introduced via config, likely through `default_processing_config(...)` or the nearest validated config surface.

### 14.2 Required selector properties
- defaults to baseline
- explicit opt-in for non-baseline
- logs chosen variant internally
- can be invoked from tests and bakeoff harnesses
- denies unsupported contexts
- cannot silently widen scope beyond PDF visual lane in pass 1

### 14.3 Failure behavior
- strict mode: explicit error on invalid selection
- normal runtime: fail closed to baseline or explicit error according to policy
- always log resolution internally

## 15. Development model

## 15.1 Frozen baseline
Must include:
- commit/tag/worktree reference
- config snapshot
- output examples
- artifact equivalence evidence
- acceptance matrix
- rollback target

## 15.2 Three experimental tracks
Create three baseline-derived worktrees/branches, each with:
- objective statement
- allowed scope
- variant class
- dependency policy
- success criteria
- stop conditions
- change ledger

## 15.3 Integration rule
An experimental track does **not** become a selectable integrated implementation merely because it exists.

Integration requires:
- scope compliance
- baseline comparison
- no forbidden contract drift
- explicit approval

## 16. Multi-variant risks

1. selector becomes a new failure surface
2. duplicate worktrees create drift
3. baseline invariants become fuzzy
4. variant identity leaks into contract surfaces
5. replay/promotion/report/export/review flows break unexpectedly
6. test matrix expands without control
7. experiment-only logic leaks into normal runtime
8. promotion becomes subjective without evidence
9. media-type scope accidentally widens
10. OCR and visual consumers drift further apart instead of becoming cleaner

## 17. Hard rules

1. baseline remains default
2. no experimental variant becomes default accidentally
3. no variant changes artifact semantics in current scope
4. no outward taxonomy widening in current scope
5. no replay/promotion/safeguard variant-awareness in first integrated pass
6. no report/export/review contract changes in first integrated pass
7. no selector integration before consumer/invariant mapping is complete
8. no promotion without baseline comparison
9. no first-pass selector spanning all media types
10. no simultaneous integration of baseline + A + B + C

## 18. Missing docs that must be added before implementation

1. `00D_MULTI_VARIANT_PROGRAM_DECISION.md`
   - formally adopts baseline + three experimental tracks as the program model

2. `00E_REPO_CONSUMER_AND_INVARIANT_MAP.md`
   - owner, contract, gate, report/export/review, replay/promotion/safeguard, batch/runtime consumers

3. `03B_VARIANT_BOUNDARY_AND_SELECTOR_ARCHITECTURE.md`
   - exact swappable seam

4. `03C_VARIANT_REGISTRY_AND_MANIFEST_SPEC.md`
   - registry fields and variant metadata

5. `03D_MEDIA_TYPE_SCOPE_AND_SELECTOR_BOUNDARY.md`
   - PDF-only first-scope freeze

6. `03E_VARIANT_IDENTITY_VISIBILITY_POLICY.md`
   - where variant identity is allowed / forbidden

7. `03F_REPLAY_PROMOTION_AND_REVIEW_COMPATIBILITY_POLICY.md`
   - baseline-only policy initially

8. `05B_BASELINE_REPLAY_VARIANT_SPEC.md`
   - first-class baseline variant definition

9. `05C_VARIANT_BOOTSTRAP_PLAN_FOR_A_B_C.md`
   - how the three worktree tracks are created and constrained

10. `05D_SELECTOR_BOOTSTRAP_BASELINE_ONLY_PLAN.md`
    - integrate selector with baseline only first

11. `06B_CROSS_VARIANT_BAKEOFF_AND_COMPARISON_PLAN.md`
    - cross-variant comparison rules

12. `06C_ACTIVE_TEST_SURFACE_AND_COMMAND_MATRIX.md`
    - live test commands, acceptance matrix, and validation surfaces

13. `08D_VARIANT_PROMOTION_AND_DEPRECATION_RULES.md`
    - graduation / retirement rules

14. `09C_VARIANT_SELECTION_AND_EXECUTION_TELEMETRY.md`
    - internal telemetry and provenance requirements

## 19. Revised phased execution plan

### Phase 0 — planning-pack expansion
Add the missing docs above.

### Phase 1 — multi-variant-aware baseline freeze
Freeze:
- swappable PDF visual-lane boundary
- consumer map
- non-swappable surfaces
- active config surfaces
- artifact invariants
- live test and command matrix
- performance baseline
- replay/promotion/report/review compatibility rules

### Phase 2 — selector bootstrap with baseline only
Integrate:
- registry
- selector
- baseline replay variant only
- no experimental integrated variants yet

### Phase 3 — create A/B/C worktree variants
Separate development tracks:
- variant A
- variant B
- variant C

Still not normal runtime selectable yet unless explicitly approved.

### Phase 4 — cross-variant bakeoff
Compare:
- baseline vs A
- baseline vs B
- baseline vs C
- optionally A vs B vs C

### Phase 5 — controlled integration of candidates
Allow one experimental variant at a time into the integrated registry if it qualifies.

### Phase 6 — promotion, retention, or retirement
Each variant becomes:
- adopted
- experiment-only retained
- or retired

## 20. Final recommendation

The correct path is:

- preserve one frozen baseline
- create three experimental worktree variants
- introduce a **PDF-visual-lane-only** selector seam
- integrate **baseline only** first
- keep variant identity out of public/report/export/review surfaces initially
- keep replay/promotion/safeguard flows baseline-only initially
- only integrate one experimental variant at a time after consumer mapping and baseline comparison
- use bakeoff and promotion rules to determine what survives

This is stricter, safer, and more repo-aligned than the earlier spec.
