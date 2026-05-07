# 08 Layer 3 Post-695 Reference Plan

## Purpose

This document is the current repo-tracked reference plan after PR #695. It exists to keep intended next work, scope limits, stop conditions, and dependency order out of chat-only history.

It is documentation only. It does not implement browser harness fixes, deeper Playwright flows, raw ingestion, local upload, local-directory ingestion, web connector retrieval, RAG/vector retrieval, source adapter registry behavior, package mutation or reconstruction, connector or destination dispatch, provider or public URLs, full mockup activation, hidden LLM behavior, model or migration changes, or auth/security behavior.

## Authority

Use this authority order when entering any later pass:

1. live `project6-origin/main`;
2. live source code and tests;
3. `tools/l3-progress-check.py`;
4. current PR comments, reviews, review threads, and CI state;
5. this reference plan;
6. older planning docs, proof manifests, and prior session logs.

Planning docs and progress/proof manifests must not be treated as stronger proof than live source/tests. If this document conflicts with live source/tests, live source/tests win and this document should be corrected in a docs-only pass.

## Current Live Baseline

Current bounded Layer 3 posture after PR #695:

- `POST /api/v1/layer3/source/mixed-corpus/seed` is live only as `raw_mixed_corpus_bridge_seed_only`.
- Supported source classes remain `dataset_version` and `aps_content_document`.
- The seed bridge reads only hash-checked server-owned storage-root manifests and existing admitted source authority rows.
- The seed bridge writes no DB rows and writes no files.
- The seed bridge starts no Layer 3 flow.
- The bounded API E2E path exists through external export/download delivery.
- The raw mixed bridge-to-bounded API E2E proof exists.
- The rendered `/review/layer3` raw mixed UI smoke proves bridge API setup can feed existing rendered source visibility, selection, material preview, Gate B, and Gate C preview enablement.
- The manual `/review/layer3` runbook exists in `07_L3_UI_MANUAL_RUNBOOK.md`.

Current no-go boundaries remain:

- no raw ingestion;
- no local upload;
- no local-directory ingestion;
- no web connector retrieval;
- no RAG/vector retrieval;
- no broad source adapter registry;
- no package mutation or reconstruction;
- no real connector or destination dispatch;
- no provider/public URL generation;
- no full mockup activation;
- no hidden LLM planning;
- no model or migration changes for this next tranche;
- no auth/security behavior changes.

## Immediate Critical Gap

The immediate next pass is not a deeper UI flow. It is a test-only browser-harness isolation hardening pass.

Observed failure:

```powershell
python -m pytest .\backend\tests\test_review_browser_server.py .\backend\tests\test_layer3_bounded_e2e.py -q
```

This order fails because the browser harness installs Layer 3-specific monkeypatches that are not restored by the existing review-browser patch-state helpers.

Relevant live surfaces:

- `backend/tests/review_browser_server.py`
- `backend/tests/review_browser_fixture.py`
- `backend/tests/test_review_browser_server.py`
- `backend/tests/test_layer3_bounded_e2e.py`

Reason this matters:

- Deeper UI automation will rely more heavily on the browser harness.
- Same-process patch leakage makes validation order-sensitive.
- Order-sensitive test state undermines non-fragility even when isolated target tests pass.
- Fixing this first prevents future UI proof from resting on polluted process state.

Allowed scope:

- test-only;
- restore/capture Layer 3 browser harness patches installed by `review_browser_server.py`;
- add or adjust the narrowest tests needed to prove restoration.

Forbidden scope:

- production backend service changes;
- production API route or DTO changes;
- rendered UI control changes;
- source/runtime behavior expansion;
- model or migration changes;
- raw ingestion or source adapter work;
- package, connector, provider, RAG/vector, mockup, hidden LLM, or auth/security work.

Required validation:

