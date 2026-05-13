# 316 - Source Intake Package Review Submit Boundary Freeze

Status: planning/control freeze for `source_intake_package_review_submit_boundary`.

Branch: `codex/l3-source-intake-package-review-submit-freeze`
Current-main predecessor commit: `824d3bb2c415e81f91bdef52e09349f881648c1b`
Predecessor implementation: `315_SOURCE_INTAKE_PACKAGE_CONSTRUCTION_COMMIT_BOUNDARY.md`
Owner service: `backend/app/services/layer3_workbench.py`
Current failure boundary: `source_intake_package_review_submit_not_admitted`

## Canonical source of truth

The canonical source of truth for the next implementation is the server-owned source-intake package construction state produced by `package_construction_commit`, including `layer3.source_intake_package_construction_commit.v1`, the durable `L3ReconciliationRecord`, the three `L3OutputPackage` rows, package payload refs/hashes, `source_intake_record_id`, `candidate_id`, and source-intake output payload hash.

The live failure boundary is repo-confirmed in `backend/app/services/layer3_workbench.py`: `package_review_submit` still calls `_raise_if_source_intake_downstream_not_admitted` and returns `source_intake_package_review_submit_not_admitted` for source-intake status authority after the request contract and output metadata checks pass.

## Frozen next code-bearing action

The next code-bearing action is `implement_source_intake_package_review_submit_boundary` only.

That implementation must reuse the existing `package_review_submit` request contract. It must require the source-intake package construction commit authority from `layer3.source_intake_package_construction_commit.v1`, preserve the underlying `layer3.source_intake_execution_output.v1` output authority, require the supplied reconciliation record and output package ids/hashes to match the durable server-owned package state, preserve `source_intake_record_id`, `candidate_id`, output payload hash, package payload refs, and package payload hashes, and record only bounded source-intake package-review submit decision state.

The implementation must not create `AnalysisRun`, new route, rendered UI, model, migration, auth/security, connector, provider URL, RAG/vector, generic source upload, local path/directory, handoff/export, APS dispatch, external export/download, or broad qualitative behavior.

## Required future proofs

- `source_intake_package_construction_can_record_package_review_submit_decision`
- `source_intake_package_review_submit_identity_is_deterministic_and_server_derived`
- `source_intake_identity_preserved_in_package_review_submit_state`
- `package_payload_refs_and_hashes_match_durable_package_state`
- `no_analysis_run_required_or_created`
- `duplicate_or_conflicting_package_review_submit_requests_fail_closed_or_replay_idempotently`
- `mismatched_construction_basis_hash_fails_closed`
- `mismatched_reconciliation_record_fails_closed`
- `mismatched_output_package_ids_or_payload_hashes_fail_closed`
- `unsupported_submit_decisions_follow_existing_contract`
- `handoff_export_remains_blocked`
- `aps_handoff_dispatch_remains_blocked`
- `external_export_download_remains_blocked`
- `existing_associated_cohort_and_single_aps_package_review_submit_unchanged`

## Explicit non-goals

- handoff/export prepare or dispatch
- APS handoff dispatch
- external export/download readiness or delivery
- connector destination dispatch
- provider public/private URL behavior
- RAG/vector retrieval or hybrid qualitative analysis
- generic source upload or local path/directory authority
- rendered UI changes
- backend route changes
- model or migration changes
- auth/security behavior changes
- broad qualitative execution

## Stop condition for this freeze

This freeze is complete when the planning doc, progress board, progress manifest, proof manifest, and `tools/l3-progress-check.py` all agree that `source_intake_package_review_submit_boundary` is selected as the next exact runtime boundary and that no runtime behavior is admitted by this branch.
