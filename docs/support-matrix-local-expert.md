# Local Expert Support Matrix

> **2026-09-04 current interpretation:** The 32 capability IDs, their statuses,
> and the selected-profile pin set remain intentionally scoped and unchanged.
> Public ScienceBase DatasetVersion analysis and public result-value inspection
> are bounded experimental default-off subfeatures beneath the existing
> `sciencebase_public_connector_slice` and `layer3_workbench_ui` capabilities;
> they do not add capability rows. Their source defaults are
> `LAYER3_PUBLIC_DATASET_ANALYSIS_ENABLED=false` and
> `LAYER3_PUBLIC_CONNECTOR_VALUE_REVEAL_ENABLED=false`. Values require both
> flags, newest admitted `sciencebase/public_api` provenance, provenance
> co-display, and storage-reference exclusion. This clarification changes no
> support status, schema, default, runtime state, or production-readiness claim.

This support matrix applies to the selected final 0.3.0 profile `base=local_expert` with `overlays=["public_connectors","sec_xbrl_offline"]`.

The profile is a single-operator local source-run posture: `DEPLOYMENT_MODE=local`, `AUTH_OWNER=none`, SQLite/local filesystem, and loopback/local trust. Under this posture there is no authentication boundary; the local principal is constant and identity or role enforcement is not a product claim.

`config/release_readiness.yaml` remains profile-neutral. Its `owner_selected_profile_specific_gates` list must stay empty; selected-profile acceptance lives in `config/support_matrix.yaml`, `scripts/support_matrix_check.py`, and the RC capstone scripts, including `scripts/rc3_sec_xbrl_offline_acceptance.py` for the current final 0.3.0 profile.

The selected final 0.3.0 profile claims the public_connectors overlay for public/anonymous connectors and the sec_xbrl_offline overlay for offline/replay SEC XBRL proof only. ScienceBase public/MCS, Senate LDA anonymous metadata, World Bank Indicators anonymous metadata, BLS Public Data API v1 anonymous metadata, OECD SDMX anonymous SDMX-CSV metadata, CFTC COT anonymous public report rows, and connector run observability are supported for operator-workflow + local-deployment under the local_expert base. BLS v1 enforces per-query/per-run caps locally; 25-queries/day compliance across runs remains an operator responsibility. OECD SDMX enforces per-run caps locally; 60-downloads/hour and no-VPN/no-anonymized-traffic compliance remain operator responsibility. SEC XBRL value-bearing support remains simulation/offline-replay on already-acquired operator-supplied evidence, and bounded SEC live source-artifact acquisition remains explicit-default-off.

For the public connector slice, restart recovery is operator-resume-driven: after a crash or process loss, the operator rechecks the run and posts `POST /api/v1/connectors/runs/{connector_run_id}/resume`. The selected profile does not claim an automatic orphan-run or lease-expiry reaper. Runs left `running` with an expired lease are detectable through status and persisted lease fields. The local connector posture is single worker and single process; leases are single-process safe, while multi-worker concurrent execution, cross-process atomic leases, and high availability are not current selected-profile claims.

Connector lifecycle support is bounded to a single local API/executor process with explicit operator action. Persisted checkpoints and run state support operator-triggered resume after restart; completed runs are resume no-ops; terminal runs clear public lease ownership; and an unexpired active lease fails closed as `lease_conflict`. This is not a durable queue, automatic replay, multi-executor, HA, keyed connector, real provider delivery, OCR, default-on SEC live network/value reveal, model/agent egress, or nonlocal trust claim.

## Canonical Operator Journey

The canonical local_expert operator journey for the current RC3 selected profile is the documented composition of the `method_aware_analytics_vertical`, `sciencebase_public_connector_slice`, `senate_lda_anonymous_connector_slice`, `worldbank_indicators_anonymous_connector_slice`, `bls_v1_anonymous_connector_slice`, `oecd_sdmx_anonymous_connector_slice`, `cftc_cot_anonymous_connector_slice`, `connector_run_observability`, `layer3_workbench_ui`, `health_readiness_openapi`, and offline SEC XBRL simulation capabilities selected by `config/support_matrix.yaml`.

