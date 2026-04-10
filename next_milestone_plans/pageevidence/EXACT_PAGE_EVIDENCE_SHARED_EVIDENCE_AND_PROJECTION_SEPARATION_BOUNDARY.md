# Exact PageEvidence Shared-Evidence and Projection-Separation Boundary

## Purpose

Freeze the exact strengthening boundary for the next PageEvidence lane.

This lane exists to improve PageEvidence by separating:

- **shared evidence extraction**
- from **candidate-policy projection / classification**

while preserving the current baseline-default runtime posture and avoiding broader widening by implication.

This document is a boundary/control input.
It does **not** itself authorize:

- new admitted selector values
- outward schema widening
- general A/B/C runtime support
- OCR / hybrid OCR / media-scope redesign
- or a broad visual-understanding subsystem program

---

## Status note

Current repo state already includes:

- a dedicated PageEvidence workbench lane
- a later narrow Candidate A admission lane
- retained `baseline` as the current default horizon state

This strengthening boundary must therefore be read as:

- a **follow-on refinement lane** for the PageEvidence substrate and Candidate A projection quality
- **not** as a new candidate-admission lane
- **not** as a new broad subsystem charter
- **not** as authorization to proceed into Candidate B implementation

---

## Current live anchors this lane is built on

1. PageEvidence already exists as a dedicated internal service and standalone workbench surface.
2. Candidate A already exists as the only admitted non-`baseline` selector value through the narrow integrated visual-lane seam.
3. `baseline` remains the default for the current horizon.
4. The pre-Pass1 comparison baseline at `4e89592043867726756aad16805529ae23c8fb6f` used a fully fused PageEvidence service.
5. The current merged-main state now separates raw evidence extraction from projected visual-page classification inside `backend/app/services/nrc_aps_page_evidence.py`, but does not yet require a separate helper module or runner/report compatibility bridge.
6. The current projected class logic is still permissive enough that dense-text pages with nonzero drawing/image counts may still be projected as visual.
7. The outward binary visual contract remains part of the live baseline-facing surface and must not be widened casually.

Interpretation rule:

- do not confuse the historical fused comparison baseline with the current realized branch topology
- the boundary remains active because in-file separation does not, by itself, justify helper extraction, seam widening, or behavior recalibration

---

## Exact role of the strengthening lane

The strengthening lane exists to make all of the following true:

1. PageEvidence becomes a **shared deterministic evidence extractor**.
2. Candidate-policy projection becomes a **separate derived layer** rather than the conceptual center of the core PageEvidence service.
3. Candidate A can continue to derive a projection from the strengthened evidence layer without reopening broader non-PageEvidence scope.
4. Internal evidence richness may increase without outward schema or identity widening.
5. Evaluation discipline becomes stronger through disagreement analysis and calibration-oriented summaries.

Current merged-main adequacy note:

- the current merged-main state already satisfies items 1-3 inside the existing owner file and runner surface
- future work should therefore start from a fresh insufficiency finding, not from the stale assumption that separation is still undone

---

## Exact lane-type split

The strengthening lane must distinguish between two different classes of work.

### Lane Class A — substrate strengthening with no material Candidate A behavior drift

This class may include:

- splitting evidence extraction from projection
- removing or demoting Candidate-A-specific identity from the core evidence layer
- adding richer internal evidence fields
- improving cleanup / resource-lifecycle hygiene
- improving workbench reporting and evaluation artifacts
- compatibility-preserving schema evolution

This class is allowed under the strengthening boundary **without** treating the lane as a new admission/amendment lane, so long as current Candidate A admitted behavior remains materially unchanged.

### Lane Class B — Candidate A behavior recalibration

This class includes any change that materially alters what the admitted selector value `candidate_a_page_evidence_v1` does in the integrated owner path.

Examples include:

- changing the effective projection rule
- changing thresholds in a way that materially alters page-level decisions
- changing how Candidate A decides visual significance/preservation eligibility in the admitted seam

