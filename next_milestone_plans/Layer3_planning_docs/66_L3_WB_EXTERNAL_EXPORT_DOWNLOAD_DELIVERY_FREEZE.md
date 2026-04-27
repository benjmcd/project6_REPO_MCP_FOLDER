# 66 L3 Workbench External Export Download Delivery Freeze

## Status

Planning-only governance for a future bounded Layer 3 workbench external export/download delivery boundary after recorded external export/download readiness.

This document does not implement runtime behavior by itself. It admits only the next planning boundary after `external_export_download_prepared`: one server-authorized, same-origin download delivery path over the already validated APS evidence-bundle handoff artifact. It does not admit public URLs, signed URLs, connector dispatch, destination selection, generic downstream dispatch, package mutation/rebuild, schema/runtime/source widening, qualitative/hybrid/RAG/vector execution, or full mockup activation.

## Current Live Baseline

Current `project6-origin/main` includes:

- package construction and package-review submit;
- handoff/export prepare-only backend/API and rendered `/review/layer3` UI;
- APS handoff dispatch backend/API and rendered `/review/layer3` UI;
- external export/download readiness backend/API from PR #269;
- rendered `/review/layer3` external export/download readiness UI from PR #275.

The live readiness boundary is still reference-only. It records a server-authoritative descriptor after `aps_handoff_dispatched`, but it keeps `browser_download_enabled == false`, `download_url_enabled == false`, and downstream delivery/dispatch disabled.

## Evidence Basis

Repo-confirmed download-like surfaces already exist outside this Layer 3 boundary. For example, `backend/app/api/review_nrc_aps.py` streams validated review artifacts through `FileResponse` after owner-service resolution. Those routes prove same-origin file streaming is a known FastAPI pattern in the repo, but they are not Layer 3 workbench authority and must not be reused as workbench external export/download without a Layer 3-specific authority gate.

The Layer 3 workbench-compatible source remains narrower:

- `POST /api/v1/layer3/handoff/export/download/prepare` records a reference-only descriptor only after package-review, handoff/export prepare, APS dispatch, package ref/hash, and APS bundle authority.
- The descriptor points at the existing APS evidence-bundle handoff artifact.
- The APS evidence-bundle owner-service validation remains the source of artifact validity.

Therefore the next coherent planning boundary is same-origin delivery from that recorded descriptor, not public link generation or connector dispatch.

## Slice Decision

The next admitted planning boundary is:

> Freeze one backend/API same-origin external export/download delivery endpoint after `external_export_download_prepared`. The endpoint may stream the existing APS evidence-bundle handoff artifact to an authorized workbench caller only after the server revalidates the full Layer 3 authority basis. It must not create a public URL, signed URL, connector run, destination binding, generic downstream dispatch, new package/artifact row, or rewritten package payload.

This is smaller than a general external export feature. It deliberately separates:

- delivery of the already validated artifact through the application server;
- any rendered download button/control, which still requires separate UI governance unless the implementation audit proves it can be admitted in a later bounded UI packet;
- public/signed URL generation and destination/connector dispatch, which remain higher-blast-radius future decisions.

## Admitted Future Implementation Scope

A future implementation governed by this freeze may add only:

- one thin Layer 3 backend/API delivery endpoint;
- server-side revalidation of the recorded external export/download readiness descriptor;
- server-side revalidation that the source APS evidence-bundle artifact still matches the descriptor ref/hash/schema/size basis;
- a binary response over the existing artifact using the repo's established same-origin streaming pattern;
- response headers needed for a browser download, such as content type and attachment filename, derived server-side from the validated artifact and descriptor;
- focused tests proving authority, stale-state rejection, no new rows/artifacts, and no public/signed URL behavior.

If route-method audit shows a `GET` route is the only safe browser-download shape, the future implementation may freeze or implement an equivalent `GET` route only if it preserves server-side authority, avoids long-lived bearer-like URLs, and does not expose public/signed links. If that cannot be proven, stop and freeze a smaller delivery-token or one-shot authorization prerequisite before implementation.

## Required Preconditions

A future delivery request must be blocked unless the server can prove all of the following from stored state:

