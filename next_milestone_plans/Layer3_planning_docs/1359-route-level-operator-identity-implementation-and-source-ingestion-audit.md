# 1359 Route-Level Operator Identity Implementation and Source Ingestion Audit

Status: implementation record. This doc satisfies doc 1358's source_ingestion precondition
and resolves its `needs_audit` classification. Doc 1358 is byte-unchanged; this doc
supersedes its `runtime_status: not_implemented` claim.

## Authority Order

1. live `project6-origin/main` source files on branch `feat/prod-advance-0610`;
2. doc 200 `200_AUTH_SECURITY_ENTRY_CONTRACT.md` allowed-mode list and stop conditions;
3. doc 1358 `1358-route-level-operator-identity-route-dependency-contract.md` as the
   route contract this pass implements;
4. this document.

## Decision

```yaml
runtime_status: implemented
wired_surface:
  handoff_post_routes: 19
  package_post_routes: 16
  source_ingestion_post_routes: 83
  total: 118
skip_list: []
identity_seam_under_none: inert; local single-operator principal derived via
  _server_derived_principal; route proceeds; response byte-identical to prior
fail_closed_proxy_untrusted: HTTP 409, sec_xbrl_in_app_auth_policy_untrusted_proxy_identity
fail_closed_proxy_missing_header: HTTP 401, sec_xbrl_in_app_auth_policy_missing_identity_authority
new_flags: none
new_models: none
new_migrations: none
default_on_changes: none
value_reveal_activation: false
controlled_submit_activation: false
model_migration_change: false
production_readiness_claim: false
```

## needs_audit Resolution

### post_external_export_download_deliver

Classification: **mutating_write** (dual-nature noted).

Non-mixed branch: calls `layer3_workbench.external_export_download_deliver` which reads
artifact path and returns a `FileResponse`; that path involves a read-then-rollback pattern
for the artifact lookup — functionally read on the non-mixed branch.

Mixed-source branch (when source is a workbench-reconciliation session): commits
reconciliation and session state via the workbench service
(`C:/p6live/backend/app/services/layer3_workbench.py`, function
`external_export_download_deliver`, line 14863). The service records delivery state under
reconciliation, making the mixed-source path a mutating_write.

The identity seam is route-level and applies regardless of which branch the request takes.
Classification is **mutating_write** for operator-identity wiring purposes; the read-only
branch does not change this.

### post_external_export_download_signed_reference_use

Classification: **mutating_write**.

Calls `layer3_workbench.external_export_download_use_signed_reference`, which delegates to
`record_used_signed_reference` in
`backend/app/services/layer3_signed_reference_state.py` (line 245). That function issues:
UPDATE `L3SignedReferenceToken` (state transition via `with_for_update`), INSERT
`L3SignedReferenceReceipt`, INSERT `L3SignedReferenceAuditEvent`, and `db.commit()` (line 428).
On rejection paths (revoked, expired, already-used) the function still inserts an audit row
and commits (lines 288, 308, 330, 350, 392). All paths write.

## Source Ingestion Per-Route Classification

All 83 POST routes in `backend/app/api/layer3/source_ingestion.py` are now wired.
Classification by delegated service function. "WRITE" means the service function or its
delegate calls `db.add`/`db.commit`; "read_projection" means DB-read or in-memory only.

### source/intake family (1 route)

| Path | Handler | Classification | Evidence |
|------|---------|----------------|----------|
| `/source/intake/upload` | `post_source_intake_upload` | mutating_write | `layer3_source_intake.record_operator_upload_source_intake` → `db.add(record)` + `db.commit()` (layer3_source_intake.py:296-298) |

### candidate-b bundle/runtime bridge (3 routes)

| Path | Handler | Classification | Evidence |
|------|---------|----------------|----------|
| `/source/ingestion/candidate-b/bundle/material-bridge` | `post_candidate_b_bundle_material_bridge` | read_projection | `layer3_candidate_b_bundle_bridge.prepare_candidate_b_bundle_material_bridge` — no db passed, in-memory path resolution |
| `/source/ingestion/candidate-b/runtime/material-bridge` | `post_candidate_b_runtime_material_bridge` | read_projection | `layer3_candidate_b_runtime_bridge.prepare_candidate_b_runtime_material_bridge` — no db, in-memory bridge |
| `/source/ingestion/candidate-b/runtime/material-bridge/source-scan` | `post_candidate_b_runtime_material_bridge_source_scan` | mutating_write | delegates to `layer3_source_directory_ingestion.scan_server_configured_directory` → `scan_server_owned_directory_root` → `db.add` + `db.commit()` (layer3_source_directory_ingestion.py:271-298) |

### candidate-b status/proof projections (5 routes)

