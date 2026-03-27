# NRC APS Review UI Canonical Graph Registry

## 1. Purpose

This document freezes the canonical NRC APS review graph used by both:

- the cleaner `Pipeline Overview`
- the denser `Run-specific Overview`

The graph registry exists so the UI does not derive its structure from Mermaid text, arbitrary file discovery, or one-off run behavior.

## 2. Canonical Source Of Truth

Authority inputs for this registry:

- the proven NRC APS proof flow documented in the verified runtime summary:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\storage_test_runtime\lc_e2e\20260327_062011\local_corpus_e2e_summary.json`
- the live downstream API surfaces in:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\api\router.py`
- the live persisted downstream artifact families under:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\storage_test_runtime\lc_e2e\20260327_062011\storage\connectors\reports\`

## 3. Registry Rules

- Node ids are canonical and renderer-independent.
- Node ids do not depend on filenames.
- Node ids do not depend on the current run id.
- The general overview and run-specific overview must share this registry.
- View-specific density differences are achieved through projection rules, not separate graph definitions.

## 4. Canonical Base Node Registry

These node ids are frozen for v1.

### 4.1 Upstream And Core Nodes

| Node Id | Display Label | Stage Family | Notes |
| --- | --- | --- | --- |
| `source_corpus` | Source corpus | source | conceptual source input for the selected review root |
| `preflight` | Preflight | preparation | proof-run preflight checks |
| `submission` | Run submitted | run_lifecycle | run identity and top-level run submission/result state |
| `artifact_ingestion` | Artifact ingestion | core_pipeline | raw target processing and persistence |
| `content_index` | Content index | core_pipeline | content-unit persistence and indexed search basis |
| `search_smoke` | Search smoke | verification | proof-run search verification branch |

### 4.2 Branch A Nodes

| Node Id | Display Label | Stage Family |
| --- | --- | --- |
| `branch_a_bundle` | Bundle A | downstream_branch |
| `branch_a_citation_pack` | Citation Pack A | downstream_branch |
| `branch_a_evidence_report` | Evidence Report A | downstream_branch |
| `branch_a_export` | Export A | downstream_branch |

### 4.3 Branch B Nodes

| Node Id | Display Label | Stage Family |
| --- | --- | --- |
| `branch_b_bundle` | Bundle B | downstream_branch |
| `branch_b_citation_pack` | Citation Pack B | downstream_branch |
| `branch_b_evidence_report` | Evidence Report B | downstream_branch |
| `branch_b_export` | Export B | downstream_branch |

### 4.4 Shared Downstream Nodes

| Node Id | Display Label | Stage Family |
| --- | --- | --- |
| `export_package` | Export package from A+B | downstream_shared |
| `context_packet_package` | Context packet from package | downstream_shared |
| `context_packet_export_a` | Context packet from Export A | downstream_shared |
| `context_packet_export_b` | Context packet from Export B | downstream_shared |
| `context_dossier` | Context dossier from export-derived packets | downstream_shared |
| `deterministic_insight_artifact` | Deterministic insight artifact | deterministic |
| `deterministic_challenge_artifact` | Deterministic challenge artifact | deterministic |
| `deterministic_challenge_review_packet` | Deterministic challenge review packet | deterministic |
| `validate_only_gates` | Validate-only gates | verification |

## 5. Canonical Edge Registry

These edges are frozen for v1.

### 5.1 Core Flow

- `source_corpus -> preflight`
- `preflight -> submission`
- `submission -> artifact_ingestion`
- `artifact_ingestion -> content_index`

### 5.2 Verification Side Branch

- `content_index -> search_smoke`

### 5.3 Branch A

- `content_index -> branch_a_bundle`
- `branch_a_bundle -> branch_a_citation_pack`
- `branch_a_citation_pack -> branch_a_evidence_report`
- `branch_a_evidence_report -> branch_a_export`

### 5.4 Branch B

- `content_index -> branch_b_bundle`
- `branch_b_bundle -> branch_b_citation_pack`
- `branch_b_citation_pack -> branch_b_evidence_report`
- `branch_b_evidence_report -> branch_b_export`

### 5.5 Shared Downstream Chain

- `branch_a_export -> export_package`
- `branch_b_export -> export_package`
- `export_package -> context_packet_package`
- `branch_a_export -> context_packet_export_a`
- `branch_b_export -> context_packet_export_b`
- `context_packet_export_a -> context_dossier`
- `context_packet_export_b -> context_dossier`
- `context_dossier -> deterministic_insight_artifact`
- `deterministic_insight_artifact -> deterministic_challenge_artifact`
- `deterministic_challenge_artifact -> deterministic_challenge_review_packet`
- `deterministic_challenge_review_packet -> validate_only_gates`

## 6. View Projection Rules

The UI has two views over the same registry.

### 6.1 General `Pipeline Overview`

The general view should be materially cleaner and more conceptual.

Allowed simplifications:

- show `source_corpus`, `preflight`, `submission`, `artifact_ingestion`, and `content_index` as one vertical chain
- show `Branch A` and `Branch B` as composite visual groups instead of exposing every internal node if necessary
- keep the downstream shared chain readable with explicit labels
- show the tree pane at category/file-layout level rather than dense run-file detail

The general view must still preserve the canonical stage order and branch topology.

### 6.2 `Run-specific Overview`

The run-specific view should materialize the full base node registry with:

- actual run ids
- actual artifact filenames
- actual counts
- actual branch anchors
- actual warnings and mismatches

## 7. Node Multiplicity Rules

- `source_corpus`, `preflight`, `submission`, `artifact_ingestion`, `content_index`, `search_smoke`, `export_package`, `context_packet_package`, `context_dossier`, `deterministic_insight_artifact`, `deterministic_challenge_artifact`, `deterministic_challenge_review_packet`, and `validate_only_gates` are singletons per reviewed run.
- Branch A and Branch B nodes are exactly two explicit branches in the current proof-backed v1 review model.
- Additional branch scaling beyond two branches is out of scope for v1 and should not be inferred automatically.

## 8. Node State Registry

Each canonical node must render one of these states.

| State | Meaning |
| --- | --- |
| `complete` | expected artifacts exist and mapping succeeded |
| `not_exercised` | node is part of the canonical graph but the selected run did not materially exercise it |
| `missing` | expected artifacts should exist for this run state but do not |
| `mismatch` | artifact references disagree with on-disk state or competing authorities disagree |
| `disabled` | only for selector/run-level state, not for an otherwise reviewable node |

## 9. Canonical Stage Families

These stage families are frozen for v1:

- `source`
- `preparation`
- `run_lifecycle`
- `core_pipeline`
- `verification`
- `downstream_branch`
- `downstream_shared`
- `deterministic`

Stage family names should drive styling and grouping, not node identity.

## 10. Canonical Node Ordering

The stable display order for the run-specific view is:

1. `source_corpus`
2. `preflight`
3. `submission`
4. `artifact_ingestion`
5. `content_index`
6. `search_smoke`
7. `branch_a_bundle`
8. `branch_a_citation_pack`
9. `branch_a_evidence_report`
10. `branch_a_export`
11. `branch_b_bundle`
12. `branch_b_citation_pack`
13. `branch_b_evidence_report`
14. `branch_b_export`
15. `export_package`
16. `context_packet_package`
17. `context_packet_export_a`
18. `context_packet_export_b`
19. `context_dossier`
20. `deterministic_insight_artifact`
21. `deterministic_challenge_artifact`
22. `deterministic_challenge_review_packet`
23. `validate_only_gates`

## 11. Prohibited Shortcuts

The implementation should not:

- derive nodes from filenames alone
- derive branch identity from filename ordering alone
- create or remove canonical nodes based on one run's artifact presence
- allow Mermaid text labels to become stable ids

## 12. Completion Standard

This registry is complete for v1 only if:

- every rendered node comes from this document
- both UI views consume this same registry
- every run-specific node payload can point back to one canonical node id
