# 664 - Source L3 Output Package Replacement Activation Freeze

## Status

Status: implementation-entry freeze for `source_l3_output_package_replacement_activation`.

Doc: `664_SOURCE_L3_OUTPUT_PACKAGE_REPLACEMENT_ACTIVATION_FREEZE.md`.

Predecessor current-main sync doc: `663_RENDERED_REPLACEMENT_PACKAGE_NAMESPACE_CONTROL_RUNTIME_CURRENT_MAIN_SYNC.md`.

Current-main preflight commit: `1352b18e205ebe961d94db9579a32fe34dca40b9`.

Current selected surface: `package_mutation_reconstruction`.

Selected package lifecycle action: `activate_replacement_output_package_namespace`.

Selected implementation-entry mode: `source_l3_output_package_replacement_activation`.

Selected future route: `POST /api/v1/layer3/package/replacement-activation/commit`.

Future owner service: `backend/app/services/layer3_package_replacement_activation.py`.

Entry decision: `freeze_only`.

Runtime status in this pass: `not_implemented_in_this_pass`.

## Selection Rationale

Current main already records replacement package namespace rows through `POST /api/v1/layer3/package/replacement-namespace/record`, renders `State.replacementPackageNamespace`, and preserves the source `L3OutputPackage` rows unchanged. That is the correct staging posture, but downstream handoff/export still has no governed current-package authority that points at the replacement package set.

This freeze selects the smallest next mutating package lifecycle step needed for end-to-end Layer 3 use: activate one complete, already-governed replacement package namespace as the current package authority for the session. It comes before downstream invalidation, re-delivery, source expansion, RAG/vector work, or provider-public delivery because those later steps need a single authoritative package set to consume.

The rejected alternatives for this pass are broader:

- Package rebuild from corrected artifacts is upstream of the already-recorded replacement artifacts and namespace rows.
- Package payload rewrite would accept or generate new package bytes and is broader than activating already-governed artifacts.
- Downstream invalidation and re-delivery depend on knowing which package set is active.
- Source expansion and RAG/vector need package authority to be settled before they can safely consume or index outputs.

## Current Authority Inputs

The future runtime may use only existing current-main authority:

- `L3ReplacementOutputPackage` rows produced by `record_replacement_package_namespace_row`.
- `L3ReplacementPackageArtifactManifest` authority from the server-computed replacement artifact manifest runtime.
- `L3ReplacementPackageSetAuthority` authority from the replacement package set authority lane.
- `L3PackageSupersessionCommit` authority from the package supersession commit lane.
- Existing source `L3OutputPackage` rows for the same `session_id` and package kinds.
- Server-held artifact hash and byte-size verification already recorded in the replacement artifact manifest.

The future runtime must not accept browser/operator package bytes, arbitrary refs, arbitrary hashes, local paths, URLs, or destination instructions as authority.

## Future Request Contract

The future request must be allowlisted and must fail closed on unknown or forbidden fields.

Required request fields:

- `client_request_id`
- `session_id`
- `replacement_artifact_manifest_id`
- `replacement_package_set_authority_id`
- `package_supersession_commit_id`
- `replacement_output_package_ids`
- `source_output_package_ids`
- `package_kinds`
- `replacement_activation_basis_hash`
- `operator_decision`

Required values:

- `operator_decision`: `activate_replacement_output_package_namespace`
- `package_kinds`: the complete package-kind set expected by current package authority
- `replacement_activation_basis_hash`: server-verifiable basis over the source package rows, replacement namespace rows, replacement artifact manifest, replacement package-set authority, package supersession commit, package kinds, operator decision, and client request id

Forbidden request fields include:

- `package_payload`
- `package_payload_bytes`
- `replacement_package_payloads`
- `replacement_content`
- `artifact_bytes`
- `generated_file_bytes`
- `rebuild_package`
- `rewrite_output`
- `mutate_package`
- `replace_package_bytes`
- `destination_path`
- `destination_url`
- `local_directory`
- `source_upload`
- `connector_run_id`
- `connector_payload`
- `provider_public_url`
- `public_url`
- `signed_url`
- `download_url`
- `rag_vector_index`
- `qualitative_execution_instruction`
- `hidden_llm_prompt`
- `auth_context`
- `security_context`

