# Layer 3 Deferred Gates

## Status

Post-synthesis authority guardrail: `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md` records the current local synthesis correction for mockup, Codesight, progress-prose, and stale-audit overclaims. This deferred-gates document remains a freeze/control document only; it does not implement or newly admit provider/public URLs, broad connector/destination dispatch, broad package mutation/reconstruction, broad source/upload expansion, broad qualitative/hybrid/RAG execution, authentication/security work, or full mockup activation. The exact `internal_dispatch_record_only` runtime is live only as an internal record and does not change the broader deferred gates. Doc `122_PACKAGE_MUTATION_FREEZE.md` governs a live `package_supersession_preview_only` runtime only as a read-only preview with no database writes, no package payload writes, and no in-place mutation. Doc `127_PACKAGE_REPLACEMENT_SET_FREEZE.md` governs a live `replacement_package_set_authority` runtime only as a durable metadata authority record with no replacement package rows, no package payload writes, and no UI behavior. Doc `126_PACKAGE_COMMIT_FREEZE.md` now governs the live `package_supersession_commit_entry` runtime only as a durable immutable lineage record with no package row mutation, no package payload write, no replacement package rows, no UI behavior, and no broad package mutation/reconstruction. Doc `128_PACKAGE_REPLACEMENT_ARTIFACT_FREEZE.md` is planning/control only: it names `replacement_package_artifact_authority_only` as the package lifecycle prerequisite before any replacement package artifact generation, replacement package row creation, payload write, rendered package mutation control, or broad package mutation/reconstruction can be considered. Doc `129_PACKAGE_REPLACEMENT_ARTIFACT_MANIFEST_FREEZE.md` remains the implementation-entry planning authority; the exact `replacement_package_artifact_manifest_only` runtime is live only as server-side manifest verification through `/api/v1/layer3/package/replacement-artifact/manifest/record`, `L3ReplacementPackageArtifactManifest`, and migration `0020_layer3_replacement_package_artifact_manifest.py`, with no package payload write, no replacement package row, no artifact generation, no rendered control, and no broad package mutation/reconstruction. Doc `130_PACKAGE_REPLACEMENT_NAMESPACE_FREEZE.md` is planning/control only: it selected `replacement_package_namespace_rows` with `selected_namespace_design: separate_replacement_output_package_table` as the row namespace prerequisite while preserving `uq_l3_output_package_session_kind`. Doc `131_PACKAGE_REPLACEMENT_NAMESPACE_ENTRY_FREEZE.md` now governs the live bounded `replacement_package_namespace_rows` runtime through `/api/v1/layer3/package/replacement-namespace/record`, `L3ReplacementOutputPackage`, `l3_replacement_output_package`, and migration `0021_layer3_replacement_output_package.py`; it creates only replacement namespace metadata rows, performs no source `L3OutputPackage` row mutation, performs no package payload write, adds no rendered controls, and broad package mutation/reconstruction remains blocked. Docs `132_PLAN_REVISION_RECOVERY_FREEZE.md` and `133_PLAN_REVISION_RECOVERY_CONTRACT.md` remain planning/control authority for `plan_revision_recovery_lifecycle`; doc `134_PLAN_REVISION_RECOVERY_ENTRY_FREEZE.md` now governs only the live bounded `plan_revision_recovery_preview_refresh_entry` runtime. That route records summary-state recovery metadata, forces a fresh server-backed plan preview, and still does not admit approved-plan supersession, execution, package/handoff/export behavior, connector/destination dispatch, source widening, broad qualitative/hybrid/RAG execution, full mockup activation, or authentication/security work. Doc `123_SOURCE_EXPANSION_FREEZE.md` freezes `supported_source_classes_only`; source upload, local directory, broad file upload, web connector, RAG/vector, and unbounded runtime DB source expansion remain blocked. Doc `124_QUAL_HYBRID_RAG_FREEZE.md` freezes `single_aps_doc_qualitative_pass_only`; broad qualitative execution, qualitative cohort execution, comparative execution, cross-document synthesis, hybrid execution, RAG/vector retrieval, hidden LLM planning, and qualitative package/handoff/export remain blocked. Doc `125_MOCKUP_TRUTH_STATE_FREEZE.md` freezes `mockups_target_state_only`; full mockup activation and frontend-only durable state remain blocked.

