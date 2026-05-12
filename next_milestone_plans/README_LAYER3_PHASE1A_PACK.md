# Layer3 Phase1A Planning Pack

## Purpose

This file is the front door for the bounded Phase 1A Layer 3 planning and closure pack that was landed from `codex/layer3-lane` and is now carried forward on current `main`.

Use it to orient quickly across the three active pack directories:
- `next_milestone_plans/Layer3_planning_docs`
- `next_milestone_plans/Layer3_execution_handoff`
- `next_milestone_plans/Layer3_execution_freeze`

Current post-PR #695 execution-handoff references:
- `next_milestone_plans/Layer3_execution_handoff/07_L3_UI_MANUAL_RUNBOOK.md`
- `next_milestone_plans/Layer3_execution_handoff/08_L3_POST_695_REFERENCE_PLAN.md`

Current qualitative APS package-review runtime references:
- `next_milestone_plans/Layer3_planning_docs/138_QUAL_APS_PACKAGE_REVIEW_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/139_QUAL_APS_PACKAGE_REVIEW_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/141_QUAL_APS_PACKAGE_CONSTRUCTION_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/142_POST_709_ROADMAP_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/143_QUAL_APS_PACKAGE_REVIEW_SUBMIT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/144_QUAL_APS_PACKAGE_REVIEW_SUBMIT_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/145_QUAL_APS_HANDOFF_EXPORT_PREPARE_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/146_QUAL_APS_HANDOFF_EXPORT_PREPARE_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/147_QUAL_APS_APS_HANDOFF_DISPATCH_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/148_QUAL_APS_APS_HANDOFF_DISPATCH_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/149_QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/150_QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/151_QUAL_APS_RENDERED_UI_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/152_QUAL_APS_RENDERED_UI_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/153_SOURCE_BREADTH_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/154_RAW_INGESTION_MATERIALIZATION_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/234_PROVIDER_PRIVATE_SIGNED_URL_USE_REVOKE_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/235_PROVIDER_PRIVATE_SIGNED_URL_USE_REVOKE_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/239_PROVIDER_PRIVATE_SIGNED_URL_REVOKE_API.md`
- `next_milestone_plans/Layer3_planning_docs/240_PROVIDER_PRIVATE_SIGNED_URL_USE_AUTHORITY_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/241_PROVIDER_PRIVATE_SIGNED_URL_USE_AUTHORITY_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/242_LIVE_THEME_PARITY_PROOF.md`
- `next_milestone_plans/Layer3_planning_docs/243_PROVIDER_PRIVATE_SIGNED_URL_USE_MODEL_CLOSEOUT.md`
- `next_milestone_plans/Layer3_planning_docs/244_PROVIDER_PRIVATE_SIGNED_URL_USE_MODEL_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/245_PROVIDER_PRIVATE_SIGNED_URL_RENDERED_UI_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/246_PROVIDER_PRIVATE_SIGNED_URL_RENDERED_UI_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/247_PROVIDER_PRIVATE_SIGNED_URL_RENDERED_UI_PROOF.md`
- `next_milestone_plans/Layer3_planning_docs/248_POST_PROVIDER_PRIVATE_ROADMAP_SELECTION_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/249_SOURCE_BREADTH_REENTRY_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/250_SOURCE_BREADTH_AUTHORITY_PACKET.md`
- `next_milestone_plans/Layer3_planning_docs/251_POST_807_CLOSEOUT.md`
- `next_milestone_plans/Layer3_planning_docs/252_GOAL_STACK_IMPLEMENTATION_AUDIT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/253_SOURCE_RENDERED_CONTROL_DECISION_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/254_CONNECTOR_DESTINATION_REENTRY_DECISION_FREEZE.md
- `Layer3_planning_docs/255_PACKAGE_MUTATION_REENTRY_DECISION_FREEZE.md
- `Layer3_planning_docs/256_QUAL_HYBRID_RAG_REENTRY_DECISION_FREEZE.md
- `Layer3_planning_docs/257_FULL_MOCKUP_ACTIVATION_REENTRY_DECISION_FREEZE.md
- `Layer3_planning_docs/258_GOAL_STACK_REENTRY_CLOSEOUT_AND_IMPLEMENTATION_GATE.md`````

Docs `138`/`139` govern the live read-only `qual_aps_package_review_preview_only` boundary after PR `#702` proved the standalone APS content-document qualitative API path through result review. Docs `140`/`141` now govern the bounded live `qual_aps_package_construction_commit_entry` boundary through `POST /api/v1/layer3/package/review/commit`: it creates exactly one qualitative APS reconciliation record, exactly three package rows, and server-owned package payload files for `canonical_internal`, `user_facing`, and `review_facing`. Docs `143`/`144` now govern the live bounded `qual_aps_package_review_submit_entry` boundary through `POST /api/v1/layer3/package/review/submit`: it records exactly one qualitative APS package-review decision object in existing JSON-bearing state and creates no rows or files. Docs `145`/`146` now govern the live bounded `qual_aps_handoff_export_prepare_entry` boundary through `POST /api/v1/layer3/handoff/export/prepare`: it records exactly one prepare-only internal envelope decision object in existing JSON-bearing state and creates no rows or files. Docs `147`/`148` now govern the live bounded `qual_aps_aps_handoff_dispatch_entry` boundary through `POST /api/v1/layer3/handoff/aps/dispatch`: it creates exactly one APS evidence-bundle handoff package row, writes one server-owned APS bundle artifact, and records one dispatch state object after revalidating the qualitative authority chain. Docs `149`/`150` now govern the live bounded `qual_aps_external_export_download_prepare_deliver` boundary through the existing external export/download prepare and deliver routes. Docs `151`/`152` now govern the live `qual_aps_rendered_downstream_existing_controls_only` rendered UI runtime over the already-live qualitative APS backend/API chain: API/test setup reaches approved qualitative APS result review, then existing `/review/layer3` controls drive package preview, package construction commit, package review submit, handoff/export prepare, APS handoff dispatch, and external export/download prepare while qualitative delivery stays disabled from `delivery_ui: null`. Doc `247` now records the bounded rendered provider-private signed URL prepare/status/revoke controls over existing backend APIs, with `use` still closed and redacted receipt state only. Docs `248`/`249` select `source_breadth_reentry_authority_packet` as the next planning lane after provider-private rendered UI completion and require a source-breadth reentry contract before any source runtime implementation. Connector/destination dispatch, provider/public URLs beyond the provider-private redacted marker, source expansion runtime, package mutation/reconstruction, broad qualitative/hybrid/RAG, full mockup, auth/security behavior, same-origin delivery changes, same-origin signed-reference changes, and raw provider-private token custody remain blocked.

Doc `142` is the current roadmap/reference freeze. It centralizes the intended ordering after qualitative APS external export/download runtime and the rendered qualitative APS UI runtime: source breadth, raw ingestion, broad execution/RAG, package lifecycle, connector/provider expansion, mockup activation, auth/security, and observability hardening. It is planning/control only and does not make any future pass live.

Doc `153` is the current source-breadth implementation-entry freeze before any raw ingestion/source-adapter expansion. It selects `current_admitted_classes_with_server_owned_raw_materialization_only`: the admitted source classes remain `dataset_version` and `aps_content_document`, and any later raw-ingestion/source-authority materialization must stay under server-owned storage-root, hash-checked authority for those existing families unless a later source-family freeze admits more. It does not make raw ingestion live and keeps local upload, local-directory ingestion, web connector retrieval, RAG/vector retrieval, provider/public URLs, connector/destination dispatch, package mutation/reconstruction, hidden LLM planning, full mockup activation, auth/security behavior, and new rendered controls blocked.

Doc `154` now governs the raw-ingestion materialization runtime boundary. It selects `raw_mixed_existing_source_materialization_entry` for `POST /api/v1/layer3/source/mixed-corpus/materialize`: a server-owned, SHA-256 checked manifest may materialize deterministic `dataset_version` and `aps_content_document` source authority rows for the existing Layer 3 source/material preview path, while the existing seed route remains no-write and seed-only. The runtime writes no files, starts no Layer 3 flow, adds no models or migrations, and still blocks source adapter registry behavior, local upload, local-directory ingestion, web connector retrieval, RAG/vector retrieval, provider/public URLs, connector/destination dispatch, package mutation/reconstruction, hidden LLM planning, full mockup activation, auth/security behavior, rendered controls, frontend-only durable authority, and theme behavior changes.

Docs `234`/`235` are the current provider-private signed URL corrective planning/control boundary after doc `233` made prepare/status live. The filenames are retained for milestone continuity, but the admitted next runtime slice is revoke-only; the use route remains deferred by the redacted-token boundary until a separate token/delivery authority freeze exists. They keep rendered controls, real provider network/object-store behavior, provider/public URL runtime, public proxy runtime, connector/destination dispatch, package mutation/reconstruction, source expansion, RAG/vector, hidden LLM, full mockup, auth/security behavior, same-origin delivery changes, same-origin signed-reference changes, Playwright behavior, and frontend-only durable authority blocked.

Doc `242` records the current test-only live-theme parity proof for `/review/layer3` across `system`, `light`, `dark`, and `workbench` on the canonical raw-mixed rendered external export/download signed-reference path. It excludes Claude as prototype-only, restores entry theme state after each parity checkpoint, and adds no backend/API/model/migration/production UI behavior, rendered provider-private controls, provider network writes, connector/destination dispatch, source expansion, package mutation/reconstruction, broad qualitative/hybrid/RAG runtime, hidden LLM planning, full mockup activation, auth/security behavior, or frontend-only durable authority.

Docs `243`/`244` close the provider-private signed URL use-model gap by selecting `no_use_api_external_provider_consumption` for the current lane. The `use` route is intentionally closed and not implemented; prepare/status/revoke remain the only admitted provider-private backend/API surfaces. Future real-provider delivery, server proxy use, encrypted token retention, public/proxy URL exposure, rendered provider-private controls, or connector/destination delivery require a separate implementation-entry freeze.

Docs `245`/`246` freeze the next rendered provider-private signed URL UI entry. The only allowed next implementation is `/review/layer3` prepare/status/revoke controls over existing backend APIs, with `use` still closed, redacted display only, no backend/API/model/migration change, and headed/headless live-theme proof across `system`, `light`, `dark`, and `workbench`.

Docs `248`/`249` are the current post-provider-private roadmap-selection and source-breadth reentry controls. They select source breadth as the next planning lane because it is the foundational unresolved input/provenance surface for later broad qualitative, hybrid/RAG, connector/destination, and package lifecycle work. Doc `250` records the source-breadth authority packet outcome: `entry_decision: no_runtime_now`, because no concrete new-source use case, selected new source family, adapter/input mode, or new-source auth/security posture is selected. Doc `251` records PR `#807` merge closeout on current `main` at `9ffc5c64154b5175f56cb0e1b15b9ffc1492f233`. Doc `252` reconciles the goal stack against current implementation truth: current-class source runtime, current raw-mixed rendered controls, internal connector record-only behavior, backend package lifecycle, and single APS-document qualitative execution are live bounded implementations, while new source-family runtime, external connector/destination writes, rendered package mutation controls, broad qualitative/hybrid/RAG/vector behavior, and full mockup activation remain blocked. Doc `253` freezes the source rendered-control decision: current raw-mixed current-class controls are live, but no new rendered source-family, local upload, local directory, web connector, or RAG/vector control is admitted. Doc `254` freezes connector/destination reentry: internal dispatch record-only is live, but external connector invocation, destination writes, connector-run creation, generic downstream dispatch, rendered connector/destination controls, and provider/public URL side effects remain blocked. These docs do not admit source adapter registry behavior, local upload, local-directory ingestion, web connector retrieval, RAG/vector retrieval beyond current blocked posture, route/API/DTO/model/migration/service behavior change, executable test behavior change, external connector/destination dispatch, rendered package mutation/reconstruction, full mockup activation, auth/security behavior, or frontend-only durable authority.

Docs `143`/`144` define the current `qual_aps_package_review_submit_entry` runtime boundary over the already constructed qualitative APS package set. They select reuse of the package-review submit route family, require persisted PR `#709` construction authority, and keep handoff/export, APS dispatch, external export/download, connector/destination dispatch, provider/public URLs, rendered controls/theme behavior, source expansion, RAG/vector, hidden LLM, full mockup, auth/security, model/migration, package mutation/reconstruction, and package supersession blocked.

Docs `145`/`146` define the live `qual_aps_handoff_export_prepare_entry` runtime boundary over an already approved qualitative APS package-review submit state. They reuse the handoff/export prepare route family, require qualitative submit schema `layer3.qual_aps_package_review_submit.v1`, require persisted construction and submit authority, create no rows or files, and keep APS dispatch, external export/download, connector/destination dispatch, provider/public URLs, rendered controls/theme behavior, source expansion, RAG/vector, hidden LLM, full mockup, auth/security, model/migration, package mutation/reconstruction, and package supersession blocked.

Docs `147`/`148` now define the live bounded `qual_aps_aps_handoff_dispatch_entry` over an already prepared qualitative APS internal handoff/export envelope. They reuse the APS handoff dispatch route family, require persisted qualitative prepare authority, and allow only the APS owner-service handoff package row/artifact and dispatch state needed for APS evidence-bundle handoff. They keep qualitative APS external export/download blocked with `qualitative_aps_external_export_download_not_admitted`, and continue to block connector/destination dispatch, provider/public URLs, rendered controls/theme behavior, source expansion, RAG/vector, hidden LLM, full mockup, auth/security, model/migration, package mutation/reconstruction, and package supersession.

Docs `149`/`150` define the live bounded `qual_aps_external_export_download_prepare_deliver` runtime over an already dispatched qualitative APS evidence-bundle handoff. They reuse the external export/download prepare and deliver route family, require persisted qualitative APS dispatch authority plus server-owned APS bundle artifact authority, record readiness JSON state, and stream only the same-origin APS bundle artifact through same-origin artifact streaming. They keep provider/public URLs, signed URLs, connector/destination dispatch, rendered controls/theme behavior, source expansion, RAG/vector, hidden LLM, full mockup, auth/security, model/migration, package mutation/reconstruction, and package supersession blocked.

Docs `151`/`152` define the live `qual_aps_rendered_downstream_existing_controls_only` UI freeze/contract. They govern only rendered `/review/layer3` activation over already-live qualitative APS backend/API package/downstream steps through external export/download prepare, require server-authoritative state and headed/headless Chromium theme proof, and keep backend changes, source expansion, provider/public URLs, signed URLs, connector/destination dispatch, RAG/vector behavior, hidden LLM planning, package mutation/reconstruction, full mockup activation, auth/security behavior, new rendered controls, and qualitative delivery without server `delivery_ui` blocked.

Post-synthesis authority guardrail:
- `next_milestone_plans/Layer3_planning_docs/117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md`

That guardrail is the current tracked pointer for preventing mockup, Codesight, progress-prose, or stale-audit overclaims. It is not an implementation freeze and does not activate broad execution, qualitative/hybrid/RAG, provider/public URL support, connector/destination dispatch, package mutation/reconstruction, broad source/upload expansion, or full mockup behavior.

It also now points to the narrow post-Phase 1A Gate C entry-freeze bridge:
- `next_milestone_plans/Layer3_planning_docs/04_GATEC_ENTRY_FREEZE.md`

And to the actual first Gate C implementation-entry freeze packet:
- `next_milestone_plans/Layer3_planning_docs/05_GATEC_IMPLEMENTATION_FREEZE.md`

And to the carried-forward Gate C plan/pass-entry freeze packet for the landed bounded plan/pass slice:
- `next_milestone_plans/Layer3_planning_docs/06_GATEC_PASS_FREEZE.md`

And to the carried-forward Gate C quantitative associated/cohort continuation freeze packet for the landed bounded cohort slice:
- `next_milestone_plans/Layer3_planning_docs/07_GATEC_COHORT_FREEZE.md`

And to the carried-forward Gate D package-entry freeze packet for the landed bounded packaging/reconciliation entry slice:
- `next_milestone_plans/Layer3_planning_docs/08_GATED_PACKAGE_FREEZE.md`

And to the carried-forward Gate D APS handoff freeze packet for the bounded first APS evidence-bundle-family handoff slice now landed on current `main`:
- `next_milestone_plans/Layer3_planning_docs/09_GATED_APS_HANDOFF_FREEZE.md`

And to the carried-forward Gate D APS citation continuation freeze packet for the bounded citation-pack-family handoff slice now landed on current `main` after the landed evidence-bundle handoff:
- `next_milestone_plans/Layer3_planning_docs/10_GATED_APS_CITATION_FREEZE.md`

And to the carried-forward Gate D APS report continuation freeze packet for the bounded evidence-report-family continuation slice now landed on current `main` after the landed citation-pack handoff:
- `next_milestone_plans/Layer3_planning_docs/11_GATED_APS_REPORT_FREEZE.md`

And to the carried-forward Gate D APS report-export continuation freeze packet for the bounded evidence-report-export-family continuation slice now landed on current `main` beyond the landed evidence-report handoff:
- `next_milestone_plans/Layer3_planning_docs/12_GATED_APS_REPORT_EXPORT_FREEZE.md`

And to the carried-forward Gate D APS context continuation freeze packet for the bounded export-derived context-packet slice now landed on current `main` beyond the landed evidence-report-export handoff:
- `next_milestone_plans/Layer3_planning_docs/13_GATED_APS_CONTEXT_FREEZE.md`

And to the carried-forward Gate D APS multisource continuation freeze packet for the bounded same-run shared-source admission boundary now landed on current `main` beyond the landed export-derived context-packet slice:
- `next_milestone_plans/Layer3_planning_docs/14_GATED_APS_MULTISOURCE_FREEZE.md`

And to the carried-forward Gate D APS export-package first shared-consumer freeze packet for the bounded now-landed choice of `evidence_report_export_package` as the first later shared APS family beyond the landed multisource slice on current `main`:
- `next_milestone_plans/Layer3_planning_docs/15_GATED_APS_EXPORT_PACKAGE_FREEZE.md`

And to the carried-forward Gate D APS package-derived-context continuation freeze packet now landed on current `main` for the bounded next shared APS family beyond the landed export-package boundary:
- `next_milestone_plans/Layer3_planning_docs/16_GATED_APS_PACKAGE_CONTEXT_FREEZE.md`

And to the carried-forward Gate D APS context-dossier continuation freeze packet now landed on current `main` for the bounded next later shared APS family beyond the landed package-context boundary:
- `next_milestone_plans/Layer3_planning_docs/17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md`

And to the carried-forward Gate D APS deterministic-insight continuation freeze packet now landed on current `main` for the bounded first deterministic continuation beyond the landed dossier boundary:
- `next_milestone_plans/Layer3_planning_docs/18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md`

And to the carried-forward Gate D APS deterministic-challenge continuation freeze packet now landed on current `main` for the bounded next deterministic continuation beyond the landed deterministic-insight boundary:
- `next_milestone_plans/Layer3_planning_docs/19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE.md`

And to the carried-forward Gate D APS review-packet continuation freeze packet now landed on current `main` for the bounded next deterministic continuation beyond the landed deterministic-challenge boundary:
- `next_milestone_plans/Layer3_planning_docs/20_GATED_APS_REVIEW_PACKET_FREEZE.md`

And to the bounded Gate D APS review-packet handoff lane now landed on current `main` for the exact deterministic continuation beyond that landed review-packet freeze:
- `backend/app/services/layer3_aps_deterministic_challenge_review_packet_handoff.py`
- `backend/app/services/nrc_aps_deterministic_challenge_review_packet_gate.py`
- `backend/tests/test_layer3_aps_deterministic_challenge_review_packet_handoff.py`

And to the Layer 3 workbench execution-readiness packet from PR `#212`, which remains planning-only and does not admit execution:
- `next_milestone_plans/Layer3_planning_docs/36_L3_WB_EXECUTION_READINESS_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/37_L3_WB_STATE_HASH_IDEMPOTENCY_CONTRACT.md`
- `next_milestone_plans/layer3_workbench_proof_manifest.json`

PR `#213` adds only read-only implementation-readiness proof around that packet, including `/api/v1/layer3/readiness`, plan-preview identity/hash metadata, and approval/revision serialization checks. It still must not create pass runs, run analysis, write result/package/handoff artifacts, widen schema/runtime DB behavior, or admit qualitative/hybrid/RAG/vector execution.

And to the Layer 3 workbench execution-selection freeze packet from PR `#215`, which remains planning-only and does not admit analysis execution or results:
- `next_milestone_plans/Layer3_planning_docs/38_L3_WB_EXECUTION_SELECTION_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/39_L3_WB_EXECUTION_SELECTION_API_AND_STATE_CONTRACT.md`

PR `#215` freezes the next eligible implementation boundary as execution-selection/pass-run shell creation only after approved-plan and preview-hash validation. It still must not create `AnalysisRun`, run analysis, write result/package/handoff artifacts, reopen or supersede approved plans, widen schema/runtime DB behavior, expand source breadth, or activate the full mockup target state.

PR `#216` implements only that bounded execution-selection/pass-run shell boundary: `POST /api/v1/layer3/execution/select` validates one current approved plan, matches the approved preview id/hash, requires `client_request_id`, and creates selected/not-started `L3PassRun` shell rows only. It still must not call `materialize_pass_entry(...)`, create `AnalysisRun`, run analysis, write artifact manifests or result/package/handoff artifacts, reopen or supersede approved plans, widen schema/runtime DB behavior, expand source breadth, change UI, or activate the full mockup target state.

And to the Layer 3 workbench analysis-execution-start freeze packet from PR `#217`, which remains planning-only and does not make analysis execution live:
- `next_milestone_plans/Layer3_planning_docs/40_L3_WB_ANALYSIS_EXECUTION_START_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/41_L3_WB_ANALYSIS_EXECUTION_START_API_AND_STATE_CONTRACT.md`

PR `#217` freezes the next eligible implementation boundary as one selected-pass-run wrapped quantitative execution start from an existing PR `#216` selected/not-started shell. It still must not call `materialize_pass_entry(...)` as-is, create new `L3AnalysisPlan` or `L3PassRun` rows, run batch execution, enable result/package/handoff state, reopen or supersede approved plans, widen runtime DB/schema behavior, expand source breadth, change UI, or activate qualitative/hybrid/RAG/vector/full mockup behavior.

