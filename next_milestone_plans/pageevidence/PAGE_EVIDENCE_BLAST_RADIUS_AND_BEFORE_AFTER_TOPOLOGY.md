# PageEvidence Blast Radius and Before/After Topology

## Purpose

Freeze the blast-radius, connection-surface, and before/after-topology rules for the PageEvidence strengthening lane.

This document exists because the strengthening lane is not only a question of "what files may be edited." It is also a question of:

- what each touched file actually owns
- which downstream or hidden-consumer surfaces are affected if it changes
- which changes are behavior-preserving versus behavior-changing
- what the repo topology looks like before the lane
- and what the repo topology is allowed to look like after the lane

No implementation should claim adequate scoping unless the relevant change class and file-level blast radius are explicitly mapped through this document.

---



## Taxonomy note

This document defines **step classes**, not lane classes.

- **Lane classes** classify the overall strengthening lane (`Lane Class A` or `Lane Class B`)
- **Step classes** classify individual implementation steps for blast-radius, rollback, and control purposes

A Lane Class A strengthening effort may still include Step Class C work, for example, if compatibility-bridge handling is required.


## Core interpretation rule

The strengthening lane must classify proposed work into one or more of the following change classes before implementation begins:

1. **Step Class R — substrate refactor / no material behavior drift**
2. **Step Class P — projection recalibration / admitted Candidate A behavior drift**
3. **Step Class C — schema / artifact compatibility evolution**
4. **Step Class H — hidden-consumer compatibility touch**

A proposed implementation may span more than one class.
If it does, the strictest applicable controls govern the whole change set unless the work is cleanly split into separate passes/commits.

---

## Current merged-main and comparison-baseline topology

### Before-state A — pre-Pass1 comparison baseline

The pre-Pass1 baseline topology was:

1. At baseline commit `4e89592043867726756aad16805529ae23c8fb6f`, `nrc_aps_page_evidence.py` contained shared evidence extraction, candidate identity, and projected class logic in one place.
2. `run_nrc_aps_page_evidence_workbench.py` consumes that fused service output and emits a workbench artifact.
3. `nrc_aps_document_processing.py` contains the admitted Candidate A seam-local helper and consumes PageEvidence-derived signals inside the integrated PDF visual lane.
4. Hidden-consumer surfaces downstream of processing already exist across content index, models/schemas, retrieval, evidence bundles, review, and report/export chains.
5. Candidate A is already admitted; `baseline` remains the default for the current horizon.

This before-state remains the source-of-truth comparison anchor for representative-equivalence, runner-equivalence, and no-drift judgments.

### Current realized merged-main topology

On merged `main`:

1. `nrc_aps_page_evidence.py` now separates shared evidence extraction from Candidate A projection inside the same owner file.
2. `run_nrc_aps_page_evidence_workbench.py` still consumes the stable service output shape without a helper-extraction or report-compatibility bridge.
3. `nrc_aps_document_processing.py` remains untouched and still consumes the PageEvidence service through the admitted seam-local helper.
4. Hidden-consumer validation and route/API/report/export/package closure checks are already green for this merged-main state.
5. This realized merged-main topology is the live truth for deciding whether any later pass is still needed.

---

## Allowed after-state topologies

### After-state 1 — substrate-only strengthening / no material Candidate A behavior drift

Allowed target shape:

- shared evidence extraction is separated from candidate-policy projection
- Candidate A admitted behavior remains materially unchanged
- runtime semantics remain stable
- hidden-consumer meaning remains stable or compatibly bridged
- no new outward identity surfaces are introduced

This is the preferred strengthening topology.

### After-state 2 — substrate strengthening plus Candidate A behavior recalibration

Allowed only if all of the following are true:

- the lane is explicitly classified as behavior-changing
- selector-semantics / behavior-drift policy is consulted and satisfied
- comparison evidence includes baseline, current admitted Candidate A, and proposed strengthened Candidate A where applicable
- no broadened non-PageEvidence scope is inferred beyond the explicit recalibration change