Doc `134_PLAN_REVISION_RECOVERY_ENTRY_FREEZE.md` is the bounded runtime contract for `plan_revision_recovery_preview_refresh_entry`. It implements only `POST /api/v1/layer3/plan/revision/recover`, `backend/app/services/layer3_plan_revision_recovery.py`, strict DTOs, summary-state recovery metadata in existing `L3Session.summary_json`, and preview-refresh identity invalidation. It does not implement approved-plan supersession, `L3AnalysisPlan` mutation, `L3PassRun` creation, `AnalysisRun` creation, package/handoff/export behavior, connector/destination dispatch, source widening, broad qualitative/hybrid/RAG execution, full mockup activation, or authentication/security work.

Doc `135_APPROVED_PLAN_CORRECTION_FREEZE.md` remains planning/control only for the broader `approved_plan_correction_lifecycle`. The exact cancellation-without-replacement mode is now separately admitted by the doc 136 runtime branch, but approved-plan reopening, replacement, deletion, supersession, replacement-plan creation, UI behavior, package behavior, execution behavior, connector/destination behavior, source widening, broad qualitative/hybrid/RAG behavior, full mockup activation, authentication/security work, and broad package mutation/reconstruction remain blocked.

Doc `136_APPROVED_PLAN_CANCEL_ENTRY_FREEZE.md` remains the historical implementation-entry freeze for `approved_plan_cancel_without_replacement` and admits no runtime behavior by itself. Current main separately implements only the bounded cancel-without-replacement path through `POST /api/v1/layer3/plan/approved/cancel` and `backend/app/services/layer3_approved_plan_correction.py`: it marks the existing approved `L3AnalysisPlan` row as cancelled and records `approved_plan_cancel` state in existing plan/session JSON. It fails closed before mutation when same-session `L3PassRun`, `L3ReconciliationRecord`, or `L3OutputPackage` state already exists. It creates no replacement plan, no `L3PassRun`, no `AnalysisRun`, no output/package/handoff/export artifact, and still does not admit approved-plan supersession, replacement, reopening, deletion, connector/destination dispatch, source/schema/runtime widening, broad qualitative/hybrid/RAG behavior, full mockup activation, authentication/security work, or broad package mutation/reconstruction.

Current-main decision freeze for the remaining requested deferred categories after PR `#499`, PR `#513`, and PR `#514` rendered signed-reference UI slice in `104_signed-ui.md`.

Current-main docs `106_DURABLE_FREEZE.md` and `107_DURABLE_CONTRACT.md` selected durable token, receipt, revocation, and audit state as the next planning/control question only after PR `#516`. PR `#520` later implemented only bounded same-origin durable signed-reference runtime behavior behind the existing PR `#499` endpoints.

Current-main docs `108_DURABLE_ENTRY.md` and `109_DURABLE_STATE.md` named the implementation-entry surfaces and state contract for that durable same-origin signed-reference code lane. They remain the implementation-entry authority for PR `#520` and do not admit provider/public URLs, connector/destination dispatch, rendered revoke/copy/share UI behavior, qualitative execution, or package/source/schema/runtime widening beyond the named durable table family.

Current-main docs `110_PROVIDER_URL_FREEZE.md` and `111_PROVIDER_URL_CONTRACT.md` freeze provider/public URL behavior as not admitted. They require a future implementation-entry freeze to choose exactly one provider/public mode and prove provider/object-store authority, ACL/expiry/revocation/header/security behavior, leakage controls, and tests before code.