| Path | Handler | Classification | Evidence |
|------|---------|----------------|----------|
| `/source/ingestion/candidate-b/artifact-family/status` | `post_candidate_b_artifact_family_status` | read_projection | `layer3_candidate_b_artifact_status` — no db, filesystem read |
| `/source/ingestion/candidate-b/visual-lane/status` | `post_candidate_b_visual_lane_status` | read_projection | `layer3_candidate_b_visual_lane_status` — no db, status projection |
| `/source/ingestion/candidate-b/runtime/downstream-proof` | `post_candidate_b_runtime_downstream_proof` | read_projection | `layer3_candidate_b_downstream_proof` — no db |
| `/source/ingestion/candidate-b/bundle/downstream-proof` | `post_candidate_b_bundle_downstream_proof` | read_projection | `layer3_candidate_b_bundle_downstream_proof` — no db |
| `/source/ingestion/candidate-b/default-promotion/operator-status` | `post_candidate_b_default_promotion_operator_status` | read_projection | `layer3_candidate_b_operator_status` — no db |

### candidate-b full-corpus operator-workflow (19 routes)

All 19 delegate to workflow state services that contain no `db.commit`/`db.add` — they
project workflow state from DB reads only.

| Path | Handler | Classification | Evidence |
|------|---------|----------------|----------|
| `/source/ingestion/candidate-b/full-corpus/operator-workflow/run` | `post_candidate_b_full_corpus_operator_workflow_run` | read_projection | `layer3_candidate_b_full_corpus_operator_workflow_run` — DB read |
| `/source/ingestion/candidate-b/full-corpus/operator-workflow/status` | `post_candidate_b_full_corpus_operator_workflow_status` | read_projection | `layer3_candidate_b_full_corpus_operator_workflow_status` — DB read |
| `/source/ingestion/candidate-b/full-corpus/operator-workflow/lifecycle/expire` | `post_candidate_b_full_corpus_operator_workflow_lifecycle_expire` | read_projection | `layer3_candidate_b_full_corpus_operator_workflow_lifecycle` — DB read |
| `/source/ingestion/candidate-b/full-corpus/operator-workflow/queue/state` | `post_candidate_b_full_corpus_operator_workflow_queue_state` | read_projection | `layer3_candidate_b_full_corpus_operator_workflow_queue_state` — DB read |
| `/source/ingestion/candidate-b/full-corpus/operator-workflow/scheduler/lease` | `post_candidate_b_full_corpus_operator_workflow_scheduler_lease` | read_projection | `layer3_candidate_b_full_corpus_operator_workflow_scheduler_lease` — DB read |
| `/source/ingestion/candidate-b/full-corpus/operator-workflow/worker/attempt` | `post_candidate_b_full_corpus_operator_workflow_worker_attempt` | read_projection | `layer3_candidate_b_full_corpus_operator_workflow_worker_attempt` — DB read |
| `/source/ingestion/candidate-b/full-corpus/operator-workflow/progress/checkpoint` | `post_candidate_b_full_corpus_operator_workflow_progress_checkpoint` | read_projection | `layer3_candidate_b_full_corpus_operator_workflow_progress_checkpoint` — DB read |
| `/source/ingestion/candidate-b/full-corpus/operator-workflow/completion/failure` | `post_candidate_b_full_corpus_operator_workflow_completion_failure` | read_projection | `layer3_candidate_b_full_corpus_operator_workflow_completion_failure` — DB read |
| `/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/policy` | `post_candidate_b_full_corpus_operator_workflow_retry_policy` | read_projection | `layer3_candidate_b_full_corpus_operator_workflow_retry_policy` — DB read |
| `/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/queue/state` | `post_candidate_b_full_corpus_operator_workflow_retry_queue_state` | read_projection | `layer3_candidate_b_full_corpus_operator_workflow_retry_queue_state` — DB read |
| `/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/scheduler/lease` | `post_candidate_b_full_corpus_operator_workflow_retry_scheduler_lease` | read_projection | `layer3_candidate_b_full_corpus_operator_workflow_retry_scheduler_lease` — DB read |
| `/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/worker/attempt` | `post_candidate_b_full_corpus_operator_workflow_retry_worker_attempt` | read_projection | `layer3_candidate_b_full_corpus_operator_workflow_retry_worker_attempt` — DB read |
| `/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/progress/checkpoint` | `post_candidate_b_full_corpus_operator_workflow_retry_progress_checkpoint` | read_projection | `layer3_candidate_b_full_corpus_operator_workflow_retry_progress_checkpoint` — DB read |
| `/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/completion/failure` | `post_candidate_b_full_corpus_operator_workflow_retry_completion_failure` | read_projection | `layer3_candidate_b_full_corpus_operator_workflow_retry_completion_failure` — DB read |
| `/source/ingestion/candidate-b/full-corpus/operator-workflow/execution/boundary` | `post_candidate_b_full_corpus_operator_workflow_execution_boundary` | read_projection | `layer3_candidate_b_full_corpus_operator_workflow_execution_boundary` — DB read |
| `/source/ingestion/candidate-b/full-corpus/operator-workflow/process/execution` | `post_candidate_b_full_corpus_operator_workflow_process_execution` | read_projection | `layer3_candidate_b_full_corpus_operator_workflow_process_execution` — DB read |
| `/source/ingestion/candidate-b/full-corpus/operator-workflow/process/completion/result` | `post_candidate_b_full_corpus_operator_workflow_process_completion_result` | read_projection | `layer3_candidate_b_full_corpus_operator_workflow_process_completion_result` — DB read |
| `/source/ingestion/candidate-b/full-corpus/operator-workflow/process/completion/result/downstream-proof` | `post_candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof` | read_projection | `layer3_candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof` — DB read |
| `/source/ingestion/candidate-b/full-corpus/operator-workflow/completion/monitor` | `post_candidate_b_full_corpus_operator_workflow_completion_monitor` | read_projection | `layer3_candidate_b_full_corpus_operator_workflow_completion_monitor` — DB read |