This is a stronger-control topology, not a routine substrate refactor.

### Disallowed after-state topologies

The lane must not end in any of the following states without a separate explicit broader freeze:

- generic A/B/C candidate registry or runtime framework
- outward identity/schema widening by implication
- OCR/hybrid/media-scope reopening
- broad visual-understanding subsystem expansion
- silent semantic drift of `candidate_a_page_evidence_v1`

---

## Connection-surface map

The strengthening lane must explicitly account for the following repo-native connection surfaces:

1. **core evidence service -> workbench runner**
2. **core evidence service -> Candidate A projection layer/helper**
3. **Candidate A projection layer/helper -> `_run_candidate_a_visual_lane(...)`**
4. **document processing -> page summaries / visual refs / diagnostics-like outputs**
5. **processing outputs -> content index / models / schemas / retrieval / evidence bundle**
6. **persisted or exposed outputs -> review / report / export / package consumers**
7. **workbench artifact -> pinned historical artifact compatibility surface**

Any file change that affects one of these connections must record:

- which connection is touched
- whether the touch is direct or indirect
- whether compatibility is preserved, bridged, or broken

---

## Per-file blast-radius matrix

### 1. `backend/app/services/nrc_aps_page_evidence.py`

**Direct ownership**

- evidence schema/content
- threshold normalization
- extraction logic
- candidate identity in artifact output if still present
- projected class logic while still fused

**Potential change classes**

- Class R
- Class C
- Class P (if projection semantics are changed here or via extracted equivalent)

**Direct blast radius**

- service output meaning
- workbench report shape/meaning
- unit-test expectations
- Candidate A projection assumptions

**Indirect blast radius**

- historical artifact interpretation
- future comparison logic
- any reader assuming current field meaning

**Minimum required checks if changed**

- substrate/projection bundle
- schema/artifact compatibility policy
- blast-radius summary in implementation record

---

### 2. `tools/run_nrc_aps_page_evidence_workbench.py`

**Direct ownership**

- workbench artifact construction
- path/timestamp handling
- failure-path behavior
- pinned report reproducibility

**Potential change classes**

- Class R
- Class C
- Class H

**Direct blast radius**

- durable workbench artifact compatibility
- runner tests
- comparability of historical vs new reports

**Indirect blast radius**

- any consumer or reviewer relying on pinned artifacts

**Minimum required checks if changed**

- runner bundle
- schema/artifact compatibility policy
- pinned-artifact impact note in implementation record

---

### 3. `backend/tests/test_nrc_aps_page_evidence.py`

**Direct ownership**

- substrate expectations
- normalization/failure expectations
- projection invariants if retained here

**Potential change classes**

- Class R
- Class P
- Class C

**Direct blast radius**

- defines what counts as preserved extractor behavior
- may conceal or reveal admitted-behavior drift if too weakly scoped

**Minimum required checks if changed**

- ensure extractor invariants and projection invariants are separated where possible

---

### 4. `tests/test_nrc_aps_page_evidence_workbench.py`

**Direct ownership**

- runner/report expectations
- durable output semantics
- canonical path/timestamp behavior

**Potential change classes**

- Class R
- Class C
- Class H

**Direct blast radius**

- report compatibility expectations
- pinned artifact comparability

**Minimum required checks if changed**

- runner bundle
- disagreement/evaluation expectations if artifact meaning changes

---

### 5. `backend/app/services/nrc_aps_document_processing.py` (conditional)

**Direct ownership**

- integrated owner-path behavior
- admitted Candidate A seam-local execution
- what `candidate_a_page_evidence_v1` actually does inside the PDF visual lane

**Potential change classes**

- Class R (only if strict equivalence is preserved)
- Class P
- Class H

**Direct blast radius**

- admitted selector semantics
- page-summary and persisted output behavior
- performance if execution path changes

**Indirect blast radius**