```powershell
python .\tools\l3-progress-check.py
python -m pytest .\backend\tests\test_review_browser_server.py .\backend\tests\test_layer3_bounded_e2e.py -q
python -m pytest .\backend\tests\test_layer3_bounded_e2e.py -q
python -m pytest .\backend\tests -k layer3 -q
npx playwright test e2e/layer3-workbench.spec.js
git diff --check
```

Stop if the pass requires production behavior changes. Report the exact blocker instead.

## Planned Sequence

### 1. Browser-harness Layer 3 patch restoration

Goal: make browser harness tests and bounded Layer 3 E2E tests safe to run in the same pytest process regardless of order.

Current blocker: `review_browser_server.py` installs Layer 3 patches that are not included in `capture_review_browser_patch_state()` / `restore_review_browser_patches()`.

Implementation-entry freeze needed: no, if test-only.

Likely files:

- `backend/tests/review_browser_fixture.py`
- `backend/tests/test_review_browser_server.py`

Required tests:

- explicit same-process ordering test or equivalent focused proof;
- bounded E2E test;
- full `-k layer3` backend selection;
- Layer 3 workbench Playwright smoke or full workbench spec.

Negative invariants:

- no production behavior change;
- no rendered UI change;
- no source expansion;
- no package or connector expansion.

Priority: P0.

Why before other work: deeper UI proof depends on reliable harness isolation.

### 2. Deeper Playwright bridge-to-rendered-UI path

Goal: use the raw mixed seed bridge as API setup and drive existing rendered `/review/layer3` controls beyond Gate B only as far as current controls and server-authoritative state already support.

Current blocker: browser-harness patch isolation must be fixed first.

Implementation-entry freeze needed: no, if test-only and no new controls are added.

Likely files:

- `e2e/layer3-workbench.spec.js`
- `e2e/layer3-helpers.js`
- possibly `backend/tests/review_browser_server.py` for test setup only.

Required tests:

- new focused Playwright smoke;
- full `e2e/layer3-workbench.spec.js`;
- targeted backend Layer 3 tests touched by setup.

Negative invariants:

- no manifest picker;
- no upload/directory/web/RAG/provider/connector UI;
- no browser-local durable authority;
- no hidden backend setup after the seed response except explicit API setup boundaries.

Priority: P1.

Why after patch restoration: otherwise a deeper UI test may pass or fail because of leaked harness state.

### 3. Standalone APS content-document qualitative E2E

Goal: prove the admitted single APS content-document qualitative path independently from the raw mixed/cohort path.

Current blocker: fixture strategy and expected qualitative output/assertion boundaries need a focused test plan.

Implementation-entry freeze needed: no for test-only proof; yes if runtime qualitative behavior expands.

Likely files:

- Layer 3 qualitative service tests;
- Layer 3 API E2E tests;
- possibly Playwright only after backend/API proof is stable.

Required tests:

- deterministic APS content fixture;
- API flow proof;
- negative guards for broad qualitative, hybrid, RAG/vector, hidden LLM, connector, provider, and package mutation behavior.

Negative invariants:

- no broad qualitative execution;
- no qualitative cohort execution unless separately frozen;
- no RAG/vector retrieval;
- no hidden LLM planning.

Priority: P1.

Why after UI/harness non-fragility: the current immediate problem is proof infrastructure reliability.

### 4. Mixed admitted-source UI/API E2E

Goal: prove combined `dataset_version` plus `aps_content_document` behavior across API and rendered UI using admitted source classes only.

Current blocker: deeper UI path and standalone APS qualitative posture should be clearer first.

Implementation-entry freeze needed: no for test-only proof; yes if source behavior changes.

Likely files:

- `backend/tests/test_layer3_bounded_e2e.py`;
- `e2e/layer3-workbench.spec.js`;
- `backend/tests/review_browser_server.py`.

Required tests:

- API mixed-source E2E;
- rendered UI mixed-source smoke;
- forbidden side-effect assertions.

Negative invariants:

- no raw ingestion;
- no source-class widening;
- no local upload/directory/web/RAG behavior.

Priority: P2.

Why after standalone paths: mixed proof should compose already-stable single-path behavior.