PR `#218` implements only that bounded analysis-execution-start boundary: `POST /api/v1/layer3/execution/start` executes one existing selected/not-started single-item wrapped quantitative `L3PassRun` shell, creates exactly one wrapped quantitative `AnalysisRun` plus selected-pass output metadata, preserves `client_request_id` idempotency, and still does not make result review, package review, handoff, source expansion, runtime DB/schema widening, UI changes, qualitative/hybrid/RAG/vector execution, or full mockup activation live.

And to PR `#221`'s Layer 3 workbench result/status freeze packet, which is planning-only and does not make result/status inspection, result review, package review, or handoff live by itself:
- `next_milestone_plans/Layer3_planning_docs/42_L3_WB_RESULT_STATUS_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/43_L3_WB_RESULT_STATUS_API_AND_STATE_CONTRACT.md`

The result/status packet freezes the next eligible implementation boundary after PR `#218` as read-only status and execution-proof inspection for one terminal selected pass. It still must not create or rerun analysis, write result/package/handoff artifacts, approve or reject results, reopen or supersede approved plans, widen runtime DB/schema behavior, expand source breadth, change UI unless separately implemented and browser-proven, or activate qualitative/hybrid/RAG/vector/full mockup behavior.

And to the Layer 3 workbench result-review freeze packet, which is planning-only and does not make result review, package review, or handoff live by itself:
- `next_milestone_plans/Layer3_planning_docs/44_L3_WB_RESULT_REVIEW_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/45_L3_WB_RESULT_REVIEW_API_AND_STATE_CONTRACT.md`

The result-review packet freezes the next eligible planning boundary after PR `#222` as one bounded operator review decision for one terminal selected pass that already satisfies result/status authority. It still must not create package artifacts, package review state, handoff/export state, rerun/recovery behavior, new execution runs, new plan/pass/run/artifact/package/reconciliation rows, source expansion, schema/runtime widening, UI changes by itself, local upload/directory ingestion, qualitative/hybrid/RAG/vector behavior, or full mockup activation.

PR `#227` now implements that packet on current `main`. It adds only `POST /api/v1/layer3/execution/result/review` and records one selected-pass operator review decision in existing `L3PassRun`/`L3Session` JSON summaries. It does not add package review, handoff/export, rerun/recovery, new plan/pass/run/package/reconciliation rows, schema/runtime widening, UI changes, local upload/directory ingestion, qualitative/hybrid/RAG/vector behavior, or full mockup activation.

And to the Layer 3 workbench result-review UI freeze packet, which is planning-only and does not make UI behavior live by itself, plus the later PR `#232` bounded UI implementation governed by that packet:
- `next_milestone_plans/Layer3_planning_docs/46_L3_WB_RESULT_REVIEW_UI_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/47_L3_WB_RESULT_REVIEW_UI_STATE_CONTRACT.md`

The result-review UI packet freezes the `/review/layer3` presentation/control boundary for current backend result-review state after PR `#227`. PR `#232` now implements that bounded UI surface: it can render server-authoritative selected-pass result/status and result-review state and submit one bounded result-review decision, but it still does not admit execution selection/start UI, package review, handoff/export, rerun/recovery, new backend endpoints by default, source/schema/runtime widening, local upload/directory ingestion, qualitative/hybrid/RAG/vector behavior, or full mockup activation.

And to the Layer 3 workbench package-review preview freeze packet, which is planning-only on current `main` and does not make package review, package construction, or handoff live by itself:
- `next_milestone_plans/Layer3_planning_docs/48_L3_WB_PACKAGE_REVIEW_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/49_L3_WB_PACKAGE_REVIEW_API_AND_STATE_CONTRACT.md`

The package-review preview packet was merged as planning-only PR `#234` after PR `#232`. PR `#235` now implements only that read-only package-review readiness/preview step after one selected-pass result-review decision is already recorded as `approved`. It explicitly does not create `L3OutputPackage` or `L3ReconciliationRecord` rows, does not call `materialize_package_entry(...)` as-is, and does not admit package-review submission, package payload writes, handoff/export, rerun/recovery, source/schema/runtime widening, local upload/directory ingestion, qualitative/hybrid/RAG/vector behavior, or full mockup activation.

And to the Layer 3 workbench package-construction freeze packet from PR `#237`, plus the bounded PR `#238` package-construction implementation:
- `next_milestone_plans/Layer3_planning_docs/50_L3_WB_PACKAGE_CONSTRUCTION_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/51_L3_WB_PACKAGE_CONSTRUCTION_API_AND_STATE_CONTRACT.md`

The package-construction packet freezes only the bounded commit step after PR `#235` read-only preview: exactly one reconciliation row, exactly three package rows, and exactly three payload files for `canonical_internal`, `user_facing`, and `review_facing`, guarded by approved selected-pass result-review and preview-basis authority. PR `#238` implements that backend commit as `POST /api/v1/layer3/package/review/commit`. By itself it does not admit package-review submit/decision state, handoff/export, `materialize_package_entry(...)` as-is from `/review/layer3`, schema/runtime/source widening, rerun/recovery, qualitative/hybrid/RAG/vector behavior, new UI code or package-creation controls, or full mockup activation; PR `#243` is the separate backend-only package-review submit implementation, PR `#245` is the separate merged bounded rendered package-review UI implementation, and PR `#247` hardens that same UI boundary against stale session-summary fallback after package commit. The existing package-preview panel reflects the new backend state by no longer listing package commit as disabled.

And to the Layer 3 workbench package-review submit freeze packet from PR `#241`, which is planning-only on current `main` and does not make package-review submit, handoff, or export live by itself:
- `next_milestone_plans/Layer3_planning_docs/52_L3_WB_PACKAGE_REVIEW_SUBMIT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/53_L3_WB_PACKAGE_REVIEW_SUBMIT_API_AND_STATE_CONTRACT.md`

The package-review submit packet from PR `#241` freezes only the operator decision over the already constructed package set from PR `#238`. It keeps package ids, package kinds, payload refs, and payload hashes server-verified and immutable; it does not admit package payload mutation, package reconstruction, additional package/reconciliation/artifact rows, handoff/export, result-review amendment, schema/runtime/source widening, qualitative/hybrid/RAG/vector behavior, new UI code, or full mockup activation.

PR `#243` is the merged backend-only implementation for that packet. It adds `POST /api/v1/layer3/package/review/submit`, records one operator decision in existing reconciliation/session JSON, verifies the constructed package ids and payload hashes, and keeps package rows, package payload refs/hashes, handoff/export, rendered UI behavior on current `main`, schema/runtime/source widening, and full mockup activation out until separately admitted. PR `#245` is the merged bounded rendered UI implementation that renders the package construction commit and package-review submit controls over the already-live PR `#238` and PR `#243` endpoints on current `main`; PR `#247` is a post-review hardening pass inside that same rendered UI scope so submit readiness can use fresh package-construction commit state if the post-commit session-summary refresh fails.

And to the Layer 3 workbench handoff/export preparation freeze packet, which is planning-only and does not make handoff/export, APS dispatch, or external export live by itself:
- `next_milestone_plans/Layer3_planning_docs/54_L3_WB_HANDOFF_EXPORT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/55_L3_WB_HANDOFF_EXPORT_API_AND_STATE_CONTRACT.md`

The handoff/export preparation packet freezes only the next eligible planning boundary after package-review approval: a future internal `prepare_only` export-envelope decision over already approved package-review state. It does not add a live endpoint by itself, does not dispatch to APS, does not export externally, does not create physical export files, does not create `AnalysisArtifact` rows, does not mutate package payloads, does not rebuild packages, does not widen source/schema/runtime scope, and does not activate the full mockup target state.

And to the Layer 3 workbench handoff/export preparation UI freeze packet, which is planning-only and does not make rendered `/review/layer3` handoff/export controls live by itself:
- `next_milestone_plans/Layer3_planning_docs/56_L3_WB_HANDOFF_EXPORT_UI_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/57_L3_WB_HANDOFF_EXPORT_UI_STATE_CONTRACT.md`

The handoff/export preparation UI packet freezes only the rendered prepare-only control boundary over the already-live backend prepare endpoint. PR `#256` now implements that bounded UI surface on current `main`: it may render one server-gated preparation decision form from `/review/layer3` after approved package-review authority, but it still does not admit APS handoff, external export/download, downstream dispatch, destination selection, physical export artifacts, `AnalysisArtifact`, package payload mutation, package reconstruction, source/schema/runtime widening, execution selection/start UI expansion, qualitative/hybrid/RAG/vector behavior, or full mockup activation.

And to the Layer 3 workbench APS handoff dispatch freeze/API contract from PR `#258`, now implemented backend/API-only by PR `#260` and hardened by PR `#261`/`#263`:
- `next_milestone_plans/Layer3_planning_docs/58_L3_WB_APS_HANDOFF_DISPATCH_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/59_L3_WB_APS_HANDOFF_DISPATCH_API_AND_STATE_CONTRACT.md`

The APS handoff dispatch packet governs the bounded backend/API workbench dispatch from exactly one `handoff_export_prepared` envelope into the existing `aps_evidence_bundle_handoff` owner-service family. PR `#260` implements `POST /api/v1/layer3/handoff/aps/dispatch`; PR `#261` tightens fail-closed handling for malformed canonical APS provenance and unexpected package kinds, and PR `#263` restricts APS handoff package-row allowance to recorded dispatch state. That backend/API packet itself did not render APS dispatch controls; PR `#266` separately implements only the bounded rendered UI under docs `60`/`61`. The APS handoff dispatch packet still does not admit external export/download, connector dispatch, destination selection, package mutation/reconstruction, additional reconciliation rows, schema/runtime/source widening, execution selection/start UI expansion beyond already admitted work, qualitative/hybrid/RAG/vector behavior, or full mockup activation.

And to the Layer 3 workbench APS handoff dispatch UI freeze packet, which is planning-only and does not make rendered `/review/layer3` APS dispatch controls live by itself:
- `next_milestone_plans/Layer3_planning_docs/60_L3_WB_APS_HANDOFF_DISPATCH_UI_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/61_L3_WB_APS_HANDOFF_DISPATCH_UI_STATE_CONTRACT.md`

The APS handoff dispatch UI packet freezes only a rendered readiness/read-only-result panel plus one server-gated `dispatch_aps_handoff` control over the already-live backend/API APS dispatch endpoint. Docs `60`/`61` still do not admit UI behavior by themselves; PR `#266` separately implements the bounded rendered `/review/layer3` APS dispatch UI and still does not admit external export/download, generic downstream dispatch, connector dispatch, destination selection, package payload mutation/reconstruction/rebuild/amendment, additional reconciliation rows, `AnalysisArtifact`, schema/runtime/source widening, execution selection/start expansion beyond already admitted work, qualitative/hybrid/RAG/vector behavior, or full mockup activation.

And to the Layer 3 workbench external export/download freeze packet, which is planning-only and does not make export/download behavior live by itself:
- `next_milestone_plans/Layer3_planning_docs/62_L3_WB_EXTERNAL_EXPORT_DOWNLOAD_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/63_L3_WB_EXTERNAL_EXPORT_DOWNLOAD_API_AND_STATE_CONTRACT.md`

The external export/download packet freezes only a future backend/API readiness preparation boundary after recorded `aps_handoff_dispatched` state. It selects a reference-only descriptor over the existing APS evidence-bundle handoff artifact as the narrow first boundary, not a browser download route, public/signed URL, destination selector, connector dispatch, generic downstream dispatch, package mutation/reconstruction, additional package/reconciliation/artifact rows, `AnalysisArtifact`, schema/runtime/source widening, execution expansion beyond already admitted work, qualitative/hybrid/RAG/vector behavior, or full mockup activation.

And to the Layer 3 workbench external export/download readiness UI freeze packet and its separate bounded rendered implementation:
- `next_milestone_plans/Layer3_planning_docs/64_L3_WB_EXTERNAL_EXPORT_DOWNLOAD_READINESS_UI_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/65_L3_WB_EXTERNAL_EXPORT_DOWNLOAD_READINESS_UI_STATE_CONTRACT.md`

The external export/download readiness UI packet freezes only rendered `/review/layer3` readiness over the already-live PR `#269` backend/API endpoint. Docs `64`/`65` remain governance by themselves; PR `#275` separately implements the bounded rendered readiness panel, read-only recorded descriptor display, and one server-gated `prepare_external_export_download` action. It does not admit rendered browser download controls, public or signed URLs, file streaming, connector dispatch, destination selection, generic downstream dispatch, package mutation/reconstruction, additional package/reconciliation/artifact rows, `AnalysisArtifact`, schema/runtime/source widening, qualitative/hybrid/RAG/vector behavior, or full mockup activation.

And to the Layer 3 workbench external export/download delivery freeze packet, which is planning-only by itself and governs the separate PR `#278` bounded backend/API delivery implementation:
- `next_milestone_plans/Layer3_planning_docs/66_L3_WB_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/67_L3_WB_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_API_AND_STATE_CONTRACT.md`

The external export/download delivery packet freezes only the same-origin backend/API delivery boundary after recorded `external_export_download_prepared` readiness. PR `#278` separately implements that bounded endpoint as `POST /api/v1/layer3/handoff/export/download/deliver`, streaming only the existing validated APS evidence-bundle handoff artifact after full server-side authority proof. PR `#289` later hardens that same endpoint by snapshotting scalar delivery facts and releasing the read-only DB transaction/row lock before APS bundle artifact validation/read/hash/stat. It does not admit rendered download controls, public or signed URLs, connector dispatch, destination selection, generic downstream dispatch, package mutation/reconstruction, additional package/reconciliation/artifact rows, `AnalysisArtifact`, schema/runtime/source widening, qualitative/hybrid/RAG/vector behavior, or full mockup activation.

And to the Layer 3 workbench external export/download delivery UI freeze packet, which is planning-only by itself and governs the rendered `/review/layer3` download control separately implemented by PR `#282` over the already-live PR `#278` same-origin delivery endpoint, with PR `#285`/`#286` hardening that same UI/API boundary:
- `next_milestone_plans/Layer3_planning_docs/68_L3_WB_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_UI_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/69_L3_WB_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_UI_STATE_CONTRACT.md`

The external export/download delivery UI packet admits only the bounded rendered control boundary: server-authoritative delivery availability, one server-gated `deliver_external_export_download` browser action, admitted-field-only requests to the PR `#278` endpoint, and same-origin attachment handling. Docs `68`/`69` do not implement UI behavior by themselves; PR `#282` is the separate live rendered UI implementation, and PR `#285`/`#286` only harden that boundary with browser-managed form delivery, UI-local submitted fallback state, and controlled malformed-JSON errors; PR `#289` separately hardens backend/API delivery lock-release under the same endpoint. Neither the docs nor PR `#282`/`#285`/`#286`/`#289` admit public or signed URLs, connector dispatch, destination selection, generic downstream dispatch, package mutation/reconstruction, additional package/reconciliation/artifact rows, `AnalysisArtifact`, schema/runtime/source widening, qualitative/hybrid/RAG/vector behavior, or full mockup activation.

And to the Layer 3 analysis method registry governance packet, which is planning-only by itself and freezes the current-methods-only quantitative registry boundary before any method expansion:
- `next_milestone_plans/Layer3_planning_docs/70_L3_ANALYSIS_METHOD_REGISTRY_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/71_L3_ANALYSIS_METHOD_REGISTRY_CONTRACT.md`

The analysis method registry packet admits only governance for the existing wrapped quantitative methods in `backend/app/services/analysis.py`: `cross_correlation`, `decomposition`, and `structural_break`. The docs do not implement a registry, add methods, change execution behavior, change artifacts, widen schemas/runtime/source scope, add qualitative/hybrid/RAG/vector execution, or activate any new UI/full mockup behavior.

PR `#316` separately implements that current-methods registry in `backend/app/services/analysis.py` without adding methods or changing execution behavior. New quantitative methods, qualitative/hybrid/RAG/vector expansion, source/schema/runtime widening, UI activation, and full mockup behavior remain deferred until separately governed.

And to the current-main Layer 3 descriptive-summary governance packet from PR `#402`, implemented by PR `#411` for lower-level analysis API support and separately extended by PR `#417` for single-item Gate C admission only:
- `next_milestone_plans/Layer3_planning_docs/72_L3_DESCRIPTIVE_SUMMARY_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/73_L3_DESCRIPTIVE_SUMMARY_CONTRACT.md`

The descriptive-summary packet governs the bounded method-expansion path for the existing `descriptive_summary` recommendation label. PR `#411` implemented only the lower-level analysis API method: registry membership, fallback execution for datasets outside starter time-series assumptions, deterministic JSON artifacts, and assumption/caveat rows. PR `#417` separately admits that method through the existing single-item Gate C pass-entry path. PR `#424` admits only the explicit service-owned associated-cohort `materialize_pass_entry(...)` path, PR `#425` hardens exact `requested_method_name` matching, PR `#432` admits only selected-pass associated-cohort execution-start/result-status through existing backend/API surfaces, PR `#438` admits only exact selected-pass associated-cohort result review through the existing backend/API result-review endpoint, PR `#441` adds planning-only governance for rendered associated-cohort result-review UI, PR `#443` implements only that exact rendered `/review/layer3` associated-cohort result-review UI tranche, docs `86`/`87` govern only read-only associated-cohort package-review preview/readiness, PR `#447` implements only that read-only preview/readiness tranche, PR `#451` implements docs `88`/`89` as the bounded associated-cohort package-construction slice, PR `#456` implements only associated-cohort package-review submit, PR `#458` lands docs `92`/`93` as planning-only handoff/export governance, PR `#460` implements only bounded backend/API associated-cohort handoff/export prepare-only behavior, PR `#462` proves the existing rendered prepare path, PR `#464` lands docs `94`/`95` as current-main planning-only APS dispatch governance, PR `#466` implements only exact associated-cohort APS evidence-bundle handoff dispatch, docs `96`/`97` govern associated-cohort external export/download readiness, and PR `#479` implements only that bounded reference-only readiness path. None of these PRs or docs widens schema/runtime/source scope, qualitative/hybrid/RAG/vector behavior, delivery, connector dispatch, broader UI behavior, or full mockup behavior; docs `84`/`85` do not make UI behavior live by themselves, docs `86`/`87` do not make package-review preview live by themselves, docs `88`/`89` do not make package construction live by themselves, docs `92`/`93` do not make handoff/export live by themselves without PR `#460` implementation authority, docs `94`/`95` do not make APS dispatch live by themselves without PR `#466` implementation authority, and docs `96`/`97` do not make readiness live by themselves without PR `#479` implementation authority. PR `#481` adds docs `98`/`99` as current-main planning governance for same-origin associated-cohort delivery after PR `#479`; PR `#483` proves the backend/API portion through the existing same-origin delivery endpoint without adding a new route; PR `#485` adds docs `100`/`101` as rendered-control gate governance; PR `#487` implements only that explicit server-authoritative associated-cohort rendered delivery UI gate. These do not admit public/signed URLs, connector/generic dispatch, destination selection, package mutation, schema/runtime/source widening, broader UI, or full mockup behavior.

And to the planning-only deferred implementation playbook from PR `#407`, which defines the operational requirements, activation gates, test expectations, stop conditions, and post-merge practices for any future deferred item:
- `next_milestone_plans/Layer3_planning_docs/74_L3_DEFERRED_IMPLEMENTATION_PLAYBOOK.md`

The playbook does not by itself select a new lane or implement deferred behavior. It keeps the broader deferred categories blocked behind their activation contracts; PR `#411` used it for the first bounded lower-level `descriptive_summary` analysis-service tranche, PR `#417` used docs `75`/`76` for the bounded single-item Gate C admission tranche, PR `#424`/`#425` used docs `78`/`79` for the bounded service-only associated-cohort tranche, PR `#432` used docs `80`/`81` for selected-pass associated-cohort execution-start/result-status, PR `#438` used docs `82`/`83` for exact selected-pass associated-cohort result review, PR `#443` uses docs `84`/`85` for exact rendered associated-cohort result-review UI implementation, PR `#447` uses docs `86`/`87` for read-only associated-cohort package-review preview/readiness, PR `#451` uses docs `88`/`89` for the bounded associated-cohort package-construction implementation, PR `#456` uses docs `90`/`91` for bounded package-review submit, PR `#458` lands docs `92`/`93` as planning-only handoff/export governance, PR `#460` implements only bounded backend/API associated-cohort handoff/export prepare-only behavior, PR `#464` lands docs `94`/`95` as current-main APS dispatch governance only, PR `#466` implements only bounded backend/API associated-cohort APS evidence-bundle handoff dispatch, docs `96`/`97` govern external export/download readiness, PR `#479` implements only bounded reference-only readiness after exact APS dispatch authority, docs `98`/`99` govern associated-cohort same-origin delivery, PR `#483` proves the backend/API delivery portion through the existing endpoint, PR `#485` docs `100`/`101` settle the separate rendered-control activation gate, and PR `#487` implements only that explicit server-authoritative gate over the existing same-origin attachment form. Connector dispatch, schema/runtime/source widening, qualitative/hybrid/RAG/vector behavior, retry/recovery/rerun expansion, pass-entry changes, broader UI behavior, and full mockup activation remain blocked until separately implemented.

And to the current-main signed delivery-reference governance packet from PR `#497` and the separate bounded backend/API same-origin signed-reference implementation from PR `#499`:
- `next_milestone_plans/Layer3_planning_docs/102_COHORT_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_URL_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/103_COHORT_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_URL_CONTRACT.md`

The signed URL packet freezes the minimum questions and no-go boundaries for a short-lived, server-authorized associated-cohort signed delivery reference after PR `#483` same-origin delivery and PR `#487` rendered gate authority. Docs `102`/`103` do not make signed-reference behavior live by themselves; PR `#499` separately implements only same-origin signed-reference generation/use through backend/API POST endpoints. It does not make rendered signed URL controls, public/provider URLs, connector/generic dispatch, destination selection, package mutation, durable token/receipt/audit/revocation state, schema/runtime/source widening, broader UI, or full mockup behavior live.