Current-main docs `112_CONNECTOR_DISPATCH_FREEZE.md` and `113_CONNECTOR_DISPATCH_CONTRACT.md` freeze connector/destination/generic downstream dispatch behavior as not admitted. Doc `121_CONNECTOR_DISPATCH_ENTRY_FREEZE.md` now selects and bounds `internal_dispatch_record_only`; that exact runtime is live only as an internal record in existing `L3ReconciliationRecord.summary_json`. `connector_destination_dispatch` remains deferred, and `single_named_connector_dispatch` and `single_named_destination_dispatch` remain blocked. This does not admit external connector invocation, destination writes, provider/public URLs, package mutation/reconstruction, source widening, qualitative/hybrid/RAG execution, or full mockup activation.

Current-main docs `114_QUAL_APS_EXEC_FREEZE.md`, `115_QUAL_APS_EXEC_CONTRACT.md`, `119_L3_QUAL_APS_EXEC_ENTRY_FREEZE.md`, and `124_QUAL_HYBRID_RAG_FREEZE.md` freeze and narrow qualitative APS content document execution to the one initial `single_aps_doc_qualitative_pass` mode. That exact mode is implemented on current main; broader qualitative execution, qualitative cohort execution, comparative execution, cross-document synthesis, hybrid execution, RAG/vector execution, and hidden LLM planning remain not admitted. Docs `138_QUAL_APS_PACKAGE_REVIEW_FREEZE.md` and `139_QUAL_APS_PACKAGE_REVIEW_CONTRACT.md` govern the live read-only `qual_aps_package_review_preview_only` runtime boundary after PR `#702`. Docs `140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE.md` and `141_QUAL_APS_PACKAGE_CONSTRUCTION_CONTRACT.md` govern the live bounded `qual_aps_package_construction_commit_entry` runtime boundary: current-main code creates exactly one reconciliation row, exactly three qualitative APS package rows, and server-owned package payload files. Docs `143_QUAL_APS_PACKAGE_REVIEW_SUBMIT_FREEZE.md` and `144_QUAL_APS_PACKAGE_REVIEW_SUBMIT_CONTRACT.md` govern the live bounded `qual_aps_package_review_submit_entry` runtime boundary: current-main code records exactly one qualitative APS package-review decision object in existing JSON-bearing state and creates no rows or files. Docs `145_QUAL_APS_HANDOFF_EXPORT_PREPARE_FREEZE.md` and `146_QUAL_APS_HANDOFF_EXPORT_PREPARE_CONTRACT.md` now govern the live bounded `qual_aps_handoff_export_prepare_entry` runtime boundary: current-main code records exactly one qualitative APS prepare-only handoff/export decision/envelope object in existing JSON-bearing state and creates no rows or files. Docs `147_QUAL_APS_APS_HANDOFF_DISPATCH_FREEZE.md` and `148_QUAL_APS_APS_HANDOFF_DISPATCH_CONTRACT.md` now govern the live qualitative APS APS handoff dispatch boundary: current-main code creates exactly one APS evidence-bundle handoff package row, writes one server-owned APS bundle artifact, records dispatch state for the exact qualitative authority chain, and hands readiness to docs `149` and `150`. Docs `149_QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_FREEZE.md` and `150_QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_CONTRACT.md` now govern the live qualitative APS external export/download prepare/deliver boundary only: `qual_aps_external_export_download_prepare_deliver` records readiness over the dispatched server-owned APS bundle and streams that same-origin artifact. Docs `151_QUAL_APS_RENDERED_UI_FREEZE.md` and `152_QUAL_APS_RENDERED_UI_CONTRACT.md` now freeze only future `qual_aps_rendered_downstream_existing_controls_only` rendered UI activation over the live qualitative APS backend/API chain. Connector/destination dispatch, provider/public URLs, signed URLs, rendered qualitative controls until that separate runtime PR, source expansion, RAG/vector behavior, and auth/security behavior remain blocked.

