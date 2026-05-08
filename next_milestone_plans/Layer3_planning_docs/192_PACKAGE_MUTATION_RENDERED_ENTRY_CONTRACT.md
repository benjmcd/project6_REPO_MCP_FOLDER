# Package Mutation/Reconstruction Rendered Entry Contract

Status: planning/control contract paired with `191_PACKAGE_MUTATION_RENDERED_ENTRY_FREEZE.md`.

This contract defines the requirements for moving beyond the deferred `package_mutation_reconstruction_rendered_entry_freeze` decision. It admits no rendered package mutation runtime, rendered package mutation control, route, DTO, service behavior, model, migration, test behavior, package payload rewrite, source package row mutation, replacement payload generation, downstream invalidation, re-delivery, provider/public URL runtime, connector/destination dispatch, source expansion, RAG/vector retrieval, full mockup activation, hidden LLM planning, frontend-only durable authority, or auth/security behavior change.

Docs `122`, `126`, and `127` through `131` remain authority for existing bounded backend/API package lifecycle runtimes. Docs `184` through `190` remain the broader post-signed-reference, provider/public URL, and connector/destination governance chain. This contract is the narrower post-PR #750 rendered package mutation/reconstruction entry-decision layer.

## Authority Order

1. live `project6-origin/main` source, tests, models, migrations, routes, service code, and checker behavior;
2. docs `122`, `126`, and `127` through `131` for existing backend/API package lifecycle runtimes;
3. package lifecycle services in `backend/app/services/` and package lifecycle routes in `backend/app/api/layer3.py`;
4. rendered raw mixed downstream proofs in `e2e/layer3-workbench.spec.js` and docs `168`, `171`, `174`, `177`, `180`, and `183`;
5. docs `184` and `185` for post-745 downstream expansion ordering;
6. docs `187` through `190` for provider/public URL and connector/destination deferred entry decisions;
7. this contract and `191_PACKAGE_MUTATION_RENDERED_ENTRY_FREEZE.md`.

Planning prose, browser state, mockup screenshots, manually edited package bytes, local fixture state, copied artifact paths, or prior PR titles are not sufficient authority for runtime implementation.

## Entry Decision Contract

```yaml
entry_decision: deferred
selected_mode: null
runtime_status: not_implemented
live_backend_package_lifecycle_status: existing_bounded_backend_api_runtimes_admitted
receipt_family: no_receipt_planning_only
```

The decision may change only in a later freeze if all of these are repo-confirmed: concrete rendered operator use case, selected rendered package mutation mode, exact source and replacement package authority, package payload source, immutable package rule, downstream invalidation policy, re-delivery compatibility, receipt/audit compatibility, stale-authority failure plan, idempotency/replay/recovery/duplicate-action policy, light/dark/workbench theme behavior plan, headed/headless Chromium proof plan, and no-cross-mode privilege escalation proof.

## Allowed Future Modes

A later rendered runtime freeze must choose exactly one of:

- `rendered_package_supersession_preview_control`;
- `rendered_package_supersession_commit_control`;
- `rendered_replacement_package_namespace_review_control`;
- `rendered_package_lifecycle_read_only_dashboard`.

Existing backend/API package lifecycle runtimes must not be renamed or represented as broad package mutation/reconstruction.

## Request Contract For Later Runtime

A future rendered package mutation request must be server-authority based. It may include or derive server-side session, plan, pass, reconciliation, source package ids/kinds/refs/hashes, package-review authority, package lifecycle authority, downstream handoff/export and delivery authority, selected rendered package mutation mode, and fresh idempotency key or `client_request_id`.

The request must not accept package payload bytes, edited package content, browser-generated package diffs, raw artifact manifests, arbitrary local paths, local upload payloads, local-directory paths, web retrieval instructions, source package row updates, payload ref/hash updates, replacement row mutations, package delete flags, in-place reconstruction flags, provider URLs, public URLs, signed URLs, connector ids, connector credentials, destination ids, destination URLs, destination credentials, RAG/vector fields, broad qualitative fields, hidden LLM fields, auth/security fields, retry/rerun/recovery/cancel fields, or full mockup activation fields unless a later freeze explicitly admits one narrow server-authoritative mode.

## Response Contract For Later Runtime