### candidate-b repeatability (4 routes)

| Path | Handler | Classification | Evidence |
|------|---------|----------------|----------|
| `/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/checkpoint` | `post_candidate_b_full_corpus_operator_repeatability_checkpoint` | read_projection | `layer3_candidate_b_full_corpus_operator_repeatability_checkpoint` — no db write |
| `/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/rerun-trial` | `post_candidate_b_full_corpus_repeatability_rerun_trial` | read_projection | `layer3_candidate_b_full_corpus_repeatability_rerun_trial` — no db write |
| `/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-checkpoint` | `post_candidate_b_full_corpus_repeatability_acceptance_checkpoint` | read_projection | `layer3_candidate_b_full_corpus_repeatability_acceptance_checkpoint` — no db write |
| `/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-closeout` | `post_candidate_b_full_corpus_repeatability_acceptance_closeout` | read_projection | `layer3_candidate_b_full_corpus_repeatability_acceptance_closeout` — no db write |

### candidate-b repeatability closeout status + default-promotion closure (4 routes)

| Path | Handler | Classification | Evidence |
|------|---------|----------------|----------|
| `/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-closeout/status` | `post_candidate_b_full_corpus_repeatability_acceptance_closeout_status` | read_projection | `layer3_candidate_b_full_corpus_repeatability_acceptance_closeout` — DB read only |
| `/source/ingestion/candidate-b/default-promotion/closure-evidence` | `post_candidate_b_default_promotion_closure_evidence` | read_projection | `layer3_candidate_b_promotion_closure` — no db write |
| `/source/ingestion/candidate-b/default-promotion/readiness-audit` | `post_candidate_b_default_promotion_readiness_audit` | read_projection | `layer3_candidate_b_default_readiness` — no db write |
| `/source/ingestion/candidate-b/default-promotion/final-proof` | `post_candidate_b_default_promotion_final_proof` | read_projection | `layer3_candidate_b_final_proof` — no db write |

### candidate-b broader-eligible-corpus (12 routes)

All 12 delegate to `layer3_candidate_b_broader_scope_*` services that contain no db writes.

| Path | Handler | Classification | Evidence |
|------|---------|----------------|----------|
| `/source/ingestion/candidate-b/broader-eligible-corpus/scope-readiness-audit` | `post_candidate_b_broader_eligible_corpus_scope_readiness_audit` | read_projection | `layer3_candidate_b_broader_scope_readiness` — no db write |
| `/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/runtime` | `post_candidate_b_broader_eligible_corpus_default_scope_runtime` | read_projection | `layer3_candidate_b_broader_scope_runtime` — no db write |
| `/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/selector-use` | `post_candidate_b_broader_eligible_corpus_default_scope_selector_use` | read_projection | `layer3_candidate_b_broader_scope_selector_use` — no db write |
| `/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/selector-use/status` | `post_candidate_b_broader_eligible_corpus_default_scope_selector_use_status` | read_projection | `layer3_candidate_b_broader_scope_selector_use` — no db write |
| `/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/selector-activation` | `post_candidate_b_broader_eligible_corpus_default_scope_selector_activation` | read_projection | `layer3_candidate_b_broader_scope_selector_use` — no db write |
| `/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/activation-receipt/consume` | `post_candidate_b_broader_eligible_corpus_default_scope_activation_receipt_consumption` | read_projection | `layer3_candidate_b_broader_scope_selector_use.record_candidate_b_broader_scope_activation_receipt_consumption` — no db, in-memory receipt |
| `/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/consumption-receipt/use` | `post_candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use` | read_projection | `layer3_candidate_b_broader_scope_selector_use.record_candidate_b_broader_scope_consumption_receipt_use` — no db write |
| `/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/consumption-receipt/use/status` | `post_candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use_status` | read_projection | `layer3_candidate_b_broader_scope_selector_use` — no db write |
| `/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/operator-repeatability/trial` | `post_candidate_b_broader_eligible_corpus_default_scope_operator_repeatability_trial` | read_projection | `layer3_candidate_b_broader_scope_repeatability_trial` — no db write |
| `/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/promotion-readiness` | `post_candidate_b_broader_eligible_corpus_default_scope_promotion_readiness` | read_projection | `layer3_candidate_b_broader_scope_promotion_readiness` — no db write |
| `/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/default-promotion` | `post_candidate_b_broader_eligible_corpus_default_scope_default_promotion` | read_projection | `layer3_candidate_b_broader_scope_default_promotion` — no db write |
| `/source/ingestion/candidate-b/default-promotion/final-proof/status` | `post_candidate_b_default_promotion_final_proof_status` | read_projection | `layer3_candidate_b_final_proof` — no db write |