This class is **not** merely a substrate-refinement lane.
It is an admitted-behavior amendment class and must obey the dedicated selector-semantics / behavior-drift policy before implementation proceeds.

---


## Exact blast-radius / topology rule

No strengthening lane should treat file-edit scope alone as sufficient scoping.

The lane must also classify:

- change class
- connection surfaces touched
- before-state topology
- after-state topology
- direct and indirect blast radius by file

The canonical source of truth for this requirement is:

- `PAGE_EVIDENCE_BLAST_RADIUS_AND_BEFORE_AFTER_TOPOLOGY.md`

Interpretation rule:

- a narrow file list does not guarantee narrow blast radius
- a substrate-only refactor and an admitted-behavior recalibration are not the same class of change

---
## Exact separation rule

The lane must preserve the distinction between the following two roles:

### 1. Shared evidence extraction

This layer may own:

- deterministic PyMuPDF-derived page signals
- threshold-normalized shared evidence inputs if still needed
- region-aware derived evidence fields
- evidence schema/version metadata
- deterministic provenance about how evidence was derived

This layer should **not** be treated as the canonical owner of candidate-policy judgment.

### 2. Candidate-policy projection

This layer may own:

- Candidate A projection logic
- candidate-specific threshold combinations
- projection labels or policy decisions
- future comparison-only candidate projections

This layer should consume shared PageEvidence outputs rather than being fused into the core extractor.

---

## Allowed strengthening areas

This lane may:

1. separate core evidence extraction from projection logic
2. rename or demote the existing projected class field so it is no longer treated as intrinsic truth
3. add richer internal region-aware evidence fields
4. reduce Candidate-A-specific coupling in the core evidence layer
5. improve calibration of Candidate A projection logic
6. expand workbench reports or add companion evaluation artifacts focused on disagreement / borderline-page analysis
7. improve resource-lifecycle hygiene and deterministic cleanup in the PageEvidence service / runner

---

## Exact non-goals

This strengthening lane does **not** authorize:

- direct admission of any new selector value
- replacement of the current baseline-default runtime rule
- generic A/B/C registry construction
- broad candidate-lifecycle framework work
- broad visual-understanding subsystem work
- review/API/report/export schema widening
- new outward variant-identity fields
- OCR / hybrid OCR / media-scope redesign
- runtime-root allowlist redesign
- report/export visibility redesign

---

## Exact outward-contract rule

The strengthening lane must preserve the outward binary baseline-facing contract unless a later stronger freeze explicitly reopens it.

That means:

- no new outward review/API/report/export identity fields
- no new public meaning of variant identity
- no broad exposure of richer internal evidence fields by default
- no change to the current baseline-default runtime posture

Internal evidence richness is allowed.
Outward binary compatibility remains the default requirement.

---

## Exact candidate rule

The lane may make the **core evidence extractor** more candidate-neutral.

The lane may **not**:

- activate Candidate B
- create empty Candidate B/C scaffolding
- imply that a later candidate workbench/admission lane is now authorized

Interpretation rule:

- candidate-neutral evidence infrastructure is allowed
- candidate-runtime framework widening is not allowed by implication

---

## Filesystem / ownership rule

Default filesystem roles:

- `backend/app/services/` for shared PageEvidence extraction and candidate projection helpers
- `tools/` for explicit standalone workbench/evaluation runners
- `backend/tests/` for service-level and projection-level tests
- `tests/` for runner-level and disagreement/evaluation tests

This lane does **not** require:

- a new top-level subsystem directory
- candidate-specific folder trees
- or broad repo reorganization

---

## Result

The strengthening lane is now bounded as:

- a **PageEvidence substrate refinement lane**
- plus a **Candidate A projection-quality refinement lane**
- without broader candidate-framework or subsystem authorization

This closes the conceptual ambiguity between:

- improving PageEvidence as shared evidence infrastructure
- and incorrectly treating the lane as a broad runtime/program re-expansion.
