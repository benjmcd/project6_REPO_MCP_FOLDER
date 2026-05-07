# Layer 3 Qualitative APS External Export/Download Contract

Status: current-main API and state contract paired with `149_QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_FREEZE.md`.

This contract defines the live API/state/proof shape for `qual_aps_external_export_download_prepare_deliver`. Current main admits the qualitative APS path only after exact qualitative APS APS handoff dispatch authority and still rejects broader source, connector, provider, package-mutation, RAG/vector, UI, theme, auth, model, and migration behavior.

## Authority Order

Qualitative APS external export/download must resolve authority in this order:

1. live source and tests on `project6-origin/main`;
2. `149_QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_FREEZE.md`;
3. `147_QUAL_APS_APS_HANDOFF_DISPATCH_FREEZE.md` and `148_QUAL_APS_APS_HANDOFF_DISPATCH_CONTRACT.md`;
4. `145_QUAL_APS_HANDOFF_EXPORT_PREPARE_FREEZE.md` and `146_QUAL_APS_HANDOFF_EXPORT_PREPARE_CONTRACT.md`;
5. `143_QUAL_APS_PACKAGE_REVIEW_SUBMIT_FREEZE.md` and `144_QUAL_APS_PACKAGE_REVIEW_SUBMIT_CONTRACT.md`;
6. `140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE.md` and `141_QUAL_APS_PACKAGE_CONSTRUCTION_CONTRACT.md`;
7. `138_QUAL_APS_PACKAGE_REVIEW_FREEZE.md` and `139_QUAL_APS_PACKAGE_REVIEW_CONTRACT.md`;
8. qualitative execution governance in `114_QUAL_APS_EXEC_FREEZE.md`, `115_QUAL_APS_EXEC_CONTRACT.md`, and `119_L3_QUAL_APS_EXEC_ENTRY_FREEZE.md`;
9. current external export/download services in `backend/app/services/layer3_workbench.py`, `backend/app/services/layer3_external_export_response.py`, `backend/app/services/layer3_external_export_contract.py`, and `backend/app/api/layer3.py`;
10. current bounded E2E and API tests;
11. request payload as operator readiness or delivery intent only;
12. browser state as non-authoritative display/cache only.

Planning prose, browser state, raw document text, mockup state, PR titles, branch names, client-provided package bytes, and client-provided APS bundle bytes are never sufficient external export/download authority.

## Route Contract

Selected live prepare route:

- `POST /api/v1/layer3/handoff/export/download/prepare`

Selected live prepare response schema:

- `layer3.qual_aps_external_export_download_prepare.v1`

Selected live deliver route:

- `POST /api/v1/layer3/handoff/export/download/deliver`

Selected live delivery schema/header:

- `layer3.qual_aps_external_export_download_delivery.v1`

Route reuse is preferred because the existing route family already separates readiness preparation from same-origin artifact delivery, signed-reference generation/use, connector record behavior, and provider/public URL behavior. A new route is allowed only if source inspection proves route reuse would make qualitative APS and associated-cohort authority ambiguous.

## Prepare Request Contract

Expected required fields:

- `client_request_id`;
- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `preview_id`;
- `preview_hash`;
- `result_review_record_ref`;
- `package_review_preview_hash`;
- `reconciliation_record_id`;
- `output_package_ids`;
- `package_kinds`;
- `payload_refs`;
- `payload_hashes`;
- `package_review_submit_record_ref`;
- `package_review_state`;
- `prepare_record_ref`;
- `handoff_export_state`;
- `handoff_export_envelope_ref`;
- `handoff_target`;
- `export_mode`;
- `aps_handoff_record_ref`;
- `aps_handoff_state`;
- `aps_handoff_target`;
- `dispatch_mode`;
- `aps_output_package_id`;
- `aps_output_package_kind`;
- `aps_bundle_ref`;
- `aps_bundle_id`;
- `aps_schema_id`;
- `export_download_target`;
- `download_mode`;
- `operator_decision`.

Conditionally allowed:

- `decision_notes`;
- `analysis_run_id`, but it must be absent or null for qualitative APS execution;
- `aps_bundle_hash` and `aps_bundle_size_bytes` only if they are treated as client echo fields and revalidated against persisted server-owned artifact authority.

Required values:

- `package_review_state`: `package_review_approved`;
- `handoff_export_state`: `handoff_export_prepared` or the shared-route persisted equivalent for the qualitative prepared envelope;
- `handoff_target`: `internal_export_envelope`;
- `export_mode`: `prepare_only`;
- `aps_handoff_state`: `aps_handoff_dispatched`;
- `aps_handoff_target`: `aps_evidence_bundle`;
- `dispatch_mode`: `server_side_aps_handoff`;
- `aps_output_package_kind`: `aps_evidence_bundle_handoff`;
- `export_download_target`: `aps_evidence_bundle_download_reference`;
- `download_mode`: `reference_only_prepare`;
- `operator_decision`: `prepare_external_export_download`.

Forbidden prepare fields include provider/public URL fields, signed URL fields, connector fields, destination fields, local paths, external target fields, package mutation/reconstruction fields, package payload overrides, source expansion fields, upload fields, local-directory fields, web connector fields, RAG/vector fields, adapter registry fields, prompt/model/LLM fields, retry/recovery/rerun fields, cancel fields, auth fields, UI fields, theme fields, and mockup fields.

## Delivery Request Contract

Expected required fields include the prepare authority fields that identify session, plan, pass, package, handoff, APS dispatch, and readiness authority, excluding prepare-only intent fields (`operator_decision` and `decision_notes`) and adding:

- `external_export_download_record_ref`;
- `export_download_descriptor_ref`;
- `external_export_download_state`;
- `delivery_mode`.

Required values:

- `external_export_download_state`: `external_export_download_prepared`;
- `delivery_mode`: `same_origin_artifact_stream`;
- `operator_decision`: `deliver_external_export_download`;
- `export_download_target`: `aps_evidence_bundle_download_reference`;
- `download_mode`: `reference_only_prepare`.

Delivery must use the recorded readiness object as durable authority. Delivery must not accept raw artifact bytes, arbitrary paths, public URLs, signed URLs, provider URLs, connector ids, destination ids, credentials, package edits, source expansion instructions, prompt/model fields, UI/theme fields, or mockup fields.

Delivery overrides prepare intent. It must use `operator_decision: deliver_external_export_download` and must not inherit `prepare_external_export_download` from the prepare request.

## Admission Contract

An available qualitative APS external export/download prepare requires:

- current session exists and matches the request;
- approved analysis plan exists and matches `preview_id` and `preview_hash`;
- selected pass run exists for the same session and approved plan;
- pass run engine family is `qualitative_aps_document`;
- pass scope is `single_aps_doc_qualitative_pass`;
- qualitative execution is terminal with readable output metadata;
- `analysis_run_id` is absent or null;
- result-review state is approved and matches request authority;
- package-review preview state and hash match server-derived qualitative authority;
- package construction state exists for source gate `140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE`;
- exactly one reconciliation record and exactly three reviewed package rows exist for `canonical_internal`, `user_facing`, and `review_facing`;
- package-review submit state exists, is approved, and uses schema `layer3.qual_aps_package_review_submit.v1`;
- handoff/export prepare state exists with matching prepare record ref and internal envelope ref;
- APS handoff dispatch state exists with matching APS handoff record ref;
- APS output package row exists for `aps_evidence_bundle_handoff`;
- APS bundle ref, bundle id, schema id, payload hash, file hash, and file size match server-owned artifact authority;
- no existing qualitative external export/download readiness state conflicts with the request.

An available qualitative APS delivery requires:

- recorded external export/download readiness state is `external_export_download_prepared`;
- supplied readiness ref and descriptor ref match recorded readiness;
- supplied APS bundle ref/id/schema match recorded readiness and current APS handoff package authority;
- prepare validation still succeeds against current persisted state and server-owned artifact hash/size;
- delivery mode is same-origin artifact streaming.

Any missing, stale, malformed, mismatched, non-approved, duplicate-conflicting, or cross-session authority must fail closed before mutation or streaming.

## State Contract

Allowed state effects for successful prepare:

- record exactly one qualitative APS external export/download readiness object in `L3ReconciliationRecord.summary_json`;
- optionally record session summary pointer fields in `L3Session.summary_json`.

Allowed state effects for successful delivery:

- stream the existing server-owned APS bundle artifact;
- no DB row creation;
- no DB row mutation;
- no file creation;
- no file mutation.

Forbidden state effects:

- create reconciliation rows or mutate reconciliation rows except for the single admitted qualitative APS external export/download readiness object in existing `L3ReconciliationRecord.summary_json` during prepare;
- mutate reconciliation rows during delivery;
- create or mutate output package rows, source authority rows, connector rows, destination rows, provider rows, delivery rows, signed-reference rows, auth rows, source-ingestion rows, RAG/vector rows, runtime snapshot rows, mockup rows, plan rows, pass rows, run rows, artifact rows, or migration/model state;
- mutate package payload files, APS bundle files, qualitative execution output, result-review state, package-review preview state, package construction state, package-review submit state, handoff/export prepare state, APS handoff dispatch state, package refs, package hashes, or source authority rows.

## Response Contract

Minimum live prepare response fields:

- `schema_id`;
- `status`;
- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `preview_identity`;
- `analysis_run_id`;
- `result_review_record_ref`;
- `package_review_preview_hash`;
- `reconciliation_record_id`;
- `output_package_ids`;
- `package_kinds`;
- `payload_refs`;
- `payload_hashes`;
- `package_review_submit_record_ref`;
- `package_review_state`;
- `prepare_record_ref`;
- `handoff_export_state`;
- `handoff_export_envelope_ref`;
- `handoff_target`;
- `export_mode`;
- `aps_handoff_record_ref`;
- `aps_handoff_state`;
- `aps_handoff_target`;
- `dispatch_mode`;
- `aps_output_package_id`;
- `aps_output_package_kind`;
- `aps_bundle_ref`;
- `aps_bundle_id`;
- `aps_schema_id`;
- `export_download_target`;
- `download_mode`;
- `operator_decision`;
- `external_export_download_state`;
- `external_export_download_record_ref`;
- `export_download_descriptor_ref`;
- `source_artifact_ref`;
- `source_artifact_schema_id`;
- `source_artifact_hash`;
- `source_artifact_size_bytes`;
- `browser_download_enabled`;
- `download_url_enabled`;
- `connector_dispatch_enabled`;
- `destination_selection_enabled`;
- `generic_downstream_dispatch_enabled`;
- `downstream_unavailable`;
- `next_state`;
- `authority_rail`.

Minimum live delivery response/header contract:

- schema id/header `layer3.qual_aps_external_export_download_delivery.v1`;
- source artifact ref/hash/size headers or authority payload;
- same-origin attachment filename/media type derived from the server-owned APS bundle;
- no public URL, signed URL, provider URL, connector run id, destination id, or mutable package payload body.

## Idempotency And Concurrency Contract

`client_request_id` is required for prepare and delivery.

Rules:

- duplicate prepare `client_request_id` with the same readiness basis returns the same readiness state or an explicit already-prepared response;
- duplicate prepare `client_request_id` with a different readiness basis fails closed;
- conflicting later prepare requests fail closed unless they prove the same authority basis;
- delivery revalidates current readiness and never relies on browser state alone;
- concurrent prepare attempts cannot create duplicate or divergent readiness state;
- partial readiness state fails closed.

The readiness basis hash must include request identity fields, result-review record ref, package-review preview hash, package-review submit record ref, prepare record ref, handoff/export envelope ref, APS handoff record ref, APS bundle ref/id/schema, source artifact hash/size, reconciliation id, package ids, package kinds, payload refs, payload hashes, operator decision, and decision notes.

## Failure Contract

The runtime must fail closed when:

- the qualitative APS pass is not the exact standalone APS content-document qualitative pass;
- qualitative APS external export/download would otherwise be bypassed without a recorded APS handoff dispatch;
- session, plan, preview hash, pass run, output metadata, result-review state, package-review preview state, construction state, package-review submit state, handoff/export prepare state, APS handoff dispatch state, reconciliation record, package rows, APS handoff package row, APS bundle artifact, content document, chunks, material snapshot, analysis unit, or analysis set is missing;
- any supplied ref, hash, id, schema id, state, package list, package kind list, payload ref list, or payload hash list differs from persisted authority;
- bundle file hash or size differs from package/readiness authority;
- forbidden fields are present;
- provider/public URL, signed URL, connector/destination, package mutation, source expansion, RAG/vector, hidden LLM, UI/theme, model/migration, or auth/security behavior would be required.

## Required Proof

Before runtime implementation can be considered complete:

- focused API tests must prove prepare success, delivery success, and all required fail-closed cases;
- the bounded qualitative APS E2E must extend from APS handoff dispatch through prepare and deliver;
- associated-cohort external export/download prepare, deliver, delivery UI, and signed-reference tests must remain green;
- `tools/l3-progress-check.py` must guard the qualitative APS freeze/contract docs and current runtime proof terms;
- `git diff --check` must pass apart from known line-ending warnings if present.
