# Provenance Of `tests/reports/*.json`

> Documentation only. Recorded against `project6-origin/main` at
> `abd8c3f8ac2b2545fda8b88d46aa916a22b626e8`.

## What These Files Are

The checked-in JSON files in this directory are operator-generated validation and gate snapshots.
They are not CI outputs, and no workflow currently writes and commits them during a CI run.

## Why They Are Not Current-Commit Proof

- Their filesystem metadata can reflect bulk copy or refresh operations rather than generation time.
- Their payloads can reference operator-local runtime storage outside the committed repository.
- Several snapshots predate the current main tip and do not carry a producing commit SHA.

Treat them as historical evidence unless a report is freshly regenerated in an isolated environment
and records the producing commit, generation time, and run context.

## Do Not Relocate Casually

These reports are read by NRC APS gate services under `backend/app/services/`. Moving or renaming them
without coordinated reader updates can break those gates. If a report is retired, move it only through
the repo archive process and update every reader that references the old path.

## Making Future Proof Attributable

Either have CI generate commit-stamped reports without committing runtime artifacts, or run the
operator gate in isolated state and record `{commit, generated_at, run_id}` beside the artifact.