And to the current-main rendered signed-reference UI freeze plus deferred-gate decision freeze:

- `next_milestone_plans/Layer3_planning_docs/104_signed-ui.md`
- `next_milestone_plans/Layer3_planning_docs/105_deferred-gates.md`

`104_signed-ui.md` admits only the rendered `/review/layer3` same-origin signed-reference controls over the already-live PR `#499` endpoints, preserving PR `#487` delivery UI authority and all public/provider/connector/destination/durable-state no-go boundaries. `105_deferred-gates.md` keeps provider/public signed URLs, connector/destination dispatch, durable token/receipt/audit/revocation state, and qualitative APS content document execution as separately frozen decisions rather than hidden side effects of this UI tranche. PR `#513` is current-main UI/theme trace alignment only and does not make qualitative execution or new downstream runtime behavior live.

And to the durable signed-reference state planning/control freeze:

- `next_milestone_plans/Layer3_planning_docs/106_DURABLE_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/107_DURABLE_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/108_DURABLE_ENTRY.md`
- `next_milestone_plans/Layer3_planning_docs/109_DURABLE_STATE.md`

Current-main docs `106`/`107` select durable token, receipt, revocation, and audit state after the current same-origin signed-reference chain. Current-main docs `108`/`109` from PR `#518` name the implementation-entry surfaces, durable table family, service seam, API compatibility rule, and test obligations. PR `#520` implements only the bounded durable runtime backing state behind the existing PR `#499` endpoints: token hash records, generation/use receipts, audit rows, revocation table awareness without a public endpoint, durable missing-state failure, and single-use replay denial. It does not expose provider/public URLs, dispatch to connectors/destinations, change rendered UI, mutate packages, widen source/schema/runtime scope, or admit qualitative APS content document execution.

And to the provider/public URL planning/control freeze:

- `next_milestone_plans/Layer3_planning_docs/110_PROVIDER_URL_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/111_PROVIDER_URL_CONTRACT.md`

Docs `110`/`111` freeze provider/public URL behavior as not admitted after PR `#520` durable same-origin signed-reference runtime and PR `#522` residual settlement. They require a future implementation-entry freeze to choose exactly one provider/public mode, prove concrete provider/object-store authority, define ACL/expiry/revocation/header/security behavior, and preserve same-origin delivery plus durable same-origin signed references unless explicitly superseded. They do not implement provider URLs, public URLs, object-store ACL changes, connector/destination dispatch, rendered controls, package mutation, schema/runtime/source widening, qualitative execution, or any route by themselves.

And to the connector/destination dispatch planning/control freeze:

- `next_milestone_plans/Layer3_planning_docs/112_CONNECTOR_DISPATCH_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/113_CONNECTOR_DISPATCH_CONTRACT.md`

Docs `112`/`113` freeze connector/destination/generic downstream dispatch behavior as not admitted after the same-origin delivery, same-origin signed-reference, durable state, residual-settlement, and provider/public URL governance chain. They require a future implementation-entry freeze to choose exactly one dispatch mode and prove connector/destination authority, lifecycle, idempotency, authorization, receipt/audit, failure, and tests before code. They do not implement connector runs, destination selection, generic downstream dispatch, rendered controls, provider/public URLs, package mutation, schema/runtime/source widening, qualitative execution, queue/retry/cancel behavior, or any route by themselves.

And to the qualitative APS content document execution planning/control freeze:

- `next_milestone_plans/Layer3_planning_docs/114_QUAL_APS_EXEC_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/115_QUAL_APS_EXEC_CONTRACT.md`

Docs `114`/`115` remain the historical qualitative APS content document governance after PR `#525` connector/destination dispatch governance. Doc `119`, current code, and the live proof surfaces now admit only the exact `single_aps_doc_qualitative_pass`; doc `124` keeps broad qualitative, qualitative cohort, hybrid, RAG/vector, source widening, package/handoff/export, connector/destination, provider/public URL, full mockup, hidden LLM planning, and auth/security behavior blocked.

And to the descriptive-summary Gate C admission packet, whose single-item implementation boundary was satisfied by PR `#417` after PR `#411` lower-level method support:
- `next_milestone_plans/Layer3_planning_docs/75_L3_DESCRIPTIVE_SUMMARY_GATEC_ADMISSION_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/76_L3_DESCRIPTIVE_SUMMARY_GATEC_ADMISSION_CONTRACT.md`

The Gate C admission packet admits only single-item pass-entry for already-live lower-level `descriptive_summary` analysis. Service-only associated-cohort admission is separately governed by docs `78`/`79` and implemented by PR `#424`/`#425`; selected-pass associated-cohort execution-start/result-status is separately governed by docs `80`/`81` and implemented by PR `#432`; selected-pass associated-cohort result review is separately governed by docs `82`/`83` and implemented by PR `#438`; selected-pass associated-cohort result-review UI is separately governed by docs `84`/`85` and implemented only for the exact rendered `/review/layer3` result-review path by PR `#443`; read-only associated-cohort package-review preview/readiness is separately governed by docs `86`/`87` and implemented by PR `#447`; associated-cohort package construction is separately governed by docs `88`/`89` and implemented by PR `#451` as a bounded current-main slice; associated-cohort package-review submit is separately governed by docs `90`/`91` and implemented by PR `#456`; associated-cohort handoff/export is governed by planning docs `92`/`93` from PR `#458`, PR `#460` implements only the bounded backend/API prepare-only state, PR `#462` proves the rendered prepare path, docs `94`/`95` from PR `#464` govern associated-cohort APS dispatch, PR `#466` implements only that bounded APS evidence-bundle handoff dispatch path, docs `96`/`97` govern associated-cohort external export/download readiness, PR `#479` implements only bounded reference-only readiness after exact APS dispatch authority, docs `98`/`99` govern associated-cohort same-origin delivery, PR `#483` proves the backend/API delivery path through the existing endpoint, PR `#485` docs `100`/`101` govern the separate associated-cohort rendered delivery activation gate, and PR `#487` implements only that explicit server-authoritative gate over the existing same-origin attachment form. Connector dispatch, schema/runtime/source widening, qualitative/hybrid/RAG/vector behavior, retry/recovery/rerun expansion, pass-entry changes, broader UI behavior, and full mockup activation remain blocked until separately implemented.

And to the planning-only associated-cohort `descriptive_summary` requirements gate:
- `next_milestone_plans/Layer3_planning_docs/77_COHORT_REQS.md`

The requirements gate records the decisions needed before associated-cohort `descriptive_summary` service governance: cohort data shape, method-selection rule, execution surface, provenance manifest, failure behavior, and proof expectations. It does not by itself admit selected-pass workbench cohort execution, UI/schema/runtime/source, package/handoff/export, connector dispatch, qualitative/hybrid/RAG/vector behavior, or full mockup activation.

And to the service-materialize associated-cohort `descriptive_summary` freeze/contract, now satisfied for the bounded service-owned path by PR `#424`/`#425`:
- `next_milestone_plans/Layer3_planning_docs/78_COHORT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/79_COHORT_CONTRACT.md`

The service freeze/contract selects only the `aligned_wide_table` plus `service_materialize_only` path with explicit `formation_basis_json["requested_method_name"] == "descriptive_summary"` method-selection metadata. PR `#424` implements that service-only path in `backend/app/services/layer3_pass_entry.py`, and PR `#425` hardens it so absent, malformed, trimmable, or non-descriptive metadata preserves the default `cross_correlation` cohort path. It does not widen selected-pass workbench execution, change API/UI/schema/runtime/source scope, or activate package/handoff/export/connector/qualitative/hybrid/RAG/vector/full mockup behavior.

And to the selected-pass associated-cohort execution-start/result-status freeze/contract, now satisfied for the bounded backend/API path by PR `#432`:
- `next_milestone_plans/Layer3_planning_docs/80_COHORT_EXECUTION_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/81_COHORT_EXECUTION_CONTRACT.md`

The selected-pass cohort execution packet freezes only the backend/API tranche over the existing `/api/v1/layer3/execution/start` and `/api/v1/layer3/execution/result/status` surfaces. PR `#432` implements that bounded path for exact selected-pass associated-cohort `descriptive_summary` metadata/provenance, while preserving fail-closed behavior for invalid binding/provenance. PR `#432` itself kept result review out; PR `#438` separately admits only exact selected-pass associated-cohort result review while keeping UI, package, handoff, export, schema/runtime/source, connector, qualitative/hybrid/RAG/vector, retry/recovery, and full mockup behavior out.

And to the selected-pass associated-cohort result-review freeze/contract from PR `#434`, now satisfied for the bounded backend/API path by PR `#438`:
- `next_milestone_plans/Layer3_planning_docs/82_COHORT_RESULT_REVIEW_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/83_COHORT_RESULT_REVIEW_CONTRACT.md`

The associated-cohort result-review packet freezes only reuse of the existing `/api/v1/layer3/execution/result/review` endpoint for exact PR `#432` selected-pass associated-cohort `descriptive_summary` terminal outputs. PR `#438` implements that bounded backend/API path while preserving the existing route and review envelope; it does not admit UI, package, handoff, export, schema/runtime/source, connector, qualitative/hybrid/RAG/vector, retry/recovery, pass-entry changes, or full mockup behavior.

And to the selected-pass associated-cohort result-review UI freeze/contract from PR `#441`, plus the bounded rendered UI implementation from PR `#443`:
- `next_milestone_plans/Layer3_planning_docs/84_COHORT_RESULT_REVIEW_UI_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/85_COHORT_RESULT_REVIEW_UI_CONTRACT.md`

The associated-cohort result-review UI packet freezes only the rendered `/review/layer3` presentation/control boundary over exact PR `#432` execution-start/result/status authority and PR `#438` backend/API result-review authority. Docs `84`/`85` do not make rendered UI behavior live by themselves; PR `#443` separately implements only that exact rendered associated-cohort result-review path, with server-provenance projection, traceable `reviewed_output_items`, preserved single-item result-review behavior, and package/handoff/export controls unavailable for associated-cohort review state. It does not admit backend/API changes, package, handoff, export, schema/runtime/source, connector, qualitative/hybrid/RAG/vector, retry/recovery, pass-entry changes, broader cohort review, broader UI behavior, or full mockup behavior.

And to the selected-pass associated-cohort package-review preview freeze/contract, which is planning-only and does not make package preview, package construction, package-review submit, handoff, or export live by itself:
- `next_milestone_plans/Layer3_planning_docs/86_COHORT_PACKAGE_REVIEW_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/87_COHORT_PACKAGE_REVIEW_CONTRACT.md`

The associated-cohort package-review preview packet freezes only a read-only preview/readiness inspection boundary after exact PR `#432` execution-start/result/status authority, PR `#438` backend/API result-review authority, and PR `#443` rendered result-review UI authority. It treats docs `48`/`49` as the single-item pattern source, not direct cohort package authority. PR `#447` implements only that read-only preview/readiness inspection through the existing package-preview route and `/review/layer3` UI. It does not admit package construction, package-review submit, `L3OutputPackage` or `L3ReconciliationRecord` creation, package payload files, handoff/export, APS dispatch, external export/download, connector dispatch, schema/runtime/source widening, retry/recovery, pass-entry changes, broader UI behavior, or full mockup activation.

And to the selected-pass associated-cohort package-construction freeze/contract, which is planning-only and does not make package construction, package-review submit, handoff, or export live by itself:
- `next_milestone_plans/Layer3_planning_docs/88_COHORT_PACKAGE_CONSTRUCTION_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/89_COHORT_PACKAGE_CONSTRUCTION_CONTRACT.md`

The associated-cohort package-construction packet freezes only a bounded package-construction commit boundary after exact PR `#432` execution-start/result/status authority, PR `#438` backend/API result-review authority, PR `#443` rendered result-review UI authority, and PR `#447` read-only package-review preview/readiness authority. It treats docs `50`/`51` and the existing single-item package-construction route/helper as pattern sources, not direct cohort construction authority. PR `#450` adds this planning-only governance; PR `#451` is the bounded implementation that narrows `associated_cohort_package_construction_commit_not_admitted` only for that exact authority chain, creates one reconciliation row, three package rows, and three payload files, and still does not admit package-review submit, handoff/export, APS dispatch, external export/download, connector dispatch, schema/runtime/source widening, retry/recovery, pass-entry changes, broader UI behavior, or full mockup activation.

And to the selected-pass associated-cohort package-review submit freeze/contract, which is planning-only by itself and does not make package-review submit, handoff, or export live by itself:
- `next_milestone_plans/Layer3_planning_docs/90_COHORT_PACKAGE_REVIEW_SUBMIT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/91_COHORT_PACKAGE_REVIEW_SUBMIT_CONTRACT.md`

The associated-cohort package-review submit packet freezes only a bounded operator decision boundary after exact PR `#451` package-construction authority. It treats docs `52`/`53` and the existing single-item package-review submit route/helper as pattern sources, not direct cohort submit authority. PR `#456` separately implements only that submit boundary. It does not admit handoff/export, APS dispatch, external export/download, connector dispatch, schema/runtime/source widening, retry/recovery, pass-entry changes, broader UI behavior, or full mockup activation.

And to the selected-pass associated-cohort handoff/export freeze/contract, which is planning-only and does not make handoff/export, APS dispatch, external export/download, or connector behavior live by itself:
- `next_milestone_plans/Layer3_planning_docs/92_COHORT_HANDOFF_EXPORT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/93_COHORT_HANDOFF_EXPORT_CONTRACT.md`

The associated-cohort handoff/export packet freezes only a bounded internal prepare-only decision boundary after exact PR `#456` approved package-review submit authority. It treats docs `54`/`55` and the existing single-item handoff/export route/helper as pattern sources, not direct cohort handoff/export authority. It does not implement `handoff_export_deferred_for_associated_cohort_package_review_submit`, APS dispatch, external export/download, connector dispatch, package payload copy/rewrite, package reconstruction, schema/runtime/source widening, retry/recovery, pass-entry changes, broader UI behavior, or full mockup activation by itself.

And to the Gate D APS validate-only-gates continuation freeze packet now landed on current `main` for the bounded next verification continuation beyond the landed review-packet boundary:
- `next_milestone_plans/Layer3_planning_docs/21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md`

And to the Gate D APS dedicated validate-only runtime/report-ref continuation freeze packet now landed on current `main` from PR `#140` for the bounded next read-only decision beyond the landed generic gate-report refresh lane:
- `next_milestone_plans/Layer3_planning_docs/22_GATED_APS_VALIDATE_ONLY_RUNTIME_FREEZE.md`

This README is operational and navigational.
If it conflicts with the stronger frozen control docs, the control docs govern.

## Authority note

The active control docs in this pack use `P` citations whose path segment begins `layer3_primary_planningdocs/`.
Those citations point to the external canonical Layer 3 planning corpus at `C:\Users\benny\OneDrive\Desktop\Layer3\layer3_primary_planningdocs`.
Those source files are not tracked in this repo/worktree.
Treat them as external planning authority, not repo-local implementation truth.
Repo-local implementation truth still comes from the `R|...` repo paths cited in the pack.

## Current state

The lane now contains:
- the frozen Phase 1A planning baseline
- the execution handoff/control fence
- the implementation-local freeze docs
- the committed bounded Phase 1A code slice
- the committed postcode acceptance audit
- the pack-local roadmap, reconciliation, navigation, and concrete surface-map surfaces needed for bounded Phase 1A closure
- the narrow post-Phase 1A Gate C entry-freeze bridge that identified the blocker set before later Gate C slices could open safely
- the carried-forward first Gate C typing/unit implementation-entry packet that governed the bounded typing/unit lane now landed on current `main`
- the carried-forward Gate C quantitative single-item plan/pass-entry packet that governed the bounded plan/pass lane now landed on current `main`
- the carried-forward Gate C quantitative associated/cohort shaping continuation packet that governed the bounded cohort pass lane now landed on current `main`
- the carried-forward Gate D package-entry freeze packet that governed the bounded packaging/reconciliation entry slice now landed on current `main` without reopening route/UI or APS handoff scope
- the carried-forward Gate D APS handoff freeze packet that governed the bounded APS evidence-bundle-family adapter/handoff slice now landed on current `main` without widening route/UI, runtime DB, or later APS-family scope
- the carried-forward Gate D APS citation continuation freeze packet that governed the bounded citation-pack-family handoff slice now landed on current `main` without widening route/UI, runtime DB, or later APS-family fan-out
- the carried-forward Gate D APS report continuation freeze packet that governed the bounded evidence-report-family continuation slice now landed on current `main` beyond the landed citation-pack handoff while keeping export/context/deterministic fan-out, route/UI, and runtime DB widening out
- the carried-forward Gate D APS report-export continuation freeze packet that now governs the bounded evidence-report-export-family continuation slice now landed on current `main` beyond the landed evidence-report handoff while keeping export-package/context/deterministic fan-out, route/UI, and runtime DB widening out
- the carried-forward Gate D APS context continuation freeze packet that now governs the bounded export-derived context-packet continuation slice now landed on current `main` beyond the landed evidence-report-export handoff while keeping export-package implementation, package-derived context/dossier/deterministic fan-out, route/UI, and runtime DB widening out
- the carried-forward Gate D APS multisource continuation freeze packet that now governs the bounded same-run shared-source admission boundary now landed on current `main` beyond the landed export-derived context-packet slice while keeping direct export-package, package-derived context, dossier, deterministic fan-out, route/UI, runtime DB, and schema widening out
- the carried-forward Gate D APS export-package first shared-consumer freeze packet that now governs the landed read-only choice on current `main` of `evidence_report_export_package` as the first downstream shared APS family beyond the landed multisource slice while keeping package-derived context, context-dossier, deterministic fan-out, route/UI, runtime DB, and schema widening out
- the landed Gate D APS export-package handoff implementation slice rooted in `backend/app/services/layer3_aps_report_export_package_handoff.py` and `backend/tests/test_layer3_aps_report_export_package_handoff.py`, plus the merged narrow export/export-package gate-hardening follow-up in `backend/app/services/nrc_aps_evidence_report_export_gate.py` and `backend/app/services/nrc_aps_evidence_report_export_package_gate.py`; this still does not mean package-derived context, context-dossier, deterministic fan-out, route/UI, runtime DB, or schema widening have landed on current `main`
- the carried-forward Gate D APS package-derived-context freeze packet that now lands on current `main` and selects the next later shared APS family beyond the landed export-package boundary; it still does not mean package-derived context implementation, `context_dossier`, deterministic fan-out, route/UI, runtime DB, or schema widening have landed on current `main`
- current `main` now also includes the bounded Gate D APS package-derived context handoff implementation slice rooted in `backend/app/services/layer3_aps_context_packet_package_handoff.py` and `backend/tests/test_layer3_aps_context_packet_package_handoff.py`, plus the now-landed malformed-scoped candidate-discovery hardening across `backend/app/services/nrc_aps_evidence_report_export_gate.py`, `backend/app/services/nrc_aps_evidence_report_export_package_gate.py`, and `backend/app/services/nrc_aps_context_packet_gate.py`; this still does not mean broader package-derived context, `context_dossier`, deterministic fan-out, route/UI, runtime DB, or schema widening have landed
- current `main` now also includes the read-only Gate D APS context-dossier freeze packet rooted in `next_milestone_plans/Layer3_planning_docs/17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md`; it settles `context_dossier` as the next later shared APS family after the landed package-context milestone while preserving paired export-derived context packets as dossier inputs, but it still does not mean `context_dossier` implementation, deterministic fan-out, route/UI, runtime DB, or schema widening have landed on current `main`
- current `main` now also includes the bounded Gate D APS context-dossier handoff implementation slice rooted in `backend/app/services/layer3_aps_context_dossier_handoff.py` and `backend/tests/test_layer3_aps_context_dossier_handoff.py`, plus the narrow dossier-gate scope hardening in `backend/app/services/nrc_aps_context_dossier_gate.py`; that landed lane preserves paired export-derived context packets as dossier inputs and still does not mean deterministic fan-out, route/UI, runtime DB, or schema widening have landed
- current `main` now also includes the read-only Gate D APS deterministic-insight continuation freeze packet rooted in `next_milestone_plans/Layer3_planning_docs/18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md`; it selects `deterministic_insight_artifact` as the next deterministic continuation beyond the landed dossier boundary without admitting deterministic implementation, challenge/review-packet fan-out, route/UI, runtime DB, or schema widening by itself
- current `main` now also includes the bounded Gate D APS deterministic-insight handoff implementation slice rooted in `backend/app/services/layer3_aps_deterministic_insight_artifact_handoff.py` and `backend/tests/test_layer3_aps_deterministic_insight_artifact_handoff.py`, plus the narrow deterministic-gate hardening in `backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py`; that landed lane keeps one persisted dossier as the deterministic source boundary, leaves `ConnectorRun.query_plan_json` untouched, and still does not mean challenge/review-packet fan-out, route/UI, runtime DB, or schema widening have landed on current `main`
- current `main` now also includes the read-only Gate D APS deterministic-challenge continuation freeze packet rooted in `next_milestone_plans/Layer3_planning_docs/19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE.md`; it selects `deterministic_challenge_artifact` as the next deterministic continuation beyond the landed deterministic-insight boundary without admitting challenge implementation, challenge-review-packet fan-out, validate-only expansion, route/UI, runtime DB, or schema widening by itself
- current `main` now also includes the bounded Gate D APS deterministic-challenge handoff implementation slice rooted in `backend/app/services/layer3_aps_deterministic_challenge_artifact_handoff.py` and `backend/tests/test_layer3_aps_deterministic_challenge_artifact_handoff.py`, plus the narrow deterministic challenge gate hardening in `backend/app/services/nrc_aps_deterministic_challenge_artifact_gate.py`; that landed lane keeps one persisted deterministic insight artifact as the immediate source boundary and still does not mean later review-packet fan-out, validate-only expansion, route/UI, runtime DB, or schema widening have landed on current `main`
- current `main` now also includes the read-only Gate D APS deterministic challenge review-packet continuation freeze packet rooted in `next_milestone_plans/Layer3_planning_docs/20_GATED_APS_REVIEW_PACKET_FREEZE.md`; it selects `deterministic_challenge_review_packet` as the exact next deterministic continuation beyond the landed deterministic-challenge boundary while keeping validate-only gates later
- current `main` now also includes the bounded Gate D APS deterministic challenge review-packet handoff implementation slice rooted in `backend/app/services/layer3_aps_deterministic_challenge_review_packet_handoff.py`, plus the narrow review-packet gate hardening in `backend/app/services/nrc_aps_deterministic_challenge_review_packet_gate.py`; that landed lane keeps one persisted deterministic challenge artifact as the immediate source boundary and still does not admit validate-only expansion, route/UI, runtime DB, or schema widening
- current `main` now also includes the read-only Gate D APS validate-only-gates continuation freeze packet from PR `#136`, rooted in `next_milestone_plans/Layer3_planning_docs/21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md`; it selects `validate_only_gates` as the exact next verification continuation beyond the landed review-packet handoff while keeping validate-only execution/report refresh, promotion, retrieval cutover, route/UI, runtime DB, and schema widening later
- current `main` now also includes the bounded validate-only gate-report refresh lane from PR `#138`, and the post-PR138 docs/progress sync from PR `#139`, rooted in `backend/app/services/review_nrc_aps_gate_reports.py`, `tools/nrc_aps_refresh_review_gate_reports.py`, `tools/run_nrc_aps_local_corpus_e2e.py`, `backend/tests/test_review_nrc_aps_gate_reports.py`, and `project6.ps1`
- current `main` now also includes the read-only `22_GATED_APS_VALIDATE_ONLY_RUNTIME_FREEZE.md` freeze from PR `#140`, selecting the dedicated validate-only family-specific runtime/report-ref decision as the next bounded continuation beyond that landed generic gate-report boundary; it still does not mean dedicated validate-only implementation, promotion, retrieval cutover, route/UI, runtime DB, or schema widening have landed on current `main`
- current `main` now also includes the post-PR140 docs/progress sync from PR `#141` and the post-PR141 docs/progress sync from PR `#142`
- current `main` now also includes the bounded dedicated validate-only runtime/report-ref implementation slice from PR `#143`, rooted in `backend/app/services/nrc_aps_validate_only_gates_contract.py`, `backend/app/services/nrc_aps_validate_only_gates.py`, `backend/app/services/nrc_aps_validate_only_gates_gate.py`, `backend/tests/test_nrc_aps_validate_only_gates.py`, `tools/nrc_aps_refresh_validate_only_gates.py`, `tools/nrc_aps_validate_only_gates_gate.py`, `backend/app/services/review_nrc_aps_runtime.py`, `backend/app/services/review_nrc_aps_gate_reports.py`, `backend/app/services/review_nrc_aps_graph.py`, `backend/app/services/review_nrc_aps_tree.py`, `backend/app/services/connectors_sciencebase.py`, and `project6.ps1`; that landed lane keeps the landed generic gate-report refresh posture as upstream truth and still does not admit later validate-only top-chain expansion, promotion, retrieval cutover, route/UI, runtime DB, or schema widening on current `main`
- current `main` now also includes the landed read-only `23_GATED_APS_PROMOTION_FREEZE.md` freeze from PR `#145`; that freeze selected promotion as the first later APS family beyond the landed dedicated validate-only boundary, and live repo truth now also shows the existing promotion governance family already sufficient on current `main` while retrieval cutover already exists there as a separate validate-only parity-proof family, so no further later APS family decision or implementation lane is currently justified by default