The supported analytics path is: CSV upload, variable profiling, transform recommend/apply, annotation, analysis with `cross_correlation`, `decomposition`, or `structural_break`, inspection of result artifacts, assumptions, and caveats, then persisted recovery through `GET /api/v1/analysis-runs/{id}` and dataset detail reads. The public connector path covers ScienceBase public/MCS discovery/download/CSV ingest into analysis, Senate LDA anonymous metadata query/detail handling, World Bank Indicators anonymous metadata query handling, BLS Public Data API v1 anonymous metadata query handling, OECD SDMX anonymous SDMX-CSV dataflow handling, CFTC COT current report-row parsing into connector reports, observable degraded states, checkpointed resume, lease conflict handling, and reports/events. These operator paths run on local libraries, SQLite, and the local filesystem under the default local auth posture; they do not use OCR, model/agent egress, provider delivery, keyed connector secrets, HA, or a nonlocal base.

Inspectable output includes method artifacts, method assumptions, caveats for limitations or degraded states, and source traceability from CSV ingest. The source-fidelity fields `content_hash`, `source_row_count`, and `dropped_row_count` make dropped all-empty source rows explicit while preserving the existing post-clean `row_count` used by analytics.

The operator-workflow proof includes coherent state recovery through a fresh API client and fresh database session, plus a governed degraded state: an unsupported analysis method returns an `unsupported_method` caveat instead of blank output or an exception. Existing method-specific tests also cover decomposition short-series and structural-break no-breakpoint caveat paths.

## Status Legend

| Status | Meaning |
| --- | --- |
| `supported` | In scope for local expert RC3 under the default local posture and selected `public_connectors` plus `sec_xbrl_offline` overlays. |
| `experimental_default_off` | Present or partially wired, but not supported/default-on in the selected local RC3 profile without explicit future decision or runtime configuration. This includes features guarded by false defaults and features that require an external engine that is not bundled with this profile. |
| `simulation` | Useful as offline/replay/staged proof only, not a live production capability. |
| `unsupported` | Not armable or not claimed for this selected profile. |

## Capability Table

