# NRC ADAMS APS Status Handoff

## 1. Purpose and scope
This document is the canonical repo handoff surface for the current NRC ADAMS APS stack state as of March 11, 2026.

It is a documentation/status freeze, not a feature plan. Repo truth in this document follows this precedence order:
1. Current code, tests, scripts, migrations, and repo-contained artifacts
2. Current proof reports/manifests/revalidation artifacts
3. Current runbooks/docs
4. Older status prose and historical planning notes

## 2. Current status summary
| Status surface | Current state | Proof |
| --- | --- | --- |
| Local aggregate NRC gate suite | Green | Revalidated in this pass with `.\project6.ps1 -Action gate-nrc-aps`; result: `58 passed, 25 deselected`; replay validation PASS; fail-closed local validator reports PASS |
| Fresh live batch | Green | Existing finalized manifest `backend/app/storage/connectors/reports/nrc_aps_live_batches/aps_live_batch_20260311T063437Z_fde44a3a/aps_live_batch_20260311T063437Z_fde44a3a_manifest_v1.json` shows `batch_status=completed`, `completed_cycle_count=3`, `failed_cycle_count=0`, and `v1_status=observed` for all 3 cycles |
| Promotion validation | Green | Revalidated in this pass with `.\project6.ps1 -Action validate-nrc-aps-promotion -NrcApsBatchManifest "<corrected manifest>"`; report PASS with `evaluated_cycles=3` and `pass_rate=1.0` in `tests/reports/nrc_aps_promotion_validation_report.json` |
| Policy tuning needed for current green state | No | Canonical policy `backend/app/services/nrc_adams_resources/aps_promotion_policy_v1.json` passes against the corrected batch; no tuned-policy comparison artifact was required for the current passing state |
| Stack treated as green through evidence retrieval / assembly | Yes | Local aggregate gate suite is green, evidence-bundle gate is green, corrected fresh live batch is green, and promotion validation is green against that corrected batch |

## 3. Closed layers
| Layer | Why it matters | Primary repo truth |
| --- | --- | --- |
| Replay regression control | Locks parser/compiler/normalizer/negotiator behavior against captured evidence | `backend/app/services/nrc_aps_replay_gate.py`, `tests/fixtures/nrc_aps_replay/v1`, `tests/reports/nrc_aps_replay_validation_report.json` |
| 2A sync delta / drift correctness | Freezes metadata change/baseline/delta semantics | `backend/app/services/nrc_aps_sync_drift.py`, `tests/reports/nrc_aps_sync_drift_validation_report.json` |
| Operational safeguards | Freezes limiter/timeout/retry/lint/runtime safety semantics | `backend/app/services/nrc_aps_safeguards.py`, `tests/reports/nrc_aps_safeguard_validation_report.json` |
| 2B promotion governance | Freezes batch-centric promotion evaluation and policy-only tuning workflow | `backend/app/services/nrc_aps_live_batch.py`, `backend/app/services/nrc_aps_promotion_gate.py`, `backend/app/services/nrc_aps_promotion_tuning.py`, `tests/reports/nrc_aps_promotion_validation_report.json` |
| Beyond-metadata artifact ingestion | Freezes additive artifact download/hydration/normalization contracts | `backend/app/services/nrc_aps_artifact_ingestion.py`, `tests/reports/nrc_aps_artifact_ingestion_validation_report.json` |
| Content indexing | Freezes deterministic content-unit generation and derived DB indexing | `backend/app/services/nrc_aps_content_index.py`, `tests/reports/nrc_aps_content_index_validation_report.json` |
| Evidence retrieval / assembly | Freezes provenance-preserving evidence bundle assembly over indexed content | `backend/app/services/nrc_aps_evidence_bundle_contract.py`, `backend/app/services/nrc_aps_evidence_bundle.py`, `tests/reports/nrc_aps_evidence_bundle_validation_report.json` |

These layers should be treated as closed except for defect-driven work.

## 4. Important defect history
### APS-V1 safeguard-scope defect
- Failed proof batch: `aps_live_batch_20260311T063035Z_29f07671`
- Failure mode: APS-V1 ramp requests exhausted safeguard scope attempt budget; the failed batch manifest shows `v1_status=error` in every cycle while V2 behavior was otherwise consistent
- Not the cause:
  - not a promotion-policy defect
  - not an evidence-bundle defect
  - not a live APS contract reversal for `shape_a`