Key lane closure commits include:
- `a95bc104` `docs(layer3): freeze phase1a planning pack`
- `0b0ecf7e` `feat(layer3): add Phase 1A feeder-ledger entry slice`
- `d67bc0e8` `docs(layer3): add Phase 1A postcode acceptance audit`
- `f252d820` `docs(layer3): add phase1a pack front door and roadmap`
- `119c1d73` `docs(layer3): add phase1a surface map`

These are the milestone commits that define the bounded Phase 1A lane shape.
Later doc-only alignment commits may exist without changing that milestone meaning.

Current bounded posture:
- Phase 1A remains Gate-B-only feeder / ledger entry
- landed objects remain exactly:
  - `l3_session`
  - `l3_selection_manifest`
  - `l3_descriptor`
  - `l3_retrieval_event`
  - `l3_material_snapshot`
- Phase 1A itself does not admit typing, orchestration, packaging, APS handoff, route-family work, UI widening, or consumer widening
- later carried-forward Gate C freezes now cover the landed typing/unit, single-item pass, and quantitative cohort slices
- later carried-forward Gate D freeze now covers the landed bounded package-entry slice only; it does not mean packaging or consumer routes beyond that slice have already landed
- the carried-forward Gate D APS handoff freeze now covers the bounded APS evidence-bundle-family handoff slice now landed on current `main` only; it does not mean broader APS families, route/UI surfaces, or consumer routes beyond that slice have already landed
- the carried-forward Gate D APS citation and report freezes now cover the landed bounded citation-pack and evidence-report slices only; they do not mean later APS families beyond those slices have already landed
- the carried-forward Gate D APS report-export freeze now covers the bounded evidence-report-export slice now landed on current `main` only; it does not mean evidence-report-export-package or later APS families have already landed
- the carried-forward Gate D APS context freeze now covers only the bounded export-derived context-packet slice now landed on current `main`; it does not mean export-package implementation, package-derived context, dossier, deterministic, or route/UI surfaces have already landed
- the carried-forward Gate D APS multisource freeze now covers only the bounded shared same-run source-admission slice now landed on current `main`; it does not mean export-package implementation, package-derived context, context-dossier, deterministic, or schema surfaces have already landed
- the carried-forward Gate D APS export-package first shared-consumer freeze now covers the now-landed decision on current `main` to select `evidence_report_export_package` as the first later shared APS family beyond the landed multisource slice, and the bounded export-package handoff slice now also lands on current `main`; that still does not mean package-derived context, context-dossier, deterministic, or schema surfaces have already landed
- the carried-forward Gate D APS package-derived-context freeze now covers the landed read-only choice on current `main` to select package-derived context packet as the next later shared APS family beyond the landed export-package boundary, but it does not mean package-derived context implementation, `context_dossier`, deterministic, or schema surfaces have landed on current `main`
- current `main` now also includes the bounded package-derived context handoff slice rooted in `backend/app/services/layer3_aps_context_packet_package_handoff.py` and `backend/tests/test_layer3_aps_context_packet_package_handoff.py`, plus the now-landed malformed-scoped candidate-discovery hardening across `backend/app/services/nrc_aps_evidence_report_export_gate.py`, `backend/app/services/nrc_aps_evidence_report_export_package_gate.py`, and `backend/app/services/nrc_aps_context_packet_gate.py`; it still does not mean broader package-derived context, `context_dossier`, deterministic, or schema surfaces have landed
- current `main` now also includes the read-only `17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md` freeze selecting `context_dossier` as the next later shared APS family after the landed package-context milestone while preserving paired export-derived context packets as dossier inputs; it does not mean `context_dossier` implementation, deterministic, or schema surfaces have landed on current `main`
- current `main` now also includes the bounded `aps_context_dossier_handoff` slice rooted in `backend/app/services/layer3_aps_context_dossier_handoff.py`, plus the narrow dossier-gate scope hardening in `backend/app/services/nrc_aps_context_dossier_gate.py`; that landed lane keeps paired export-derived context packets as dossier inputs and does not admit deterministic fan-out by itself
- current `main` now also includes the read-only `18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md` freeze selecting `deterministic_insight_artifact` as the next deterministic continuation beyond the landed dossier boundary; it does not mean deterministic implementation, challenge/review-packet fan-out, or schema surfaces have landed on current `main`
- current `main` now also includes the bounded `aps_deterministic_insight_artifact_handoff` slice rooted in `backend/app/services/layer3_aps_deterministic_insight_artifact_handoff.py`, plus the narrow deterministic-gate hardening in `backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py`; that landed lane preserves one persisted dossier as the deterministic source boundary and does not admit later deterministic fan-out, route/UI, runtime DB, or schema widening by itself
- current `main` now also includes the read-only `19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE.md` freeze selecting `deterministic_challenge_artifact` as the next deterministic continuation beyond the landed deterministic-insight boundary; it does not mean deterministic challenge implementation, challenge-review-packet fan-out, validate-only expansion, route/UI, runtime DB, or schema surfaces have landed
- current `main` now also includes the bounded `aps_deterministic_challenge_artifact_handoff` lane from PR `#130`, rooted in `backend/app/services/layer3_aps_deterministic_challenge_artifact_handoff.py` and `backend/tests/test_layer3_aps_deterministic_challenge_artifact_handoff.py`, plus the narrow deterministic challenge gate hardening in `backend/app/services/nrc_aps_deterministic_challenge_artifact_gate.py`; that landed lane preserves one persisted deterministic insight artifact as the immediate source boundary, leaves `ConnectorRun.query_plan_json` untouched, and does not admit later deterministic review-packet fan-out, validate-only expansion, route/UI, runtime DB, or schema widening by itself
- current `main` now also includes the read-only `20_GATED_APS_REVIEW_PACKET_FREEZE.md` freeze selecting `deterministic_challenge_review_packet` as the exact next deterministic continuation beyond the landed deterministic-challenge boundary; it does not mean review-packet implementation or validate-only surfaces have landed on current `main`
- current `main` now also includes the bounded `aps_deterministic_challenge_review_packet_handoff` lane rooted in `backend/app/services/layer3_aps_deterministic_challenge_review_packet_handoff.py` and `backend/tests/test_layer3_aps_deterministic_challenge_review_packet_handoff.py`, plus the narrow review-packet gate hardening in `backend/app/services/nrc_aps_deterministic_challenge_review_packet_gate.py`; that landed lane preserves one persisted deterministic challenge artifact as the immediate source boundary and still does not admit validate-only expansion, route/UI, runtime DB, or schema widening by itself
- current `main` now also includes the read-only `21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md` freeze plus the post-PR136 docs/progress sync from PR `#137`, and current `main` now also includes the bounded validate-only gate-report refresh lane from PR `#138`, rooted in `backend/app/services/review_nrc_aps_gate_reports.py`, `tools/nrc_aps_refresh_review_gate_reports.py`, `tools/run_nrc_aps_local_corpus_e2e.py`, `backend/tests/test_review_nrc_aps_gate_reports.py`, and `project6.ps1`

The active REV2 control docs in this pack have also been re-audited against current `main` after the repo-root analyst-insight page, alias-router, static-asset, and runtime-helper surfaces landed. Treat the REV1 artifacts and the REV1-to-REV2 correction memo as historical context only.

## One-line use rule

Use this pack as the authoritative planning and closure bundle for the bounded Phase 1A Layer 3 slice; do not treat it as permission to reopen broader Layer 3 scope.

## Pack layout

### 1. Planning baseline

Read these first when you need the tranche boundary, prep rules, and validation posture:
- `Layer3_planning_docs/01_IMPLEMENTATION_ENTRY_BASELINE_REV2.md`
- `Layer3_planning_docs/02_PHASE1A_IMPLEMENTATION_PREP_SPEC_REV2.md`
- `Layer3_planning_docs/03_PHASE1A_VALIDATION_AND_EXECUTION_PLAN_REV2.md`

Read this after the REV2 trio if you are deciding what the first Gate C slice had to freeze before any write-enabled Gate C implementation started:
- `Layer3_planning_docs/04_GATEC_ENTRY_FREEZE.md`

Read this after `04_GATEC_ENTRY_FREEZE.md` if you need the carried-forward contract for the first bounded Gate C typing/unit slice that has now landed on current `main`:
- `Layer3_planning_docs/05_GATEC_IMPLEMENTATION_FREEZE.md`

Read this after `05_GATEC_IMPLEMENTATION_FREEZE.md` if you need the carried-forward contract for the bounded Gate C quantitative single-item plan/pass slice that has now landed on current `main`:
- `Layer3_planning_docs/06_GATEC_PASS_FREEZE.md`

Read this after `06_GATEC_PASS_FREEZE.md` if you need the carried-forward contract for the bounded Gate C quantitative associated/cohort continuation slice that has now landed on current `main`:
- `Layer3_planning_docs/07_GATEC_COHORT_FREEZE.md`

Read this after `07_GATEC_COHORT_FREEZE.md` if you need the carried-forward contract that governed the bounded Gate D package-entry slice now landed on current `main`:
- `Layer3_planning_docs/08_GATED_PACKAGE_FREEZE.md`

Read this after `08_GATED_PACKAGE_FREEZE.md` if you need the carried-forward contract that governed the bounded APS evidence-bundle-family handoff slice now landed on current `main`:
- `Layer3_planning_docs/09_GATED_APS_HANDOFF_FREEZE.md`

Read this after `09_GATED_APS_HANDOFF_FREEZE.md` if you need the carried-forward contract that governed the bounded citation-pack-family handoff slice now landed on current `main`:
- `Layer3_planning_docs/10_GATED_APS_CITATION_FREEZE.md`

Read this after `10_GATED_APS_CITATION_FREEZE.md` if you need the governing contract for the bounded evidence-report-family continuation slice now landed on current `main`:
- `Layer3_planning_docs/11_GATED_APS_REPORT_FREEZE.md`

Read this after `11_GATED_APS_REPORT_FREEZE.md` if you need the governing contract for the bounded evidence-report-export-family continuation slice now landed on current `main` beyond the landed evidence-report handoff:
- `Layer3_planning_docs/12_GATED_APS_REPORT_EXPORT_FREEZE.md`

Read this after `12_GATED_APS_REPORT_EXPORT_FREEZE.md` if you need the governing contract for the bounded export-derived context-packet continuation slice now landed on current `main` beyond the landed evidence-report-export handoff:
- `Layer3_planning_docs/13_GATED_APS_CONTEXT_FREEZE.md`

Read this after `13_GATED_APS_CONTEXT_FREEZE.md` if you need the governing contract for the bounded same-run shared-source admission boundary now landed on current `main` beyond the landed export-derived context-packet slice:
- `Layer3_planning_docs/14_GATED_APS_MULTISOURCE_FREEZE.md`

Read this after `15_GATED_APS_EXPORT_PACKAGE_FREEZE.md` if you need the governing contract for the now-landed next later shared APS family beyond the landed export-package boundary:
- `Layer3_planning_docs/16_GATED_APS_PACKAGE_CONTEXT_FREEZE.md`

Read this after `16_GATED_APS_PACKAGE_CONTEXT_FREEZE.md` if you need the now-landed bounded package-derived context handoff slice on current `main`:
- `backend/app/services/layer3_aps_context_packet_package_handoff.py`
- `backend/app/services/nrc_aps_context_packet_gate.py`
- `backend/tests/test_layer3_aps_context_packet_handoff.py`
- `backend/tests/test_layer3_aps_context_packet_package_handoff.py`

Read this after `18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md` if you need the governing contract for the now-landed next deterministic continuation beyond the landed deterministic-insight boundary:
- `Layer3_planning_docs/19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE.md`

Read this after `19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE.md` if you need the governing contract for the now-landed next deterministic continuation beyond the landed deterministic-challenge boundary:
- `Layer3_planning_docs/20_GATED_APS_REVIEW_PACKET_FREEZE.md`

Read this after `20_GATED_APS_REVIEW_PACKET_FREEZE.md` if you need the now-landed read-only validate-only-gates freeze on current `main` beyond the now-landed deterministic challenge review-packet handoff:
- `Layer3_planning_docs/21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md`

Read these after `21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md` if you need the landed bounded validate-only gate-report refresh lane on current `main` beyond that freeze:
- `backend/app/services/review_nrc_aps_gate_reports.py`
- `tools/nrc_aps_refresh_review_gate_reports.py`
- `tools/run_nrc_aps_local_corpus_e2e.py`
- `backend/tests/test_review_nrc_aps_gate_reports.py`
- `project6.ps1`

Read this after the landed generic gate-report refresh lane if you need the landed read-only next decision from PR `#140` beyond that landed boundary:
- `Layer3_planning_docs/22_GATED_APS_VALIDATE_ONLY_RUNTIME_FREEZE.md`

### 2. Execution handoff

Read these when you need the touch envelope, proof runbook, and direct write-enabled contract:
- `Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md`
- `Layer3_execution_handoff/05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md`
- `Layer3_execution_handoff/06_PHASE1A_CODEWRITING_HANDOFF.md`

### 3. Local freeze and closure

Read these when you need the implementation-local defaults, acceptance criteria, write-enabled prompt, reconciliation posture, roadmap, and postcode audit:
- `Layer3_execution_freeze/07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS_REV2.md`
- `Layer3_execution_freeze/08_PHASE1A_PRECODE_ACCEPTANCE_CHECKLIST_REV2.md`
- `Layer3_execution_freeze/09_PHASE1A_WRITE_ENABLED_CODEX_PROMPT_REV2.md`
- `Layer3_execution_freeze/10_PHASE1A_POSTCODE_ACCEPTANCE_AUDIT.md`
- `Layer3_execution_freeze/11_PHASE1A_RECONCILIATION_CHECKLIST.md`
- `Layer3_execution_freeze/12_PHASE1A_ROADMAP_AND_DECISION_NOTES.md`
- `Layer3_execution_freeze/13-phase1a-surface-map.md`
- `Layer3_execution_freeze/layer3_phase1a_roadmap.png`
- `Layer3_execution_freeze/FREEZE_PACK_REV1_TO_REV2_SOURCE_HYGIENE_MEMO.md`

## Doc classification

### Normative control docs

These define the actual tranche boundary and control posture:
- `01_IMPLEMENTATION_ENTRY_BASELINE_REV2.md`
- `02_PHASE1A_IMPLEMENTATION_PREP_SPEC_REV2.md`
- `03_PHASE1A_VALIDATION_AND_EXECUTION_PLAN_REV2.md`
- `04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md`
- `05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md`
- `06_PHASE1A_CODEWRITING_HANDOFF.md`
- `07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS_REV2.md`
- `08_PHASE1A_PRECODE_ACCEPTANCE_CHECKLIST_REV2.md`
- `09_PHASE1A_WRITE_ENABLED_CODEX_PROMPT_REV2.md`
- `10_PHASE1A_POSTCODE_ACCEPTANCE_AUDIT.md`

### Operational companion docs

These help navigation, reconciliation, and visual orientation, but do not override the normative set:
- `README_LAYER3_PHASE1A_PACK.md`
- `11_PHASE1A_RECONCILIATION_CHECKLIST.md`
- `12_PHASE1A_ROADMAP_AND_DECISION_NOTES.md`
- `13-phase1a-surface-map.md`
- `layer3_phase1a_roadmap.png`

### Post-Phase 1A carried-forward bridge

This bridge document is not part of the accepted Phase 1A normative control spine.
It exists to explain why a separate Gate C freeze packet was required:
- `04_GATEC_ENTRY_FREEZE.md`

### Post-Phase 1A carried-forward freeze packet

This document is also outside the accepted Phase 1A normative control spine.
It is the actual frozen contract that governed the first bounded Gate C typing/unit implementation lane now landed on current `main`:
- `05_GATEC_IMPLEMENTATION_FREEZE.md`

### Post-Phase 1A carried-forward continuation freeze packet

This document is also outside the accepted Phase 1A normative control spine.
It is the actual frozen contract that governed the bounded Gate C quantitative single-item plan/pass implementation lane now landed on current `main`:
- `06_GATEC_PASS_FREEZE.md`

### Post-Phase 1A carried-forward cohort continuation freeze packet

This document is also outside the accepted Phase 1A normative control spine.
It is the actual frozen contract that governed the bounded Gate C quantitative associated/cohort shaping and pass-entry lane now landed on current `main`:
- `07_GATEC_COHORT_FREEZE.md`

### Post-Phase 1A carried-forward Gate D package freeze packet

This document is also outside the accepted Phase 1A normative control spine.
It is the actual frozen contract that governed the bounded Gate D package-entry slice now landed on current `main`, and it does not itself imply that packaging or consumer routes beyond that slice have already landed:
- `08_GATED_PACKAGE_FREEZE.md`

### Post-Phase 1A carried-forward APS handoff freeze packet

This document is also outside the accepted Phase 1A normative control spine.
It is the narrow frozen contract that governed the bounded APS evidence-bundle-family adapter/handoff slice now landed on current `main`, and it does not itself imply that broader APS fan-out, route/UI surfaces, or consumer routes beyond that slice have already landed:
- `09_GATED_APS_HANDOFF_FREEZE.md`

### Post-Phase 1A carried-forward APS citation continuation freeze packet

This document is also outside the accepted Phase 1A normative control spine.
It is the narrow frozen contract that governed the bounded citation-pack-family handoff slice now landed on current `main` after the already-landed evidence-bundle slice, and it does not itself imply that report/context/deterministic families or route/UI surfaces have already landed:
- `10_GATED_APS_CITATION_FREEZE.md`

Rule:
- if a rule exists only in an operational companion doc, move or restate it in the normative control spine before relying on it as durable control guidance

### Post-Phase 1A carried-forward APS report continuation freeze packet

This document is also outside the accepted Phase 1A normative control spine.
It is the narrow frozen contract that governed the bounded evidence-report-family continuation slice now landed on current `main` beyond the already-landed citation-pack slice, and it does not itself imply that export/context/deterministic families or route/UI surfaces have already landed:
- `11_GATED_APS_REPORT_FREEZE.md`

### Post-Phase 1A carried-forward APS report-export continuation freeze packet

This document is also outside the accepted Phase 1A normative control spine.
It is the narrow frozen contract that governs the bounded evidence-report-export-family continuation slice now landed on current `main` beyond the already-landed evidence-report slice, and it does not itself imply that evidence-report-export-package, context, deterministic, or route/UI surfaces have already landed:
- `12_GATED_APS_REPORT_EXPORT_FREEZE.md`

### Post-Phase 1A carried-forward APS context continuation freeze packet

This document is also outside the accepted Phase 1A normative control spine.
It is the narrow frozen contract that governs the bounded export-derived context-packet continuation slice now landed on current `main` beyond the already-landed evidence-report-export slice, and it does not itself imply that export-package implementation, package-derived context, dossier, deterministic, or route/UI surfaces have already landed:
- `13_GATED_APS_CONTEXT_FREEZE.md`