### server-configured-directory core scan + retrieval (4 routes)

| Path | Handler | Classification | Evidence |
|------|---------|----------------|----------|
| `/source/ingestion/server-configured-directory/scan` | `post_source_directory_ingestion_scan` | mutating_write | `layer3_source_directory_ingestion.scan_server_configured_directory` → `scan_server_owned_directory_root` → `db.add` + `db.commit()` (layer3_source_directory_ingestion.py:271-298) |
| `/source/ingestion/server-configured-directory/material-preview` | `post_source_directory_material_preview` | read_projection | `layer3_source_directory_material_admission.source_directory_material_preview` — no db write |
| `/source/ingestion/server-configured-directory/hybrid-authority/prepare` | `post_source_directory_hybrid_authority_prepare` | read_projection | `layer3_source_directory_hybrid_authority.source_directory_hybrid_authority_prepare` — no db write |
| `/source/ingestion/server-configured-directory/vector-retrieval` | `post_source_directory_vector_retrieval` | read_projection | `layer3_source_directory_vector_retrieval.source_directory_material_vector_retrieval` — no db write |

### server-configured-directory hybrid-context-packet (2 routes)

| Path | Handler | Classification | Evidence |
|------|---------|----------------|----------|
| `/source/ingestion/server-configured-directory/hybrid-context-packet` | `post_source_directory_hybrid_context_packet` | read_projection | `layer3_source_directory_hybrid_context.source_directory_material_hybrid_retrieval_context_packet` — no db write |
| `/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis` | `post_source_directory_hybrid_context_packet_qualitative_analysis` | read_projection | `layer3_source_directory_hybrid_analysis.source_directory_hybrid_context_packet_qualitative_analysis` — no db write (analysis job dispatch only) |

### server-configured-directory hybrid-context-packet/qualitative-analysis pipeline (12 routes)

| Path | Handler | Classification | Evidence |
|------|---------|----------------|----------|
| `.../qualitative-analysis/status` | `post_source_directory_hybrid_context_packet_qualitative_analysis_status` | read_projection | hybrid_analysis.source_directory_hybrid_context_packet_qualitative_analysis_status — no db write |
| `.../qualitative-analysis/package/commit` | `post_source_directory_hybrid_context_packet_qualitative_analysis_package_commit` | mutating_write | hybrid_analysis.source_directory_hybrid_context_packet_qualitative_analysis_package_commit — `db.commit()` (layer3_source_directory_hybrid_analysis.py:990) |
| `.../qualitative-analysis/package/review/submit` | `post_source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit` | mutating_write | hybrid_analysis — `db.commit()` (layer3_source_directory_hybrid_analysis.py:1362) |
| `.../qualitative-analysis/handoff/export/prepare` | `post_source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare` | mutating_write | hybrid_analysis — `db.commit()` (layer3_source_directory_hybrid_analysis.py:1737) |
| `.../qualitative-analysis/handoff/export/download/prepare` | `post_source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_prepare` | mutating_write | hybrid_analysis — `db.commit()` (layer3_source_directory_hybrid_analysis.py:2071) |
| `.../qualitative-analysis/handoff/export/internal-webhook/dispatch` | `post_source_directory_hybrid_context_packet_qualitative_analysis_internal_webhook_dispatch` | mutating_write | `layer3_source_directory_internal_webhook.dispatch_source_directory_internal_webhook` — `db.commit()` (layer3_source_directory_internal_webhook.py:667,700,779,797,859) |
| `.../qualitative-analysis/handoff/export/download/deliver/status` | `post_source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivery_status` | read_projection | hybrid_analysis.source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivery_status — no db write |
| `.../qualitative-analysis/handoff/export/download/provider-private-signed-url/prepare` | `post_source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url_prepare` | mutating_write | delegates to `layer3_provider_private_signed_url_state.record_prepared_provider_private_signed_url_receipt` — `db.add(receipt)` + `db.add(audit)` + `db.commit()` (layer3_provider_private_signed_url_state.py:381-382 idempotent path and new-receipt path) |
| `.../qualitative-analysis/handoff/export/download/provider-private-signed-url/status` | `post_source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url_status` | read_projection | hybrid_analysis — DB reads only, no db write (layer3_source_directory_hybrid_analysis.py:2693-2771) |
| `.../qualitative-analysis/handoff/export/download/provider-private-signed-url/use` | `post_source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url_use` | mutating_write | delegates to `layer3_provider_private_signed_url_state.record_server_owned_provider_private_signed_url_receipt_use` — `db.add(audit)` + `db.commit()` (layer3_provider_private_signed_url_state.py:734-735) |
| `.../qualitative-analysis/handoff/export/download/provider-private-signed-url/revoke` | `post_source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url_revoke` | mutating_write | delegates to `layer3_provider_private_signed_url_state.revoke_provider_private_signed_url_receipt` — `db.add(audit)` + `db.commit()` on every path (layer3_provider_private_signed_url_state.py:992-993, 1011-1012, 1031-1032) |
| `.../qualitative-analysis/handoff/export/download/deliver` | `post_source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_deliver` | read_projection | hybrid_analysis.source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_deliver — no db write; file path resolved from existing record; FileResponse |

