# Layer 3 Selected-Pass Cohort External Export Download Delivery Freeze

## Status

Current-main governance from PR `#481`, with branch-local implementation proof on `codex/l3-cohort-delivery-impl-p17`.

This document does not implement runtime behavior by itself. The branch-local implementation audit proves that the existing same-origin `POST /api/v1/layer3/handoff/export/download/deliver` backend/API endpoint can stream an exact associated-cohort readiness artifact after revalidating the recorded PR `#479` descriptor and the APS evidence-bundle handoff artifact. It does not admit rendered download controls, public URLs, signed URLs, connector dispatch, generic downstream dispatch, destination selection, package mutation/rebuild, schema/runtime/source widening, qualitative/hybrid/RAG/vector behavior, or full mockup activation.

## Current Live Baseline

Current `project6-origin/main` includes:

- exact selected-pass associated-cohort `descriptive_summary` execution/result-review authority;
- associated-cohort package-review preview, package construction, and package-review submit;
- associated-cohort handoff/export prepare-only backend/API and rendered prepare authority projection;
- associated-cohort APS evidence-bundle handoff dispatch from PR `#466`;
- associated-cohort external export/download readiness from PR `#479`.

The live associated-cohort readiness boundary remains reference-only until a delivery request is made through the existing same-origin backend/API delivery endpoint. This branch adds executable proof that delivery revalidates that recorded descriptor and streams only the existing APS evidence-bundle handoff artifact; it still keeps rendered browser controls, public/signed URL generation, connector dispatch, destination selection, generic downstream dispatch, package mutation, schema/runtime/source widening, broader UI, and full mockup behavior unavailable.

## Authority Boundary

This freeze is downstream of the exact associated-cohort chain already frozen and implemented by docs `77` through `97`, including:

- service-owned associated-cohort `descriptive_summary` materialization;
- selected-pass associated-cohort execution/result-status and result review;
- package-review preview, package construction, and package-review submit;
- handoff/export prepare-only state;
- APS evidence-bundle handoff dispatch;
- reference-only external export/download readiness.

Docs `66_L3_WB_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FREEZE.md` and `67_L3_WB_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_API_AND_STATE_CONTRACT.md` remain the closest general single-item delivery precedent. They are pattern evidence for same-origin artifact streaming, not direct authority to deliver associated-cohort artifacts without the cohort-specific gates in this freeze and `99_COHORT_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_CONTRACT.md`.

## Slice Decision

The planning boundary selected by PR `#481` is:

> Freeze backend/API same-origin associated-cohort external export/download delivery after exact PR `#479` readiness. The endpoint may stream only the existing validated APS evidence-bundle handoff artifact to an authorized workbench caller after the server revalidates the full associated-cohort authority chain. It must not create public or signed URLs, connector runs, destination bindings, generic downstream dispatch, new rows, copied package payloads, rewritten artifacts, schema/runtime/source changes, or rendered download controls.

This is smaller than a general associated-cohort export feature. It deliberately separates:

- server-side delivery of the already validated APS evidence-bundle artifact;
- rendered `/review/layer3` download controls, which require separate UI governance;
- public/signed URL generation, destination selection, and connector/generic dispatch, which remain later higher-blast-radius decisions.

## Branch-Local Implementation Proof

Branch `codex/l3-cohort-delivery-impl-p17` does not add a new route or owner-service. It proves that the existing delivery endpoint already re-runs `external_export_download_prepare(...)` from recorded readiness state before streaming bytes, so stale associated-cohort APS dispatch provenance such as mismatched `source_dataset_version_ids` fails closed with `associated_cohort_external_export_download_prepare_not_admitted`. The proof is backend/API only and changes no rendered `/review/layer3` controls.

## Admitted Implementation Scope

An implementation governed by this freeze may add or prove only:

- one thin backend/API delivery path for associated-cohort readiness, or reuse of the existing delivery path when executable proof shows the cohort-specific authority branch remains explicit and fail-closed;
- server-side revalidation of the recorded PR `#479` readiness descriptor;
- server-side revalidation that the APS evidence-bundle handoff artifact still matches the readiness descriptor and APS owner-service artifact contract;
- a same-origin binary response over the existing artifact using the repo's established streaming pattern;
- server-derived content type and attachment filename headers;
- focused tests for authority, stale-state rejection, forbidden fields, no row/artifact creation, no public/signed URL behavior, and no mutation of source packages or APS artifacts.

If route-method audit proves that a `GET` route is the only safe browser-download shape, the implementation must preserve server-side authority, avoid long-lived bearer-like URLs, and fail closed on query/path designs that behave like public or signed links. If that cannot be proven, stop and freeze a smaller prerequisite before coding.

## Required Preconditions

A future delivery request must fail closed unless the server can prove all of the following from stored state:

