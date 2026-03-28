# Agent Bake-Off Submission Checklist: APS Tier1 Retrieval Plane Phase1C

Each submission must provide all of the following in its owned workspace directory.

## Deliverables

- one concise implementation summary
- one changed-file list with reasons
- one architecture note describing tool/service/test boundaries
- one assumptions and tradeoffs note
- one scope-conformance statement

## Logs

- one validation log listing exact commands run
- one explicit statement on whether `project6.ps1` validation was executed
- one explicit statement on whether the review UI regression suite was run

## Patches

- one exported patch or diff artifact

## Required Content

The submission must explicitly state:

- whether public routes were left unchanged
- whether any hidden cutover switch was introduced
- whether empty-runtime and retrieval-not-materialized cases fail closed
- what mismatch categories the proof gate emits
- any tech-debt risks introduced or avoided by the design
