# 617 - Target Selection Structured Record Validator

## Status

Status: validate-only structured record parser guard for `612_TARGET_SELECTION_INTAKE.md`.

Doc: `617_TARGET_SELECTION_STRUCTURED_RECORD_VALIDATOR.md`.

Current-main checkpoint at validator creation: `4e849bd69c871a4f29d61bb140222fd8432f6426`.

Validated intake: `612_TARGET_SELECTION_INTAKE.md`.

Validated field contract: `616_TARGET_SELECTION_FIELD_CONTRACT.md`.

Validated record heading: `## Structured Selection Record`.

Runtime status: `not_implemented`.

Parser status: `pending_record_required`.

Selection complete: false.

Implementation-entry freeze written: false.

## Purpose

This validator makes the structured target-selection intake fail closed as a parseable record, not only as literal doc text.

It does not select a target and does not admit runtime behavior.

## Guarded Failures

The progress checker must fail closed on:

- missing fenced `yaml` block under `## Structured Selection Record`;
- malformed key/value mapping line;
- duplicate key;
- missing required key;
- unexpected key;
- non-null required field while pending;
- `selection_complete` not `false`; and
- `implementation_entry_freeze_written` not `false`.

## Current Pending Record Rule

While no operator target is selected, every required target-selection field in `612_TARGET_SELECTION_INTAKE.md` must remain `null`.

The only valid current structured state is:

```yaml
selection_complete: false
implementation_entry_freeze_written: false
```

Any filled target field requires the same lane to update the field contract, the validate-only guard, the current-main sync evidence, and the downstream implementation-entry freeze evidence before runtime implementation begins.

## Non-Admission Boundary

This validator admits no runtime behavior, backend route behavior, service behavior, response-model shape change, schema/model/migration change, rendered UI behavior, real connector invocation, destination write, connector-run creation, credential handling, real provider network/object-store behavior, provider-public delivery/use, package mutation/reconstruction, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, or frontend-durable authority.

## Next Posture

The next required action remains operator completion of `612_TARGET_SELECTION_INTAKE.md` with exactly one real connector or destination target, followed by a separate implementation-entry freeze before any real external side effect.