- downstream indexing/retrieval/review/report/export behavior through changed outputs

**Minimum required checks if changed**

- classify the lane under selector-semantics policy
- run baseline-compatibility bundle
- run tri-comparison evaluation if behavior changes
- record before/after admitted behavior summary explicitly

---

### 6. Hidden-consumer surfaces (inspect-only unless escalated)

Relevant surfaces include at minimum:

- `nrc_aps_artifact_ingestion.py`
- `nrc_aps_content_index.py`
- model/schema surfaces
- retrieval plane / retrieval readers
- evidence bundle surfaces
- review surfaces
- report/export/package surfaces

**Potential change classes**

- Class H
- Class C

**Direct blast radius**

- compatibility of consumed fields, refs, and meanings

**Minimum required checks if indirectly affected**

- complete hidden-consumer compatibility checklist
- explicit statement of unaffected / compatible / bridged / blocked status

---

## Pass-scoped default blast-radius expectations

### Pass 1 — lifecycle hardening and in-file separation

Default direct owners:

- `backend/app/services/nrc_aps_page_evidence.py`
- `backend/tests/test_nrc_aps_page_evidence.py`

Default indirect surfaces that still require proof:

- workbench runner compatibility
- representative-fixture equivalence
- targeted integrated Candidate A seam sanity

### Pass 2 — helper extraction / compatibility bridge only if Pass 1 proved insufficient

Default direct owners only if activated:

- `backend/app/services/nrc_aps_page_evidence.py`
- `tools/run_nrc_aps_page_evidence_workbench.py`
- `tests/test_nrc_aps_page_evidence_workbench.py`
- one narrow helper file under `backend/app/services/` if needed

Default indirect surfaces that become active if Pass 2 is truly needed:

- pinned artifact comparability
- runner/report compatibility meaning
- possible pressure against the protected integrated seam

Stop rule:

- if these surfaces are not actually implicated by a repo-confirmed insufficiency, do **not** open Pass 2

### Pass 3 — internal evidence-field enrichment only

Default direct owners:

- `backend/app/services/nrc_aps_page_evidence.py`
- `backend/tests/test_nrc_aps_page_evidence.py`

Default indirect surfaces:

- artifact compatibility expectations
- hidden-consumer inspect-only review for accidental outward meaning drift

### Pass 4 — disagreement / evaluation expansion

Default direct owners:

- `tools/run_nrc_aps_page_evidence_workbench.py`
- `tests/test_nrc_aps_page_evidence_workbench.py`
- one narrow evaluation/disagreement helper under `tools/` if needed

Default indirect surfaces:

- pinned artifact comparability
- reviewer interpretation of disagreement/report outputs

Interpretation rule:

- every pass must account for both the files it edits and the connection surfaces it activates
- a later pass that activates no new surfaces should normally be skipped

---

## Required before/after summary in implementation work

Every implementation report must include:

1. **Before-state summary**
   - current fused or pre-change topology
2. **After-state summary**
   - resulting topology after the lane
3. **Change-class classification**
   - R / P / C / H as applicable
4. **Per-file touched-surface summary**
   - direct and indirect blast radius
5. **Rollback target**
   - what state can be restored if the lane is reverted

---

## Commit choreography recommendation

To reduce fragility, the strengthening lane should separate implementation into the following order where possible:

1. cleanup / lifecycle / pure refactor-only changes
2. compatibility bridge changes
3. richer internal evidence-field additions
4. runner/report/evaluation strengthening
5. projection recalibration changes only if separately authorized and explicitly classified

Do not mix pure refactor changes and admitted-behavior changes in one undifferentiated step if a narrower sequence is possible.

---

## Result

The strengthening lane now has a frozen blast-radius and before/after-topology rule set.

This prevents the lane from understating:

- what each touched file owns
- how far a change can propagate
- when a refactor becomes an admitted-behavior amendment
- and what repo-wide relationship changes are actually being introduced.