1. the Layer 3 session, approved plan, selected pass, result-review, package construction, package-review submit, handoff/export prepare, APS handoff dispatch, and external export/download readiness records still exist and match;
2. `package_review_state == package_review_approved`;
3. `handoff_export_state == handoff_export_prepared`;
4. `aps_handoff_state == aps_handoff_dispatched`;
5. `external_export_download_state == external_export_download_prepared`;
6. package ids, package kinds, payload refs, and payload hashes still match the recorded readiness basis;
7. `aps_output_package_kind == aps_evidence_bundle_handoff`;
8. `export_download_target == aps_evidence_bundle_download_reference`;
9. `download_mode == reference_only_prepare`;
10. the APS bundle ref/id/schema/hash still validates through the APS evidence-bundle owner-service contract;
11. no request field asks for public URL generation, signed URL generation, connector dispatch, destination selection, generic downstream dispatch, package mutation, artifact creation, schema migration, source expansion, rerun, retry, recovery, or cancellation.

If any authority input is absent, stale, malformed, ambiguous, or inconsistent, the implementation must fail closed before streaming bytes.

## Write Boundary

This freeze admits no durable workbench write by default.

The future delivery endpoint should be read-only against Layer 3 workbench state and the APS evidence-bundle artifact. If implementation audit proves that a short-lived in-process delivery nonce, access log, or delivery summary is required, that must be frozen separately unless it can be represented as non-authoritative response metadata without new rows, schema changes, or persistent artifact mutation.

## Response Boundary

The future endpoint may return the existing APS evidence-bundle artifact body as a same-origin binary response only after server-side authority checks pass.

The response may include:

- `Content-Type`, derived from the validated artifact;
- `Content-Disposition: attachment`, with a server-derived filename;
- optional non-sensitive headers such as checksum or schema id if already known and safe to expose;
- standard error responses for blocked, stale, missing, or conflict states.

The response must not include or create:

- public URLs;
- signed URLs;
- local filesystem paths intended for browser use;
- connector-run ids;
- destination ids;
- package payload bodies other than the single already validated APS evidence-bundle artifact body;
- rewritten package content;
- new export artifact manifests.

## UI Boundary

This freeze does not admit rendered `/review/layer3` download controls by itself.

A later UI freeze is required before:

- showing an active browser download button or link;
- invoking the delivery endpoint from `/review/layer3`;
- representing a completed file download in page state;
- retrying or cancelling downloads from the browser.

Until that later UI boundary lands, `/review/layer3` may continue to show readiness as recorded but must keep browser download and download URL controls unavailable.

## Explicit Non-Goals

This freeze does not admit:

- public or signed URL generation;
- file materialization beyond the existing APS evidence-bundle handoff artifact;
- connector dispatch or connector-run handling;
- destination selection;
- generic downstream dispatch;
- package amendment, rebuild, supersession, mutation, copying, or reconstruction;
- additional reconciliation rows;
- additional package rows;
- `AnalysisArtifact` expansion;
- schema migration;
- runtime DB widening;
- source expansion;
- local upload or local-directory ingestion;
- qualitative, hybrid, RAG, or vector execution;
- execution-start expansion beyond already admitted work;
- full mockup activation.

## Required Proof For Implementation

At minimum, a future implementation must prove:

- delivery succeeds only after recorded `external_export_download_prepared` state;
- stale or missing package-review, handoff/export prepare, APS handoff dispatch, readiness descriptor, package refs/hashes, APS package row, or APS bundle artifact fails closed;
- forbidden request fields fail closed;
- the response streams only the validated APS evidence-bundle artifact;
- no new package rows, reconciliation rows, `AnalysisArtifact` rows, connector-run rows, schema migrations, runtime DB writes, source-ingestion rows, or physical export artifacts are created;
- existing external export/download readiness backend/API tests still pass;
- existing rendered readiness UI tests still pass without adding an active download control.

## Deferred After This Freeze

Still separate and not admitted:

- rendered `/review/layer3` download button/control;
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
- qualitative/hybrid/RAG/vector execution;
- full mockup activation.