- Fix: [tools/run_nrc_aps_live_validation.py](../../tools/run_nrc_aps_live_validation.py) now assigns distinct `explicit_scope` values per APS-V1 ramp attempt, for example `live_validation_v1_rps:3:attempt:3`
- Regression coverage: [tests/test_nrc_aps_live_validation.py](../../tests/test_nrc_aps_live_validation.py) locks distinct safeguard scopes per APS-V1 attempt
- Fresh proof of fix: corrected batch `aps_live_batch_20260311T063437Z_fde44a3a` completed with `v1_status=observed` in all 3 cycles, and promotion validation passed against that batch

## 5. Schema/contract inventory
| Layer | Schemas / contract ids | Current repo truth |
| --- | --- | --- |
| Replay | `schema_version=1` only | Current replay contract code defines replay schema version `1`, but no explicit replay `schema_id` was found in `backend/app/services/nrc_aps_replay_models.py` or `backend/app/services/nrc_aps_replay_gate.py` |
| 2A sync delta / drift | `aps.sync_delta.v1`, `aps.sync_drift.v1`, `aps.sync_drift_failure.v1`, `aps_comparison_basis_v1`, `aps_projection_hash_v1` | `backend/app/services/nrc_aps_sync_drift.py` |
| Safeguards | `aps_safeguard_policy.v1`, `aps.safeguard_lint.v1`, `aps.safeguard_report.v1`, `aps.safeguard_validation.v1` | `backend/app/services/nrc_aps_safeguards.py` |
| Live validation / promotion | `aps.live_validation_report.v1`, `aps.live_validation_batch.v1`, `aps.promotion_policy.v1`, `aps.promotion_governance.v2`, `aps.promotion_policy_diff.v1`, `aps.promotion_policy_compare.v1`, `aps.promotion_policy_rationale.v1` | `backend/app/services/nrc_aps_live_batch.py`, `backend/app/services/nrc_aps_promotion_gate.py`, `backend/app/services/nrc_aps_promotion_tuning.py` |
| Artifact ingestion | `aps.artifact_ingestion_target.v1`, `aps.artifact_ingestion_run.v1`, `aps.artifact_ingestion_failure.v1`, `aps.artifact_ingestion_gate.v1`, `aps_text_normalization_v1` | `backend/app/services/nrc_aps_artifact_ingestion.py` |
| Content indexing | `aps.content_units.v1`, `aps.content_index_run.v1`, `aps.content_index_failure.v1`, `aps.content_index_gate.v1`, `aps_content_units_v1`, `aps_chunking_v1` | `backend/app/services/nrc_aps_content_index.py` |
| Evidence bundles | `aps.evidence_bundle.v1`, `aps.evidence_bundle_failure.v1`, `aps.evidence_bundle_gate.v1`, `aps_evidence_request_norm_v1`, `aps_evidence_ranking_v1`, `aps_evidence_snippet_v1`, `aps_evidence_snapshot_v1` | `backend/app/services/nrc_aps_evidence_bundle_contract.py` |

### Additive run-level `report_refs` keys surfaced today
These keys are operator-visible on `GET /api/v1/connectors/runs/{id}`:
- `aps_sync_delta`
- `aps_sync_drift`
- `aps_sync_drift_failure`
- `aps_safeguard`
- `aps_artifact_ingestion`
- `aps_artifact_ingestion_failure`
- `aps_content_index`
- `aps_content_index_failure`
- `aps_evidence_bundles`
- `aps_evidence_bundle_failures`

Internal helper containers such as `aps_sync_report_refs` and `aps_evidence_bundle_report_refs` live in `query_plan_json`; they are implementation detail surfaces, not the outward API contract.

## 6. API surface inventory
| Endpoint | Purpose | Current repo truth |
| --- | --- | --- |
| `POST /api/v1/connectors/nrc-adams-aps/runs` | Submit NRC APS connector run | `backend/app/api/router.py` |
| `GET /api/v1/connectors/runs/{id}` | Run detail view, including additive NRC APS `report_refs` | `backend/app/api/router.py`, `backend/app/services/connectors_sciencebase.py` |
| `GET /api/v1/connectors/runs/{id}/targets` | Target list | `backend/app/api/router.py` |
| `GET /api/v1/connectors/runs/{id}/events` | Event log | `backend/app/api/router.py` |
| `GET /api/v1/connectors/runs/{id}/reports` | Base report bundle only | `backend/app/api/router.py`, `backend/app/services/connectors_sciencebase.py` |
| `POST /api/v1/connectors/runs/{id}/cancel` | Cancel request | `backend/app/api/router.py` |
| `POST /api/v1/connectors/runs/{id}/resume` | Resume request | `backend/app/api/router.py` |
| `GET /api/v1/connectors/runs/{id}/content-units` | Read-only indexed content units for a run | `backend/app/api/router.py`, `backend/app/services/nrc_aps_content_index.py` |
| `POST /api/v1/connectors/nrc-adams-aps/content-search` | Read-only lexical content search over indexed chunks; empty query is `422` | `backend/app/api/router.py`, `backend/app/services/nrc_aps_content_index.py` |
| `POST /api/v1/connectors/nrc-adams-aps/evidence-bundles` | Assemble evidence bundle from DB-backed content index rows | `backend/app/api/router.py`, `backend/app/services/nrc_aps_evidence_bundle.py` |
| `GET /api/v1/connectors/nrc-adams-aps/evidence-bundles/{bundle_id}` | Read persisted bundle snapshot page | `backend/app/api/router.py`, `backend/app/services/nrc_aps_evidence_bundle.py` |