### Post-Phase 1A carried-forward APS multisource continuation freeze packet

It is the narrow frozen contract that governs the bounded same-run shared-source admission slice now landed on current `main` beyond the already-landed export-derived context-packet slice, and it does not itself imply that direct export-package implementation, package-derived context, context-dossier, deterministic, or schema surfaces have already landed:
- `14_GATED_APS_MULTISOURCE_FREEZE.md`

### Post-Phase 1A carried-forward APS export-package first shared-consumer freeze packet

It is the narrow frozen contract that governs the now-landed read-only choice on current `main` of `evidence_report_export_package` as the first downstream shared APS family beyond the already-landed multisource slice, and it does not itself imply that export-package implementation, package-derived context, context-dossier, deterministic, or schema surfaces have already landed:
- `15_GATED_APS_EXPORT_PACKAGE_FREEZE.md`

### Post-Phase 1A carried-forward APS package-derived-context continuation freeze packet

This document is outside the accepted Phase 1A normative control spine.
It is the carried-forward read-only freeze now landed on current `main` that selects package-derived context packet as the next later shared APS family beyond the already-landed export-package boundary, and it does not itself imply that package-derived context implementation, `context_dossier`, deterministic, or schema surfaces have landed on current `main`:
- `16_GATED_APS_PACKAGE_CONTEXT_FREEZE.md`

### Post-Phase 1A carried-forward APS context-dossier continuation freeze packet

This document is outside the accepted Phase 1A normative control spine.
It is the carried-forward read-only freeze now landed on current `main` that selects `context_dossier` as the next later shared APS family beyond the already-landed package-context boundary while preserving paired export-derived context packets as dossier inputs, and it does not itself imply that deterministic, review-packet, or schema surfaces have landed on current `main`:
- `17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md`

### Post-Phase 1A carried-forward APS deterministic-insight continuation freeze packet

This document is outside the accepted Phase 1A normative control spine.
It is the now-landed read-only freeze on current `main` that selects `deterministic_insight_artifact` as the first deterministic continuation beyond the already-landed dossier boundary, and it does not itself imply that deterministic implementation, challenge/review-packet fan-out, or schema surfaces have landed on current `main`:
- `18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md`

### Post-Phase 1A carried-forward APS deterministic-challenge continuation freeze packet

This document is outside the accepted Phase 1A normative control spine.
It is the now-landed read-only freeze on current `main` that selects `deterministic_challenge_artifact` as the next deterministic continuation beyond the already-landed deterministic-insight boundary, and it does not itself imply that review-packet, validate-only, or schema surfaces have landed on current `main`:
- `19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE.md`

### Post-Phase 1A carried-forward APS review-packet continuation freeze packet

This document is outside the accepted Phase 1A normative control spine.
It is the now-landed read-only freeze on current `main` that selects the bounded deterministic challenge review-packet continuation beyond the already-landed deterministic challenge boundary, and it does not itself imply that validate-only, route/UI, or schema surfaces have landed on current `main`:
- `20_GATED_APS_REVIEW_PACKET_FREEZE.md`

### Post-Phase 1A carried-forward APS validate-only gates continuation freeze packet

This document is outside the accepted Phase 1A normative control spine.
It is the now-landed read-only freeze on current `main` that selects the bounded `validate_only_gates` continuation beyond the already-landed review-packet boundary, and it does not itself imply that validate-only runtime/report-ref, route/UI, or schema surfaces have landed on current `main`:
- `21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md`

### Post-Phase 1A carried-forward APS validate-only runtime continuation freeze packet

This document is outside the accepted Phase 1A normative control spine.
It is the now-landed read-only freeze on current `main` that selects the bounded dedicated validate-only runtime/report-ref continuation beyond the already-landed `validate_only_gates` boundary, and it does not itself imply that promotion, retrieval cutover, route/UI, or schema surfaces have landed on current `main`:
- `22_GATED_APS_VALIDATE_ONLY_RUNTIME_FREEZE.md`

### Post-Phase 1A carried-forward APS promotion settlement freeze packet

This document is outside the accepted Phase 1A normative control spine.
It is the now-landed read-only freeze on current `main` that selected promotion as the first later APS family beyond the dedicated validate-only runtime/report-ref boundary before the later APS family packet was settled, and it does not itself imply that broader deferred-scope Layer3 work, runtime DB writes, or schema widening have landed on current `main`:
- `23_GATED_APS_PROMOTION_FREEZE.md`

### Post-settlement broader workbench planning-only freeze doc

This document is outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
It is the merged planning-only prep doc on current `main` for the deferred `future workbench route family`, and it does not itself activate that lane, reopen the settled packet, or imply route/UI, runtime DB, schema, or shared-contract widening:
- `24_L3_WB_FREEZE.md`

### Post-settlement broader workbench exact-input prep doc

This document is outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
It is the merged planning-only companion prep doc on current `main` for the deferred `future workbench route family`, and it now records the adopted planning-only operator-insufficiency trigger, additive route-family choice, and minimum typing posture plus the exact owner-surface map, proof matrix, and remains-out list that keep a later implementation-entry packet narrow without implying activation:
- `26_L3_WB_INPUTS.md`

### Broader workbench first-slice setup freeze doc

This document is outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
It is the merged first-slice setup doc from PR `#178` for the `future workbench route family`; it narrowed the later additive `/review/layer3` plus `/api/v1/layer3/...` implementation-entry target through Gate C typing review before PR `#184` implemented that bounded first slice. It remains the governing scope/no-go contract and does not activate downstream execution, package review, qualitative, hybrid, RAG/vector, runtime snapshot DB write, schema, or handoff scope:
- `28_L3_WB_FIRST_SLICE_FREEZE.md`

### Broader workbench first-slice API/state contract

This document is outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
It is the merged API/state companion from PR `#182` for the `future workbench route family`; it froze endpoint, DTO, Gate B persistence, Gate C override, authority-rail, browser-state, and proof expectations for the later PR `#184` `/review/layer3` plus `/api/v1/layer3/...` implementation pass. It remains the governing API/state contract and does not change the no-go list:
- `29_L3_WB_FIRST_SLICE_API_AND_STATE_CONTRACT.md`

### Broader workbench second-slice plan-preview freeze docs

These documents are outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
They were merged as planning docs in PR `#191` and govern the PR `#194` workbench slice after the landed first-slice shell/API: a read-only plan-preview step after explicit Gate C typing commit. PR `#194` implements that bounded endpoint/UI state, while PRs `#195` and `#196` only record/align post-merge proof and board metadata. None of these activate execution, results, package review, handoff, qualitative/hybrid/RAG/vector execution, runtime snapshot DB writes, schema widening, or broader route/UI scope:
- `30_L3_WB_PLAN_PREVIEW_FREEZE.md`
- `31_L3_WB_PLAN_PREVIEW_API_AND_STATE_CONTRACT.md`

### Broader workbench third-slice plan-approval freeze docs

These documents are outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
They were merged as planning docs in PR `#198` and freeze the third workbench slice after read-only plan preview: operator approval and durable formation of an approved owner-service plan, without pass-run creation, analysis execution, results review, package review, handoff, runtime snapshot DB writes, schema widening, qualitative/hybrid/RAG/vector execution, hidden LLM planning, or broader route/UI scope. PR `#199` implements only that approval-only persistence boundary:
- `32_L3_WB_PLAN_APPROVAL_FREEZE.md`
- `33_L3_WB_PLAN_APPROVAL_API_AND_STATE_CONTRACT.md`

### Broader workbench fourth-slice plan-revision freeze docs

These documents are outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
PR `#203` freezes the fourth workbench slice as planning-only governance for explicit operator rejection and revision-request semantics against the current server-backed plan preview before approval, and PR `#204` corrects the associated deferred-scope count metadata. These docs govern the PR `#205` implementation and the PR `#207` submission-hardening follow-up; PR `#206` records the post-PR205 docs/control state, and PRs `#208`/`#209`/`#210`/`#211` record post-hardening docs/progress cohesion only. None of these docs-only or hardening follow-ups reopen or supersede already approved plans, call `materialize_pass_entry(...)`, create `L3PassRun`, run analysis, write manifests, enable results/package/handoff, widen runtime DB/schema behavior, or admit qualitative/hybrid/RAG/vector/LLM planning:
- `34_L3_WB_PLAN_REVISION_FREEZE.md`
- `35_L3_WB_PLAN_REVISION_API_AND_STATE_CONTRACT.md`

### Broader workbench first-slice through analysis-execution-start implementation

This implementation is outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
It is the bounded first-slice workbench implementation from PR `#184`, with post-implementation status/cohesion/explicit-Gate-C-typing/review-feedback closeouts through PR `#190`; PR `#194` then adds read-only plan preview after explicit Gate C typing commit, PRs `#195`/`#196` record proof/board metadata for that state, PR `#198` freezes plan approval, PR `#199` adds approval-only `L3AnalysisPlan` persistence, PR `#205` adds pre-approval plan-revision control, PR `#207` hardens revision submission with serialized backend decision writes and shared UI in-flight locking, PR `#213` adds read-only readiness proof, PR `#216` adds bounded execution-selection/pass-run shell creation only, PR `#217` adds adjacent planning-only analysis-execution-start governance, and PR `#218` implements that governance only as one selected-pass wrapped quantitative execution-start boundary. PR `#206` and PRs `#208`/`#209`/`#210`/`#211` are docs/control or docs/progress cohesion syncs for that same bounded revision state, not new functional slices. Together they make `/review/layer3` and `/api/v1/layer3/...` live only for intent/preflight, deterministic source preview, material preview, Gate B decision recording, Gate C UI non-authoritative typing preview, explicit API owner-service typing materialization when `commit_typing` is true, explicit Gate C override unavailability, session summary, read-only plan preview, approval-only plan persistence, revision-control for the current server-backed preview before approval, read-only readiness proof, selected/not-started `L3PassRun` shell creation from an approved, hash-matched plan, and one selected-pass wrapped quantitative analysis-execution-start:
- `backend/main.py`
- `backend/app/api/router.py`
- `backend/app/api/layer3.py`
- `backend/app/services/layer3_workbench.py`
- `backend/app/services/layer3_pass_entry.py`
- `backend/app/review_ui/static/layer3.html`
- `backend/app/review_ui/static/layer3.css`
- `backend/app/review_ui/static/layer3.js`
- `backend/tests/test_layer3_workbench.py`
- `backend/tests/test_layer3_api.py`
- `backend/tests/test_layer3_page.py`
- `backend/tests/test_layer3_pass_entry.py`
- `e2e/layer3-workbench.spec.js`

### Broader workbench analysis-execution-start planning-only freeze docs

These documents are outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
PR `#217` freezes the next eligible implementation boundary after PR `#216` as one selected-pass-run wrapped quantitative execution start from an existing selected/not-started `L3PassRun` shell. These docs did not make analysis execution live by themselves, and they remain the governing scope contract for the PR `#218` bounded implementation. They do not admit `materialize_pass_entry(...)` as-is, new plan/pass-run shell creation, batch execution, result/package/handoff, approved-plan supersession, runtime DB/schema widening, source expansion, UI change, qualitative/hybrid/RAG/vector execution, or full mockup activation:
- `40_L3_WB_ANALYSIS_EXECUTION_START_FREEZE.md`
- `41_L3_WB_ANALYSIS_EXECUTION_START_API_AND_STATE_CONTRACT.md`

### Broader workbench result/status planning-only freeze docs

These documents are outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
They freeze the next eligible implementation boundary after merged PR `#218` as read-only selected-pass result/status inspection. They do not make result/status inspection live by themselves and do not admit result review, result approval/rejection, package review, handoff, rerun/recovery, approved-plan supersession, runtime DB/schema widening, source expansion, UI change, qualitative/hybrid/RAG/vector execution, or full mockup activation:
- `42_L3_WB_RESULT_STATUS_FREEZE.md`
- `43_L3_WB_RESULT_STATUS_API_AND_STATE_CONTRACT.md`

### Broader workbench result-review planning-only freeze docs

These documents are outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
They freeze the next eligible planning boundary after merged PR `#222` as one bounded selected-pass result-review decision. They do not make result review live by themselves and do not admit package review, handoff/export, rerun/recovery, approved-plan supersession, runtime DB/schema widening, source expansion, UI change by itself, qualitative/hybrid/RAG/vector execution, local upload/directory ingestion, or full mockup activation:
- `44_L3_WB_RESULT_REVIEW_FREEZE.md`
- `45_L3_WB_RESULT_REVIEW_API_AND_STATE_CONTRACT.md`

### Selected-pass associated-cohort result-review planning docs

These documents are outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
They freeze a planning boundary after merged PR `#432` as one bounded result-review decision for an exact selected-pass associated-cohort `descriptive_summary` terminal output. They do not make associated-cohort result review live by themselves; PR `#438` separately implements only the bounded backend/API result-review path. They do not admit UI, package review, handoff/export, rerun/recovery, source/schema/runtime widening, connector dispatch, qualitative/hybrid/RAG/vector execution, or full mockup activation:
- `82_COHORT_RESULT_REVIEW_FREEZE.md`
- `83_COHORT_RESULT_REVIEW_CONTRACT.md`

### Broader workbench result-review UI freeze docs and bounded implementation

These documents are outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
They freeze the `/review/layer3` result-review presentation and bounded UI control surface after the merged PR `#227` backend result-review endpoint. They do not make UI behavior live by themselves; PR `#232` is the later bounded implementation that makes only session refresh, selected-pass result/status inspection, and one result-review submission live. Neither the docs nor PR `#232` admit execution selection/start UI, package review, handoff/export, rerun/recovery, new backend endpoints by default, runtime DB/schema widening, source expansion, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, or full mockup activation:
- `46_L3_WB_RESULT_REVIEW_UI_FREEZE.md`
- `47_L3_WB_RESULT_REVIEW_UI_STATE_CONTRACT.md`

### Broader workbench package-review preview planning-only freeze docs

These documents are outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
They freeze the next eligible planning boundary after merged PR `#232` as read-only package-review readiness/preview after an approved selected-pass result review. PR `#234` makes that governance current-main planning/control state, and PR `#235` implements only the bounded read-only preview. Neither the docs nor PR `#235` make package review submission, package construction, `L3OutputPackage` or `L3ReconciliationRecord` creation, `materialize_package_entry(...)` as-is admission, package payload writes, handoff/export, rerun/recovery, approved-plan supersession, runtime DB/schema widening, source expansion, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, or full mockup activation live:
- `48_L3_WB_PACKAGE_REVIEW_FREEZE.md`
- `49_L3_WB_PACKAGE_REVIEW_API_AND_STATE_CONTRACT.md`

### Broader workbench package-construction freeze docs and implementation

These documents are outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
They freeze the next eligible boundary after merged PR `#235` as package construction only, not package-review submission or handoff. The admitted write set is limited to one `L3ReconciliationRecord`, three `L3OutputPackage` rows, and three package payload files for `canonical_internal`, `user_facing`, and `review_facing`, using a workbench-compatible owner-service helper rather than calling `materialize_package_entry(...)` as-is from `/review/layer3`. PR `#238` implements only that backend commit boundary and still does not admit package-review submit/decision state, handoff/export, result-review amendment, approved-plan supersession, source/schema/runtime widening, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, new UI code or package-creation controls, or full mockup activation. The existing package-preview panel reflects the new backend state by no longer listing package commit as disabled:
- `50_L3_WB_PACKAGE_CONSTRUCTION_FREEZE.md`
- `51_L3_WB_PACKAGE_CONSTRUCTION_API_AND_STATE_CONTRACT.md`

### Broader workbench package-review submit planning-only freeze docs

These documents are outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
PR `#241` freezes the next eligible planning boundary after merged PR `#238` as package-review submit/decision state only, not handoff/export or package reconstruction. The admitted future write set is limited to one operator package-review decision object over the already constructed package set, preferably in existing `L3ReconciliationRecord.summary_json` plus an optional `L3Session.summary_json` pointer if no schema widening is required. It does not make package-review submission live by itself and does not admit package payload mutation, additional package/reconciliation rows, `AnalysisArtifact` creation, handoff/export, result-review amendment, approved-plan supersession, source/schema/runtime widening, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, package rebuild/amendment after changes requested, new UI code by docs alone, or full mockup activation. PR `#243` implements the bounded backend submit endpoint/state on current `main`; PR `#245` is the separate merged bounded rendered-control implementation over that endpoint; PR `#247` hardens stale-refresh fallback behavior without widening the rendered-control boundary:
- `52_L3_WB_PACKAGE_REVIEW_SUBMIT_FREEZE.md`
- `53_L3_WB_PACKAGE_REVIEW_SUBMIT_API_AND_STATE_CONTRACT.md`

### Broader workbench handoff/export preparation governance and backend implementation

These documents are outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
PR `#250` freezes the next eligible planning boundary after merged package-review submit approval as internal handoff/export preparation only. PR `#251` implements that boundary as a backend/API-only `prepare_only` endpoint over existing JSON-bearing workbench state, and PR `#252` hardens blocker vocabulary plus active package-substate session-summary priority. The live boundary keeps external handoff/export/dispatch disabled, does not dispatch to APS, does not export externally, does not create physical export files, does not create `AnalysisArtifact` rows, does not create or mutate package rows or payloads, does not rebuild packages, does not render handoff/export controls, does not widen source/schema/runtime scope, and does not activate the full mockup target state:
- `54_L3_WB_HANDOFF_EXPORT_FREEZE.md`
- `55_L3_WB_HANDOFF_EXPORT_API_AND_STATE_CONTRACT.md`

### Broader workbench handoff/export preparation UI governance and implementation

These documents are outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
They freeze only the rendered `/review/layer3` presentation/control boundary over the already-live backend prepare-only endpoint from PR `#251`/`#252`. By themselves they do not make UI behavior live or change backend behavior. PR `#256` is the separate bounded implementation that renders one server-gated prepare-only decision form and read-only recorded-state presentation; it still does not admit APS handoff, external export/download, downstream dispatch, destination selection, physical export artifacts, `AnalysisArtifact`, package payload mutation, package reconstruction, source/schema/runtime widening, execution selection/start UI expansion, qualitative/hybrid/RAG/vector behavior, or full mockup activation:
- `56_L3_WB_HANDOFF_EXPORT_UI_FREEZE.md`
- `57_L3_WB_HANDOFF_EXPORT_UI_STATE_CONTRACT.md`

### Broader workbench APS handoff dispatch governance and UI planning

These documents are outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
Docs `58`/`59` govern the backend/API APS handoff dispatch bridge into the existing `aps_evidence_bundle_handoff` owner-service family; PR `#260` implements that endpoint, with PR `#261`/`#263` hardening the fail-closed authority boundary. Docs `60`/`61` freeze only the rendered `/review/layer3` presentation/control boundary over that already-live endpoint, and PR `#266` separately implements that bounded rendered UI. By themselves docs `60`/`61` do not render APS dispatch controls, change backend behavior, admit external export/download, connector dispatch, destination selection, package mutation/reconstruction, additional reconciliation rows, `AnalysisArtifact`, source/schema/runtime widening, execution selection/start UI expansion, qualitative/hybrid/RAG/vector behavior, or full mockup activation:
- `58_L3_WB_APS_HANDOFF_DISPATCH_FREEZE.md`
- `59_L3_WB_APS_HANDOFF_DISPATCH_API_AND_STATE_CONTRACT.md`
- `60_L3_WB_APS_HANDOFF_DISPATCH_UI_FREEZE.md`
- `61_L3_WB_APS_HANDOFF_DISPATCH_UI_STATE_CONTRACT.md`

### Broader workbench mockup source mirror

These files are outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
They mirror the text mockup/spec artifact and record the local visual asset hashes that informed the first-slice setup doc. They are planning input only; they do not make the visual assets implementation dependencies or override current repo truth:
- `layer3-mockups/mockup-spec.txt`
- `layer3-mockups/assets.md`

### Post-settlement qualitative single-item planning-only freeze doc

This document is outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
It is the merged planning-only prep doc on current `main` for the deferred qualitative single-item breadth axis, and it does not itself activate that lane, reopen the settled packet, or imply route/UI, runtime DB, schema, or shared-contract widening:
- `25_L3_QUAL1_FREEZE.md`

### Merged qualitative single-item exact-input prep doc

This is the merged planning-only companion prep doc on current `main` for the deferred qualitative single-item breadth axis.
It remains planning-only, does not itself activate the lane, and must not be described as a merged milestone, packet-reopen signal, or active lane:
- `27_L3_QUAL1_INPUTS.md`

## Current use guidance

### If you are auditing scope

Start with:
- `01_IMPLEMENTATION_ENTRY_BASELINE_REV2.md`
- `04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md`
- `10_PHASE1A_POSTCODE_ACCEPTANCE_AUDIT.md`

### If you are checking whether the lane is closed enough to review

Start with:
- `10_PHASE1A_POSTCODE_ACCEPTANCE_AUDIT.md`
- `11_PHASE1A_RECONCILIATION_CHECKLIST.md`
- `12_PHASE1A_ROADMAP_AND_DECISION_NOTES.md`
- `13-phase1a-surface-map.md`

### If you need the concrete implementation surface map

Start with:
- `Layer3_execution_freeze/13-phase1a-surface-map.md`
- `Layer3_execution_handoff/06_PHASE1A_CODEWRITING_HANDOFF.md`
- the four code files from commit `0b0ecf7e`

### If you are deciding whether more Phase 1A code work is justified

Start with:
- `10_PHASE1A_POSTCODE_ACCEPTANCE_AUDIT.md`
- the committed code diff at `0b0ecf7e`

Current answer:
- no additional Phase 1A code work is justified by default from the current lane state

### If you are deciding what must happen before broader Gate C continuation is allowed

Start with:
- `Layer3_planning_docs/04_GATEC_ENTRY_FREEZE.md`
- `Layer3_planning_docs/05_GATEC_IMPLEMENTATION_FREEZE.md`
- `Layer3_planning_docs/06_GATEC_PASS_FREEZE.md`
- `Layer3_planning_docs/07_GATEC_COHORT_FREEZE.md`
- `Layer3_execution_freeze/13-phase1a-surface-map.md`
- `docs/analyst_insight/analyst_insight_status_handoff.md`
- `docs/nrc_adams/nrc_aps_status_handoff.md`