1. the session, approved plan, selected associated-cohort pass, result/status, result review, package construction, package-review submit, handoff/export prepare, APS handoff dispatch, and external export/download readiness records all exist and match;
2. `pass_type == associated_cohort`;
3. `pass_scope == quantitative_associated_cohort_dataset_version`;
4. `method == descriptive_summary`;
5. `source_gate == 78_COHORT_FREEZE`;
6. `source_shape == aligned_wide_table`;
7. `source_dataset_version_ids` match the package, prepare, APS dispatch, and readiness authority basis;
8. `package_review_state == package_review_approved`;
9. `handoff_export_state == handoff_export_prepared`;
10. `aps_handoff_state == aps_handoff_dispatched`;
11. `external_export_download_state == external_export_download_prepared`;
12. `aps_output_package_kind == aps_evidence_bundle_handoff`;
13. `export_download_target == aps_evidence_bundle_download_reference`;
14. `download_mode == reference_only_prepare`;
15. the APS bundle ref/id/schema/hash/size still validates through the APS evidence-bundle owner-service contract;
16. no request field asks for public URL generation, signed URL generation, connector dispatch, destination selection, generic downstream dispatch, package mutation, artifact creation, schema migration, source expansion, rerun, retry, recovery, or cancellation.

If any authority input is absent, stale, malformed, ambiguous, mismatched, non-cohort, cross-session, or inconsistent, the implementation must fail closed before streaming bytes.

## Write Boundary

This freeze admits no durable workbench write by default.

The delivery endpoint must be read-only against Layer 3 workbench state, source package rows, source package payloads, the APS handoff package row, and the APS evidence-bundle artifact. If implementation audit proves that a short-lived in-process delivery nonce, access log, or delivery summary is required, that must be frozen separately unless it can be represented as non-authoritative response metadata without new rows, schema changes, runtime DB widening, or persistent artifact mutation.

## Response Boundary

The future endpoint may return the existing APS evidence-bundle artifact body as a same-origin binary response only after server-side authority checks pass.

The response may include:

- `Content-Type`, derived from the validated artifact;
- `Content-Disposition: attachment`, with a server-derived filename;
- optional non-sensitive checksum or schema headers if already known and safe to expose;
- standard error responses for blocked, stale, missing, malformed, or conflict states.

The response must not include or create:

- public URLs;
- signed URLs;
- local filesystem paths intended for browser use;
- connector-run ids;
- destination ids;
- package payload bodies other than the single validated APS evidence-bundle artifact body;
- rewritten package content;
- new export artifact manifests.

## UI Boundary

This freeze does not admit rendered `/review/layer3` download controls.

A separate UI freeze is required before:

- showing an active browser download button or link;
- invoking the delivery endpoint from `/review/layer3`;
- representing a completed download in page state;
- retrying, cancelling, or refreshing downloads from the browser.

Until a later UI boundary lands, rendered associated-cohort readiness may remain visible only as readiness state and must keep browser download and URL controls unavailable.

## Explicit Non-Goals

- No rendered download button, rendered download link, or browser control activation.
- No public URL, signed URL, or local path exposure.
- No connector dispatch, connector-run creation, destination selection, non-APS downstream dispatch, or generic downstream dispatch.
- No package payload editing, copying, reconstruction, rebuild, amendment, supersession, or variant rewrite controls.
- No new `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, `AnalysisArtifact`, `L3ReconciliationRecord`, source, migration, model, runtime, connector-run, or additional `L3OutputPackage` rows.
- No new physical export artifact beyond streaming the existing APS evidence-bundle handoff artifact.
- No changes to lower-level `descriptive_summary`, service-materialize admission, package construction, package-review submit, handoff/export prepare-only behavior, APS dispatch, or readiness behavior outside the narrow delivery gate.
- No qualitative, hybrid, RAG, vector, retry, recovery, replay expansion, broader associated-cohort review, broader UI, or full mockup activation.

## Required Proof For Implementation

At minimum, an implementation must prove:

- delivery succeeds only after exact recorded associated-cohort `external_export_download_prepared` state;
- stale or missing package-review, handoff/export prepare, APS handoff dispatch, readiness descriptor, package refs/hashes, APS handoff package row, or APS bundle artifact fails closed;
- non-cohort, cross-session, forbidden-field, public/signed URL, connector, destination, generic dispatch, package mutation, schema/runtime/source, retry/recovery, rerun, or browser-only authority inputs fail closed;
- the response streams only the validated APS evidence-bundle artifact;
- no new package rows, reconciliation rows, `AnalysisArtifact` rows, connector-run rows, plan/pass/analysis rows, schema migrations, runtime DB writes, source-ingestion rows, or physical export artifacts are created;
- no source package payload refs/hashes/files, APS handoff package refs/hashes, or APS evidence-bundle artifact bytes change;
- existing single-item external export/download readiness and delivery tests still pass;
- existing associated-cohort readiness tests still pass;
- headed and headless Chrome proof is added only if rendered UI behavior changes.

## Deferred After This Freeze

Still separate and not admitted:

- rendered `/review/layer3` download controls;
- public URL generation;
- signed URL generation;
- connector dispatch or connector-run handling;
- destination selection;
- generic downstream dispatch;
- package amendment/rebuild/supersession;
- package payload mutation/reconstruction;
- additional reconciliation/package/artifact rows;
- `AnalysisArtifact` expansion;
- schema/runtime/source widening;
- qualitative/hybrid/RAG/vector behavior;
- broader UI or full mockup activation.
