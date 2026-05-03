# Root Surface Policy

The repository root is an operator entry surface, not a scratch area. New top-level files and directories should be intentional, declared, and easy for agents to classify before they edit.

## Current Rule

- `tools/validate_structure.py` is the current non-mutating structural check.
- Unknown tracked top-level entries are errors.
- Invalid tracked JSON is an error.
- Local absolute path references and oversized tracked files are warnings in the MVP rollout because historical tracked evidence already contains both.
- Use `--strict` only when a lane is ready to treat warnings as failures.

## Classification Before Relocation

Do not delete root artifacts. If a file family should move, first classify it as one of:

- live source
- operator docs
- generated report
- historical evidence
- local-only scratch
- archive material

Relocation requires a file-specific rationale and must follow the repo archive convention.