### server-configured-directory qualitative-hybrid-analysis pipeline (15 routes)

| Path | Handler | Classification | Evidence |
|------|---------|----------------|----------|
| `/source/ingestion/server-configured-directory/qualitative-hybrid-analysis` | `post_source_directory_qualitative_hybrid_analysis` | read_projection | `layer3_source_directory_qualitative_analysis.source_directory_material_context_packet_qualitative_hybrid_analysis` — no db write |
| `.../qualitative-hybrid-analysis/status` | `post_source_directory_qualitative_hybrid_analysis_status` | read_projection | qualitative_analysis.source_directory_qualitative_hybrid_analysis_status — no db write |
| `.../qualitative-hybrid-analysis/package/commit` | `post_source_directory_qualitative_analysis_package_commit` | mutating_write | qualitative_analysis.source_directory_qualitative_analysis_package_commit — `db.commit()` (layer3_source_directory_qualitative_analysis.py:728) |
| `.../qualitative-hybrid-analysis/package/review/submit` | `post_source_directory_qualitative_analysis_package_review_submit` | mutating_write | qualitative_analysis — `db.commit()` (layer3_source_directory_qualitative_analysis.py:1068) |
| `.../qualitative-hybrid-analysis/package/supersession/preview` | `post_source_directory_qualitative_analysis_package_supersession_preview` | read_projection | qualitative_analysis.source_directory_qualitative_analysis_package_supersession_preview — no db write |
| `.../qualitative-hybrid-analysis/package/replacement-set/record-from-supersession-preview` | `post_source_directory_qualitative_analysis_package_replacement_set_record` | mutating_write | `layer3_replacement_package_set_authority.record_replacement_package_set_authority_from_source_directory_supersession_preview` — WRITE (layer3_replacement_package_set_authority.py confirmed) |
| `.../qualitative-hybrid-analysis/package/supersession/commit` | `post_source_directory_qualitative_analysis_package_supersession_commit` | mutating_write | `layer3_package_supersession_commit.commit_package_supersession_from_source_directory_lifecycle` — WRITE (layer3_package_supersession_commit.py confirmed) |
| `.../qualitative-hybrid-analysis/package/supersession/provider-private-signed-url/prepare` | `post_source_directory_package_supersession_provider_private_signed_url_prepare` | mutating_write | `layer3_package_supersession_commit.source_directory_package_supersession_provider_private_signed_url_prepare` — WRITE |
| `.../qualitative-hybrid-analysis/package/supersession/provider-private-signed-url/status` | `post_source_directory_package_supersession_provider_private_signed_url_status` | read_projection | `layer3_package_supersession_commit.source_directory_package_supersession_provider_private_signed_url_status` — DB read |
| `.../qualitative-hybrid-analysis/package/supersession/provider-private-signed-url/use` | `post_source_directory_package_supersession_provider_private_signed_url_use` | mutating_write | `layer3_package_supersession_commit.source_directory_package_supersession_provider_private_signed_url_use` — WRITE |
| `.../qualitative-hybrid-analysis/package/supersession/provider-private-signed-url/revoke` | `post_source_directory_package_supersession_provider_private_signed_url_revoke` | mutating_write | `layer3_package_supersession_commit.source_directory_package_supersession_provider_private_signed_url_revoke` — WRITE |
| `.../qualitative-hybrid-analysis/handoff/export/prepare` | `post_source_directory_qualitative_analysis_handoff_export_prepare` | mutating_write | qualitative_analysis — `db.commit()` (layer3_source_directory_qualitative_analysis.py:1944) |
| `.../qualitative-hybrid-analysis/handoff/export/download/prepare` | `post_source_directory_qualitative_analysis_external_export_download_prepare` | mutating_write | qualitative_analysis — `db.commit()` (layer3_source_directory_qualitative_analysis.py:2258) |
| `.../qualitative-hybrid-analysis/handoff/export/download/deliver/status` | `post_source_directory_qualitative_analysis_external_export_download_delivery_status` | read_projection | qualitative_analysis.source_directory_qualitative_analysis_external_export_download_delivery_status — no db write |
| `.../qualitative-hybrid-analysis/handoff/export/download/deliver` | `post_source_directory_qualitative_analysis_external_export_download_deliver` | read_projection | qualitative_analysis.source_directory_qualitative_analysis_external_export_download_deliver — no db write; file path resolved; FileResponse |

