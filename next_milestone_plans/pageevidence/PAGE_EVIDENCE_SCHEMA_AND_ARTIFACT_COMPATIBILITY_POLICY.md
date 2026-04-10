# PageEvidence Schema and Artifact Compatibility Policy

## Purpose

Freeze the schema and artifact compatibility rules for PageEvidence strengthening work.

This document exists because the current core PageEvidence service and workbench report already emit durable schema-bearing artifacts.
If the strengthening lane separates evidence extraction from projection or changes what fields are emitted, compatibility must be handled explicitly rather than improvised during implementation.

---

## Current live anchors

The core service currently emits a schema-bearing PageEvidence payload and the workbench emits a schema-bearing report artifact that has already been pinned in repo-native form.

The current shape includes:

- PageEvidence schema identity
- page-level evidence fields
- projected visual-page classification
- candidate identity in the core output
- workbench report schema and pinned artifact path

Strengthening work must therefore answer:

- what stays the same
- what changes compatibly
- what is renamed/demoted
- and what readers/artifacts must continue to tolerate

---

## Compatibility goal

The default strengthening goal is:

- improve the internal conceptual model
- while preserving compatibility as far as reasonable
- and avoiding unnecessary breakage in readers, tests, or pinned review artifacts

This policy favors **additive or clearly versioned change**, not ambiguous silent breakage.

---

## Core schema rule

The strengthening lane must explicitly choose one of the following for the core PageEvidence schema:

### Option A — compatibility-preserving refinement within existing schema version

Allowed only if:

- existing consumers can still parse the output safely
- existing key fields remain present or are cleanly demoted with compatibility support
- no field is removed in a way that makes prior artifacts misleading or unreadable

### Option B — explicit new schema version

Required if:

- the conceptual split between evidence and projection would otherwise make the old schema misleading
- projected-class fields are removed or fundamentally reinterpreted
- candidate identity moves out of the core artifact in a way that existing readers cannot safely assume away

When in doubt, prefer explicit versioning over ambiguous continuity.

---

## Projected-class field rule

The lane must explicitly decide the fate of the current projected-class field.

Allowed outcomes:

1. retain it as-is for compatibility, but document that it is a derived/candidate-layer convenience field rather than intrinsic evidence truth
2. rename/demote it while preserving a compatibility bridge
3. move it into a projection-specific artifact or section under a new schema version

Disallowed outcome:

- silently keep the same field name while fundamentally changing what it means without explicit compatibility language

---

## Candidate identity rule

The lane must explicitly decide whether candidate identity remains in the core PageEvidence output.

Preferred direction:

- candidate identity should move out of the **core shared evidence** artifact
- candidate identity may remain in:
  - workbench/report metadata
  - projection-layer artifacts
  - comparison outputs

If candidate identity remains in the core schema for compatibility, the implementation record must explain why and whether that is transitional.

---

## Workbench artifact rule

The pinned repo-native workbench artifact must be treated as a durable compatibility surface.
Its authority is about workbench/report compatibility and historical before-state evidence; it does not redefine the current admitted integrated Candidate A behavior in the owner path.

The strengthening lane must choose one of the following:

### Option A — keep current workbench schema and extend compatibly
### Option B — emit a new report schema/version and preserve the old pinned artifact as historical evidence
### Option C — emit both legacy-compatible and strengthened artifacts during transition

The lane must not overwrite the historical meaning of the already-pinned artifact silently.

---

## Reader compatibility rule

The strengthening lane must identify all known readers or validators that depend on:

- core PageEvidence output shape
- workbench artifact shape
- projected-class-related fields
- candidate-identity-related fields

The hidden-consumer compatibility checklist must be used to confirm whether each reader:

- is unaffected
- tolerates additive fields
- requires compatibility handling
- or must remain completely unchanged

---

## Additive-field rule

New internal evidence fields are encouraged to be additive by default.

Examples:

- dominant visual region ratio
- largest image bbox area ratio
- largest drawing bbox area ratio
- meaningful region counts
- region-overlap summaries

If fields are additive and internal-facing only, compatibility burden is lower.
If they replace or reinterpret existing fields, explicit schema/version handling is required.

---

## Historical-artifact rule

No strengthening lane may retroactively reinterpret historical artifacts silently.

If strengthened logic changes how a field should be read, the lane must:

- either preserve the old field meaning in historical artifacts
- or version the new artifact shape explicitly

This is especially important for pinned workbench artifacts cited in planning docs.

---

## Required implementation-record fields

Any strengthening implementation record must explicitly state:

- chosen core schema handling option
- chosen workbench artifact handling option
- whether projected-class fields were retained, renamed, demoted, or moved
- whether candidate identity remained in the core artifact
- which readers required compatibility handling
- whether any version bump occurred

---

## Result

The repo now has a frozen compatibility rule preventing PageEvidence strengthening work from silently breaking schema-bearing artifacts or obscuring the historical meaning of already-pinned workbench evidence.


---

## Relationship to the payload-example doc

The companion payload-example doc is **illustrative rather than binding** unless a later repo-inserted control doc explicitly promotes a specific example to binding compatibility-fixture status.

Binding compatibility is governed by:
- this policy
- explicit implementation tests
- explicit compatibility artifacts if later added
