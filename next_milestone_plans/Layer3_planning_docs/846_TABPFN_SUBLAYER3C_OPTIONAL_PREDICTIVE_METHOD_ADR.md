# 846 - TabPFN Sublayer 3C Optional Predictive Method ADR

## Status

Status: evaluation-only ADR for `tabpfn_sublayer3c_optional_predictive_method_adr`.

Doc: `846_TABPFN_SUBLAYER3C_OPTIONAL_PREDICTIVE_METHOD_ADR.md`.

Branch: `codex/l3-tabpfn-optional-tool-adr`.

Current-main preflight checkpoint: `82607f277201dd1aa3c6126395b7a3f77f164b76`.

Selected from posture: `select_first_sublayer3c_optional_tool_adr_from_planning_index`.

Decision: `evaluate_tabpfn_static_benchmark_planning_only`.

Runtime status: `not_implemented`.

Runtime behavior introduced by this ADR: `false`.

## Decision

Evaluate TabPFN only as a candidate for future static benchmark planning over already-authorized Layer 3 Sublayer 3C quantitative use-sites.

This ADR does not adopt TabPFN as a runtime method, default dependency, provider, model, package/handoff/export/download participant, Gate C/pass-entry engine, rendered control, or production feature.

The candidate remains blocked at runtime until a later current-main freeze proves all of the following:

- an exact current-main quantitative use-site where TabPFN could provide measurable predictive value over simpler baselines;
- license and output-use authority compatible with the intended project6 use;
- dependency isolation that keeps the base repo working without TabPFN installed;
- no hidden checkpoint download, no hidden browser login, and no hidden model call;
- deterministic benchmark fixtures and acceptance thresholds;
- fail-closed readiness behavior; and
- explicit rollback and no-adopt stop rules.

## Canonical Source Of Truth

Live source, tests, manifests, current-main review/check state, and repo-native validation remain authority.

The governing Layer 3 planning/control chain is:

- `844_PUBLIC_URL_DELIVERY_SUBLAYER3C_PREREQUISITE_CLOSEOUT.md`;
- `845_SUBLAYER3C_OPTIONAL_TOOL_PLANNING_INDEX_ADR_GATE.md`;
- `C:\Users\benny\Downloads\Planning_packs\accepted\l3_tabpfn_sublayer3c_tool_planning_pack`;
- `backend/app/services/layer3_pass_entry.py`;
- `backend/app/services/analysis.py`; and
- `backend/tests/test_layer3_pass_entry.py`.

The accepted TabPFN planning pack remains planning context only. It does not authorize runtime activation, dependency installation, checkpoint loading, hidden download, cloud/API inference, rendered controls, Gate C/pass-entry admission, package/handoff/export/download integration, agent tool-call runtime, or causal/econometric claims.

## Current External TabPFN Checkpoint

Current external TabPFN guidance was rechecked on 2026-05-19 from official Prior Labs sources:

- `https://github.com/PriorLabs/tabpfn`;
- `https://priorlabs.ai/tabpfn-license/`.

The current official posture increases the need for a conservative evaluation gate:

- `TabPFN-3` is currently the default model in the official repository;
- installing the package is separate from model/checkpoint access;
- first use can download model checkpoints;
- headless/CI use can require `TABPFN_TOKEN`;
- model cache behavior can write outside repo-owned state; and
- current default model weights are under non-commercial licenses, with commercial or production use requiring separate licensing.

These facts do not block static benchmark planning, but they block default dependency, runtime inference, hidden download, credentialed model access, and production behavior until a later exact authority freeze.

## Current Project6 Use-Site Candidates

The only current-main use-site candidates for future TabPFN evaluation are existing bounded quantitative surfaces:

- `quantitative_single_item_dataset_version`;
- `quantitative_associated_cohort_dataset_version`;
- engine family `wrapped_quantitative_analysis`; and
- existing supported method names `cross_correlation`, `descriptive_summary`, `decomposition`, and `structural_break`.

No qualitative APS, source-directory qualitative analysis, NRC RAG, connector, provider-public URL, provider-private URL, package/handoff/export/download, signed-reference, or rendered UI flow is a TabPFN use-site under this ADR.

## Evaluation Plan

A later evaluation-planning PR may define benchmark fixtures only if it remains no-runtime and no-dependency by default.

The benchmark plan must compare TabPFN against simpler project6-native baselines for the exact selected quantitative use-site:

- existing wrapped quantitative method output;
- trivial persistence or descriptive baseline when appropriate;
- small tabular train/test fixture with fixed seed and explicit leakage checks;
- dataset-version-backed fixture provenance;
- metric selection before running any candidate model; and
- no acceptance based on demo output, hidden model behavior, or one-off manual inference.

Any benchmark plan must include no-adopt thresholds. If TabPFN cannot beat simpler baselines by a predeclared margin, or if license/runtime constraints are incompatible with project6 use, the correct result is `no_adopt_tabpfn_for_sublayer3c_optional_predictive_method`.

## Non-Admission Boundary

This ADR admits no runtime behavior, backend route, API DTO, response model, database model, migration, dependency, provider adapter, provider credential, network egress, rendered optional-tool controls, frontend durable authority, connector dispatch, agent tool-call runtime, package mutation, handoff/export/download integration, signed-reference integration, Gate C/pass-entry admission, source-authority promotion, quantitative method-selection behavior, hidden model call, cloud/API inference, checkpoint loading, hidden download, browser login, token handling, model cache writes, or auth/security behavior change.

This ADR specifically admits no TabPFN runtime, no TabPFN dependency, no `pip install tabpfn`, no TabPFN fit/predict execution, no TabPFN model/checkpoint loading, no TabPFN cloud/API inference, no request-owned TabPFN runtime settings, no TabPFN output persistence, no TabPFN package artifact, no package/handoff/export/download integration, and no causal/econometric claims.

## Validation Basis

Required validation for this ADR:

- `python .\tools\l3-progress-check.py`;
- `python .\tools\l3-target-selection-validate.py --expect frozen`;
- `python -m py_compile .\tools\l3-progress-check.py`;
- JSON validation for `layer3_progress_manifest.json` and `layer3_workbench_proof_manifest.json`; and
- `git diff --check`.

No runtime test is required for this ADR because no runtime behavior, route, dependency, or UI behavior is changed.

## Next Posture

The next exact posture is `select_nrc_rag_sublayer3c_optional_tool_adr_or_tabpfn_static_benchmark_plan`.

A TabPFN benchmark-planning PR remains optional and must stay no-runtime until a later freeze explicitly admits readiness or runtime behavior.
