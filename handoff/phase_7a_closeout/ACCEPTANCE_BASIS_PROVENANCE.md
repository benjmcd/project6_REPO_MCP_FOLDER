# Provenance Note For `accepted_facts.json`

> Documentation only. Recorded against `project6-origin/main` at
> `abd8c3f8ac2b2545fda8b88d46aa916a22b626e8`.
> This file does not modify `accepted_facts.json`.

## Verifiability Gap

`handoff/phase_7a_closeout/accepted_facts.json` cites:

```text
acceptance_basis = "Artifact Audit run_20260314_010136"
backend/app/storage_test_runtime/advanced_validation_runs/run_20260314_010136
backend/app/storage_test_runtime/advanced_validation_runs/run_20260314_010136/artifact_audit
```

That runtime evidence directory is absent from the committed tree. The run id remains referenced by
docs and accepted facts, but the physical runtime package is not available as committed evidence.

## Consequence

The accepted counts in `accepted_facts.json` remain useful historical state, but their cited basis is
not reproducible from the current repository alone. Treat them as historical or advisory unless the
runtime package is restored, a replacement committed proof is generated, or the accepted-facts surface
is updated through its normal Tier-2 process.

## Resolution Options

1. Restore the cited runtime package into an appropriate committed evidence location.
2. Regenerate the Phase 7A validation in an isolated environment and point the basis at a
   commit-stamped artifact.
3. Add a status field, through the Tier-2 accepted-facts process, marking the cited basis as
   superseded because the source run is absent from the committed tree.

Until one of those happens, downstream readers should not treat the acceptance basis as current-commit
proof.
