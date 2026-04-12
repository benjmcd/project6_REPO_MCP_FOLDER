# 04B - Candidate B OpenDataLoader Baseline and Candidate A Crosswalk

## Purpose

Define what Candidate B must compare against now,
and what remains a deferred secondary comparison.

---

## A. Primary mandatory comparison in v1

The primary mandatory comparison target is the **current live lower-layer baseline truth**:
- current `nrc_aps_document_processing.process_document(...)` outputs
- current lower-layer proof corpus
- current lower-layer tests/invariants

This comparison is mandatory because it is directly repo-grounded.

---

## B. Secondary Candidate A comparison in v1

For the first Candidate B implementation-entry pass, the explicit decision is:
- secondary Candidate A comparison = `NO`

Reason:
- baseline comparison is the mandatory repo-truth target
- Candidate A is already an admitted merged-main lane with its own closed hold-state
- reopening that lane as part of first-run Candidate B setup would create avoidable runtime-adjacent drift

Interpretation:
- baseline comparison = mandatory
- Candidate A comparison = optional only in a later separately frozen pass

If a later pass explicitly reopens the optional comparison,
it must freeze exact refs/hashes first.
No guessed Candidate A comparison from memory or file-name guesswork is allowed.

---

## C. Win / divergence / limitation taxonomy

### `program_relevant_gain`
Candidate B reveals semantic/layout evidence that is genuinely useful relative to current lower-layer outputs.

### `expected_semantic_divergence`
Candidate B emits different semantic structure, but the difference is expected and not clearly useful.

### `owner_path_not_competing`
The page/doc is currently governed by the live owner path (for example visual-preservation or OCR strictness), and Candidate B is not competing on that axis.

### `known_limitation_control`
The page/doc falls into a known ODL limitation/control class (especially vector-heavy pages in local non-hybrid mode).

### `regression_or_false_claim`
Candidate B loses useful structure, creates misleading claims, or tries to claim value outside its allowed axis.

---

## D. Candidate B may never claim
- that it replaces `visual_page_refs`
- that it supersedes the current visual-preservation lane
- that it resolves OCR strictness
- that it owns connector/report/runtime behavior

Those claims are out of scope in v1.

---
