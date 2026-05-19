# 860 - Downstream Analysis Environment Authority Gap Selection

## Status

Status: no-runtime current-main gap-selection control for `downstream_analysis_environment_authority_projection`.

Selection doc: `860_DOWNSTREAM_ANALYSIS_ENVIRONMENT_AUTHORITY_GAP_SELECTION.md`.

Predecessor current-main sync doc: `859_RECURSIVE_SOURCE_INGESTION_RUNTIME_CURRENT_MAIN_SYNC.md`.

Current-main checkpoint before this selection: `8e099ce8fd36ef3f9020c874a31b2bc2d48c978e`.

Selected gap: `downstream_analysis_environment_authority_projection`.

Selected next posture: `freeze_downstream_analysis_environment_authority_projection_before_runtime`.

Runtime behavior introduced by this selection: `false`.

Implementation-entry allowed next: false until a later freeze names exact route/API, service, rendered, proof, and no-go surfaces for the downstream Analysis Environment authority projection.

## Current-Main Evidence

Current main already has two separate authority surfaces that should not be conflated:

- rendered Sublayer 3C target-state/operator surface in `backend/app/review_ui/static/layer3.js`, including `Analysis Execution Environments / Planes` and the `Qualitative Data Analysis Environment` plane label;
- server-owned read-only state projection in `backend/app/services/layer3_sublayer_state.py`, with schema `layer3.sublayer_visualization_state.v1`, authority source `read_only_persisted_layer3_rows`, and `no_side_effects: True`.

Current main also includes the source-directory hybrid qualitative-analysis downstream chain through package, handoff/export, external export/download, rendered delivery control, server-configured source-directory rendered scan/status controls, and recursive source-directory ingestion under `recursive_server_configured_directory_text_table_policy_v1`.

That is enough current-main evidence to select the downstream Analysis Environment authority projection as the next major Layer 3 gap, but not enough to implement it in this pass.

## Selected Gap Boundary

The selected gap is the missing explicit contract that explains how the rendered Analysis Environment planes relate to server-authoritative Layer 3 state and downstream outputs after the current source-directory and source-directory-hybrid chains.

A later freeze must decide whether the first slice is:

- a read-only server authority contract for Analysis Environment plane projection;
- a rendered status/projection control over the existing `sublayer_visualization` and source-directory qualitative/hybrid status surfaces;
- a package/delivery handoff reader that proves delivered outputs are consumable by a downstream analysis environment; or
- a no-runtime closeout if existing `sublayer_visualization` plus rendered structural planes are already sufficient.

## Non-Admission Boundary

This selection admits no runtime behavior.

Still blocked:

- route, DTO, model, migration, or service behavior changes;
- rendered control changes;
- browser storage or frontend-only durable authority;
- caller-provided paths, URLs, globs, file bytes, or recursive flags;
- source authority promotion;
- package mutation, package reconstruction, or payload rewrite;
- handoff/export rerun, external export/download rerun, or delivery rerun;
- connector dispatch, destination writes, `ConnectorRun`, or `ConnectorRunTarget`;
- provider-private or provider-public URL behavior;
- credentials, network egress, or provider/object-store behavior;
- semantic/vector RAG widening, embedding generation, or persistent vector-store behavior;
- prompt/model/provider qualitative generation;
- TabPFN runtime or NRC RAG runtime;
- optional-tool Gate C/pass-entry admission;
- broad auth/security behavior;
- PDFs, OCR, Office documents, images, archives, arbitrary binaries, browser uploads, web connectors, or database connectors.

## Required Future Freeze

Before any implementation, the next freeze must name:

- canonical source of truth for Analysis Environment projection state;
- exact owner service and any route/API contract;
- exact rendered surface, if any;
- relationship to `session_sublayer_visualization_state`;
- relationship to source-directory qualitative/hybrid analysis status and output package/delivery authority;
- idempotency, stale-authority, no-side-effect, and leakage policy;
- headed and headless browser proof obligations if rendered controls change; and
- negative invariants proving no package/source/provider/connector/auth/security widening.

## Next Posture

The next exact posture is `freeze_downstream_analysis_environment_authority_projection_before_runtime`.

Do not implement Analysis Environment projection runtime, rendered controls, or delivery integration until that freeze is current-main selected, review-cleared, and checker-backed.