### If you are deciding what must happen before bounded Gate D packaging continuation is allowed

Start with:
- `Layer3_planning_docs/07_GATEC_COHORT_FREEZE.md`
- `Layer3_planning_docs/08_GATED_PACKAGE_FREEZE.md`
- `Layer3_execution_freeze/13-phase1a-surface-map.md`
- `docs/analyst_insight/analyst_insight_status_handoff.md`
- `docs/nrc_adams/nrc_aps_status_handoff.md`

### If you are deciding what must happen before bounded later APS-family continuation is allowed

Start with:
- `Layer3_planning_docs/20_GATED_APS_REVIEW_PACKET_FREEZE.md`
- `Layer3_planning_docs/21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md`
- `Layer3_planning_docs/22_GATED_APS_VALIDATE_ONLY_RUNTIME_FREEZE.md`
- `Layer3_planning_docs/23_GATED_APS_PROMOTION_FREEZE.md`
- `next_milestone_plans/layer3_progress_board.md`
- `next_milestone_plans/layer3_progress_manifest.json`
- `docs/nrc_adams/nrc_aps_status_handoff.md`

Current answer:
- no further later APS-family decision or implementation lane is justified by default from current `main`

### If you are deciding what deferred broader Layer3 planning-only prep now exists on current `main`

Start with:
- `Layer3_planning_docs/24_L3_WB_FREEZE.md`
- `Layer3_planning_docs/26_L3_WB_INPUTS.md`
- `Layer3_planning_docs/28_L3_WB_FIRST_SLICE_FREEZE.md`
- `Layer3_planning_docs/29_L3_WB_FIRST_SLICE_API_AND_STATE_CONTRACT.md`
- `Layer3_planning_docs/25_L3_QUAL1_FREEZE.md`
- `Layer3_planning_docs/27_L3_QUAL1_INPUTS.md`
- `next_milestone_plans/layer3_progress_board.md`
- `next_milestone_plans/layer3_progress_manifest.json`
- `docs/nrc_adams/nrc_aps_status_handoff.md`

### If you are deciding the first Layer 3 workbench implementation slice

Start with:
- `Layer3_planning_docs/24_L3_WB_FREEZE.md`
- `Layer3_planning_docs/26_L3_WB_INPUTS.md`
- `Layer3_planning_docs/28_L3_WB_FIRST_SLICE_FREEZE.md`
- `Layer3_planning_docs/29_L3_WB_FIRST_SLICE_API_AND_STATE_CONTRACT.md`
- `next_milestone_plans/layer3_progress_board.md`
- `next_milestone_plans/layer3_progress_manifest.json`

Current answer:
- first-slice setup and API/state contract docs were planning-only when PR `#178` and PR `#182` landed, but PR `#184` now implements that bounded first slice on current `main`, with closeout/correction passes through PR `#190`
- the live first-slice surface is an additive `/review/layer3` page plus `/api/v1/layer3/...` API family
- the live first implementation stops at intent/preflight, deterministic source selection, material preview, Gate B material review, Gate C UI non-authoritative typing preview, explicit API owner-service typing materialization when `commit_typing` is true, explicit Gate C override unavailability, and session summary
- the implementation uses `29_L3_WB_FIRST_SLICE_API_AND_STATE_CONTRACT.md` as the endpoint, DTO, state, persistence, browser-state, and proof contract
- downstream plan, execution, results, package review, qualitative, hybrid, RAG/vector, runtime snapshot DB writes, schema widening, and handoff remain unavailable unless separately activated

### If you are deciding the second Layer 3 workbench implementation slice

Start with:
- `Layer3_planning_docs/30_L3_WB_PLAN_PREVIEW_FREEZE.md`
- `Layer3_planning_docs/31_L3_WB_PLAN_PREVIEW_API_AND_STATE_CONTRACT.md`
- `Layer3_planning_docs/26_L3_WB_INPUTS.md`
- `backend/app/services/layer3_pass_entry.py`
- `backend/app/services/layer3_workbench.py`
- `backend/tests/test_layer3_pass_entry.py`
- `backend/tests/test_layer3_workbench.py`
- `backend/tests/test_layer3_api.py`
- `e2e/layer3-workbench.spec.js`

Current answer:
- the next adequate implementation slice after the landed first-slice shell/API was read-only plan preview after explicit Gate C typing commit; PR `#194` implements that slice, and PRs `#195`/`#196` only record post-merge proof/board metadata for it
- plan preview composes around the landed pass-entry owner service through a read-only helper rather than duplicating pass-entry classification in route or browser code
- execution, results, package review, handoff, qualitative/hybrid/RAG/vector execution, runtime snapshot DB writes, schema widening, and hidden LLM planning remain out of scope

### If you are auditing the third Layer 3 workbench implementation slice

Start with:
- `Layer3_planning_docs/32_L3_WB_PLAN_APPROVAL_FREEZE.md`
- `Layer3_planning_docs/33_L3_WB_PLAN_APPROVAL_API_AND_STATE_CONTRACT.md`
- `Layer3_planning_docs/30_L3_WB_PLAN_PREVIEW_FREEZE.md`
- `Layer3_planning_docs/31_L3_WB_PLAN_PREVIEW_API_AND_STATE_CONTRACT.md`
- `backend/app/services/layer3_pass_entry.py`
- `backend/app/services/layer3_workbench.py`
- `backend/tests/test_layer3_pass_entry.py`
- `backend/tests/test_layer3_workbench.py`
- `backend/tests/test_layer3_api.py`
- `e2e/layer3-workbench.spec.js`

Current answer:
- PR `#199` already implements operator plan approval plus durable `L3AnalysisPlan` formation only
- the existing `materialize_pass_entry(...)` helper remains execution-bearing and must not be called by the approval path
- the implementation uses a narrower owner-service helper that persists the approved plan without creating `L3PassRun`, running analysis, writing manifests, changing package/handoff state, adding migrations, or widening schema
- execution, results review, package review, handoff, qualitative/hybrid/RAG/vector execution, runtime snapshot DB writes, schema widening, and hidden LLM planning remain out of scope

PR `#199` is the bounded implementation lane for that third slice. It makes only approval-only plan persistence live through `/api/v1/layer3/plan/approve` and the existing `/review/layer3` plan panel; it still does not admit `L3PassRun`, analysis execution, result review, package review, handoff, runtime snapshot DB writes, schema widening, qualitative/hybrid/RAG/vector execution, or hidden LLM planning.

PRs `#200`, `#201`, and `#202` are post-approval docs/control syncs. They keep approval-state, mockup-spec, and workbench progress-control surfaces aligned without making execution, results/package/handoff, runtime DB/schema widening, or qualitative/hybrid/RAG/vector/LLM planning live.

### If you are auditing the fourth Layer 3 workbench revision-control slice

Start with:
- `Layer3_planning_docs/34_L3_WB_PLAN_REVISION_FREEZE.md`
- `Layer3_planning_docs/35_L3_WB_PLAN_REVISION_API_AND_STATE_CONTRACT.md`
- `Layer3_planning_docs/32_L3_WB_PLAN_APPROVAL_FREEZE.md`
- `Layer3_planning_docs/33_L3_WB_PLAN_APPROVAL_API_AND_STATE_CONTRACT.md`
- `backend/app/services/layer3_pass_entry.py`
- `backend/app/services/layer3_workbench.py`
- `backend/tests/test_layer3_api.py`
- `e2e/layer3-workbench.spec.js`

Current answer:
- the fourth slice is now live only as bounded revision-control through PR `#205`, with PR `#207` hardening the same bounded behavior rather than adding a new functional slice; PR `#206` and PRs `#208`/`#209`/`#210`/`#211` are docs/control or docs/progress cohesion syncs only
- it admits explicit operator rejection and revision request against the current server-backed preview before approval
- already approved plans remain terminal for this slice; reopening, replacing, or superseding them requires a later freeze
- execution, results review, package review, handoff, qualitative/hybrid/RAG/vector execution, runtime snapshot DB writes, schema widening, and hidden LLM planning remain out of scope

Merged PR `#218` makes only one selected-pass wrapped quantitative analysis-execution-start boundary live after PR `#216` execution-selection shell creation. It still does not make broad analysis execution, result review, package review, handoff, approved-plan supersession, runtime DB/schema widening, source expansion, UI/full-mockup activation, or qualitative/hybrid/RAG/vector/LLM planning live. PR `#221` docs `42`/`43` freeze the result/status boundary as planning-only read-only result/status inspection for one terminal selected pass, and PR `#222` implements that boundary as read-only backend behavior only. Docs `44`/`45` now freeze the next planning boundary as selected-pass result review only; they do not make result review, package review, or handoff live by themselves.

### If you are auditing the Layer 3 workbench execution-readiness packet

Start with:
- `Layer3_planning_docs/36_L3_WB_EXECUTION_READINESS_FREEZE.md`
- `Layer3_planning_docs/37_L3_WB_STATE_HASH_IDEMPOTENCY_CONTRACT.md`
- `next_milestone_plans/layer3_workbench_proof_manifest.json`
- `Layer3_planning_docs/34_L3_WB_PLAN_REVISION_FREEZE.md`
- `Layer3_planning_docs/35_L3_WB_PLAN_REVISION_API_AND_STATE_CONTRACT.md`
- `next_milestone_plans/layer3_progress_board.md`
- `next_milestone_plans/layer3_progress_manifest.json`
- `docs/nrc_adams/nrc_aps_status_handoff.md`

Current answer:
- PR `#212` landed this packet as execution-readiness planning only
- it adds proof/readiness, state, preview-hash, idempotency, concurrency, revision-recovery, approved-plan-correction, output-taxonomy, and source-breadth gates before any later execution branch
- by itself it does not make execution selection, `L3PassRun`, analysis execution, results/package/handoff, approved-plan supersession, runtime DB/schema widening, qualitative/hybrid/RAG/vector execution, local upload ingestion, or full mockup activation live
- PR `#213` adds only read-only readiness proof around that packet, including `/api/v1/layer3/readiness`, plan-preview identity/hash metadata, and approval/revision serialization checks
- PR `#216` is the separate later implementation that uses the readiness/hash/idempotency constraints to create selected/not-started `L3PassRun` shell rows only; it still does not start analysis or write downstream artifacts
- browser proof is not required for a backend-only readiness metadata slice because no rendered UI behavior changes, but any future UI or execution slice must run headed and headless browser proof when browser behavior changes

### If you are auditing the Layer 3 workbench execution-selection freeze packet

Start with:
- `Layer3_planning_docs/38_L3_WB_EXECUTION_SELECTION_FREEZE.md`
- `Layer3_planning_docs/39_L3_WB_EXECUTION_SELECTION_API_AND_STATE_CONTRACT.md`
- `Layer3_planning_docs/36_L3_WB_EXECUTION_READINESS_FREEZE.md`
- `Layer3_planning_docs/37_L3_WB_STATE_HASH_IDEMPOTENCY_CONTRACT.md`
- `next_milestone_plans/layer3_progress_board.md`
- `next_milestone_plans/layer3_progress_manifest.json`
- `docs/nrc_adams/nrc_aps_status_handoff.md`

Current answer:
- PR `#215` lands this packet as planning-only
- it selects an execution-selection/pass-run shell boundary, not analysis execution
- PR `#216` implements that boundary through `POST /api/v1/layer3/execution/select`; it creates selected/not-started `L3PassRun` shell rows only after approved-plan and preview-hash validation
- it does not admit `AnalysisRun`, analysis execution, result/package/handoff artifacts, approved-plan supersession, runtime DB/schema widening, source-breadth expansion, UI changes, or full mockup activation
- browser proof is required only if a later implementation changes rendered UI behavior

### If you are auditing the Layer 3 workbench analysis-execution-start freeze packet

Start with:
- `Layer3_planning_docs/40_L3_WB_ANALYSIS_EXECUTION_START_FREEZE.md`
- `Layer3_planning_docs/41_L3_WB_ANALYSIS_EXECUTION_START_API_AND_STATE_CONTRACT.md`
- `Layer3_planning_docs/38_L3_WB_EXECUTION_SELECTION_FREEZE.md`
- `Layer3_planning_docs/39_L3_WB_EXECUTION_SELECTION_API_AND_STATE_CONTRACT.md`
- `next_milestone_plans/layer3_workbench_proof_manifest.json`
- `next_milestone_plans/layer3_progress_board.md`
- `next_milestone_plans/layer3_progress_manifest.json`
- `docs/nrc_adams/nrc_aps_status_handoff.md`

Current answer:
- PR `#217` lands this packet as planning-only
- it selects one selected-pass-run wrapped quantitative execution-start boundary, not broad execution
- it starts from PR `#216` selected/not-started `L3PassRun` shells, and PR `#218` is the later bounded implementation that creates exactly one wrapped quantitative `AnalysisRun` for one existing selected pass
- it does not admit result/package/handoff artifacts, approved-plan supersession, runtime DB/schema widening, source-breadth expansion, UI changes, qualitative/hybrid/RAG/vector execution, or full mockup activation
- browser proof is required only if a later implementation changes rendered UI behavior

### If you are auditing the Layer 3 workbench result/status freeze packet

Start with:
- `Layer3_planning_docs/42_L3_WB_RESULT_STATUS_FREEZE.md`
- `Layer3_planning_docs/43_L3_WB_RESULT_STATUS_API_AND_STATE_CONTRACT.md`
- `Layer3_planning_docs/40_L3_WB_ANALYSIS_EXECUTION_START_FREEZE.md`
- `Layer3_planning_docs/41_L3_WB_ANALYSIS_EXECUTION_START_API_AND_STATE_CONTRACT.md`
- `next_milestone_plans/layer3_workbench_proof_manifest.json`
- `next_milestone_plans/layer3_progress_board.md`
- `next_milestone_plans/layer3_progress_manifest.json`
- `docs/nrc_adams/nrc_aps_status_handoff.md`

Current answer:
- PR `#221` docs `42`/`43` are planning-only result/status governance after merged PR `#218`
- they select read-only selected-pass status and execution-proof inspection as the next eligible boundary, not result review
- they do not implement `/api/v1/layer3/execution/result/status` by themselves
- they do not admit result approval/rejection, package review, handoff, rerun/recovery, runtime DB/schema widening, source-breadth expansion, UI changes, qualitative/hybrid/RAG/vector execution, or full mockup activation
- browser proof is required only if a later implementation changes rendered UI behavior

### If you are auditing the Layer 3 workbench result-review freeze packet

Start with:
- `Layer3_planning_docs/44_L3_WB_RESULT_REVIEW_FREEZE.md`
- `Layer3_planning_docs/45_L3_WB_RESULT_REVIEW_API_AND_STATE_CONTRACT.md`
- `Layer3_planning_docs/42_L3_WB_RESULT_STATUS_FREEZE.md`
- `Layer3_planning_docs/43_L3_WB_RESULT_STATUS_API_AND_STATE_CONTRACT.md`
- `next_milestone_plans/layer3_workbench_proof_manifest.json`
- `next_milestone_plans/layer3_progress_board.md`
- `next_milestone_plans/layer3_progress_manifest.json`
- `docs/nrc_adams/nrc_aps_status_handoff.md`

Current answer:
- docs `44`/`45` are planning-only result-review governance after merged PR `#222`
- they select one bounded operator review decision for one terminal selected pass that already satisfies result/status authority
- they do not implement `/api/v1/layer3/execution/result/review` by themselves
- they do not admit package review, handoff/export, rerun/recovery, runtime DB/schema widening, source-breadth expansion, UI changes by themselves, qualitative/hybrid/RAG/vector execution, local upload/directory ingestion, or full mockup activation
- browser proof is required only if a later implementation changes rendered UI behavior

### If you are auditing the Layer 3 workbench result-review UI packet after PR `#232`

Start with:
- `Layer3_planning_docs/46_L3_WB_RESULT_REVIEW_UI_FREEZE.md`
- `Layer3_planning_docs/47_L3_WB_RESULT_REVIEW_UI_STATE_CONTRACT.md`
- `Layer3_planning_docs/44_L3_WB_RESULT_REVIEW_FREEZE.md`
- `Layer3_planning_docs/45_L3_WB_RESULT_REVIEW_API_AND_STATE_CONTRACT.md`
- `next_milestone_plans/layer3_workbench_proof_manifest.json`
- `next_milestone_plans/layer3_progress_board.md`
- `next_milestone_plans/layer3_progress_manifest.json`
- `docs/nrc_adams/nrc_aps_status_handoff.md`

Read the docs as planning-only UI governance and PR `#232` as the separate bounded implementation:
- they start from current backend result-review behavior after PR `#227`
- they select only the bounded `/review/layer3` presentation/control boundary for server-authoritative selected-pass result/status and result-review state
- PR `#232` implements only that bounded UI behavior
- they do not admit execution selection/start UI, package review, handoff/export, rerun/recovery, new backend endpoints by default, runtime DB/schema widening, source-breadth expansion, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, or full mockup activation
- browser proof with both headed and headless Chrome is required when rendered UI behavior changes

### If you are auditing the package-review preview planning packet or PR `#235` implementation

Start with:
- `Layer3_planning_docs/48_L3_WB_PACKAGE_REVIEW_FREEZE.md`
- `Layer3_planning_docs/49_L3_WB_PACKAGE_REVIEW_API_AND_STATE_CONTRACT.md`
- `Layer3_planning_docs/46_L3_WB_RESULT_REVIEW_UI_FREEZE.md`
- `Layer3_planning_docs/47_L3_WB_RESULT_REVIEW_UI_STATE_CONTRACT.md`
- `Layer3_planning_docs/08_GATED_PACKAGE_FREEZE.md`
- `next_milestone_plans/layer3_workbench_proof_manifest.json`
- `next_milestone_plans/layer3_progress_board.md`
- `next_milestone_plans/layer3_progress_manifest.json`
- `docs/nrc_adams/nrc_aps_status_handoff.md`

Read the docs as planning-only package-review preview governance and PR `#235` as the separate bounded read-only implementation:
- current `main` after PR `#235` has docs `48`/`49` as planning/control and also has the read-only preview endpoint/UI implementation
- PR `#235` exposes only read-only package-review preview/readiness after approved selected-pass result review
- the implementation may inspect package candidate families and owner-service compatibility but must not call `materialize_package_entry(...)`
- it does not admit package construction, package-review submission, `L3OutputPackage`, `L3ReconciliationRecord`, `AnalysisArtifact`, package payload writes, handoff/export, rerun/recovery, runtime DB/schema widening, source-breadth expansion, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, execution selection/start UI, or full mockup activation
- browser proof with both headed and headless Chrome was required and passed because PR `#235` changes rendered `/review/layer3` behavior

### If you are auditing the package-construction packet or PR `#238` implementation

Start with:
- `Layer3_planning_docs/50_L3_WB_PACKAGE_CONSTRUCTION_FREEZE.md`
- `Layer3_planning_docs/51_L3_WB_PACKAGE_CONSTRUCTION_API_AND_STATE_CONTRACT.md`
- `Layer3_planning_docs/48_L3_WB_PACKAGE_REVIEW_FREEZE.md`
- `Layer3_planning_docs/49_L3_WB_PACKAGE_REVIEW_API_AND_STATE_CONTRACT.md`
- `Layer3_planning_docs/08_GATED_PACKAGE_FREEZE.md`
- `backend/app/services/layer3_package_entry.py`
- `backend/app/services/layer3_workbench.py`
- `backend/app/api/layer3.py`
- `backend/tests/test_layer3_api.py`
- `backend/tests/test_layer3_package_entry.py`
- `next_milestone_plans/layer3_workbench_proof_manifest.json`
- `next_milestone_plans/layer3_progress_board.md`
- `next_milestone_plans/layer3_progress_manifest.json`
- `docs/nrc_adams/nrc_aps_status_handoff.md`

Read docs `50`/`51` as package-construction governance and PR `#238` as the separate bounded backend implementation:
- the admitted construction write set is exactly one reconciliation row, three output-package rows, and three payload files
- package kinds remain exactly `canonical_internal`, `user_facing`, and `review_facing`
- PR `#238` keeps durable package payload construction inside the package owner-service boundary through a workbench-compatible helper
- PR `#238` must not call `materialize_package_entry(...)` as-is from `/review/layer3` by fabricating Gate D `phase1a_loading_closure` or `pass_entry`
- it does not admit package-review submission, package-review approval/rejection, handoff/export, `AnalysisArtifact` creation, new analysis plan/pass/run creation, result-review amendment, approved-plan supersession, source/schema/runtime widening, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, or full mockup activation

### If you are auditing the Layer 3 workbench package-review submit freeze or merged backend implementation

Start with:
- `Layer3_planning_docs/52_L3_WB_PACKAGE_REVIEW_SUBMIT_FREEZE.md`
- `Layer3_planning_docs/53_L3_WB_PACKAGE_REVIEW_SUBMIT_API_AND_STATE_CONTRACT.md`
- `Layer3_planning_docs/50_L3_WB_PACKAGE_CONSTRUCTION_FREEZE.md`
- `Layer3_planning_docs/51_L3_WB_PACKAGE_CONSTRUCTION_API_AND_STATE_CONTRACT.md`
- `backend/app/models/models.py`
- `backend/app/services/layer3_workbench.py`
- `backend/app/services/layer3_package_entry.py`
- `backend/app/api/layer3.py`
- `backend/tests/test_layer3_api.py`
- `backend/tests/test_layer3_package_entry.py`
- `next_milestone_plans/layer3_workbench_proof_manifest.json`
- `next_milestone_plans/layer3_progress_board.md`
- `next_milestone_plans/layer3_progress_manifest.json`
- `docs/nrc_adams/nrc_aps_status_handoff.md`

