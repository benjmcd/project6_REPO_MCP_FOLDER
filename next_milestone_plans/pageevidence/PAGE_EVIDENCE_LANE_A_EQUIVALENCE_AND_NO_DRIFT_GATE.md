# PageEvidence Lane Class A Equivalence and No-Drift Gate

## Purpose

Freeze the minimum proof standard for **Lane Class A — behavior-preserving substrate strengthening** so implementers and reviewers do not treat “no material behavior drift” as a subjective phrase.

This doc applies only when the strengthening lane claims to preserve the current admitted Candidate A behavior materially.

---

## Lane Class A definition

Lane Class A means:

- the strengthening work may refactor, separate, enrich, or harden the PageEvidence substrate
- but it must not materially change what the currently admitted `candidate_a_page_evidence_v1` selector does on the canonical representative corpus unless the lane is explicitly reclassified

If the lane cannot satisfy this gate, it is not Lane Class A anymore.

---

## Pack equivalence posture

The current agreed Lane Class A posture is:

- **additive internal changes are allowed**
- **no representative Candidate A projection drift is allowed**
- **no integrated behavior drift is allowed**
- **regression-only drift may occur only with written justification**
- a threshold/percentage-based materiality rule is a possible later evolution, but is **not** the current gate

This is the governing standard for this pack.

---

## Core equivalence rule

A lane may remain Lane Class A only if all of the following are true:

1. current baseline-default runtime posture remains unchanged
2. `candidate_a_page_evidence_v1` remains the only admitted non-`baseline` selector value
3. the strengthening work does not introduce new runtime-visible selector semantics
4. the strengthening work does not materially alter Candidate A projection outcomes on the canonical representative fixture set
5. any output differences are limited to:
   - additive internal evidence fields
   - non-semantic ordering differences explicitly tolerated by the compatibility policy
   - cleanup/resource-hygiene changes with no admitted-behavior effect

---

## Representative-corpus gate

For Lane Class A, compare:

- current admitted Candidate A behavior
- strengthened Candidate A behavior

across the canonical representative fixture set rooted in:

- `tests/fixtures/nrc_aps_docs/v1/manifest.json`

Minimum representative fixture emphasis:

- `ml17123a319`
- `layout`
- `fontish`
- `scanned`
- `mixed`

These representative fixtures are binding for Lane Class A.

If per-page Candidate A projection outcomes change on representative fixtures, the lane must either:

- prove the change is non-material under an explicitly frozen exception rule
- or escalate to Lane Class B

For this pack, the default assumption is that representative-fixture per-page projection drift is **material** unless explicitly neutralized under an approved exception.

---

## Regression-only rule

Regression-only fixtures are not free-drift surfaces.
They may drift only if all of the following are true:

1. the representative-fixture gate still passes
2. the drift is written up explicitly in the implementation record
3. the drift does not create hidden integrated behavior drift
4. the drift does not undermine the admitted-selector justification story

If those conditions are not met, the drift must be treated as escalation-worthy.

---

## Material-drift triggers

Any of the following automatically create a presumption of **material behavior drift**:

1. per-page Candidate A visual/non-visual decisions change on representative fixtures
2. pages previously preserved by the admitted Candidate A path are no longer preserved, or vice versa, on representative fixtures
3. disagreement summaries on representative fixtures change in a way that alters the justification story for the admitted selector
4. the strengthened lane requires changing `nrc_aps_document_processing.py` in a way that is not strict-equivalence seam refactor

If any trigger is met and cannot be explicitly neutralized with evidence, escalate to Lane Class B.

---

## Allowed non-material differences

The following may still be Lane Class A if explicitly documented:

- additive internal evidence fields that do not change admitted projection results
- deterministic cleanup/resource-handling changes
- compatibility-bridge output that preserves old consumer meaning
- runner/report output additions that do not change the meaning of existing retained fields
- regression-only fixture drift with written justification under the regression-only rule above

---

## Required proof outputs

Lane Class A must provide:

1. a comparison artifact showing current admitted Candidate A vs strengthened Candidate A on the representative corpus
2. a page-level summary of any representative-fixture differences
3. an explicit statement that no representative-fixture material drift was observed, or an escalation declaration if drift exists
4. a written justification for any regression-only drift

---

## Escalation rule

If Lane Class A cannot satisfy this gate, stop describing the work as behavior-preserving.

Required next step:

- reclassify the work as Lane Class B
- apply the selector-semantics / behavior-drift policy
- and do not continue under Lane Class A labeling by convenience

---

## Result

This gate converts “behavior-preserving substrate strengthening” from an interpretive claim into a reviewable proof obligation.