### API nuance that should not be missed
- `GET /api/v1/connectors/runs/{id}` is the outward run surface that includes NRC APS additive `report_refs`
- `GET /api/v1/connectors/runs/{id}/reports` still returns the older base report bundle from `build_report_refs(...)`
- This is current code truth, not an open contradiction

## 7. Gate/validation inventory
| Gate / validation surface | Repo command | Closest direct entrypoint | Current proof |
| --- | --- | --- | --- |
| Aggregate NRC gate | `.\project6.ps1 -Action gate-nrc-aps` | `project6.ps1` | Revalidated in this pass: PASS, `58 passed, 25 deselected`; replay PASS; validator reports PASS |
| Replay gate | `.\project6.ps1 -Action validate-nrc-aps-replay` | `tools/nrc_aps_replay_gate.py` | `tests/reports/nrc_aps_replay_validation_report.json` |
| Sync-drift gate | `.\project6.ps1 -Action validate-nrc-aps-sync-drift` | `tools/nrc_aps_sync_drift_gate.py` | `tests/reports/nrc_aps_sync_drift_validation_report.json` |
| Safeguard gate | `.\project6.ps1 -Action validate-nrc-aps-safeguards` | `tools/nrc_aps_safeguard_gate.py` | `tests/reports/nrc_aps_safeguard_validation_report.json` |
| Promotion validation / gate | `.\project6.ps1 -Action validate-nrc-aps-promotion` | `tools/nrc_aps_promotion_gate.py` | `tests/reports/nrc_aps_promotion_validation_report.json` |
| Artifact-ingestion gate | `.\project6.ps1 -Action validate-nrc-aps-artifact-ingestion` | `tools/nrc_aps_artifact_ingestion_gate.py` | `tests/reports/nrc_aps_artifact_ingestion_validation_report.json`; no dedicated runbook found |
| Content-index gate | `.\project6.ps1 -Action validate-nrc-aps-content-index` | `tools/nrc_aps_content_index_gate.py` | `tests/reports/nrc_aps_content_index_validation_report.json` |
| Evidence-bundle gate | `.\project6.ps1 -Action validate-nrc-aps-evidence-bundle` | `tools/nrc_aps_evidence_bundle_gate.py` | `tests/reports/nrc_aps_evidence_bundle_validation_report.json` |
| Fresh live batch collection | `.\project6.ps1 -Action collect-nrc-aps-live-batch` | `tools/nrc_aps_live_validation_batch.py` | Current passing batch carried forward from existing manifest `aps_live_batch_20260311T063437Z_fde44a3a` |
| Policy-only tuning comparison | `.\project6.ps1 -Action compare-nrc-aps-promotion-policy` | `tools/nrc_aps_promotion_tuning.py` | Workflow exists; not needed for current green baseline |

## 8. Commands/operator workflow
### Aggregate local validation
```powershell
.\project6.ps1 -Action gate-nrc-aps
```

### Fresh live batch collection
```powershell
.\project6.ps1 -Action collect-nrc-aps-live-batch -ConsecutiveRuns 3 -BatchSpacingSeconds 5 -TimeoutSeconds 45
```

### Promotion validation against one finalized batch
```powershell
.\project6.ps1 -Action validate-nrc-aps-promotion -NrcApsBatchManifest "<abs_manifest_path>"
```

### Replay corpus/operator workflow
```powershell
.\project6.ps1 -Action build-nrc-aps-replay-corpus
.\project6.ps1 -Action check-nrc-aps-replay-corpus
.\project6.ps1 -Action validate-nrc-aps-replay
```