### 5. Rendered raw mixed bridge UI freeze

Goal: decide whether a human-facing raw mixed manifest workflow should exist at all.

Current blocker: current UI intentionally has no manifest picker or seed button.

Implementation-entry freeze needed: yes.

Likely files:

- planning docs under `next_milestone_plans/Layer3_planning_docs`;
- possibly `Layer3_execution_handoff` runbooks.

Required tests:

- freeze/proof checker updates if admitted;
- no implementation tests until implementation is selected.

Negative invariants:

- do not turn this freeze into upload/directory ingestion;
- do not imply arbitrary path access;
- do not imply raw ingestion.

Priority: P2.

Why after deeper proof: first prove the existing API-setup plus rendered-control path before adding UI surface.

### 6. Rendered raw mixed bridge UI implementation, only if admitted

Goal: add the frozen human UI boundary if and only if a freeze selects it.

Current blocker: no freeze exists.

Implementation-entry freeze needed: yes.

Likely files:

- `backend/app/review_ui/static/layer3.html`;
- `backend/app/review_ui/static/layer3.js`;
- `e2e/layer3-workbench.spec.js`;
- possibly API setup helpers only if frozen.

Required tests:

- headed and headless Playwright;
- API forbidden-field tests;
- no deferred source-expansion controls.

Negative invariants:

- no local file upload;
- no directory picker;
- no web connector retrieval;
- no RAG/vector retrieval;
- no provider/public URL setup.

Priority: P3.

Why after freeze: UI source expansion is high-risk and must not be inferred from raw mixed seed support.

### 7. Source-breadth freeze

Goal: select any future source-class expansion deliberately.

Current blocker: current mode is `supported_source_classes_only`.

Implementation-entry freeze needed: yes.

Likely files:

- `backend/app/services/layer3_source_boundary.py`;
- planning docs;
- source-boundary tests.

Required tests:

- source boundary contract;
- unsupported-class fail-closed tests;
- no accidental local/upload/web/RAG behavior.

Negative invariants:

- no broad adapter registry by default;
- no arbitrary local path reads;
- no unbounded runtime DB source reads.

Priority: P3.

Why before raw ingestion: ingestion must target an admitted source boundary.

### 8. Raw ingestion implementation

Goal: implement exactly one frozen ingestion lane.

Current blocker: no source-breadth freeze has selected a lane.

Implementation-entry freeze needed: yes.

Likely files:

- API routes/DTOs;
- source services;
- storage handling;
- tests and proof checker.

Required tests:

- path traversal and storage-root tests;
- malformed input tests;
- idempotency tests;
- no flow-start side effects unless explicitly admitted.

Negative invariants:

- no arbitrary local path access;
- no web/RAG/provider/connector expansion unless selected;
- no hidden Layer 3 flow start.

Priority: P4.

Why later: raw ingestion is materially broader than seed-only bridging.

### 9-17. Later Expansion Summary

These later passes are intentionally compact here. Each requires a fresh freeze or superseding implementation-entry document before code changes, because they carry higher runtime, security, provenance, or external-side-effect risk.