Read PR `#241` docs `52`/`53` as package-review submit/decision governance, and read PR `#243` as the separate bounded backend implementation:
- the admitted decision records one operator disposition over an already constructed package set
- package ids, package kinds, payload refs, and payload hashes must stay hash-stable and server-verified
- the preferred persistence boundary is existing JSON-bearing state; if a new model or migration is required, stop for a separate schema/persistence freeze
- approval does not enable handoff/export by itself
- `changes_requested` does not imply package rebuild/amendment by itself
- the docs do not make `/api/v1/layer3/package/review/submit` live by themselves; PR `#243` is the current-main backend implementation
- the merged backend implementation must create no additional package/reconciliation/artifact rows and must mutate no package rows, package payload refs, or package hashes
- it does not admit package reconstruction, package payload mutation, additional package/reconciliation rows, `AnalysisArtifact` creation, handoff/export, result-review amendment, approved-plan supersession, source/schema/runtime widening, local upload/directory ingestion, rendered UI changes, qualitative/hybrid/RAG/vector execution, or full mockup activation

### If you are auditing the Layer 3 workbench handoff/export preparation freeze

Start with:
- `Layer3_planning_docs/54_L3_WB_HANDOFF_EXPORT_FREEZE.md`
- `Layer3_planning_docs/55_L3_WB_HANDOFF_EXPORT_API_AND_STATE_CONTRACT.md`
- `Layer3_planning_docs/52_L3_WB_PACKAGE_REVIEW_SUBMIT_FREEZE.md`
- `Layer3_planning_docs/53_L3_WB_PACKAGE_REVIEW_SUBMIT_API_AND_STATE_CONTRACT.md`
- `backend/app/services/layer3_workbench.py`
- `backend/app/api/layer3.py`
- `backend/app/models/models.py`
- `backend/tests/test_layer3_api.py`
- `next_milestone_plans/layer3_workbench_proof_manifest.json`
- `next_milestone_plans/layer3_progress_manifest.json`
- `next_milestone_plans/layer3_progress_board.md`

Read docs `54`/`55` as planning-only preparation governance:
- package-review approval is necessary but not sufficient for external handoff/export
- the planned future endpoint is an internal `prepare_only` envelope, not APS dispatch or external export
- the preferred persistence boundary is existing JSON-bearing state; if physical export files, `AnalysisArtifact`, a new table/model, or a migration is required, stop for a separate persistence/artifact freeze
- it does not admit package payload mutation, package reconstruction, additional package/reconciliation rows, source/schema/runtime widening, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, APS dispatch, external export, or full mockup activation

### If you are auditing the Layer 3 workbench handoff/export preparation UI freeze

Start with:
- `Layer3_planning_docs/56_L3_WB_HANDOFF_EXPORT_UI_FREEZE.md`
- `Layer3_planning_docs/57_L3_WB_HANDOFF_EXPORT_UI_STATE_CONTRACT.md`
- `Layer3_planning_docs/54_L3_WB_HANDOFF_EXPORT_FREEZE.md`
- `Layer3_planning_docs/55_L3_WB_HANDOFF_EXPORT_API_AND_STATE_CONTRACT.md`
- `backend/app/services/layer3_workbench.py`
- `backend/app/api/layer3.py`
- `backend/app/review_ui/static/layer3.html`
- `backend/app/review_ui/static/layer3.css`
- `backend/app/review_ui/static/layer3.js`
- `backend/tests/test_layer3_api.py`
- `backend/tests/test_layer3_page.py`
- `e2e/layer3-workbench.spec.js`
- `next_milestone_plans/layer3_workbench_proof_manifest.json`
- `next_milestone_plans/layer3_progress_manifest.json`
- `next_milestone_plans/layer3_progress_board.md`

Read docs `56`/`57` as planning-only UI governance by themselves and PR `#256` as the separate bounded rendered UI implementation:
- they do not make rendered handoff/export controls live by themselves
- PR `#256` implements only bounded rendered prepare-only controls over server summary and `POST /api/v1/layer3/handoff/export/prepare` authority
- the UI may render one prepare-only decision form after `package_review_approved` and server-reported `handoff_export_prepare.available == true`
- headed and headless Chrome proof is required when a later implementation changes rendered `/review/layer3` behavior; PR `#256` supplied that proof
- they do not admit APS handoff, external export/download, downstream dispatch, physical artifacts, `AnalysisArtifact`, package payload mutation/reconstruction, source/schema/runtime widening, execution selection/start UI expansion, qualitative/hybrid/RAG/vector execution, or full mockup activation


### If you are auditing selected-pass associated-cohort handoff/export prepare UI proof

Start with:
- `Layer3_planning_docs/92_COHORT_HANDOFF_EXPORT_FREEZE.md`
- `Layer3_planning_docs/93_COHORT_HANDOFF_EXPORT_CONTRACT.md`
- `backend/app/services/layer3_workbench.py`
- `backend/app/review_ui/static/layer3.js`
- `backend/tests/test_layer3_api.py`
- `e2e/layer3-workbench.spec.js`
- `next_milestone_plans/layer3_progress_manifest.json`
- `next_milestone_plans/layer3_workbench_proof_manifest.json`

Read this as a proof/hardening lane over existing rendered controls, not as a new downstream handoff/export capability:
- PR `#460` is the backend/API authority for selected-pass associated-cohort `descriptive_summary` prepare-only state.
- The rendered `/review/layer3` prepare form already exists from the prior workbench handoff/export UI path and is gated by server `handoff_export_prepare.available` state.
- PR `#462` adds read-only pass type, pass scope, method, source gate, and package source gate projection plus focused headed/headless browser proof for the existing rendered prepare control.
- It must not admit APS dispatch, external export/download, connector dispatch, package mutation/reconstruction, schema/runtime/source widening, retry/recovery, pass-entry changes, broader UI, qualitative/hybrid/RAG/vector execution, or full mockup activation.

### If you are auditing the selected-pass associated-cohort APS handoff dispatch freeze

Start with:
- `Layer3_planning_docs/94_COHORT_APS_HANDOFF_DISPATCH_FREEZE.md`
- `Layer3_planning_docs/95_COHORT_APS_HANDOFF_DISPATCH_CONTRACT.md`
- `Layer3_planning_docs/96_COHORT_EXTERNAL_EXPORT_DOWNLOAD_FREEZE.md`
- `Layer3_planning_docs/97_COHORT_EXTERNAL_EXPORT_DOWNLOAD_CONTRACT.md`
- `Layer3_planning_docs/98_COHORT_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FREEZE.md`
- `Layer3_planning_docs/99_COHORT_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_CONTRACT.md`
- `Layer3_planning_docs/100_COHORT_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_UI_FREEZE.md`
- `Layer3_planning_docs/101_COHORT_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_UI_CONTRACT.md`
- `Layer3_planning_docs/102_COHORT_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_URL_FREEZE.md`
- `Layer3_planning_docs/103_COHORT_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_URL_CONTRACT.md`
- `Layer3_planning_docs/92_COHORT_HANDOFF_EXPORT_FREEZE.md`
- `Layer3_planning_docs/93_COHORT_HANDOFF_EXPORT_CONTRACT.md`
- `Layer3_planning_docs/58_L3_WB_APS_HANDOFF_DISPATCH_FREEZE.md`
- `Layer3_planning_docs/59_L3_WB_APS_HANDOFF_DISPATCH_API_AND_STATE_CONTRACT.md`
- `backend/app/review_ui/static/layer3.js`
- `backend/app/services/layer3_workbench.py`
- `backend/app/services/layer3_aps_handoff.py`
- `backend/tests/test_layer3_api.py`
- `backend/tests/test_layer3_page.py`
- `e2e/layer3-workbench.spec.js`
- `next_milestone_plans/layer3_progress_manifest.json`
- `next_milestone_plans/layer3_workbench_proof_manifest.json`

Read docs `94`/`95` as current-main planning-only governance from PR `#464` by themselves:
- they select the next associated-cohort APS evidence-bundle handoff dispatch boundary after PR `#460` prepare-only state and PR `#462` rendered prepare proof
- PR `#466` implements exact associated-cohort APS dispatch; invalid or mismatched authority still fails closed with `associated_cohort_aps_handoff_dispatch_not_admitted`
- docs `58`/`59` and PR `#260`/`#261`/`#263` are single-item APS dispatch pattern and owner-service compatibility sources, not direct associated-cohort dispatch authority
- docs `96`/`97` govern the associated-cohort external export/download readiness boundary over PR `#466`; they do not make readiness live by themselves
- PR `#479` proves exact PR `#432`/`#438`/`#443`/`#447`/`#451`/`#456`/`#460`/`#462`/`#466` authority before narrowing `associated_cohort_external_export_download_prepare_not_admitted`
- docs `98`/`99` govern same-origin associated-cohort delivery after PR `#479`; PR `#483` proves the backend/API path through the existing same-origin endpoint, but that proof does not settle associated-cohort rendered-control activation
- docs `100`/`101` are the current-main PR `#485` rendered-control settlement boundary, and PR `#487` implements the explicit server-authoritative associated-cohort delivery UI gate over the existing generic `/review/layer3` delivery form from the earlier single-item UI path
- current-main docs `102`/`103` from PR `#497` govern the signed delivery-reference implementation audit and contract; PR `#499` is the separate backend/API same-origin signed-reference generation/use implementation
- the readiness, delivery, UI-settlement, and signed-reference governance plus PR `#499` do not admit public/provider URLs, rendered signed URL controls, connector dispatch, generic downstream dispatch, destination selection, package payload copy/rewrite/reconstruction, durable token/receipt/audit/revocation state, schema/runtime/source widening, retry/recovery/rerun expansion, pass-entry changes, broader UI, qualitative/hybrid/RAG/vector execution, or full mockup activation

### If you are auditing selected-pass associated-cohort external export/download delivery proof

Start with:
- `Layer3_planning_docs/98_COHORT_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FREEZE.md`
- `Layer3_planning_docs/99_COHORT_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_CONTRACT.md`
- `backend/app/api/layer3.py`
- `backend/app/services/layer3_workbench.py`
- `backend/tests/test_layer3_api.py`

Read PR `#483` as current-main backend/API proof, not rendered UI activation:
- it reuses the existing `POST /api/v1/layer3/handoff/export/download/deliver` endpoint rather than adding a cohort-specific route
- it proves associated-cohort delivery by streaming the existing APS evidence-bundle artifact after server-side revalidation of PR `#479` readiness
- stale cohort dispatch provenance fails closed before streaming
- successful delivery and replay create no rows/files and do not mutate readiness, packages, or APS artifact bytes
- PR `#483` itself adds no rendered-control implementation, but current repo truth already contains the generic delivery form from the single-item UI slice; docs `100`/`101` settle the associated-cohort rendered-control question by requiring an explicit server-authoritative gate before activation
- public/signed URLs, connector/generic dispatch, destination selection, schema/runtime/source widening, broader UI, and full mockup behavior remain out

### If you are auditing selected-pass associated-cohort external export/download delivery UI settlement

Start with:
- `Layer3_planning_docs/100_COHORT_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_UI_FREEZE.md`
- `Layer3_planning_docs/101_COHORT_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_UI_CONTRACT.md`
- `Layer3_planning_docs/98_COHORT_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FREEZE.md`
- `Layer3_planning_docs/99_COHORT_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_CONTRACT.md`
- `Layer3_planning_docs/68_L3_WB_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_UI_FREEZE.md`
- `Layer3_planning_docs/69_L3_WB_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_UI_STATE_CONTRACT.md`
- `backend/app/review_ui/static/layer3.js`
- `backend/app/services/layer3_workbench.py`
- `backend/tests/test_layer3_page.py`
- `e2e/layer3-workbench.spec.js`

Read docs `100`/`101` as current-main PR `#485` planning/control and PR `#487` implementation authority over existing rendered delivery UI code:
- the generic delivery form and same-origin attachment submission path already exist from PR `#282`/`#285`/`#286`
- associated-cohort activation uses PR `#487`'s explicit server-authoritative `delivery_ui` gate because PR `#483` proved backend/API delivery only
- `browser_download_enabled` remains `false`; if `delivery_ui` is absent or unavailable, associated-cohort delivery must render unavailable
- PR `#487` proved headed and headless browser behavior for the explicit gate before treating associated-cohort rendered delivery as live, and PR `#488` synced the progress/control surfaces afterward
- URLs, connectors, destinations, package mutation, schema/runtime/source widening, broader UI, and full mockup behavior remain out

### If you are auditing selected-pass associated-cohort external export/download signed URL governance

Start with:
- `Layer3_planning_docs/102_COHORT_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_URL_FREEZE.md`
- `Layer3_planning_docs/103_COHORT_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_URL_CONTRACT.md`
- `Layer3_planning_docs/98_COHORT_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FREEZE.md`
- `Layer3_planning_docs/99_COHORT_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_CONTRACT.md`
- `Layer3_planning_docs/100_COHORT_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_UI_FREEZE.md`
- `Layer3_planning_docs/101_COHORT_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_UI_CONTRACT.md`
- `backend/app/services/layer3_workbench.py`
- `backend/app/api/layer3.py`
- `backend/tests/test_layer3_api.py`
- `backend/tests/test_layer3_page.py`
- `e2e/layer3-workbench.spec.js`

Read docs `102`/`103` as current-main planning/control from PR `#497`, with PR `#499` as the separate bounded backend/API implementation:
- current live delivery remains same-origin attachment through PR `#483`, with PR `#487` as the only associated-cohort rendered delivery UI authority
- PR `#499` implements `POST /api/v1/layer3/handoff/export/download/signed-reference/generate` and `POST /api/v1/layer3/handoff/export/download/signed-reference/use`
- the post-review hardened implementation uses server-owned HMAC signed references with a 300-second TTL, requires `LAYER3_SIGNED_REFERENCE_SECRET` before generation/use, and revalidates exact associated-cohort authority at generation and use
- PR `#520` intentionally supersedes only the no-row/no-replay part by adding durable token hash records, generation/use receipts, audit rows, durable missing-state failure, and single-use replay denial behind the same endpoints
- the implementation preserves PR `#496` package-review submit legacy idempotency compatibility in the upstream authority chain
- if signed delivery needs external object-store ACL, connector, destination, rendered UI behavior, package mutation, qualitative execution, or source/schema/runtime widening beyond the named durable table family, stop for a separate freeze
- public/provider URLs, connector/generic dispatch, destination selection, package mutation, schema/runtime/source widening, broader UI, qualitative/hybrid/RAG/vector behavior, and full mockup behavior remain out

### If you are auditing durable signed-reference state planning/runtime

Start with:
- `Layer3_planning_docs/106_DURABLE_FREEZE.md`
- `Layer3_planning_docs/107_DURABLE_CONTRACT.md`
- `Layer3_planning_docs/108_DURABLE_ENTRY.md`
- `Layer3_planning_docs/109_DURABLE_STATE.md`
- `Layer3_planning_docs/105_deferred-gates.md`
- `backend/app/services/layer3_workbench.py`
- `backend/app/services/layer3_signed_reference_state.py`
- `backend/app/api/layer3.py`
- `backend/app/models/models.py`
- `backend/alembic/versions/0016_layer3_signed_reference_state.py`
- `backend/tests/test_layer3_api.py`

Read docs `108`/`109` as the current implementation-entry contract landed by PR `#520`:
- they name the durable control-plane table family, service seam, API compatibility rule, and tests
- they selected `backend/alembic/versions/0016_layer3_signed_reference_state.py` for base commit `5896b9b5910d61ff94b27ff0c142b35319dd5fa1`, where `0015_layer3_package_entry.py` was the latest migration; PR `#520` landed that migration
- if a later branch needs a newer migration or signed-reference API change, create a fresh freeze before landing
- they admit only bounded durable backing state behind existing same-origin signed-reference endpoints, not provider/public URLs, connector/destination dispatch, rendered UI changes, qualitative execution, package mutation, or source/schema/runtime widening

### If you are auditing provider/public URL planning

Start with:
- `Layer3_planning_docs/110_PROVIDER_URL_FREEZE.md`
- `Layer3_planning_docs/111_PROVIDER_URL_CONTRACT.md`
- `Layer3_planning_docs/102_COHORT_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_URL_FREEZE.md`
- `Layer3_planning_docs/103_COHORT_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_URL_CONTRACT.md`
- `Layer3_planning_docs/104_signed-ui.md`
- `Layer3_planning_docs/105_deferred-gates.md`
- `Layer3_planning_docs/106_DURABLE_FREEZE.md`
- `Layer3_planning_docs/107_DURABLE_CONTRACT.md`
- `Layer3_planning_docs/108_DURABLE_ENTRY.md`
- `Layer3_planning_docs/109_DURABLE_STATE.md`
- `backend/app/services/layer3_workbench.py`
- `backend/app/services/layer3_signed_reference_state.py`
- `backend/app/api/layer3.py`
- `backend/tests/test_layer3_api.py`

Read docs `110`/`111` as planning/control only:
- provider/public URL behavior remains blocked by default
- same-origin attachment delivery plus same-origin durable signed references remain the current live path
- a future provider/public implementation must choose exactly one mode: `provider_private_signed_url`, `provider_public_url`, or `public_proxy_url`
- provider/object-store authority, credentials/config, ACL ownership, expiry, revocation, response headers, leakage review, audit/receipt behavior, and tests must be named before code
- connector/destination dispatch, package mutation, schema/runtime/source widening, rendered controls, qualitative execution, and full mockup activation remain out

### If you are auditing connector/destination dispatch planning

Start with:
- `Layer3_planning_docs/112_CONNECTOR_DISPATCH_FREEZE.md`
- `Layer3_planning_docs/113_CONNECTOR_DISPATCH_CONTRACT.md`
- `Layer3_planning_docs/105_deferred-gates.md`
- `Layer3_planning_docs/94_COHORT_APS_HANDOFF_DISPATCH_FREEZE.md`
- `Layer3_planning_docs/95_COHORT_APS_HANDOFF_DISPATCH_CONTRACT.md`
- `Layer3_planning_docs/110_PROVIDER_URL_FREEZE.md`
- `Layer3_planning_docs/111_PROVIDER_URL_CONTRACT.md`
- `backend/app/services/layer3_workbench.py`
- `backend/app/api/layer3.py`
- `backend/app/api/router.py`

Read docs `112`/`113` as planning/control only:
- connector/destination/generic downstream dispatch remains blocked by default
- current live APS dispatch is only owner-service `aps_evidence_bundle_handoff` through `aps_handoff_target == "aps_evidence_bundle"` and `dispatch_mode == "server_side_aps_handoff"`
- a future connector/destination implementation must choose exactly one mode: `internal_dispatch_record_only`, `single_named_connector_dispatch`, or `single_named_destination_dispatch`
- connector/destination authority, allowlisted ids, lifecycle, idempotency, authorization, receipt/audit payloads, failure states, and tests must be named before code
- provider/public URLs, package mutation, schema/runtime/source widening, rendered controls, qualitative execution, queue/retry/cancel behavior, and full mockup activation remain out unless separately frozen

### If you are auditing qualitative APS content document execution planning

Start with:
- `Layer3_planning_docs/114_QUAL_APS_EXEC_FREEZE.md`
- `Layer3_planning_docs/115_QUAL_APS_EXEC_CONTRACT.md`
- `Layer3_planning_docs/138_QUAL_APS_PACKAGE_REVIEW_FREEZE.md`
- `Layer3_planning_docs/139_QUAL_APS_PACKAGE_REVIEW_CONTRACT.md`
- `Layer3_planning_docs/140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE.md`
- `Layer3_planning_docs/141_QUAL_APS_PACKAGE_CONSTRUCTION_CONTRACT.md`
- `Layer3_planning_docs/105_deferred-gates.md`
- `Layer3_planning_docs/25_L3_QUAL1_FREEZE.md`
- `Layer3_planning_docs/27_L3_QUAL1_INPUTS.md`
- `backend/app/services/layer3_workbench.py`
- `backend/app/services/layer3_typing_entry.py`
- `backend/app/services/layer3_pass_entry.py`
- `backend/app/models/models.py`
- `backend/tests/test_layer3_workbench.py`
- `backend/tests/test_layer3_typing_entry.py`
- `backend/tests/test_layer3_pass_entry.py`

Read docs `114`/`115` as historical planning/control only, then read docs `119` and `124` plus current code for live truth:
- exact `single_aps_doc_qualitative_pass` is now the only admitted qualitative APS execution mode
- current live APS document support includes selection, trace, material preview, Gate B snapshot, qualitative/document-chunk typing, and the bounded single-document qualitative pass
- docs `138`/`139` govern the live read-only `qual_aps_package_review_preview_only` runtime boundary
- docs `140`/`141` govern the live bounded `qual_aps_package_construction_commit_entry`, which admits only first construction of `canonical_internal`, `user_facing`, and `review_facing` qualitative APS packages after approved preview, while still blocking package-review submit and all downstream delivery behavior
- the qualitative pass must not reuse `DatasetVersion` conversion or wrapped quantitative `run_analysis(...)`
- APS document identity, chunk ordering/limits, citation/trace refs, execution owner, result/review vocabulary, idempotency, failure states, no-leakage behavior, and tests remain required for any future expansion beyond the exact admitted mode
- associated-cohort qualitative execution, broad qualitative execution, hybrid/RAG/vector behavior, document trace changes, rendered controls, package/handoff/export, provider/public URLs, connector/destination dispatch, source ingestion, schema/runtime/source widening, and full mockup activation remain out unless separately frozen

### If you are auditing the Layer 3 workbench APS handoff dispatch freeze

Start with:
- `Layer3_planning_docs/58_L3_WB_APS_HANDOFF_DISPATCH_FREEZE.md`
- `Layer3_planning_docs/59_L3_WB_APS_HANDOFF_DISPATCH_API_AND_STATE_CONTRACT.md`
- `Layer3_planning_docs/54_L3_WB_HANDOFF_EXPORT_FREEZE.md`
- `Layer3_planning_docs/55_L3_WB_HANDOFF_EXPORT_API_AND_STATE_CONTRACT.md`
- `backend/app/api/layer3.py`
- `backend/app/services/layer3_workbench.py`
- `backend/app/services/layer3_aps_handoff.py`
- `backend/tests/test_layer3_api.py`
- `backend/tests/test_layer3_aps_handoff.py`

