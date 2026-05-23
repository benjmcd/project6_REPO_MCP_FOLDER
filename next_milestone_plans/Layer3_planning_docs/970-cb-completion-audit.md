# 970 - Candidate B First-Class Path Completion Audit

## Purpose

Record a requirement-by-requirement completion audit for Candidate B as a first-class governed upstream corpus-processing and visual-evidence path for Layer 3.

This is an audit/checker guard only. It introduces no runtime, route, DTO, model, migration, rendered UI, parser, provider, connector, auth/security, source-expansion, RAG/vector/model, browser-storage, frontend-only durable-authority, or full-mockup behavior change.

```yaml
audit_mode: candidate_b_first_class_path_completion_audit_v1
audit_verdict: current_main_proves_candidate_b_first_class_path
current_main: fa0f6d0a82512b350db54425389067547a769ca9
remaining_product_blockers_identified_by_this_audit: []
goal_completion_state_after_this_audit_lands: candidate_b_first_class_path_complete_on_current_main
```

## Authority Inputs

- `964-cb-bridge.md` through `969-cb-vlane-sync.md`.
- Candidate B bridge, artifact-status, downstream-proof, operator-status, closure, readiness, final-proof, default-selector, and visual-lane services under `backend/app/services/`.
- Candidate B focused backend tests under `backend/tests/test_layer3_candidate_b_*.py`.
- Candidate B document-processing/default-selector tests under `backend/tests/test_nrc_aps_document_processing_default_selector.py` and `backend/tests/test_nrc_aps_run_config.py`.
- Rendered operator proof under `e2e/layer3-workbench.spec.js`.
- CI topology in `.github/workflows/playwright.yml`.
- Progress/check authority in `tools/l3-progress-check.py`.

## Requirement Audit

| Requirement | Current-main evidence | Result |
|---|---|---|
| Preserve baseline rollback | Explicit `document_processing_engine="baseline"` remains the rollback path; invalid/unsupported engines fail closed to baseline; non-PDF omitted-engine cases remain baseline. | proven |
| Preserve Candidate A semantics | Candidate A remains `candidate_a_page_evidence_v1`, remains explicit visual-lane behavior, and omitted engine with Candidate A visual lane routes through baseline PDF processing. | proven |
| Candidate B eligible PDF/corpus default selection | Omitted `document_processing_engine` selects `candidate_b_opendataloader_pdf` only for eligible PDFs; non-PDF and unsupported content types stay baseline. | proven |
| Candidate B explicit visual-lane evidence | `candidate_b_opendataloader_page_evidence_v1` is admitted only as explicit visual/page evidence, with runtime visibility separate from processing-engine authority. | proven |
| Retained artifact governance | Bundle and runtime receipts classify retained artifact families; source PDFs, annotated PDFs, visual/page evidence, provenance, delivery, and inspection artifacts are retained/governed while PDF/image text-material ingestion stays disabled unless separately admitted. | proven |
| Layer 3 material and analysis authority | Bundle and runtime bridges produce source-directory-compatible curated JSON/MD material authority with receipt/hash checks, material preview compatibility, Gate B compatibility, and qualitative-analysis downstream proof. | proven |
| Package and review | Candidate B-derived material proof covers package construction, package review submit, package replacement/supersession authority, and package status surfaces through the source-directory path. | proven |
| Handoff and export | Candidate B bundle and runtime downstream proofs cover handoff/export prepare and same-origin external export/download delivery over the governed Layer 3 package path. | proven |
| Delivery, provider-private redacted use, revoke, internal webhook | Candidate B downstream proof covers same-origin delivery, provider-private prepare/status/use/revoke with redacted provider URL/token behavior, internal webhook dispatch/status, and no provider object write or arbitrary connector dispatch. | proven |
| Final operator inspection | Operator-status, closure, readiness, final-proof, final-proof-status, and rendered workbench flows expose redacted Candidate B provenance/status/final proof for operator inspection without frontend-only durable authority. | proven |
| Default-promotion readiness | Readiness audit returns `candidate_b_default_promotion_ready_for_separate_selection`; final proof records `candidate_b_default_promotion_final_proven`; selector scope remains eligible PDF/corpus only. | proven |
| High-ROI verification improvements | Playwright is sharded by deterministic per-test grep selection, backend Layer 3 pytest is sharded by deterministic nodeid selection, aggregate `test` and `backend-layer3-api` checks remain stable, and PR #1669 proved shard durations within the 2-3 minute target window. | proven |

## Negative Invariants

The current-main Candidate B path remains bounded by these invariants:

- no baseline rollback removal;
- no Candidate A semantic weakening;
- no Candidate B visual lane as omitted/default visual lane;
- no Candidate B default beyond eligible PDF/corpus processing;
- no direct PDF, annotated-PDF, image, Office, SEC EDGAR, ZIP, or arbitrary binary material ingestion into Layer 3 text analysis through this path;
- no broad runtime DB or storage ingestion;
- no provider object writes;
- no arbitrary connector dispatch;
- no RAG/vector/model runtime expansion through Candidate B;
- no auth/security behavior change;
- no browser-storage authority;
- no frontend-only durable authority;
- no full mockup activation.

## Verification

Current local verification for this audit:

```text
python -m py_compile ./tools/l3-progress-check.py
py -3.12 ./tools/l3-progress-check.py
py -3.12 -m pytest ./backend/tests/test_nrc_aps_document_processing_default_selector.py ./backend/tests/test_nrc_aps_run_config.py ./backend/tests/test_layer3_candidate_b_artifact_status.py ./backend/tests/test_layer3_candidate_b_bundle_bridge.py ./backend/tests/test_layer3_candidate_b_runtime_bridge.py ./backend/tests/test_layer3_candidate_b_visual_lane_status.py ./backend/tests/test_layer3_candidate_b_default_readiness.py -q
git diff --check
```

Recent GitHub verification for the support-check system:

- PR `#1667` landed deterministic Playwright sharding.
- PR `#1668` landed deterministic backend Layer 3 pytest sharding.
- PR `#1669` proved the current Candidate B visual-lane sync with sharded GitHub checks: backend shards `1m49s`, `1m59s`, `1m59s`, `2m12s`; Playwright shards `2m14s`, `2m16s`, `2m39s`, `2m44s`; aggregate checks `backend-layer3-api` and `test` passed in seconds.

No current flaky check or state-isolation failure is identified by this audit. Future flake/state remediation remains required if later evidence shows repeated nondeterministic failure, but it is not a current completion blocker.

## Stop Conditions

Do not mark Candidate B complete if any of the following becomes true on current main:

- `baseline` is no longer a rollback/default path for non-PDF or explicit-baseline requests;
- Candidate A no longer preserves `candidate_a_page_evidence_v1` semantics;
- Candidate B becomes an implicit/default visual lane;
- Candidate B default scope broadens beyond eligible PDF/corpus processing;
- retained PDF/image/visual artifacts become Layer 3 text-material payloads without a separate admitted slice;
- bundle/runtime bridge receipts are missing, stale, hash-mismatched, or collapsed into one authority family;
- downstream proof no longer covers material preview, Gate B, analysis, package/review, handoff/export, delivery, provider-private redacted use/revoke, internal webhook/status, and final operator inspection;
- required CI checks return to avoidable 2-5 minute serial bottlenecks or start failing nondeterministically without remediation.

## Next Posture

Candidate B is complete for the bounded first-class current-main path described in this audit once this audit and its checker guard land on current main.

Future work should be treated as post-completion hardening or scope expansion, not as a blocker to the active Candidate B first-class path, unless new current-main evidence contradicts this audit.
