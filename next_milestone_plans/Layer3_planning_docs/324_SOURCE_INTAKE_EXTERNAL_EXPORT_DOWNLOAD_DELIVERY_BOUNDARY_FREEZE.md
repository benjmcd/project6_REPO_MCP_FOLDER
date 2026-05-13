# 324 - Source Intake External Export Download Delivery Boundary Freeze

Status: planning/control freeze for `source_intake_external_export_download_delivery_boundary`, with branch-local fail-closed guard for the current delivery over-admission risk.

Branch: `codex/l3-source-intake-download-delivery-freeze`
Current-main predecessor commit: `1dbd71744fbada7d52eceacc6fed5167fb1a1d08`
Predecessor implementation: `323_SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_BOUNDARY.md`
Owner service: `backend/app/services/layer3_workbench.py`
Response helper: `backend/app/services/layer3_external_export_response.py`
Current failure boundary: `source_intake_external_export_download_delivery_not_admitted`

## Canonical source of truth

The canonical source of truth for any future source-intake external export/download delivery is the server-owned prepare/readiness state recorded by `external_export_download_prepare` with schema `layer3.source_intake_external_export_download_prepare.v1`, plus the upstream durable source-intake APS handoff dispatch and package chain:

- `layer3.source_intake_aps_handoff_dispatch.v1`
- `layer3.source_intake_handoff_export_prepare.v1`
- `layer3.source_intake_package_review_submit.v1`
- `layer3.source_intake_package_construction_commit.v1`
- `layer3.source_intake_execution_output.v1`

The delivery boundary must not treat browser state, local paths, caller-supplied bundle metadata, provider/public URLs, signed URLs, connector state, or generic downstream dispatch as authority.

## Live boundary correction

PR #916 admitted source-intake prepare/readiness. Audit for this freeze identified that the existing generic `external_export_download_deliver` path revalidates through `external_export_download_prepare`, so source-intake readiness needed an explicit fail-closed delivery guard before delivery can be truthfully treated as a future boundary.

This branch therefore records the live failure boundary as `source_intake_external_export_download_delivery_not_admitted`: source-intake prepare/readiness remains available, but same-origin artifact streaming remains blocked until a dedicated delivery implementation proves the full server-authoritative chain.

## Frozen next code-bearing action

The next code-bearing action is `implement_source_intake_external_export_download_delivery_boundary` only.

That future implementation may reuse the existing `external_export_download_deliver` contract only if it proves exact compatibility with source-intake readiness. It must require source-intake prepare/readiness state, APS handoff dispatch state, APS evidence-bundle handoff package identity, source package refs/hashes, descriptor identity, artifact hash/size, and source-intake identity to match durable server-owned state before returning a same-origin artifact stream.

The implementation must produce a source-intake-specific delivery authority signal, rather than silently falling through to the generic delivery schema. It must not create `AnalysisRun`, mutate source packages, create new packages, expose provider/public/signed URLs, dispatch to connectors or destinations, rely on browser/local path authority, add rendered UI controls, or widen route/model/migration/auth/security behavior.

## Required future proofs

- `source_intake_external_export_download_prepare_can_deliver_same_origin_artifact_stream`
- `source_intake_delivery_revalidates_prepare_readiness_state`
- `source_intake_delivery_revalidates_aps_handoff_dispatch_state`
- `source_intake_delivery_revalidates_descriptor_ref`
- `source_intake_delivery_revalidates_aps_bundle_ref_id_schema_hash_and_size`
- `source_intake_identity_preserved_in_delivery_authority`
- `no_analysis_run_required_or_created`
- `no_source_package_rows_or_payloads_mutated`
- `mismatched_external_export_download_record_ref_fails_closed`
- `mismatched_export_download_descriptor_ref_fails_closed`
- `mismatched_aps_bundle_ref_or_hash_fails_closed`
- `connector_destination_dispatch_remains_blocked`
- `provider_public_private_url_remains_blocked`
- `signed_reference_behavior_remains_blocked`
- `rendered_ui_controls_remain_blocked`
- `existing_associated_cohort_single_aps_qualitative_aps_and_source_intake_prepare_unchanged`

## Explicit non-goals

- rendered delivery controls
- connector dispatch or destination selection
- provider public/private URL behavior
- signed-reference generation or use
- public object-store ACL behavior
- package mutation, copying, reconstruction, amendment, or supersession
- source package row mutation or source payload rewriting
- generic source upload, local file selection, or local directory ingestion
- source adapter registry or source-family expansion
- RAG/vector retrieval or hybrid qualitative analysis
- backend route changes unless route reuse is proven ambiguous
- model or migration changes
- auth/security behavior changes
- broad qualitative execution
- full mockup activation

## Stop condition for this freeze

This freeze is complete when the planning doc, progress board, progress manifest, proof manifest, checker, owner-service guard, and targeted test all agree that source-intake external export/download delivery is blocked at `source_intake_external_export_download_delivery_not_admitted` and selected as the next exact runtime boundary.