### Layer-specific fail-closed validators
```powershell
.\project6.ps1 -Action validate-nrc-aps-sync-drift
.\project6.ps1 -Action validate-nrc-aps-safeguards
.\project6.ps1 -Action validate-nrc-aps-artifact-ingestion
.\project6.ps1 -Action validate-nrc-aps-content-index
.\project6.ps1 -Action validate-nrc-aps-evidence-bundle
```

### Policy-only tuning workflow
```powershell
.\project6.ps1 -Action compare-nrc-aps-promotion-policy `
  -NrcApsBatchManifest "<abs_manifest_path>" `
  -NrcApsTunedPromotionPolicy "<abs_tuned_policy_path>" `
  -NrcApsPromotionRationale "<abs_rationale_path>"
```

### Direct script entrypoints
- `tools/run_nrc_aps_live_validation.py`
- `tools/nrc_aps_live_validation_batch.py`
- `tools/nrc_aps_replay_gate.py`
- `tools/nrc_aps_sync_drift_gate.py`
- `tools/nrc_aps_safeguard_gate.py`
- `tools/nrc_aps_artifact_ingestion_gate.py`
- `tools/nrc_aps_content_index_gate.py`
- `tools/nrc_aps_evidence_bundle_gate.py`
- `tools/nrc_aps_promotion_gate.py`
- `tools/nrc_aps_promotion_tuning.py`

## 9. Storage/environment/execution notes
- Local/test gate alignment in `project6.ps1` sets:
  - `STORAGE_DIR=backend/app/storage_test_runtime`
  - `DATABASE_URL=sqlite:///./test_method_aware.db`
- Live proofs and live run artifacts use `backend/app/storage/connectors/reports`
- Runtime environment assumptions evident in repo:
  - `NRC_ADAMS_APS_SUBSCRIPTION_KEY`
  - `NRC_ADAMS_APS_API_BASE_URL`
- Canonical writers are BOM-free
- Evidence-bundle readers and validators tolerate BOM-bearing JSON via `utf-8-sig`; that tolerance is confirmed for evidence-bundle code paths, not generalized beyond them
- Evidence-bundle run-level surfacing is plural and additive:
  - `report_refs.aps_evidence_bundles`
  - `report_refs.aps_evidence_bundle_failures`
- Artifact ingestion, content indexing, and evidence bundles are additive layers over the metadata connector flow; they do not replace replay, 2A, safeguards, or promotion
- API callers should not assume `GET /connectors/runs/{id}/reports` includes APS additive refs; use `GET /connectors/runs/{id}` for the additive `report_refs` view

## 10. DB/migration/indexing state
| Migration | Adds | Role |
| --- | --- | --- |
| `0007_aps_hardening_state_tables.py` | `aps_dialect_capability`, `aps_sync_cursor` | Runtime APS capability memory and sync-state DB layer |
| `0008_aps_content_index_tables.py` | `aps_content_document`, `aps_content_chunk`, `aps_content_linkage` | Derived DB content index over canonical content-unit artifacts |

### Current DB truth split
- `aps_dialect_capability` and `aps_sync_cursor` are runtime DB state tables
- `aps_content_document`, `aps_content_chunk`, and `aps_content_linkage` are derived index tables
- Canonical truth for content indexing remains the emitted file artifacts such as `aps.content_units.v1`; DB rows are derived for retrieval/search

## 11. Known-good proof artifacts
- Corrected fresh live batch manifest:
  - `backend/app/storage/connectors/reports/nrc_aps_live_batches/aps_live_batch_20260311T063437Z_fde44a3a/aps_live_batch_20260311T063437Z_fde44a3a_manifest_v1.json`
- Failed pre-fix live batch manifest:
  - `backend/app/storage/connectors/reports/nrc_aps_live_batches/aps_live_batch_20260311T063035Z_29f07671/aps_live_batch_20260311T063035Z_29f07671_manifest_v1.json`
- Promotion validation report:
  - `tests/reports/nrc_aps_promotion_validation_report.json`
- Replay validation report:
  - `tests/reports/nrc_aps_replay_validation_report.json`
- Sync-drift validation report:
  - `tests/reports/nrc_aps_sync_drift_validation_report.json`
- Safeguard validation report:
  - `tests/reports/nrc_aps_safeguard_validation_report.json`
- Artifact-ingestion validation report:
  - `tests/reports/nrc_aps_artifact_ingestion_validation_report.json`
- Content-index validation report:
  - `tests/reports/nrc_aps_content_index_validation_report.json`
- Evidence-bundle validation report:
  - `tests/reports/nrc_aps_evidence_bundle_validation_report.json`

## 12. Proof of current state
### Freeze timestamp
- March 11, 2026

