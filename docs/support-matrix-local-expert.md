# Local Expert Support Matrix

This support matrix applies to the selected analytics-only RC1 profile `base=local_expert` with `overlays=none`.

The profile is a single-operator local source-run posture: `DEPLOYMENT_MODE=local`, `AUTH_OWNER=none`, SQLite/local filesystem, and loopback/local trust. Under this posture there is no authentication boundary; the local principal is constant and identity or role enforcement is not a product claim.

`config/release_readiness.yaml` remains profile-neutral. Its `owner_selected_profile_specific_gates` list must stay empty; selected-profile acceptance lives in `config/support_matrix.yaml` and `scripts/support_matrix_check.py`.

The selected RC1 profile does not claim the public connectors overlay. ScienceBase, Senate LDA, and their run observability are RC2-targeted and remain outside the analytics-only RC1 supported claim.

## Canonical Operator Journey

The canonical local_expert operator journey for analytics-only RC1 is the method-aware tabular analytics flow named by `config/support_matrix.yaml`.

The supported path is: CSV upload, variable profiling, transform recommend/apply, annotation, analysis with `cross_correlation`, `decomposition`, or `structural_break`, inspection of result artifacts, assumptions, and caveats, then persisted recovery through `GET /api/v1/analysis-runs/{id}` and dataset detail reads. The path runs on local libraries, SQLite, and the local filesystem under the default local auth posture; it does not use connectors, SEC, OCR, model/agent egress, provider delivery, overlays, or a nonlocal base.

Inspectable output includes method artifacts, method assumptions, caveats for limitations or degraded states, and source traceability from CSV ingest. The source-fidelity fields `content_hash`, `source_row_count`, and `dropped_row_count` make dropped all-empty source rows explicit while preserving the existing post-clean `row_count` used by analytics.

The operator-workflow proof includes coherent state recovery through a fresh API client and fresh database session, plus a governed degraded state: an unsupported analysis method returns an `unsupported_method` caveat instead of blank output or an exception. Existing method-specific tests also cover decomposition short-series and structural-break no-breakpoint caveat paths.

## Status Legend

| Status | Meaning |
| --- | --- |
| `supported` | In scope for local expert RC1 under the default local posture. |
| `experimental_default_off` | Present or partially wired, but not part of the selected local RC1 claim without an explicit future decision. This includes features guarded by false defaults and features that require an external engine that is not bundled with this profile. |
| `simulation` | Useful as offline/replay/staged proof only, not a live production capability. |
| `unsupported` | Not armable or not claimed for this selected profile. |

## Capability Table

| Capability | Status | Evidence |
| --- | --- | --- |
| Method-aware analytics vertical | `supported` | `README.md:41-46`; `tests/test_api.py:125-138`; `backend/app/services/analysis.py:44-100` |
| ScienceBase public connector slice | `experimental_default_off` | RC2-targeted; not part of analytics-only RC1; `README.md:48-51`; `backend/app/api/router.py:319-382`; `backend/app/core/config.py:206` (`SCIENCEBASE_API_BASE_URL` alias) |
| Senate LDA anonymous connector slice | `experimental_default_off` | RC2-targeted; not part of analytics-only RC1; `README.md:146-150`; `backend/app/api/router.py:426-452`; `backend/app/core/config.py:209-210` (`SENATE_LDA_API_BASE_URL` / `SENATE_LDA_API_KEY` aliases) |
| Connector run observability | `experimental_default_off` | RC2-targeted; observes experimental connector runs, not analytics-only RC1; `README.md:54-60`; `backend/app/api/router.py:461-542`; `backend/app/services/connectors_sciencebase.py:3145-3164` |
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
| NRC APS replay corpus gate | `simulation` | `README.md:198`; `tests/test_nrc_aps_replay_gate.py`; `backend/app/services/nrc_aps_replay_gate.py` |
| Offline-staged redaction/value-store resolution | `simulation` | `backend/app/services/layer3_sec_xbrl_offline_evidence_loader.py:160-180`; `backend/app/models/models.py:1449-1536` |
| SEC live network egress | `unsupported` | `backend/app/core/config.py:134-136`; `backend/.env.example:55`; `README.md:3` |
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

The selected profile does not enable, advertise, or imply overlays. It does not select the nonlocal base or the public connectors overlay.

OCR note: NRC APS document-processing code can use an installed Tesseract runtime for image or low-text PDF handling. That path remains outside the canonical local expert analytics journey and is not part of the selected RC1 claim because the external engine is not bundled with this source-run profile.
