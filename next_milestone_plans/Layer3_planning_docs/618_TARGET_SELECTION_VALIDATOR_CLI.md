# 618 - Target Selection Validator CLI

## Status

Status: validate-only CLI for `612_TARGET_SELECTION_INTAKE.md`.

Doc: `618_TARGET_SELECTION_VALIDATOR_CLI.md`.

Current-main checkpoint at CLI creation: `489419d419a81ed74ae61c5b340b666409e0817a`.

Validated intake: `612_TARGET_SELECTION_INTAKE.md`.

Validated parser guard: `617_TARGET_SELECTION_STRUCTURED_RECORD_VALIDATOR.md`.

CLI: `tools/l3-target-selection-validate.py`.

Tests: `backend/tests/test_layer3_target_selection_validate.py`.

Runtime status: `not_implemented`.

Current intake state: `frozen`.

## Purpose

This CLI gives the operator a local validate-only command for the structured target-selection record before any implementation-entry freeze.

It does not select a target and does not admit runtime behavior.

## Supported States

The CLI supports exactly these expected states:

- `pending`: historical unfilled state; every target field is `null`, `selection_complete` is `false`, and `implementation_entry_freeze_written` is `false`.
- `selected`: future operator-filled intake before the separate freeze lands; every required target field is filled, `selection_complete` is `true`, and `implementation_entry_freeze_written` is `false`.
- `frozen`: current repo state after operator fill and current-main reconciliation to existing doc `608`; every required target field is filled, `selection_complete` is `true`, and `implementation_entry_freeze_written` is `true`.

## Commands

Validate current main frozen state:

```powershell
python .\tools\l3-target-selection-validate.py --expect frozen
```

Validate a candidate filled intake copy before freeze:

```powershell
python .\tools\l3-target-selection-validate.py .\next_milestone_plans\Layer3_planning_docs\612_TARGET_SELECTION_INTAKE.md --expect selected
```

Validate a candidate filled intake after the separate freeze records completion:

```powershell
python .\tools\l3-target-selection-validate.py .\next_milestone_plans\Layer3_planning_docs\612_TARGET_SELECTION_INTAKE.md --expect frozen
```

## Non-Admission Boundary

The CLI is validate-only. It reads the intake file and emits pass/fail output; it does not write files, seed runtime state, call providers, call connectors, create connector runs, write destinations, create credentials, mutate packages, expand sources, create RAG/vector state, alter auth/security behavior, activate the full mockup, or create frontend-durable authority.

## Next Posture

The next required action is current-main satisfied posture sync for the selected `server_owned_local_delivery_outbox_destination` target. Any future target beyond the selected server-owned local outbox destination must still name exactly one new target/action and write a separate implementation-entry freeze before any real external side effect.
