# PageEvidence Representative Fixture Lock And Canonical Subset Note

## Purpose

Freeze the canonical representative fixture subset for Lane Class A equivalence/no-drift checks so that “representative fixture” is not left to loose interpretation during implementation or review.

This note does not replace the full corpus manifest. It identifies the subset that binds Lane Class A behavior-preserving claims.

---

## Canonical representative subset for Lane Class A

The following fixture IDs are the default binding representative subset for Lane Class A work:

- `ml17123a319`
- `layout`
- `fontish`
- `scanned`
- `mixed`

These are chosen because together they cover:
- dense text with drawing-rich / layout-complex structure
- text-heavy low-visual cases
- weak-font / sparse-text cases
- full-page scanned/image cases
- mixed native-plus-image cases

The source-of-truth fixture metadata remains the canonical manifest:
- `tests/fixtures/nrc_aps_docs/v1/manifest.json`

---

## Interpretation rule

### Binding rule
For Lane Class A:
- representative subset behavior is binding
- Candidate A projection drift on this subset is presumptively material unless a stronger pack-local rule explicitly says otherwise

### Regression-only rule
For regression-only fixtures:
- drift is allowed only with written justification
- regression-only behavior must not be used to silently redefine Lane Class A equivalence expectations for the representative subset

---

## Why this subset is locked

This subset is intentionally small enough to be repeatedly re-run and manually reviewed, while still broad enough to catch the main PageEvidence risks already identified:

- permissive visual projection on dense-text documents
- obvious visual cases for scanned/image content
- mixed-content handling
- sparse/native text handling
- layout-complex edge behavior

---

## Deferred future evolution

Threshold/percentage-based materiality rules may later supplement this representative-subset rule, but they do not replace it for the current Lane Class A posture.

Until such a later rule is explicitly frozen:
- representative subset first
- regression-only drift only by written justification

---

## Result

Lane Class A no-drift claims are not valid unless they are explicitly checked against the canonical representative subset frozen here.
