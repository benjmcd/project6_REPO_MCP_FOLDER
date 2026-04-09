# PageEvidence Evaluation and Disagreement Matrix

## Purpose

Freeze the evaluation and disagreement-analysis rules for the PageEvidence strengthening lane.

This document exists because bounded determinism alone is insufficient.
The strengthening lane must also prove that:

- projection quality is not silently degrading
- borderline cases are visible
- disagreement patterns are inspectable
- and stronger claims are not made without stronger evidence

---

## Pack evaluation posture

Within this separate pack, the prepared evaluation posture is:

- Lane Class A only
- representative fixtures binding
- regression-only drift allowed only with written justification
- baseline context remains useful, but the required Lane Class A comparison center is:
  - current admitted Candidate A
  - strengthened Candidate A
- threshold/percentage-based materiality rules are deferred to later possible evolution

## Canonical corpus source of truth

The default evaluation corpus must start from:

- `tests/fixtures/nrc_aps_docs/v1/manifest.json`

The lane may add temporary local evaluation inputs, but durable repo-native evaluation should remain anchored to the canonical manifest unless a later stronger freeze explicitly expands the corpus policy.

---

## Comparison surfaces

The evaluation matrix must support different comparison modes depending on lane class.

### For Lane Class A lanes

Minimum comparison surfaces:

1. current admitted Candidate A
2. proposed strengthened Candidate A

Optional:
- baseline, if useful for context

### For Lane Class B lanes

Required comparison surfaces:

1. baseline
2. current admitted Candidate A
3. proposed strengthened Candidate A

Comparison against baseline alone is insufficient once Candidate A is already admitted.

---

## Fixture strata

The evaluation matrix must distinguish at least the following strata:

1. text-heavy / no-visual pages
2. full-page scanned/image pages
3. mixed native-plus-image pages
4. dense-text pages with decorative vector marks
5. table/form-heavy pages
6. dense engineering/diagram-heavy pages
7. regression-only edge cases

---

## Disagreement categories

For each page, evaluation must be able to classify at least the following disagreement categories:

1. baseline non-visual / Candidate A non-visual
2. baseline visual / Candidate A visual
3. baseline non-visual / Candidate A visual
4. baseline visual / Candidate A non-visual
5. current-A non-visual / proposed-A visual
6. current-A visual / proposed-A non-visual
7. borderline due to tiny drawing footprint
8. borderline due to sparse text
9. mixed-content page with one dominant image region
10. likely false-positive visual projection
11. likely false-negative visual projection

---

## Required metrics / summaries

The lane must produce, per run:

- projected visual page count
- projected text-heavy page count
- high-word-count visual pages
- low-coverage-but-visual pages
- pages whose only visual signal is tiny drawing/image presence
- threshold-borderline pages
- per-document disagreement summaries across the required comparison surfaces

If richer internal evidence fields are added, the lane should also surface:

- dominant visual region ratio
- count of meaningful visual regions above minimum size
- pages where a dominant visual region is absent but the projection is still visual

---

## Required explicit gates

The strengthening lane should not be considered successful unless all of the following are true:

1. representative text-dominant pages do not collapse into visual solely because of trivial decorative marks without explicit written justification
2. scanned and mixed pages continue to retain their obvious visual-signal behavior
3. disagreement-heavy documents are surfaced explicitly rather than hidden inside aggregate counts
4. deterministic reruns remain stable on the same inputs
5. the lane can explain why a projected visual page is visual using inspectable evidence fields
6. no representative dense-text document collapses to 100% projected-visual without explicit justification

---

## Required borderline-page surfacing rules

The evaluation artifact must explicitly list pages meeting any of the following:

- high word count + low visual coverage + visual projection
- nonzero drawing count with negligible dominant-region size
- mixed-content pages where the projection outcome is threshold-sensitive
- disagreement with baseline or current admitted Candidate A on representative fixtures

This list is mandatory.
It must not be buried in aggregate counts alone.

---

## Required report outputs

At least one durable evaluation artifact should exist in repo-native form.

Preferred output structure:

1. one strengthened workbench report or companion evaluation report containing:
   - shared evidence record
   - Candidate A projection summary
   - disagreement summaries
   - borderline-page summaries
2. one pinned durable artifact for the lane if explicit review of results is required

---

## Manual review protocol for borderline pages

The lane should define a manual-review path for pages that meet any of the mandatory borderline-page conditions.

For each manually reviewed borderline page, record:

- source document
- page number
- evidence fields
- projection decision
- which comparison surfaces disagree
- why the case is acceptable or problematic

---

## Result

The strengthening lane now has a frozen evaluation standard that is stricter than simple pass/fail smoke tests.
This prevents the lane from overclaiming improved quality without explicit disagreement analysis.
