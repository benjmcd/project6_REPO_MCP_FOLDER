# Phase P12 Mixed-Source Package Contract

Status: governed contract defined; no runtime behavior admitted.

## Scope

This phase defines the governed mixed-source package contract that follows the Phase P11 material-preview readiness projection.

The live readiness authority is the material-preview response field `mixed_source_package_semantics` with schema id `layer3.mixed_source_package_semantics_readiness.v1`. A future runtime pass may only proceed when valid `dataset_version` and `aps_content_document` material candidates are both present and the readiness response says:

- `material_authority_state`: `mixed_material_authority_present`
- `package_semantics_state`: `governed_contract_required`
- `next_allowed_actions`: `["define_mixed_source_package_contract"]`

This document satisfies that next allowed planning action. It does not enable package construction, package review preview, package review submit, handoff, export, schema changes, parser changes, source-shape expansion, or Onlook work.

## Contract Identity

Future implementation must use this contract identity unless a later contract supersedes it:

- `schema_id`: `layer3.mixed_source_package_contract.v1`
- `contract_scope`: `dataset_version_plus_aps_content_document`
- `contract_owner`: `layer3_workbench_package_state`
- `admission_boundary`: `material_preview_readiness_only_until_registry_enabled`

The contract is intentionally scoped to already-valid material candidates. It does not admit new parser behavior, generic XML/HTML, archive-member orchestration, arbitrary file upload, new source classes, raw mixed package mutation, or frontend-only authority.

## Required Authority Basis

A mixed-source package contract instance must derive from a single material-preview result and must carry:

- `material_preview_id`
- `material_preview_hash`
- `dataset_version_ids`
- `aps_content_document_ids`
- `admitted_source_classes`
- `source_trace` summaries for every included material candidate
- `source_provenance` summaries for every included material candidate

The future implementation must fail closed when any of these are missing, empty, malformed, duplicated unexpectedly, stale against the selected material preview, or inconsistent with the material candidates returned by the owner service.

The contract must not re-fetch source data, infer hidden source identity, read untracked local files, use generated session text as authority, or substitute stale candidates when the latest selected material preview is invalid.

## Narrative-Table Linking

Mixed-source packages need explicit links between document evidence and tabular evidence. A future package payload must represent those links as deterministic records, not as prose-only claims.

Each link record must include:

- `link_id`
- `document_ref`
- `dataset_ref`
- `evidence_role`
- `link_type`
- `link_basis`
- `source_trace_refs`

Allowed `link_type` values for the first runtime pass are:

- `same_artifact_family`
- `shared_run_or_target`
- `operator_selected_pair`

The first runtime pass must not admit model-inferred semantic matching, fuzzy entity resolution, financial-statement interpretation, cross-document synthesis, or generated narrative conclusions as link authority. Those can only be introduced by a later contract with its own tests and non-goals.

## Package Payload Semantics

A mixed-source package payload must be a manifest over existing authority, not a rewrite of source material.

Required top-level payload fields:

- `schema_id`: `layer3.mixed_source_package_payload.v1`
- `contract_schema_id`: `layer3.mixed_source_package_contract.v1`
- `material_preview_id`
- `material_preview_hash`
- `source_manifest`
- `document_evidence`
- `dataset_evidence`
- `narrative_table_links`
- `negative_authority_flags`

`source_manifest` must preserve the source class, source ref, source identity, source family, provenance ref, parser family where present, and validation status for each selected candidate.

`document_evidence` must refer to existing `aps_content_document` and chunk/linkage authority. It must not inline raw source documents, expose local absolute paths, or create new document rows.

`dataset_evidence` must refer to existing `dataset_version` authority. It must not rewrite rows, mutate variables, materialize new datasets, or silently downgrade table semantics to document text.

`negative_authority_flags` must explicitly keep these false in the first runtime pass:

- `schema_or_migration_changed`
- `parser_behavior_changed`
- `new_source_shape_admitted`
- `package_payload_rewrite_performed`
- `handoff_enabled`
- `export_enabled`
- `onlook_included`

P14 current-runtime note: P14 admits only read-only mixed-source package review
preview from committed Gate B material authority and this contract. Package
construction, submit, handoff, export, parser, schema, source-shape, payload
rewrite, legacy bridge deprecation, and Onlook behavior remain outside the
admitted runtime.

## Review Preview Requirements

Before package review preview is enabled for mixed sources, implementation must add a package-family policy registry that can answer whether `mixed_dataset_document` is admitted for preview, commit, submit, and handoff independently.

The first preview implementation must be read-only and must return:

- package family: `mixed_dataset_document`
- contract schema id and contract hash
- selected source ids
- narrative-table link count
- blocked downstream actions
- missing authority inputs
- negative authority flags

Preview must fail closed if a caller provides package payload content, handoff/export fields, schema/migration fields, source-expansion fields, local upload fields, Onlook fields, or any source identity not present in the material preview.

## Commit Behavior

Package construction for mixed sources remains blocked until a later runtime pass enables it through the package-family policy registry.

When enabled later, commit idempotency must include:

- package family
- material preview hash
- contract hash
- sorted dataset version ids
- sorted APS content document ids
- sorted narrative-table link ids
- expected package kinds
- operator request id

Commit must be idempotent for the same authority basis and must reject stale, broadened, or partially overlapping authority bases. It must not mutate source packages, replace source datasets/documents, or create handoff/export records.

## Handoff Policy

Handoff remains unavailable for mixed-source packages until package review submit is approved and a separate handoff/export policy admits the exact downstream target.

The handoff policy must preserve:

- redacted payload refs only
- no raw local paths
- no raw provider tokens
- no public URL behavior
- no connector/destination dispatch unless separately selected
- no frontend-only durable authority

## Required Future Verification

The future runtime sequence is:

1. Package-family policy registry, with no behavior change.
2. Mixed-source package review preview, read-only.
3. Mixed-source package construction commit.
4. Mixed-source package review submit.
5. Mixed-source handoff/export prepare only after a separate downstream policy.

Each runtime pass must include focused tests for happy path, missing authority, stale preview hash, unexpected source class, duplicate source ids, forbidden fields, Onlook exclusion, and no schema/migration/runtime widening beyond the named pass.

## Residual Work

The package-family policy registry prerequisite is satisfied by `29-p13-package-family-policy.md`. Mixed-source package review preview, construction commit, package-review submit, handoff, and export remain separate future runtime passes; `mixed_dataset_document` remains explicitly blocked until those passes prove this contract.

Legacy CSV bridge deprecation remains a separate decision and must not be coupled to mixed-source package semantics.