## Future Runtime Boundary

The future runtime may perform exactly one bounded mutation: atomically mark one complete replacement namespace set as active package authority for the session.

Admitted future mutation:

- Persist durable activation receipt/state for `source_l3_output_package_replacement_activation`.
- Bind each active package kind to the already-recorded `L3ReplacementOutputPackage` row for the same session.
- Preserve `uq_l3_output_package_session_kind` and the existing source package identity model.
- Update only the explicitly frozen package-activation authority fields needed for downstream package resolution, if the implementation audit proves those fields are the existing source-of-truth path.
- Return response-safe artifact refs and hashes from server-held replacement namespace and manifest authority.

Not admitted in this freeze:

- New package generation.
- Package payload byte rewrite.
- Browser-supplied package or replacement bytes.
- Browser-supplied artifact refs, hashes, byte sizes, paths, or URLs.
- Creation of additional source `L3OutputPackage` rows that weakens `uq_l3_output_package_session_kind`.
- Downstream invalidation.
- Re-delivery.
- Connector or destination dispatch.
- Provider-public delivery/use.
- Source expansion.
- RAG/vector behavior.
- Auth/security broadening.
- Full mockup activation.
- Frontend-durable authority.

If implementation audit proves safe downstream resolution requires a separate activation table instead of direct `L3OutputPackage` field mutation, the implementation may use that narrower activation table pattern only if it preserves the selected `source_l3_output_package_replacement_activation` operator action and proves downstream reads resolve from the same durable activation authority. It must not use that as permission to add broad package reconstruction or downstream delivery.

## Idempotency Contract

The future runtime must enforce:

- Same `client_request_id` plus same complete activation basis returns the same activation receipt/status.
- Same `client_request_id` plus different basis fails closed.
- Same complete activation basis plus new `client_request_id` returns existing activation status rather than creating duplicate active state.
- Existing active state for the same session/package-kind set returns existing status when identical.
- Existing active state for the same session/package-kind set fails closed when conflicting.
- Partial replacement namespace state cannot become active.
- Activation is all-or-nothing across the complete package-kind set.

## Failure Lifecycle

The future runtime must fail closed on:

- Missing session.
- Missing source package row.
- Missing replacement namespace row.
- Missing replacement artifact manifest.
- Missing replacement package-set authority.
- Missing package supersession commit.
- Wrong session.
- Wrong package kind.
- Incomplete package-kind set.
- Stale source package basis.
- Stale replacement namespace basis.
- Stale manifest basis.
- Stale replacement package-set authority basis.
- Stale supersession commit basis.
- Tampered artifact ref.
- Tampered artifact hash.
- Duplicate client request conflict.
- Existing active package-set conflict.
- Partial activation write.
- Raw local path exposure.
- Caller-supplied arbitrary path or URL.
- Any request field that tries to rebuild, rewrite, dispatch, deliver, ingest, index, or broaden auth/security.

Failures must return redacted error codes, blocked fields, and next allowed actions. They must not expose raw filesystem paths, package payload bytes, credential material, connector payloads, or hidden planning content.

## Response And Audit Contract

The future response must include:

- Durable activation receipt id.
- `session_id`.
- Source output package ids.
- Replacement output package ids.
- Replacement artifact manifest id.
- Replacement package-set authority id.
- Package supersession commit id.
- Package kinds.
- Response-safe active artifact refs.
- Artifact hashes.
- Activation status/history.
- Created/updated timestamps.
- Idempotency key.
- Redacted failure code when applicable.
- Disabled side-effect flags.
- Next state.

The future response must not expose:

- Raw local paths.
- Browser/operator destination paths.
- Package bytes.
- Replacement bytes.
- Connector payloads.
- Public URLs.
- Tokens or credentials.

## Proof Requirements

Implementation proof for this selected slice must include:

- Backend/API success proof for activating a complete replacement package namespace set.
- Idempotent replay proof for same key and same basis.
- Conflict proof for same key with different basis.
- Existing-basis replay proof with a new key.
- Fail-closed proof for stale source package authority.
- Fail-closed proof for stale replacement namespace authority.
- Fail-closed proof for missing namespace rows.
- Fail-closed proof for incomplete package-kind set.
- Fail-closed proof for wrong session and wrong package kind.
- Fail-closed proof for tampered artifact ref/hash.
- Fail-closed proof for conflicting active package state.
- Partial-write rollback proof.
- Redaction proof for raw local paths and package bytes.
- Negative proof that no package rebuild, package payload rewrite, downstream invalidation, re-delivery, connector dispatch, provider-public delivery, source expansion, RAG/vector behavior, auth/security broadening, full mockup activation, or frontend-durable authority occurs.

Rendered controls are not admitted by this freeze. If activation needs an operator-visible submit/status surface after backend/API implementation, that rendered control must be selected by a separate freeze after the backend/API runtime is merged and synced, unless current-main authority at that future point explicitly admits the rendered slice.

## Future Sequence

Immediate next pass after this freeze merges and is current-main synced:

1. Current-main sync for `664_SOURCE_L3_OUTPUT_PACKAGE_REPLACEMENT_ACTIVATION_FREEZE.md`.
2. Backend/API implementation of `source_l3_output_package_replacement_activation` only.
3. Runtime proof doc and targeted backend/API tests for authority, idempotency, failure lifecycle, redaction, all-or-nothing activation, and disabled side effects.
4. PR review/check/thread inspection, merge if clean, then current-main proof/control sync.

Mid-term package lifecycle sequence after activation runtime is synced:

1. Rendered activation submit/status freeze if operator-visible activation is needed.
2. Rendered activation runtime with headed/headless E2E only if the UI changes.
3. Downstream invalidation freeze for stale export/handoff/delivery artifacts that were built from pre-activation package authority.
4. Downstream invalidation runtime, then sync.
5. Re-delivery or re-export freeze for already-admitted controlled local export/outbox surfaces, then runtime and sync.
6. Package lifecycle hardening pass for activation history, operator review status, and failure-state projection if not already covered by runtime proof.

Long-term Layer 3 Data Structuring & Processing sequence:

1. Complete controlled package mutation/reconstruction lifecycle through activation, invalidation, and re-export.
2. Select exactly one named source-family expansion, such as local CSV/JSON/TXT/MD directory ingestion, and freeze it separately.
3. Implement that one source-family intake with isolated runtime state, provenance, validation, and no arbitrary path editing.
4. Sync source-family proof/control state.
5. Select one RAG/vector or qualitative-hybrid retrieval mode after source/index authority is defined.
6. Implement retrieval/index lifecycle with provenance, evaluation boundaries, redaction, and storage cleanup.
7. Add auth/security hardening only for the external surfaces that became real.
8. Integrate the proven slices into an end-to-end operator flow: source intake, analysis/validation, package review, replacement activation, handoff/export, controlled delivery, and governed downstream retrieval/qualitative analysis.

## Non-Admission Boundary

This freeze admits no runtime implementation. It does not add package rebuild, package payload rewrite, replacement artifact generation, source expansion, RAG/vector behavior, qualitative-hybrid execution, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, browser-supplied package bytes, browser-supplied replacement bytes, browser-supplied artifact bytes, browser-supplied arbitrary artifact refs, browser-supplied arbitrary hashes, or hidden LLM planning.

## Next Posture

After this freeze is merged, the next exact posture is `current_main_sync_source_l3_output_package_replacement_activation_freeze`.

After the freeze is current-main synced, the next exact implementation posture is `implement_source_l3_output_package_replacement_activation_after_freeze_sync`, unless implementation audit proves current package activation cannot be done without package payload rewrite, raw path exposure, downstream invalidation, or another forbidden surface. In that case the required stop posture is `select_package_activation_storage_boundary_after_freeze_sync`.