A future response may expose only response-safe metadata admitted by the later freeze: selected mode, server-confirmed source package authority, server-confirmed replacement or lifecycle authority, stale/invalidation/re-delivery state, receipt id or audit ref, already response-safe refs/hashes/sizes, idempotency status, operator-visible next actions, failure code, and response-safe failure reason.

The response must not expose package payload bytes, raw diffs, local filesystem paths, provider credentials, raw provider URLs, connector credentials, destination credentials, raw connector targets, raw destination URLs, bearer tokens, auth internals, source expansion state, RAG/vector internals, hidden LLM internals, or package mutation fields on existing package review, handoff/export, APS dispatch, external export/download, same-origin delivery, signed-reference, provider/public URL, or connector/destination responses unless a later compatibility freeze admits it.

## Existing Backend Package Lifecycle Compatibility Contract

This entry freeze must preserve existing backend/API package lifecycle runtimes: `/package/mutation/preview`, `/package/replacement-set/record`, `/package/supersession/commit`, `/package/replacement-artifact/manifest/record`, and `/package/replacement-namespace/record`. Source `L3OutputPackage` rows and source package payload files remain immutable authority. Broad `package_mutation_reconstruction` remains deferred.

## Browser And UI Contract

This entry freeze adds no rendered UI control. If a later freeze admits rendered package mutation controls, it must preserve `light` for status/preview/review inspection, `dark` for execution/package construction, and `workbench` for package submit, handoff/export, APS handoff, external export/download, signed-reference, provider/public URL governance, connector/destination governance, and operation-dock flows. It must prove headed and headless Chromium consistency, define disabled/ready/stale/invalidated/re-delivery-needed/committed/already-committed/failed/recovery states, and avoid browser-state-only package lifecycle authority.

## Test Contract For Later Runtime

Runtime or rendered implementation remains blocked until a later freeze names tests for disabled-by-default behavior, exact server authority binding, stale source/replacement/downstream authority, forbidden package payload/diff/local path/upload/provider/connector/destination/source/RAG/hidden-LLM/mockup/auth fields, no source `L3OutputPackage` row mutation, no source package payload rewrite, no frontend-only durable authority, no provider/public URL, no connector/destination dispatch, no source expansion, no RAG/vector retrieval, no broad qualitative execution, no full mockup activation, no hidden LLM, no auth/security behavior change, no payload/diff/URL/target/token leakage, headed/headless Chromium proof, and light/dark/workbench theme coverage if UI changes are admitted.

## Checker Contract

`tools/l3-progress-check.py` should verify structural guardrails only: docs `191` and `192` exist and are referenced; entry decision is `deferred`; selected mode is null; runtime status is `not_implemented`; the already-live backend/API package lifecycle runtimes are acknowledged without being expanded; evidence ledger exists and unverified rendered control authority forces deferral; rendered mutation exposure model exists and unknown values force deferral; capability isolation matrix exists and all new runtime flags remain false; negative invariants are present; docs do not claim rendered package mutation/reconstruction runtime is live; docs do not conflate backend/API package lifecycle metadata with rendered mutation controls; docs do not admit package payload rewrite, source package row mutation, replacement payload generation, provider/public URLs, connector/destination dispatch, source expansion, RAG/vector retrieval, auth/security changes, full mockup activation, or frontend-only durable authority.

The checker must not pretend to validate actual rendered controls, package payload generation, package diff semantics, downstream invalidation, re-delivery, receipt/audit compatibility, browser theme behavior, headed/headless execution, or operator usability in this planning-only pass.

## Stop Conditions

Stop and return to planning if a future implementation proposal tries to implement more than one rendered package mutation mode, add rendered controls without a rendered implementation-entry freeze and headed/headless proof, accept package bytes/diffs/local paths/uploads/edited content from the browser, update/delete/create source `L3OutputPackage` rows, rewrite/create/overwrite/delete/reconstruct source package payload files, bypass downstream invalidation or re-delivery policy, emit mutation fields on existing downstream routes without compatibility freeze, add provider/public URL behavior as a side effect, create connector runs or destination writes, expand source/RAG/qualitative behavior, activate target-state mockups as durable authority, or alter auth/security behavior without an auth/security freeze.