### Revalidated in this pass
1. `.\project6.ps1 -Action gate-nrc-aps`
   - Result: PASS
   - Pytest slice: `58 passed, 25 deselected`
   - Replay validation: PASS
   - Local fail-closed validator reports updated and passing:
     - replay
     - sync drift
     - safeguards
     - artifact ingestion
     - content index
     - evidence bundle
2. `.\project6.ps1 -Action validate-nrc-aps-promotion -NrcApsBatchManifest "<corrected manifest>"`
   - Result: PASS
   - `batch_id=aps_live_batch_20260311T063437Z_fde44a3a`
   - `evaluated_cycles=3`
   - `pass_rate=1.0`

### Carried forward from existing repo-contained proof artifacts
1. Corrected live batch manifest `aps_live_batch_20260311T063437Z_fde44a3a`
   - `schema_id=aps.live_validation_batch.v1`
   - `batch_status=completed`
   - `completed_cycle_count=3`
   - `failed_cycle_count=0`
   - all cycle reports show `v1_status=observed`
2. Failed pre-fix live batch manifest `aps_live_batch_20260311T063035Z_29f07671`
   - `schema_id=aps.live_validation_batch.v1`
   - `batch_status=completed`
   - all cycle reports show `v1_status=error`
3. Promotion report at `tests/reports/nrc_aps_promotion_validation_report.json`
   - `schema_id=aps.promotion_governance.v2`
   - `policy_schema_id=aps.promotion_policy.v1`
   - linked to corrected batch manifest and canonical policy checksum

### What current green means
- Local aggregate gate green means the NRC local test/gate suite is currently passing
- Fresh live batch green means the corrected finalized live batch exists and meets the current promotion evidence expectations
- Promotion validation green means canonical promotion policy passes against that corrected batch
- No policy-only tuning was needed for the current corrected green state

## 13. Recommended next milestone
Move above evidence bundles into evidence consumption/reporting. The best next direction is a higher-level evidence packaging layer such as dossier/report assembly, deterministic citation/export surfaces, or similarly provenance-preserving evidence consumption over existing evidence bundles.

This is a recommendation only. It is not started here.

## 14. Explicit non-goals / do-not-reopen guidance
Do not reopen these closed layers/contracts absent defects:
- replay contracts
- 2A sync delta / drift contracts
- safeguard architecture
- 2B promotion architecture
- artifact-ingestion contracts
- content-index contracts
- evidence-bundle contracts

Do not jump immediately into these expansions unless explicitly chosen later:
- OCR
- multimodal extraction
- embeddings / semantic search
- UI / dashboard expansion

## 15. Open contradictions / unverified areas
- No unresolved repo-truth contradiction remained after this freeze pass.
- Current absence noted explicitly, not as a contradiction:
  - an explicit replay `schema_id` was not found in the current replay corpus/index/report contract implementation; current replay truth is `schema_version=1`

## 16. Status-freeze metadata
- Freeze date: March 11, 2026
- Primary source precedence used:
  1. current code/tests/scripts/migrations and repo-contained artifacts
  2. current proof reports/manifests
  3. current runbooks/docs
  4. older status prose/historical notes
- Primary code surfaces inspected:
  - `project6.ps1`
  - `backend/app/api/router.py`
  - `backend/app/schemas/api.py`
  - `backend/app/models/models.py`
  - `backend/alembic/versions/0007_aps_hardening_state_tables.py`
  - `backend/alembic/versions/0008_aps_content_index_tables.py`
  - NRC APS service modules under `backend/app/services/`
  - NRC APS tests under `tests/`

## 17. Documentation-blocking fixes applied
None. No code/runtime changes were required for this freeze pass.

## 18. Files touched in this freeze pass
- `docs/nrc_adams/nrc_aps_status_handoff.md`
  - new canonical status/handoff doc
- `README.md`
  - updated NRC APS navigation and command coverage
- `REPO_INDEX.md`
  - added canonical handoff redirection and marked stale NRC APS status surface as historical/non-authoritative
- `docs/nrc_adams/replay_gate_runbook.md`
  - added canonical handoff note
- `docs/nrc_adams/sync_drift_gate_runbook.md`
  - added canonical handoff note
- `docs/nrc_adams/safeguard_gate_runbook.md`
  - added canonical handoff note
- `docs/nrc_adams/promotion_gate_runbook.md`
  - added canonical handoff note
- `docs/nrc_adams/content_index_gate_runbook.md`
  - added canonical handoff note
- `docs/nrc_adams/evidence_bundle_gate_runbook.md`
  - added canonical handoff note