Current-main doc `122_PACKAGE_MUTATION_FREEZE.md` freezes broad package mutation/reconstruction as not runtime-admitted and selects the exact `package_supersession_preview_only` runtime as the first eligible implementation-entry candidate. This read-only route does not admit package payload rewrite, package row mutation, package reconstruction commit, editable package variants, provider/public URLs, connector/destination dispatch, source widening, qualitative/hybrid/RAG execution, schema/model/migration changes, full mockup activation, or authentication/security work. Doc `127_PACKAGE_REPLACEMENT_SET_FREEZE.md` governs the bounded `replacement_package_set_authority` runtime because live `L3OutputPackage` still has one row per `(session_id, package_kind)` and replacement-set authority must live in a separate metadata table. Doc `126_PACKAGE_COMMIT_FREEZE.md` governs the bounded `package_supersession_commit_entry` lineage runtime through `/api/v1/layer3/package/supersession/commit`, `L3PackageSupersessionCommit`, and `0019_layer3_package_supersession_commit.py`; it records immutable supersession lineage only and still does not add package row mutation, package payload writes, UI controls, connector/destination dispatch, provider/public URLs, source widening, qualitative/hybrid/RAG execution, full mockup activation, or authentication/security work. Doc `128_PACKAGE_REPLACEMENT_ARTIFACT_FREEZE.md` keeps replacement package artifact generation planning-only until replacement package artifacts are server-owned or server-generated; replacement package refs/hashes by themselves are not proof of reconstructable package content. Doc `129_PACKAGE_REPLACEMENT_ARTIFACT_MANIFEST_FREEZE.md` governs the exact `replacement_package_artifact_manifest_only` runtime: server-side manifest verification of existing replacement refs/hashes with an immutable manifest row only, no artifact generation, no package row mutation, no payload write, and no broad package mutation/reconstruction. Doc `130_PACKAGE_REPLACEMENT_NAMESPACE_FREEZE.md` governs the planning/control namespace decision: replacement package rows use a separate replacement namespace/table and must not weaken `uq_l3_output_package_session_kind`. Doc `131_PACKAGE_REPLACEMENT_NAMESPACE_ENTRY_FREEZE.md` governs the live bounded `replacement_package_namespace_rows` runtime and still admits no source package row mutation, package payload write, rendered control, or broad package mutation/reconstruction.

Current-main doc `125_MOCKUP_TRUTH_STATE_FREEZE.md` freezes tracked mockup artifacts as target-state design/specification inputs only. The mockup files do not admit rendered controls, browser-local persistence, frontend-only durable state, broad execution, source widening, connector/destination dispatch, provider/public URL support, package mutation/reconstruction, broad qualitative/hybrid/RAG execution, hidden LLM planning, or full mockup activation.

This file does not implement deferred broad behavior. It defines the minimum questions, blockers, and proof gates required before any of the following can become an implementation lane:

- provider/public signed URL generation;
- broad connector/destination dispatch beyond the exact internal record-only lane;
- package supersession behavior beyond the exact read-only doc `122` route, and any package mutation/reconstruction commit;
- source upload, local directory, broad file upload, web connector, RAG/vector, and unbounded runtime DB source expansion beyond `supported_source_classes_only`;
- durable token, receipt, revocation, and audit behavior beyond PR `#520`, including public/API/UI revocation or cleanup/read-model expansion;
- broad qualitative execution beyond the admitted single APS-document qualitative pass.

## Source Upload/Expansion

Current decision: planning/control frozen by doc `123`; runtime source expansion remains not admitted. Current-main source selection is `supported_source_classes_only`, limited to `dataset_version` and `aps_content_document`.

Broader implementation cannot begin until doc `123` constraints are preserved and these are specified or explicitly kept blocked:

- source storage authority and allowed roots;
- upload size, type, parsing, and retention constraints;
- local directory traversal and symlink policy;
- web connector destination/source authority;
- RAG/vector index ownership, refresh, citation, and deletion semantics;
- runtime DB source query scope and row/tenant boundaries;
- tests proving unsupported source families fail closed without package, execution, connector, provider URL, or mockup activation side effects.

This lane must not be folded into package mutation, connector dispatch, provider/public URL, qualitative/RAG execution, or mockup activation work.

## Provider/Public Signed URLs

Current decision: planning/control frozen by docs `110`/`111`; implementation not admitted.

Implementation cannot begin until these are specified:

- provider and object-store authority;
- public-vs-private URL policy;
- ACL ownership and expiry semantics;
- revocation behavior;
- response header contract;
- security review for URL leakage;
- tests proving no provider URL is emitted unless explicitly requested by the admitted lane.

This lane must stay separate from same-origin signed references. A same-origin signed reference is a server-owned token for the existing API path, not a public/provider URL.

## Connector/Destination Dispatch

Current decision: planning/control frozen by docs `112`/`113`; doc `121` selects `internal_dispatch_record_only` as the first exact lane. That runtime is live only as an internal record at `/api/v1/layer3/handoff/connector/record`; broad `connector_destination_dispatch` remains deferred.

Broader implementation cannot begin until the `121_CONNECTOR_DISPATCH_ENTRY_FREEZE.md` constraints are preserved and these are specified or explicitly kept blocked:

- destination model and allowed destination ids;
- exact dispatch mode: `internal_dispatch_record_only` for the first lane; `single_named_connector_dispatch` and `single_named_destination_dispatch` remain blocked;
- connector-run lifecycle;
- server-side connector/destination allowlist and configuration authority;
- retry, cancel, and failure semantics;
- delivery receipt format;
- operator-visible state transitions;
- authorization boundary between Layer 3 and the external destination;
- idempotency and stale-authority behavior;
- tests proving the UI/API cannot dispatch without explicit connector/destination authority.

This lane must not be folded into signed-reference UI work. The signed-reference UI may display connector/destination as disabled only.

## Package Mutation/Reconstruction

Current decision: planning/control and bounded runtime governance is frozen by docs `122`, `126`, `127`, `128`, `129`, `130`, and `131`; broad runtime package mutation/reconstruction remains not admitted. The exact `package_supersession_preview_only` runtime is live only as a read-only preview with no database writes, no package payload writes, and no in-place mutation. The exact `replacement_package_set_authority` runtime is live only as a durable metadata authority record with no replacement package rows and no package payload writes. The exact `package_supersession_commit_entry` runtime is live only as a durable immutable lineage record with no package row mutation, no package payload write, no replacement package rows, and no UI behavior. Doc `128` remains a planning/control prerequisite for artifact authority. Doc `129` governs the live `replacement_package_artifact_manifest_only` runtime, which server-verifies existing replacement refs/hashes and records an immutable manifest row without generating artifacts, creating replacement package rows, writing payloads, or admitting broad package mutation/reconstruction. Doc `130` preserves the separate-table namespace rule. Doc `131` governs the live `replacement_package_namespace_rows` runtime, which creates rows only in `l3_replacement_output_package` and still performs no source `L3OutputPackage` row mutation, package payload write, rendered control, or broad package mutation/reconstruction.

Broader implementation cannot begin until doc `122` constraints are preserved and these are specified or explicitly kept blocked:

- immutable package-row and payload-file authority;
- supersession lineage model, if a commit is ever needed;
- downstream dependency detection for package-review submit, handoff/export, APS handoff, external export/download, signed-reference delivery, and connector records;
- stale package id/ref/hash behavior;
- exact preview response schema;
- dedicated supersession lineage model/migration, if a commit is ever admitted;
- replacement package-set authority that does not reuse source package rows as replacement rows;
- replacement package artifact authority proving replacement refs and hashes are server-owned or server-verified before they are treated as reconstructable package content;
- replacement package artifact manifest-only verification before any replacement package artifact generation or package-row namespace work;
- idempotency and concurrency behavior for preview and any later commit;
- tests proving existing package construction/submit/handoff/export paths are unchanged.

This lane must not be folded into connector dispatch, provider/public URL, source expansion, qualitative/RAG, or mockup activation work.

## Durable Token/Receipt/Audit State

Current decision: bounded same-origin durable runtime state is live through PR `#520`; public/API/UI revocation, cleanup/read-model expansion, provider/public URL coupling, and rendered revoke/copy/share controls are not admitted.

Additional implementation cannot begin until these are specified:

- whether the next behavior changes the existing `single_use` replay policy;
- table/model/migration requirements beyond PR `#520`, if any;
- audit event schema beyond current generate/use events;
- receipt schema beyond current generate/use receipts;
- retention and cleanup policy;
- concurrency and idempotency behavior;
- proof that existing PR `#499` HMAC behavior and PR `#520` durable state are either preserved or intentionally superseded.

This lane likely requires schema/model/migration review if it changes the current table family and must not be hidden inside provider/public URL, connector/destination, or UI-only patches.

## Qualitative APS Content Document Execution

Current decision: `119_L3_QUAL_APS_EXEC_ENTRY_FREEZE.md` admitted and current-main code implements the exact `single_aps_doc_qualitative_pass` mode only. Doc `124_QUAL_HYBRID_RAG_FREEZE.md` adds a machine-checkable boundary contract for `single_aps_doc_qualitative_pass_only` and keeps broad qualitative/hybrid/RAG activation blocked. Docs `138`/`139` govern the live read-only `qual_aps_package_review_preview_only` runtime boundary. Docs `140`/`141` govern the live bounded `qual_aps_package_construction_commit_entry` boundary. Docs `143`/`144` govern the live bounded `qual_aps_package_review_submit_entry` boundary. Docs `145`/`146` govern the live bounded `qual_aps_handoff_export_prepare_entry` boundary. Docs `147`/`148` govern the live qualitative APS APS handoff dispatch boundary. Docs `149`/`150` govern the live qualitative APS external export/download prepare/deliver boundary only as `qual_aps_external_export_download_prepare_deliver`: readiness is recorded over the dispatched server-owned APS bundle and delivery streams that same-origin artifact. Docs `151`/`152` govern only the future rendered UI freeze for `qual_aps_rendered_downstream_existing_controls_only`; they do not make rendered controls live by themselves. Connector/provider, UI/theme runtime behavior, source/RAG, package mutation, and auth/security behavior remain deferred.

Any broader qualitative implementation cannot begin until these are specified:

- exact additional execution mode, if any, and how it composes with `single_aps_doc_qualitative_pass`;
- qualitative unit contract for APS content documents;
- method admission policy for qualitative and qualitative-document inputs;
- execution engine owner;
- input chunk ordering, limits, citation, and trace requirements;
- result schema and review semantics;
- whether output is fact/finding/insight/caveat/result, and how those terms are constrained;
- tests proving DatasetVersion quantitative execution is not reused accidentally for qualitative content.

The currently live APS content document path includes selection, trace, material preview, typing/display support, theme alignment, and the exact single-document qualitative execution pass. Current tests prove APS content documents can be listed, previewed, traced, snapshotted, typed as qualitative document chunks, executed through `single_aps_doc_qualitative_pass` without `AnalysisRun` or `DatasetVersion`, and blocked from qualitative package/handoff/export broadening.

## Mockup Truth State

Current decision: `125_MOCKUP_TRUTH_STATE_FREEZE.md` admits no runtime behavior and keeps mockups as target-state design/specification artifacts only.

Full mockup activation cannot begin until these are specified:

- exact live route, API, and owner service to be changed;
- server-owned state authority for any persisted UI state;
- proof that frontend state is recovery/cache only and not durable authority;
- exact controls being activated, with deferred controls still disabled;
- headed and headless browser proof for every activated rendered state;
- negative proof that mockup activation does not widen source, execution, connector, provider, package, or auth/security scope.

This lane must not be folded into source expansion, qualitative/RAG execution, provider/public URL, connector dispatch, package mutation, or frontend-only durable state work.

## Common Stop Conditions

Stop before implementation unless a current implementation-entry freeze names and bounds the exact surface if the intended change needs:

- new database tables or migrations;
- new connector or destination state;
- external provider credentials or ACL changes;
- package reconstruction or mutation;
- source ingestion/upload/directory expansion;
- broad qualitative/hybrid/RAG/vector execution beyond the admitted single APS-document qualitative pass;
- rendered controls beyond the exact lane being admitted;
- a claim that PR `#513` made runtime behavior live.