| Step | Goal | Current blocker | Freeze | Likely files/services | Required tests | Negative invariants | Priority and ordering |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 9. Broad execution expansion | Widen execution modes after source and fixture boundaries stabilize. | Current path is narrow and method-governed. | Yes. | Execution services, method registry, result tests, package/review contracts if outputs change. | Method fixtures, result artifact checks, hidden LLM/RAG/package-mutation guards. | No implicit method widening, no hidden external calls, no output taxonomy drift. | P4, after source posture. |
| 10. Qualitative, hybrid, RAG, vector expansion | Add retrieval/qualitative behavior with explicit provenance. | Broad qualitative/hybrid/RAG/vector remains deferred. | Yes. | Qualitative services, retrieval/vector services, API contracts, proof checker. | Deterministic corpus fixtures, retrieval provenance, provider/vector fail-closed tests. | No untracked embeddings, no silent provider calls, no source expansion by side effect. | P5, after proof infrastructure and single-path qualitative proof. |
| 11. Output taxonomy | Define output artifact classes before mutation or dispatch. | Output families remain bounded to current package/handoff paths. | Yes. | Output/package contract services, planning docs, API tests. | Schema/hash stability, artifact-ref validation, package-rewrite guards. | No package mutation by taxonomy alone, no connector/provider behavior. | P5, before package mutation. |
| 12. Package mutation/reconstruction | Add controlled package change behavior with supersession authority. | Output taxonomy and mutation authority are not selected. | Yes. | Package services, replacement tests, maybe models/migrations if selected. | Idempotency, supersession lineage, source-row mutation guards, hash verification. | No payload rewrite outside admitted behavior, no dispatch/provider side effects. | P6, after output taxonomy. |
| 13. Connector/destination dispatch | Add real downstream destination behavior. | Destination contract and fake-provider proof do not exist. | Yes. | Connector services, destination DTOs/routes, fake connector tests, audit/provenance services. | Fake connector success/failure, no real CI external calls, idempotent receipts. | No uncontrolled external side effects, no package mutation during dispatch. | P6, after package authority. |
| 14. Provider/public URL strategy | Define secure delivery references beyond same-origin delivery. | Provider/security policy is not selected. | Yes. | External export/download services, storage/provider services, security tests, UI only if admitted. | Expiry, access control, leakage prevention, revocation semantics if selected. | No public URL by default, no provider URL without server authority. | P7, after dispatch/delivery policy freeze. |
| 15. Browser/full mockup activation | Activate broader UI/mockup surfaces only after runtime contracts are real. | Mockups remain target-state only. | Yes. | Static UI assets, Playwright tests, mockup boundary docs. | Headed/headless browser proof, server-authority checks. | No browser-local authority, no controls for unsupported runtime behavior. | P7, after runtime contracts stabilize. |
| 16. Auth/security hardening | Add operator/auth boundaries against stable capability surfaces. | Auth/security behavior is explicitly deferred. | Yes. | Route dependencies, security services, tests, config docs if needed. | Access control, unauthorized/forbidden cases, token/session behavior if selected. | No partial-auth overclaim, no weakening of fail-closed behavior. | P8, once route/capability surfaces stabilize. |
| 17. CI/performance/observability/provenance/audit hardening | Make proof reliable, diagnosable, and scalable. | Capability boundaries are still moving; immediate harness isolation is already P0. | No for pure CI/test organization; yes for runtime observability schema changes. | CI workflows, test harnesses, logging/provenance services, runbooks. | CI matrix, performance budgets, provenance/audit assertions, flaky-order guards. | Validate-only actions must not seed/mutate runtime state unless explicitly a fixture; no behavior expansion through observability. | Continuous, with current P0 attention to harness isolation. |

## Reference Checklist For Future Agents

Before any future pass starts:

1. Fetch `project6-origin/main`.
2. Confirm local branch, local HEAD, remote main, and `git status --short --branch`.
3. Confirm no open PRs unless the task explicitly targets one.
4. Inspect current PR comments/reviews/review threads when working from a PR.
5. Run `python .\tools\l3-progress-check.py`.
6. Classify the pass as docs-only, test-only, runtime, UI, model/migration, or external-side-effecting.
7. Verify the pass has a reference section in this document or a later superseding freeze.
8. Stop before editing if the intended change would cross a no-go boundary without a freeze.

After any future pass:

1. Re-run the focused validation listed for that pass.
2. Re-run `python .\tools\l3-progress-check.py`.
3. Run `git diff --check`.
4. Inspect changed paths for scope drift.
5. If a PR is opened, wait for checks and inspect comments/reviews/review threads.
6. Merge only when green and clean.
7. Verify post-merge `project6-origin/main`.

## Supersession Rule

If a later freeze, runbook, or implementation-entry document changes this ordering, it must explicitly say what it supersedes and why. Until then, this document is the reference for post-PR #695 Layer 3 planning order.
