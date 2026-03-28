# Agent Bake-Off Submission Checklist: APS Tier1 Retrieval Plane Phase1D

Each submission must provide all of the following in its owned workspace directory.

## Deliverables

- one concise implementation summary
- one changed-file list with reasons
- one architecture note describing router, service, and test boundaries
- one assumptions and tradeoffs note
- one scope-conformance statement

## Logs

- one validation log listing exact commands run
- one explicit statement on whether the Phase1C cutover proof was rerun after the cutover
- one explicit statement on whether `project6.ps1` was executed in this slice
- one explicit statement on whether the review UI regression suite was run

## Patches

- one exported patch or diff artifact

## Required Content

The submission must explicitly state:

- whether the public run-scoped `content-units` route was cut over
- whether the public `content-search` route was cut over only for explicit `run_id`
- whether omitted-`run_id` search remained unchanged
- whether operator routes remained unchanged
- whether absent and partial retrieval materialization now fail closed with `409`
- any tech-debt risks introduced, removed, or intentionally deferred by the cutover