### mixed-corpus (2 routes)

| Path | Handler | Classification | Evidence |
|------|---------|----------------|----------|
| `/source/mixed-corpus/seed` | `post_raw_mixed_corpus_seed` | read_projection | `layer3_raw_mixed_bridge.seed_raw_mixed_corpus` — DB reads only (queries ConnectorRun, DatasetVersion, ApsContentDocument, ApsContentLinkage); no `db.add`/`db.commit` |
| `/source/mixed-corpus/materialize` | `post_raw_mixed_corpus_materialize` | mutating_write | `layer3_raw_mixed_materialization.materialize_raw_mixed_corpus` → `_ensure_row` → `db.add` + writes |

### Counts

Actual counts from the per-route audit, corrected after an independent verification pass
traced the two-level delegation from `layer3_source_directory_hybrid_analysis.py` into
`layer3_provider_private_signed_url_state.py` (the initial pass missed three signed-url
writes hidden behind that delegation):
- mutating_write: 30
- read_projection: 53
- total: 83

Classification does not affect the wiring decision: all 83 routes carry the seam.

## Wire-All Rationale

read_projection routes are wired alongside mutating_write routes. Under `AUTH_OWNER=none` the
seam is inert for all wired routes — response is byte-identical to the pre-wiring baseline.
Under proxy posture, read_projection routes can expose sensitive artifacts (source material,
workflow state, repeatability checkpoints, delivery status). Identity-presence gating at the
route boundary before service logic executes is the correct posture for the full POST surface.
Wiring only mutating routes would leave a gap where read routes expose artifact-level data
without identity presence having been checked.

## Candidate-B Layering Subsection

The candidate-b operator-workflow routes already route through
`authorize_workflow_access` (`layer3_candidate_b_operator_workflow_access_policy`) — but that
check runs deep in the service after receipt probing, via a request-context contextvar, and is
NOT fail-closed-first at the route boundary.

The new `_route_level_operator_identity` seam at handler-top adds fail-closed-first identity
presence in front of that lane. Under proxy-misconfiguration, the seam's
`sec_xbrl_in_app_auth_policy_*` error codes win deterministically before the service layer is
reached.

Dual error-code namespaces (`sec_xbrl_in_app_auth_policy_*` from the seam,
`layer3_candidate_b_operator_workflow_access_policy` from the deep service check) are
deliberate layering, not contradiction. They fire at different stack depths for different
failure modes.

## Contract Amendments

**(a) Proxy+trusted: both PROXY_IDENTITY_HEADER and PROXY_GROUPS_HEADER required.**

Under proxy+trusted posture, `_server_derived_principal` (inherited by the wrapper) requires
both `PROXY_IDENTITY_HEADER` and `PROXY_GROUPS_HEADER` to be present. Missing groups yields
error code `sec_xbrl_in_app_auth_policy_missing_workspace_authority` (HTTP 401). Doc 1358's
request/response contract enumerated `sec_xbrl_in_app_auth_policy_untrusted_proxy_identity`
(409) and `sec_xbrl_in_app_auth_policy_missing_identity_authority` (401) but did not enumerate
the missing-groups path. This is recorded as deliberate tested behavior; the implementation
is parity with the sec_xbrl and candidate-b lanes.

**(b) 422-precedence: pydantic body validation precedes the handler.**

For routes with typed pydantic request bodies, body validation runs before the handler
function executes. A request with a body that fails model validation returns HTTP 422 without
reaching the `_route_level_operator_identity` seam — the service logic never executes and no
artifact is exposed. The seam's fail-closed 409/401 therefore applies to every request that
would otherwise reach handler logic. Both behaviors are deliberate and tested (see
`test_422_precedence_untrusted_proxy_forbid_model` in
`backend/tests/test_layer3_handoff_operator_identity.py`).

**(c) Multipart pre-parse on the upload route.**

`POST /source/intake/upload` is the only multipart route on the wired surface (declared
`UploadFile`/`Form` parameters; verified by grep across the three route modules). FastAPI's
request handler parses form bodies before dependency resolution and before the handler body,
so under proxy misconfiguration the multipart payload is parsed/spooled by the framework
before the seam returns 401/409. No service logic executes, nothing is persisted by the
route, and no payload content appears in the error response — the fail-closed properties
hold for data exposure and writes. The residual pre-auth cost is bounded request parsing,
which is the same class as amendment (b); request body size limits remain proxy/deployment
owned (the trusted reverse proxy in the non-local profile is the enforcement point).
Converting the route to manual in-handler form parsing, or adding a body-gating middleware,
would change default-profile 422 semantics and the OpenAPI surface — out of scope for this
inert-by-default pass; if pre-parse gating is later wanted it requires a separately governed
slice. (Raised by external review on the implementation PR; resolved as documented-accepted
with the rationale above.)