Read docs `58`/`59` as the governing APS handoff dispatch contract:
- PR `#260` makes the backend/API endpoint live on current `main`; PR `#261` hardens malformed provenance and unexpected package-kind fail-closed behavior, and PR `#263` hardens APS handoff package-row allowance so orphan/manual APS rows fail closed until dispatch state is recorded
- they still do not make rendered APS dispatch controls live by themselves; PR `#266` is the separate bounded rendered UI implementation
- the only APS target they select is `aps_evidence_bundle_handoff` through the existing owner-service family
- the implementation starts from existing `handoff_export_prepared` state and fails closed on stale package/review/prepare authority
- they do not admit external export/download, connector dispatch, destination selection, package mutation/reconstruction, additional reconciliation rows, source/schema/runtime widening, execution selection/start UI expansion, qualitative/hybrid/RAG/vector execution, or full mockup activation

### If you are auditing the Layer 3 workbench APS handoff dispatch UI freeze

Start with:
- `Layer3_planning_docs/60_L3_WB_APS_HANDOFF_DISPATCH_UI_FREEZE.md`
- `Layer3_planning_docs/61_L3_WB_APS_HANDOFF_DISPATCH_UI_STATE_CONTRACT.md`
- `Layer3_planning_docs/58_L3_WB_APS_HANDOFF_DISPATCH_FREEZE.md`
- `Layer3_planning_docs/59_L3_WB_APS_HANDOFF_DISPATCH_API_AND_STATE_CONTRACT.md`
- `backend/app/review_ui/static/layer3.html`
- `backend/app/review_ui/static/layer3.css`
- `backend/app/review_ui/static/layer3.js`
- `backend/tests/test_layer3_page.py`
- `e2e/layer3-workbench.spec.js`

Read docs `60`/`61` as planning-only rendered UI governance:
- they freeze only future `/review/layer3` APS dispatch readiness, one server-gated `dispatch_aps_handoff` submit control, and read-only recorded dispatch presentation over the already-live backend/API endpoint
- they do not make UI behavior live by themselves and do not change backend behavior
- PR `#266` is the separate bounded implementation: it uses server-authoritative package-review, prepare, package, and APS dispatch readiness state; it must not infer dispatch authority in the browser
- headed and headless Chrome proof is required when a later implementation changes rendered `/review/layer3` behavior
- they do not admit external export/download, connector dispatch, destination selection, package mutation/reconstruction, additional reconciliation rows, `AnalysisArtifact`, source/schema/runtime widening, execution selection/start UI expansion, qualitative/hybrid/RAG/vector execution, or full mockup activation

### If you are auditing the Layer 3 workbench external export/download freeze

Start with:
- `Layer3_planning_docs/62_L3_WB_EXTERNAL_EXPORT_DOWNLOAD_FREEZE.md`
- `Layer3_planning_docs/63_L3_WB_EXTERNAL_EXPORT_DOWNLOAD_API_AND_STATE_CONTRACT.md`
- `Layer3_planning_docs/58_L3_WB_APS_HANDOFF_DISPATCH_FREEZE.md`
- `Layer3_planning_docs/59_L3_WB_APS_HANDOFF_DISPATCH_API_AND_STATE_CONTRACT.md`
- `backend/app/services/layer3_aps_handoff.py`
- `backend/app/services/nrc_aps_evidence_bundle.py`
- `backend/tests/test_layer3_aps_handoff.py`

Read docs `62`/`63` and PR `#269` as split governance/live behavior:
- docs `62`/`63` freeze the backend/API external export/download readiness preparation boundary after `aps_handoff_dispatched`; by themselves they remain planning governance only
- PR `#269` separately implements only the bounded backend/API readiness descriptor through `POST /api/v1/layer3/handoff/export/download/prepare`
- the live PR `#269` behavior is reference-only over the existing APS evidence-bundle handoff artifact and existing JSON-bearing workbench state
- neither docs `62`/`63` nor PR `#269` make rendered UI behavior, rendered browser download controls, public/signed URLs, connector dispatch, destination selection, generic downstream dispatch, package mutation/reconstruction, additional reconciliation/package/artifact rows, `AnalysisArtifact`, source/schema/runtime widening, execution expansion beyond already admitted work, qualitative/hybrid/RAG/vector execution, or full mockup activation live
- browser proof is required only if a later implementation changes rendered `/review/layer3` behavior

### If you are auditing the Layer 3 workbench external export/download delivery freeze

Start with:
- `Layer3_planning_docs/66_L3_WB_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FREEZE.md`
- `Layer3_planning_docs/67_L3_WB_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_API_AND_STATE_CONTRACT.md`
- `Layer3_planning_docs/62_L3_WB_EXTERNAL_EXPORT_DOWNLOAD_FREEZE.md`
- `Layer3_planning_docs/63_L3_WB_EXTERNAL_EXPORT_DOWNLOAD_API_AND_STATE_CONTRACT.md`
- `backend/app/services/nrc_aps_evidence_bundle.py`

Read docs `66`/`67` as planning-only delivery governance paired with the separate PR `#278` implementation:
- they freeze only the same-origin backend/API delivery endpoint after `external_export_download_prepared`
- the delivery basis is the existing validated APS evidence-bundle handoff artifact, not a newly generated export artifact
- PR `#278` implements that backend/API endpoint and revalidates package-review, handoff/export prepare, APS dispatch, readiness, package refs/hashes, and APS bundle refs server-side before streaming bytes
- neither docs `66`/`67` nor PR `#278` admit rendered download controls, public/signed URLs, connector dispatch, destination selection, generic downstream dispatch, package mutation/reconstruction, additional row families, `AnalysisArtifact`, schema/runtime/source widening, qualitative/hybrid/RAG/vector behavior, or full mockup activation
- browser proof is required only if a later implementation changes rendered `/review/layer3` behavior

### If you are auditing the merged qualitative single-item companion prep on current `main`

Start with:
- `Layer3_planning_docs/25_L3_QUAL1_FREEZE.md`
- `Layer3_planning_docs/27_L3_QUAL1_INPUTS.md`
- `next_milestone_plans/layer3_progress_board.md`
- `next_milestone_plans/layer3_progress_manifest.json`

## Residual boundary note

This README closes the pack-local navigation gap, not broader repo-wide Layer 3 documentation closure.

It does not prove that unrelated dirty root planning pools or higher-level repo front doors are globally reconciled.
That broader question requires a separate read-only root-doc audit.

Doc `239` records the current backend/API-only revoke implementation over durable provider-private receipt state. It keeps `use` deferred by the redacted-token boundary and adds no rendered UI, provider network, object-store, public/proxy URL, connector/destination, package/source, same-origin delivery, same-origin signed-reference, auth/security, or frontend-only durable authority behavior.
Docs `240`/`241` freeze the provider-private signed URL use-route authority gap: no token/delivery model is selected, runtime implementation remains blocked, and `provider_private_signed_url_token`/`raw_provider_private_signed_url_token` stay forbidden on live revoke.

Doc `255_PACKAGE_MUTATION_REENTRY_DECISION_FREEZE.md` freezes package mutation reentry: bounded backend/API package lifecycle runtimes remain live, but rendered package mutation controls, broad package mutation/reconstruction, source package row mutation, source package payload rewrite, replacement package payload generation, downstream invalidation/re-delivery runtime, provider/public URL behavior, connector/destination dispatch side effects, source expansion, broad qualitative/hybrid/RAG behavior, full mockup activation, and browser-owned package authority remain blocked.

Doc `256_QUAL_HYBRID_RAG_REENTRY_DECISION_FREEZE.md` freezes qualitative/hybrid/RAG reentry: the single APS-document qualitative pass and bounded qualitative APS downstream chain remain live, but broad qualitative execution, cohort/comparative/cross-document analysis, hybrid execution, RAG/vector retrieval, vector indexes, embeddings, prompt/model/provider runtime, rendered qualitative/RAG controls, source expansion, package mutation side effects, provider/public URL behavior, connector/destination dispatch, full mockup activation, and browser-owned execution authority remain blocked.

Doc `257_FULL_MOCKUP_ACTIVATION_REENTRY_DECISION_FREEZE.md` freezes full mockup activation reentry: mockups remain target-state design/specification inputs and existing rendered controls remain live only where server-authoritative paths are already proven; full mockup activation, frontend-only durable workflow state, browser-local persistence as authority, new rendered mockup controls, route/API changes, source expansion, package mutation, provider/public URL behavior, connector/destination dispatch, broad qualitative/hybrid/RAG behavior, hidden LLM planning, auth/security behavior, and browser-owned workflow authority remain blocked.

Doc `258_GOAL_STACK_REENTRY_CLOSEOUT_AND_IMPLEMENTATION_GATE.md` closes the goal-stack reentry sequence as a planning/control and bounded-runtime audit stack: completed freezes do not imply broad runtime activation, and any next code must first select one named runtime mode with server authority, request/response contract, stale-authority/idempotency behavior, negative tests, leakage controls, and headed/headless/theme proof where rendered UI changes are admitted.

Doc `259_POST_REENTRY_RUNTIME_SELECTION_SYNC.md` records the current post-reentry selection state after doc `258`: no runtime family, runtime mode, or named use case is selected. It keeps source breadth, external connector/destination runtime, rendered package mutation, broad qualitative/hybrid/RAG, full mockup activation, and auth/security runtime blocked until one exact named runtime-use-case freeze is written first.

Doc `260_POST_REENTRY_NAMED_USE_CASE_ADJUDICATION.md` ranks the post-reentry candidate families and selects `source_breadth_named_use_case_packet` as the next planning artifact, not as runtime implementation. It keeps runtime code blocked until that packet names one concrete source use case or closes source breadth again as no-runtime.

Doc `261_SOURCE_BREADTH_NAMED_USE_CASE_PACKET.md` completes the selected source-breadth named-use-case packet as a no-runtime closeout: no concrete source use case is present in current authority, so source runtime remains blocked until a user/product source need names the source family, input mode, source-of-truth, storage/security, provenance, downstream semantics, rendered-control plan, and auth/security posture.

Doc `262_CONNECTOR_DESTINATION_NAMED_TARGET_PACKET.md` completes the connector/destination named-target packet as a no-runtime closeout: current authority proves only `internal_dispatch_record_only`, with no named external connector/destination use case, target family, credential/access model, lifecycle contract, receipt/audit contract, fake-target test architecture, rendered-control plan, or auth/security posture selected.

Doc `263_PACKAGE_MUTATION_NAMED_ACTION_PACKET.md` completes the package mutation named-action packet as a no-runtime closeout: backend/API package lifecycle authority is live, but no rendered operator package-revision use case, selected rendered package lifecycle mode, package payload source, downstream invalidation policy, re-delivery rule, receipt/audit contract, or headed/headless/theme proof plan is selected.

Doc `264_QUAL_HYBRID_RAG_NAMED_ANALYSIS_PACKET.md` completes the qualitative/hybrid/RAG named-analysis packet as a no-runtime closeout: the single APS-document qualitative path remains live, but no broad analysis use case, selected mode, source scope, retrieval corpus, vector storage model, embedding/model/prompt/provider authority, output taxonomy, or rendered-control proof plan is selected.

Doc `265_FULL_MOCKUP_NAMED_JOURNEY_PACKET.md` completes the full mockup named-journey packet as a no-runtime closeout: mockups remain target-state design/specification inputs, and no operator journey, activation mode, route/API contract, server authority contract, durable state owner, browser storage policy, mockup-to-live mapping, or theme/accessibility/headed/headless proof plan is selected.

Doc `266_AUTH_SECURITY_NAMED_MODE_PACKET.md` completes the auth/security named-mode packet as a no-runtime closeout: local/proxy deployment guardrails remain live, but no security/operator-access use case, auth mode, identity authority, tenant/session ownership model, permission matrix, route dependency contract, audit event contract, provider/connector secret policy, or rendered identity-control plan is selected.

Doc `267_POST_REENTRY_NAMED_PACKET_CLOSEOUT.md` closes the post-reentry named packet stack covering docs `259` through `266`: no runtime family, runtime mode, or named product/operator use case is selected after the source breadth, connector/destination, package mutation, qualitative/hybrid/RAG, full mockup, and auth/security packets. The next implementation-entry artifact requires a user/product-named use case before runtime; otherwise the correct posture is stop-at-planning to avoid speculative implementation and documentation churn.

Doc `268_MOCKUP_THEME_FREEZE.md` records the corrected product/UX intent for a dedicated pixel-perfect functional Layer 3 mockup workbench theme on `/review/layer3`. It names `layer3_mockup_workbench_theme` as the target theme and the `C:\Users\benny\Downloads\layer3mockups` corpus as the visual/user-flow acceptance authority, while keeping implementation gated behind a separate entry-freeze with server-authoritative state mapping, contextual-text classification, headed/headless visual proof, and no runtime widening.
## Mockup Theme Implementation Entry Freeze

- `Layer3_planning_docs/269_MOCKUP_THEME_ENTRY_FREEZE.md` freezes `mockup_theme_shell_and_fixture_projection` as the implementation-entry slice for `layer3_mockup_workbench_theme` on `/review/layer3`.
- The entry freeze admits rendered-theme work only after this planning pass: static Layer 3 review UI, focused rendered-page/e2e proof, planning/proof manifests, and `tools/l3-progress-check.py`.
- Backend API/model/migration/service behavior, source expansion, connector/destination runtime, package mutation, broad qualitative/hybrid/RAG behavior, auth/security behavior, full mockup durable workflow activation, and browser-owned durable authority remain blocked unless refrozen.

## Mockup Theme Shell Implementation Proof

- `Layer3_planning_docs/270_MOCKUP_THEME_SHELL_PROOF.md` records the first rendered implementation pass for `layer3_mockup_workbench_theme`.
- The pass implements `mockup_theme_shell_and_fixture_projection` as a static UI/theme variant over `/review/layer3`, with semiconductor fixture projection and Pre-3A/Gate B/Gate C/Sublayer 3A/3B/3C flow cards.
- It changes no backend API/model/migration/service behavior and does not admit source expansion, connector/destination runtime, package mutation, broad qualitative/hybrid/RAG runtime, auth/security behavior, full mockup durable workflow activation, or browser-owned workflow authority.

## Mockup Runtime Gate

- `Layer3_planning_docs/271_MOCKUP_RUNTIME_GATE.md` records `post_mockup_runtime_gate` after the static rendered theme proof only.
- The gate states that no runtime is selected after mockup visual proof; backend API/model/migration/service changes, source runtime, connector/destination dispatch, package mutation, broad qualitative/hybrid/RAG runtime, full durable mockup activation, auth/security runtime, and frontend-only durable authority remain blocked.
- The next code-bearing runtime slice requires `exact_named_server_authoritative_runtime_use_case_freeze`; without that named server authority, the Layer 3 mockup workbench remains bounded to static rendered projection and planning/control synchronization.

## PDF Location Use Case Freeze

- `Layer3_planning_docs/272_PDF_LOCATION_FREEZE.md` records `pdf_location_use_case_freeze` as the first named runtime-use-case freeze after the mockup runtime gate.
- The selected use case is `pdf_location_from_aps_content_document_citation`, a read-only projection from existing `ApsContentDocument`, `ApsContentChunk.page_start`/`ApsContentChunk.page_end`, `visual_page_refs_json`, `nrc_aps_evidence_citation_pack`, `sections[].citations[].highlight_spans`, and `source_bundle.run_id` authority.
- The freeze does not implement runtime behavior; it only permits a later `implement_read_only_pdf_location_projection_from_existing_authority` pass and keeps raw PDF blob streaming, new source families, local upload/directory/path input, RAG/vector retrieval, connector/destination dispatch, package mutation, auth/security widening, full durable mockup activation, and browser-owned authoritative PDF location blocked.

## PDF Location Projection Implementation

- `Layer3_planning_docs/273_PDF_LOCATION_PROJECTION.md` records `read_only_pdf_location_projection_from_existing_authority` as the first code-bearing PDF-location slice.
- The implementation adds `backend/app/services/layer3_pdf_location.py`, `backend/tests/test_layer3_pdf_location.py`, and the `pdf_location_projection` session-summary field for `/api/v1/layer3/session/{session_id}`.
- The projection uses existing APS document/chunk/page/citation authority only; it does not add a new endpoint, model, migration, PDF streaming path, source adapter, package mutation, connector/destination dispatch, auth/security behavior, full durable mockup activation, or browser-owned authoritative PDF location.

## PDF Location Theme Projection

- `Layer3_planning_docs/274_PDF_LOCATION_THEME.md` records `rendered_pdf_location_projection_from_session_summary` as the mockup-theme rendering pass over the already-implemented session-summary state.
- The implementation adds `#mockup-pdf-location-projection` inside the `layer3_mockup_workbench_theme` user-flow/PDF-location board and binds it only to `State.sessionSummary.pdf_location_projection`.
- The pass is rendered UI behavior only; it issues no new backend requests and does not add route/API behavior, models, migrations, raw PDF streaming, source expansion, package mutation, connector/destination dispatch, auth/security widening, browser-owned authoritative PDF location, or full durable mockup activation.

## Mockup Visual Diff Freeze

- `Layer3_planning_docs/275_MOCKUP_VISUAL_DIFF_FREEZE.md` records `repo_local_mockup_frame_visual_diff_acceptance` as the next proof mode for pixel-faithful mockup-theme work.
- The next allowed action is `implement_repo_local_mockup_visual_diff_harness`, with repo-local frame authority from `next_milestone_plans/layer3-mockups/frames/manifest.json`, headed/headless Chromium proof, and fail-closed handling for missing frames, selectors, screenshots, or over-tolerance deltas.
- This is planning/control only; it does not claim current visual parity and does not change backend API/model/migration/service behavior, source runtime, connector/destination dispatch, package mutation, qualitative/hybrid/RAG runtime, full durable mockup activation, or auth/security behavior.

## Mockup Visual Diff Harness

- `Layer3_planning_docs/276_MOCKUP_VISUAL_DIFF_HARNESS.md` records the implemented `repo_local_mockup_frame_visual_diff_acceptance` harness for `layer3_mockup_workbench_theme`.
- The Playwright test uses `MOCKUP_VISUAL_DIFF_LIMITS`, browser canvas image comparison, all eight repo-local frame manifest entries, and the `layer3-mockup-visual-diff-metrics.json` attachment.
- This is a deterministic proof-harness pass, not a pixel-perfect parity claim; it adds no backend API/model/migration/service behavior, source runtime, connector/destination dispatch, package mutation, qualitative/hybrid/RAG runtime, full durable mockup activation, or auth/security behavior.

## Mockup Pixel Refinement

- `Layer3_planning_docs/277_MOCKUP_PIXEL_REFINEMENT.md` records `pdf_location_frame_selector_precision_and_threshold_tightening`.
- The pass adds the stable `#mockup-pdf-location-card` selector, maps `pdf_location_projection` to that selector in the repo-local frame manifest, and tightens `MOCKUP_VISUAL_DIFF_LIMITS` to `normalizedMeanDeltaMax: 0.30` and `highDeltaRatioMax: 0.34`.
- This improves visual-proof strictness without claiming completed pixel-perfect parity and without changing backend API/model/migration/service behavior, source runtime, connector/destination dispatch, package mutation, qualitative/hybrid/RAG runtime, full durable mockup activation, or auth/security behavior.

## Mockup Threshold Tightening

- `Layer3_planning_docs/278_MOCKUP_THRESHOLD_TIGHTENING.md` records `visual_diff_threshold_tightening_to_observed_envelope`.
- The pass tightens `MOCKUP_VISUAL_DIFF_LIMITS` to `normalizedMeanDeltaMax: 0.22` and `highDeltaRatioMax: 0.31` after the selector precision pass measured `pdf_location_projection` at `0.272669` and `0.299356`.
- This is proof-hardening only; it does not claim full pixel-perfect parity and does not change backend API/model/migration/service behavior, source runtime, connector/destination dispatch, package mutation, qualitative/hybrid/RAG runtime, full durable mockup activation, or auth/security behavior.


## Mockup PDF-Location Panel Refinement

- `Layer3_planning_docs/279_MOCKUP_PDF_LOCATION_PANEL_REFINEMENT.md` records `pdf_location_panel_structure_and_slide_selector_refinement`.
- The rendered theme now uses a five-region `#mockup-pdf-location-card` static projection and maps query/spec slide frames to `#mockup-fixture-scenario` for tighter selector specificity.
- Current `MOCKUP_VISUAL_DIFF_LIMITS` are `normalizedMeanDeltaMax: 0.22` and `highDeltaRatioMax: 0.31` at `360 x 220`; this is not a full pixel-perfect claim.
- Runtime/backend/source/connector/package/RAG/auth/full-activation scope remains blocked until separately refrozen as a named server-authoritative implementation slice.


## Mockup Overview Selector Refinement

- `Layer3_planning_docs/280_MOCKUP_OVERVIEW_SELECTOR_REFINEMENT.md` records `overview_frame_selector_refinement_to_theme_shell`.
- Overview montage frames now use `#mockup-theme-shell`; query/spec slide frames remain on `#mockup-fixture-scenario`; PDF-location remains on `#mockup-pdf-location-card`.
- Current `MOCKUP_VISUAL_DIFF_LIMITS` are `normalizedMeanDeltaMax: 0.22` and `highDeltaRatioMax: 0.31` at `360 x 220`; this is not a full pixel-perfect claim.
- Runtime/backend/source/connector/package/RAG/auth/full-activation scope remains blocked until separately refrozen as a named server-authoritative implementation slice.


## Mockup PDF-Location Contrast Refinement

- `Layer3_planning_docs/281_MOCKUP_PDF_CONTRAST_REFINEMENT.md` records `pdf_location_contrast_palette_refinement`.
- The PDF-location board keeps the same rendered selectors and server-state boundaries while moving card/background contrast closer to the repo-local mockup frame.
- Current `MOCKUP_VISUAL_DIFF_LIMITS` are `normalizedMeanDeltaMax: 0.22` and `highDeltaRatioMax: 0.31` at `360 x 220`; this is not a full pixel-perfect claim.
- Runtime/backend/source/connector/package/RAG/auth/full-activation scope remains blocked until separately refrozen as a named server-authoritative implementation slice.