| Capability | Status | Evidence |
| --- | --- | --- |
| Method-aware analytics vertical | `supported` | `README.md:41-46`; `tests/test_api.py:125-138`; `backend/app/services/analysis.py:44-100` |
| ScienceBase public connector slice | `supported` | PR-1 correctness; PR-2 L17 negatives; PR-3 L20 lifecycle; PR-4 L11 source fidelity; PR-5 canonical journey; `tests/test_api.py::test_public_connector_operator_journey_bridges_sciencebase_target_to_analysis` |
| Senate LDA anonymous connector slice | `supported` | PR-1 correctness; PR-2 L17 negatives; PR-3 L20 lifecycle; PR-4 L11 source fidelity; PR-5 anonymous journey; `tests/test_api.py::test_senate_lda_anonymous_metadata_path_is_no_key_secondary_journey` |
| World Bank Indicators anonymous connector slice | `supported` | PR-1 correctness; PR-2 L17 negatives; PR-3 L20 lifecycle; PR-4 L11 source fidelity; PR-5 anonymous journey; `tests/test_api.py::test_worldbank_connector_happy_path_reports_and_attribution` |
| BLS Public Data API v1 anonymous connector slice | `supported` | PR-1 correctness; PR-2 L17 negatives; PR-3 L20 lifecycle; PR-4 L11 source fidelity; PR-5 anonymous journey; `tests/test_api.py::test_bls_connector_happy_single_get_reports_and_attribution` |
| OECD SDMX anonymous connector slice | `supported` | PR-1 correctness; PR-2 L17 negatives; PR-3 L20 lifecycle; PR-4 L11 source fidelity; PR-5 anonymous journey; `tests/test_api.py::test_oecd_sdmx_connector_happy_dataflow_query_reports_and_attribution`; `tests/test_api.py::test_oecd_sdmx_connector_rejects_budget_over_30`; `tests/test_api.py::test_oecd_sdmx_connector_413_restricted_parameter_terminal_with_last_n`; `tests/test_api.py::test_oecd_sdmx_connector_empty_all_null_and_malformed_fail_closed`; `tests/test_api.py::test_oecd_sdmx_connector_rate_limiter_and_backoff_use_monkeypatched_clock`; `tests/test_api.py::test_oecd_sdmx_connector_get_redirect_cap_and_final_host`; `tests/test_api.py::test_oecd_sdmx_connector_unauthorized_terminal`; `tests/test_api.py::test_oecd_sdmx_connector_idempotency_conflict_and_resume`; `tests/test_api.py::test_oecd_sdmx_connector_rejects_non_oecd_base_url`; `tests/test_api.py::test_oecd_sdmx_support_matrix_mirror_and_runtime_probe`; `backend/tests/test_legacy_api_operator_identity.py::test_post_json_route_rejected_without_identity_in_proxy_mode`; `backend/app/core/config.py:218`; `docs/public-connectors-journey.md` |
| CFTC COT anonymous connector slice | `supported` | PR-1 correctness; PR-2 L17 negatives; PR-3 L20 lifecycle; PR-4 L11 source fidelity; PR-5 anonymous journey; `tests/test_api.py::test_cftc_cot_connector_happy_path_reports_rows_and_attribution` |
| Connector run observability | `supported` | PR-1 correctness; PR-2 L17 negatives; PR-3 L20 lifecycle; PR-4 L11 source fidelity; PR-5 degraded-state journey; `tests/test_api.py::test_public_connector_journey_network_unreachable_is_degraded` |
| Layer 3 workbench UI | `supported` | `backend/main.py:498-504`; `backend/app/review_ui/static/layer3.html`; `backend/app/review_ui/static/layer3.js` |
| Health, readiness, OpenAPI | `supported` | `backend/main.py:53`; `backend/main.py:510-521`; `backend/main.py:526-536` |
| SEC value reveal | `experimental_default_off` | `backend/app/core/config.py:164-166`; `backend/.env.example:68-69`; `README.md:3` |
| Controlled value-reveal submit | `experimental_default_off` | `backend/app/core/config.py:172-174`; `backend/.env.example:86-87`; `backend/app/services/layer3_sec_xbrl_controlled_value_reveal_submit.py` |
| Arelle internal value store | `experimental_default_off` | `backend/app/core/config.py:152-154`; `backend/.env.example:62-63`; `backend/app/services/layer3_sec_xbrl_offline_evidence_loader.py:26` |
| Arelle corpus validation | `experimental_default_off` | `backend/app/core/config.py:156-158`; `backend/.env.example:64-65` |
| SEC XBRL production-admission evaluator | `experimental_default_off` | `backend/app/core/config.py:190-192`; `backend/.env.example:93-96` |
| Analysis product package inventory | `experimental_default_off` | `backend/app/core/config.py:176-178`; `backend/app/services/layer3_analysis_product_inventory_projection.py` |
| OCR external engine | `experimental_default_off` | `README.md:114`; `README.md:138`; `backend/app/services/nrc_aps_document_processing.py:342-348`; `backend/app/services/nrc_aps_document_processing.py:808-884`; `backend/app/services/nrc_aps_document_processing.py:1146-1242`; `tests/test_nrc_aps_document_processing.py` |
| SEC offline replay path | `simulation` | `backend/app/services/layer3_sec_xbrl_offline_evidence_loader.py:23-62`; `backend/tests/test_layer3_sec_xbrl_companyfacts_stage_and_oracle.py` |
| SEC XBRL offline evidence loader | `simulation` | `backend/app/services/layer3_sec_xbrl_offline_evidence_loader.py`; `backend/tests/test_sec_xbrl_offline_evidence_loader.py` |
| SEC XBRL offline companyfacts stage | `simulation` | `backend/app/services/layer3_sec_xbrl_offline_companyfacts_stage.py`; `backend/tests/test_layer3_sec_xbrl_companyfacts_stage_and_oracle.py` |
| SEC XBRL offline companyfacts oracle packet | `simulation` | `backend/app/services/layer3_sec_xbrl_offline_companyfacts_oracle_packet.py`; `backend/tests/test_layer3_sec_xbrl_companyfacts_stage_and_oracle.py` |
| SEC XBRL offline E2E orchestrator | `simulation` | `backend/app/services/layer3_sec_xbrl_e2e_offline_orchestrator.py`; `backend/tests/test_sec_xbrl_e2e_offline_orchestrator.py` |
| SEC XBRL offline evidence proof capability | `simulation` | `backend/app/services/layer3_sec_xbrl_offline_evidence_proof_capability.py`; `backend/tests/test_sec_xbrl_offline_evidence_proof_capability.py` |
| NRC APS replay corpus gate | `simulation` | `README.md:198`; `tests/test_nrc_aps_replay_gate.py`; `backend/app/services/nrc_aps_replay_gate.py` |
| Offline-staged redaction/value-store resolution | `simulation` | `backend/app/services/layer3_sec_xbrl_offline_evidence_loader.py:160-180`; `backend/app/models/models.py:1449-1536` |
| SEC live network egress | `experimental_default_off` | `backend/app/core/config.py:133-147`; `backend/app/services/layer3_sec_edgar_live_source_artifact.py`; `backend/tests/test_layer3_api.py::test_layer3_api_acquires_sec_edgar_text_table_live_source_artifact_with_fake_client`; `README.md:3` |
| Real provider delivery | `unsupported` | `README.md:3`; `backend/app/services/layer3_provider_public_url_fake_provider.py`; `backend/app/services/layer3_provider_private_signed_url_fake_provider.py` |
| Model/agent egress | `unsupported` | `backend/app/core/config.py:180-187`; `README.md:3`; `backend/app/services/layer3_egress_policy.py` |
| Nonlocal, multi-trust, multi-identity | `unsupported` | `README.md:3`; `backend/app/core/config.py:25-26`; `backend/app/core/config.py:366-400` |
| High availability | `unsupported` | `backend/app/core/config.py:110-112`; `backend/app/services/nrc_aps_safeguards.py:402` |
| Keyed connectors | `unsupported` | `backend/app/core/config.py:208-210`; `backend/.env.example:14`; `backend/.env.example:47-49` |
| Signed-reference export | `unsupported` | `backend/app/api/layer3/_shared.py:286`; `backend/.env.production.example:143`; `backend/app/api/layer3/handoff.py:377-613` |

## Local Expert Pins

The support-matrix checker pins the following flags false for this profile:

| Flag |
| --- |
| `LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED` |
| `LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED` |
| `LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED` |
| `LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED` |
| `LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED` |
| `LAYER3_MODEL_EGRESS_ENABLED` |
| `SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED` |
| `LAYER3_ANALYSIS_PRODUCT_PACKAGE_INVENTORY_ENABLED` |

The selected profile enables only the `public_connectors` and `sec_xbrl_offline` overlays. Bounded SEC live source-artifact acquisition is present but remains explicit-default-off behind `LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED=false` plus server-configured User-Agent/rate-limit controls. The selected profile does not select the nonlocal base, keyed connectors, SEC value reveal, OCR, model/agent egress, provider delivery, HA, durable queues, automatic replay, or multi-executor operation.

OCR note: NRC APS document-processing code can use an installed Tesseract runtime for image or low-text PDF handling. That path remains outside the canonical local expert RC3 selected profile, is not part of the selected public_connectors overlay, and is not part of the selected sec_xbrl_offline overlay because the external engine is not bundled with this source-run profile.