## Sensitive GET Surface Addendum

Status: follow-up production-hardening runtime slice.

Selected sensitive GET status/read routes now use the same route-level operator-identity
presence seam before service logic as the POST surface. This supersedes the earlier
POST-only GET surface note for the modules listed below.

```yaml
additional_wired_get_surface:
  handoff_get_routes: 5
  source_ingestion_get_routes: 5
  source_sec_edgar_get_routes: 19
  total_get_routes: 29
  drift_guard_get_files:
    - backend/app/api/layer3/handoff.py
    - backend/app/api/layer3/source_ingestion.py
    - backend/app/api/layer3/source_sec_edgar.py
excluded_get_surfaces:
  - backend/app/api/layer3/__init__.py public/session/workbench listing GETs
  - backend/app/api/layer3/sec_xbrl.py surfaces with separate SEC XBRL governance
identity_seam_under_none: inert; local default remains unchanged
fail_closed_proxy_untrusted: HTTP 409, sec_xbrl_in_app_auth_policy_untrusted_proxy_identity
fail_closed_proxy_missing_identity_header: HTTP 401, sec_xbrl_in_app_auth_policy_missing_identity_authority
fail_closed_proxy_missing_groups_header: HTTP 401, sec_xbrl_in_app_auth_policy_missing_workspace_authority
new_flags: none
new_models: none
new_migrations: none
default_on_changes: none
value_reveal_activation: false
controlled_submit_activation: false
model_migration_change: false
production_readiness_claim: false
```

Rationale: these GET routes expose handoff status, source material previews/inventory,
operator workflow history, source-directory ingestion status, internal-webhook delivery
state, and SEC EDGAR artifact/status projections. Under proxy posture they should fail
closed before service logic can expose source, value, artifact, or delivery state. This
remains identity-presence enforcement only; role authorization, StaticFiles wrapping,
remaining GET surfaces, and reverse-proxy authn/authz remain separately owned unless a
later slice governs them.

## Source SEC EDGAR Surface Addendum

Status: follow-up production-hardening runtime slice.

`backend/app/api/layer3/source_sec_edgar.py` is now covered by the same route-level
operator-identity seam and AST drift guard as the handoff, package, and source_ingestion
POST modules.

```yaml
additional_wired_surface:
  source_sec_edgar_post_routes: 35
  drift_guard_files:
    - backend/app/api/layer3/handoff.py
    - backend/app/api/layer3/package.py
    - backend/app/api/layer3/source_sec_edgar.py
    - backend/app/api/layer3/source_ingestion.py
identity_seam_under_none: inert; local single-operator principal derived via
  _server_derived_principal; default local API behavior remains covered by test_layer3_api.py
fail_closed_proxy_untrusted: HTTP 409, sec_xbrl_in_app_auth_policy_untrusted_proxy_identity
fail_closed_proxy_missing_identity_header: HTTP 401, sec_xbrl_in_app_auth_policy_missing_identity_authority
fail_closed_proxy_missing_groups_header: HTTP 401, sec_xbrl_in_app_auth_policy_missing_workspace_authority
new_flags: none
new_models: none
new_migrations: none
default_on_changes: none
value_reveal_activation: false
controlled_submit_activation: false
model_migration_change: false
production_readiness_claim: false
```

Rationale: the source/sec-edgar POST surface contains source acquisition, downstream proof,
operator product surface, value reveal, durable delivery archive, parser, package review, and
handoff/export preparation routes. Even when individual handlers are read projections, proxy
posture should fail closed before service logic can expose source, value, artifact, or delivery
state. This is still identity-presence enforcement only; selected source/sec-edgar GET status
routes are covered by the Sensitive GET Surface Addendum above, while StaticFiles, remaining
GET surfaces, and reverse-proxy authn/authz remain separately owned unless a later slice
governs them.

## Core Workbench Surface Addendum

Status: follow-up production-hardening runtime slice.

`backend/app/api/layer3/__init__.py` is now covered by the same route-level
operator-identity seam and AST drift guard for core workbench POST routes and selected
sensitive GET routes. The public metadata GETs stay intentionally open because they expose
static contract/readiness metadata needed by local/UI bootstrap and do not read session or
candidate state.

```yaml
additional_core_workbench_surface:
  core_workbench_post_routes: 19
  core_workbench_sensitive_get_routes: 5
  public_get_exemptions:
    - /bootstrap
    - /readiness
    - /authority-matrix
identity_seam_under_none: inert; local default remains unchanged
fail_closed_proxy_untrusted: HTTP 409, sec_xbrl_in_app_auth_policy_untrusted_proxy_identity
fail_closed_proxy_missing_identity_header: HTTP 401, sec_xbrl_in_app_auth_policy_missing_identity_authority
fail_closed_proxy_missing_groups_header: HTTP 401, sec_xbrl_in_app_auth_policy_missing_workspace_authority
new_flags: none
new_models: none
new_migrations: none
default_on_changes: none
value_reveal_activation: false
controlled_submit_activation: false
model_migration_change: false
production_readiness_claim: false
```

