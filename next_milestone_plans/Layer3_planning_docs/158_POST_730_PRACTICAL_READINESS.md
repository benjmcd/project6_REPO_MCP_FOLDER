# Layer 3 Post-730 Practical Readiness Audit

Status: current-main practical readiness checkpoint after PR `#730` and roadmap sync PR `#731`.

This document is report/control only. It does not add or admit route, DTO, service, model, migration, UI control, source, ingestion, package, connector, provider, RAG/vector, mockup, hidden LLM, or auth/security behavior.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- current-main anchor: PR `#731`, merge commit `df018510607bbcc9d07bcebdb7ec6b7701cf1c8d`
- runtime UI anchor: PR `#730`, merge commit `ec160cb3e5b829bb314498131a149b206378c3f7`
- rendered mode checked: `raw_mixed_server_owned_manifest_ref_ui_entry`
- roadmap reference: `157_POST_730_ROADMAP_SYNC.md`
- browser harness: `playwright.config.js` with fixed `SERVER_PORT = 8031`, `fullyParallel: false`, and `workers: 1`
- proof/progress surfaces: `layer3_progress_board.md`, `layer3_progress_manifest.json`, `layer3_workbench_proof_manifest.json`, and `tools/l3-progress-check.py`

Live source, tests, routes, models, migrations, and checker behavior outrank this audit.

## Validation Results

Validated on current main `df018510`:

- `python .\tools\l3-progress-check.py`: PASS
- `python -m pytest .\backend\tests\test_layer3_page.py -q`: PASS, `3 passed`
- `npx playwright test e2e/layer3-workbench.spec.js --grep "materializes raw mixed manifest through rendered controls"` run sequentially: PASS
- `npx playwright test e2e/layer3-workbench.spec.js --grep "materializes raw mixed manifest through rendered controls" --headed --project=chromium` run sequentially: PASS
- `npx playwright test e2e/layer3-workbench.spec.js`: PASS, `18 passed`

One invalid validation attempt was observed and classified:

- running the headed and headless raw mixed rendered smoke in parallel against the same worktree produced a headless `409` at plan preview and a headed web-server bind warning for `127.0.0.1:8031`;
- this was not accepted as product evidence because `playwright.config.js` deliberately defines a fixed port, one worker, and non-parallel file execution for the shared stateful harness;
- rerunning headless and headed sequentially passed both checks.

## Practical Readiness Verdict

Current main is practically ready for the live bounded rendered raw mixed materialization controls under these constraints:

- use the rendered controls only for server-owned manifest refs and hashes;
- use the API/test harness only to prepare server-owned manifest files and deterministic source authority for automated tests;
- run headed and headless browser validation sequentially when using the default fixed-port harness;
- treat browser/local storage as recovery or presentation state only, never durable authority;
- stop the current raw mixed rendered proof at plan approval unless a later test proves downstream controls work without new UI or backend behavior.

This checkpoint proves UI practical readiness for source materialization through existing rendered source/material/Gate B/Gate C/plan approval controls. It does not prove a human-facing upload, directory picker, manifest picker backed by arbitrary local paths, web connector retrieval, RAG/vector retrieval, provider/public URL, connector dispatch, package mutation, hidden LLM, full mockup, auth/security behavior, or frontend-only durable authority.

## Rendered UI Evidence

The rendered UI currently includes:

- server-owned manifest controls in `backend/app/review_ui/static/layer3.html` for corpus batch id, manifest ref, manifest SHA-256, operator confirmation, and `Materialize Source IDs`;
- request construction in `backend/app/review_ui/static/layer3.js` through `rawMixedMaterializationPayload`, `RAW_MIXED_MATERIALIZE_MODE`, and `postJson('/source/mixed-corpus/materialize', ...)`;
- candidate refresh and returned-ID verification through `materializedSourceIdsVisible` and `applyMaterializedSourceIds`;
- responsive/workbench styling in `backend/app/review_ui/static/layer3.css`;
- static shell proof in `backend/tests/test_layer3_page.py`;
- rendered workflow proof in `e2e/layer3-workbench.spec.js` test `Layer 3 workbench materializes raw mixed manifest through rendered controls`.

The raw mixed rendered smoke explicitly verifies the workbench theme surface, then switches back to light theme before continuing through existing rendered plan approval controls. Broader theme posture is covered by the full workbench spec, including theme persistence/isolation, focus, responsive workbench boundaries, and unsupported-only Gate C material routing.

## Operational Runbook Notes

For practical local verification:

1. Start from a clean checkout matching `project6-origin/main`.
2. Run `python .\tools\l3-progress-check.py`.
3. Run `python -m pytest .\backend\tests\test_layer3_page.py -q`.
4. Run the raw mixed rendered smoke headless.
5. After the headless run exits, run the same smoke headed.
6. Optionally run `npx playwright test e2e/layer3-workbench.spec.js` for full workbench coverage.

Do not run headed and headless Playwright commands for the same fixed-port harness in parallel unless the harness is explicitly reconfigured to use separate ports and isolated state.

## Next Pass Recommendation

The next implementation-eligible pass is:

- deeper rendered raw mixed downstream path using the live raw mixed controls and existing downstream controls only.

Entry conditions:

- test-only unless a concrete blocker is found;
- no new rendered controls unless a separate UI/theme freeze admits them;
- no production backend route, DTO, service, model, migration, source, package, connector, provider, RAG/vector, mockup, hidden LLM, or auth/security change;
- use API/harness setup only for deterministic server-owned manifest files and source authority;
- after materialization, drive the rendered UI only through server-backed existing controls;
- stop at the last genuinely supported rendered downstream step if execution/package/handoff/export controls cannot be driven without widening scope.

## Negative Invariants

This checkpoint keeps all of the following blocked:

- arbitrary local path input;
- local upload or local-directory ingestion;
- web connector retrieval;
- RAG/vector retrieval or index creation;
- source adapter registry or source-family expansion;
- provider/public URL or signed public URL generation;
- real connector or destination dispatch;
- broad package mutation or reconstruction;
- hidden LLM planning;
- full mockup activation;
- auth/security behavior change;
- frontend-only durable authority.

## Acceptance Criteria

This readiness audit is accepted only when:

- this file exists and names PR `#730`, PR `#731`, `raw_mixed_server_owned_manifest_ref_ui_entry`, fixed port `8031`, and the sequential headed/headless requirement;
- progress/proof manifests and the progress board reference this as report/control only;
- `tools/l3-progress-check.py` guards this file and the current-main references;
- `python .\tools\l3-progress-check.py` passes;
- `git diff --check` passes.