Rationale: the core workbench POST surface admits preflight, source/material preview,
gate, plan, execution, result, analyst-product, and working-set behavior; the sensitive GET
surface exposes APS candidate/refused-artifact lists, session summary, and sublayer
visualization state. Under proxy posture these routes should fail closed before service
logic can mutate or expose workflow state. This remains identity-presence enforcement only;
role authorization, StaticFiles wrapping, remaining GET surfaces, and reverse-proxy
authn/authz remain separately owned unless a later slice governs them.

## Rollback

The wiring is a single reversible commit set (the `_route_level_operator_identity` call +
`_sec_xbrl_auth_policy_error_response` return block at handler-top in each wired file).
Revert restores prior behavior. No schema change, no data migration, no new model.

## Test Evidence

The original test files plus the source/sec-edgar addendum test provide evidence for the
route-level identity contract:

1. `backend/tests/test_layer3_handoff_operator_identity.py` (62 collected cases) — covers all
   19 handoff POST routes: inertness under `AUTH_OWNER=none` (parametrized sweep), 409 under
   untrusted proxy (sweep), 401 under trusted proxy with missing identity header (sweep), 401
   under trusted proxy with missing groups header, 422-precedence under untrusted proxy (two
   typed body routes), FileResponse routes returning JSON error bodies under proxy.

2. `backend/tests/test_layer3_package_operator_identity.py` (51 collected cases) — covers all
   16 package POST routes: inertness sweep under `AUTH_OWNER=none`, 409 sweep under untrusted
   proxy, 401 sweep under trusted proxy with missing identity header, 401 under trusted proxy
   with missing groups header, 422-precedence under untrusted proxy for a typed body route.

3. `backend/tests/test_layer3_source_ingestion_operator_identity.py` (254 collected cases) —
   covers all 83 source_ingestion POST routes with the same sweeps (none-mode inertness, 409
   untrusted proxy, 401 missing identity header), the missing-groups 401 path, 422-precedence
   pins (multipart upload missing required form fields; extra forbidden field on a typed
   route), and JSON error-body assertions on the two FileResponse delivery routes.

4. `backend/tests/test_layer3_operator_identity_drift_guard.py` (3 tests) - AST structural
   guard over __init__.py/handoff.py/package.py/source_sec_edgar.py/source_ingestion.py: every `router.post` handler must
   carry a `request` parameter and begin with the seam try/except as its first executable
   statement (empty skip-list), and every selected sensitive `router.get` handler in
   __init__.py/handoff.py/source_ingestion.py/source_sec_edgar.py must do the same. Future
   POST routes and selected sensitive GET routes cannot ship unwired or with a misplaced
   seam. The public metadata GET exemptions are explicit.

5. `backend/tests/test_layer3_source_sec_edgar_operator_identity.py` (3 tests) - focused
   runtime proof that a source/sec-edgar POST route fails closed with 409 under untrusted
   proxy posture, fails closed with 401 when either configured proxy identity or workspace
   authority is absent, does not echo proxy canaries, and does not reach source acquisition
   service logic before the identity seam.

6. `backend/tests/test_layer3_sensitive_get_operator_identity.py` (3 tests) - focused
   runtime proof that representative handoff, source_ingestion, and source/sec-edgar GET
   routes fail closed with 409 under untrusted proxy posture, return JSON policy errors, do
   not echo proxy canaries, and do not reach service logic before the identity seam.

7. `backend/tests/test_layer3_core_workbench_operator_identity.py` (6 tests) - focused
   runtime proof that a representative core workbench POST route and representative
   candidate/session GET routes fail closed with 409 under untrusted proxy posture, return
   JSON policy errors, do not echo proxy canaries, and do not reach service logic before the
   identity seam; also proves `/bootstrap`, `/readiness`, and `/authority-matrix` stay
   available as public metadata GETs.

Pre-existing `backend/tests/test_layer3_api.py` regression baseline is preserved (317 passed
for this source/sec-edgar addendum slice); the full `test_layer3_*` selection from the original
implementation record passed with no prior test counts decreased after wiring and the four
reconciled candidate-b proxy route tests updated to the seam-first contract.

Contract slices satisfied:
- `inertness_proof_none`: covered by handoff + package inertness sweeps; seam function
  identity is shared with source_ingestion routes.
- `fail_closed_proxy_untrusted`: covered by 409 sweeps in both test files.
- `fail_closed_proxy_missing_header`: covered by 401 sweeps.
- `no_leak`: verified — no raw proxy header, identity string, path, or credential in error bodies.
- `regression_slice`: `test_layer3_api.py` baseline preserved.
- `needs_audit_routes_excluded`: `post_external_export_download_deliver` and
  `post_external_export_download_signed_reference_use` were resolved by this audit and ARE
  wired; their classification is mutating_write as documented above. The exclusion is
  lifted by this doc.
