# NRC APS Review UI Mapping And Reviewability Rules

## 1. Purpose

This document freezes the rules that determine:

- how reviewable NRC APS runs are discovered
- when a run is eligible for the review UI
- how run artifacts map to canonical graph nodes
- how mismatches and partial artifact states are surfaced

Without these rules, implementation would be forced to invent review semantics at runtime.

## 2. Canonical Source Of Truth

Live authority for these rules:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\models\models.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\api\router.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\core\config.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\storage_test_runtime\lc_e2e\20260327_062011\local_corpus_e2e_summary.json`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\storage_test_runtime\lc_e2e\20260327_062011\storage\connectors\reports\`

Repo-confirmed facts already established:

- run identity exists in DB state and connector APIs
- selector metadata cannot come from a generic live run-list API because none exists yet
- persisted runtime artifacts are required to build the strict filesystem tree and node/file mappings
- the proof-backed run summary carries the branch anchors, gate outcomes, and review root metadata needed for v1 review construction

## 3. Allowed Review Discovery Roots

The review implementation should not browse arbitrary repo paths.

### 3.1 Allowlisted Runtime Roots

V1 review discovery may scan only these roots:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\storage_test_runtime`
- the current runtime storage root implied by `settings.storage_dir`

### 3.2 Summary-Backed Review Root Rule

A runtime root is considered summary-backed only if it contains:

- `local_corpus_e2e_summary.json`

And that summary satisfies:

- `schema_id == "aps.local_corpus_e2e_summary.v1"`
- `schema_version == 1`
- `run_id` is present and non-empty

The containing directory of that summary file is the review root.

## 4. Reviewable Run Discovery Algorithm

### 4.1 Candidate Run Discovery

The catalog layer should:

1. load candidate NRC APS runs from DB state
2. load summary-backed runtime roots from the allowlisted discovery roots
3. join DB runs to review roots using `summary.run_id == connector_run.connector_run_id`

### 4.2 Default Run Selection

The default run is:

- the latest completed reviewable NRC APS run

It is not:

- the latest submitted run
- the latest pending run
- the latest failed run

## 5. Reviewable Run Contract

A run is reviewable in v1 only if all of the following are true.

### 5.1 Required Conditions

- `connector_key == "nrc_adams_aps"`
- `status == "completed"`
- a summary-backed review root is discoverable
- the review root can produce:
  - selector metadata
  - canonical/run-specific overview payloads
  - strict filesystem tree payloads
  - node details
  - file details
- core stages through `content_index` can be mapped successfully

### 5.2 Non-Disqualifying Conditions

The following do not automatically make a run non-reviewable:

- downstream stages marked `not_exercised`
- advertised report refs missing on disk, if the core review model still builds
- historical artifact drift in optional surfaces, if the mapping layer can degrade visibly and safely

## 6. Disabled Run Reason Codes

If a run is not reviewable, it should still appear in the selector when practical, but disabled with a reason code.

Frozen v1 reason codes:

- `not_nrc_aps`
- `run_not_completed`
- `missing_review_summary_root`
- `missing_core_stage_artifacts`
- `mapping_construction_failed`

The selector payload should carry both:

- `reviewable: false`
- `disabled_reason_code`

## 7. Authority Precedence Rules

The review UI uses a hybrid authority model.

### 7.1 DB/API Authority

DB/API is authoritative for:

- run existence
- run id
- connector key
- run status
- selector timestamps

### 7.2 Artifact Authority

Persisted runtime artifacts are authoritative for:

- strict filesystem tree contents
- run-specific diagram node realization
- branch anchors
- downstream artifact lineage
- per-node structured summaries

### 7.3 Conflict Rule

If DB/API and persisted artifacts disagree:

- prefer persisted artifacts for review rendering
- attach a warning to the run and relevant node(s)
- do not silently reconcile

## 8. Core Node Mapping Rules

### 8.1 `source_corpus`

Source inputs:

- summary fields: `corpus_root`, `corpus_pdf_count`

### 8.2 `preflight`

Source inputs:

- summary field: `preflight`

### 8.3 `submission`

Source inputs:

- summary fields: `submission`, `run_id`, `run_detail`
- DB/API run identity metadata
- run summary report:
  - `*_run_summary.json`

### 8.4 `artifact_ingestion`

Required artifact class:

- `*_aps_artifact_ingestion_run_v1.json`

Additional supporting artifacts:

- 43 per-target `*_aps_artifact_ingestion_target_v1.json`

### 8.5 `content_index`

Required artifact class:

- `*_aps_content_index_run_v1.json`

Additional supporting artifacts:

- per-target `*_aps_content_units_v2.json`
- diagnostics refs if needed for structured summaries

### 8.6 `search_smoke`

Source input:

- summary field: `search_smoke`

## 9. Branch Mapping Rules

Branch identity must not be inferred from filename order alone.

### 9.1 Branch Anchors

V1 branch anchors are frozen to:

- `selected_branch_rows[0]` -> Branch A
- `selected_branch_rows[1]` -> Branch B

For the verified golden run, those anchors are:

- Branch A:
  - accession: `LOCALAPS00010`
  - target: `14ccc411-c68e-46f2-9e30-0df7f0b83e70`
  - content: `103fbd1d9a36d956191127572bdffac9165598ea171484a2fed41f78d8fcfcb6`
- Branch B:
  - accession: `LOCALAPS00014`
  - target: `f6b07ecf-dbf6-4faa-ab0e-f0144d8c7991`
  - content: `1e0d2b34da5a56e83a289d2798ba324e5dc31c8ca3b5e9026c625e9810f4fc69`

### 9.2 Evidence Bundle Mapping

Bundle A and Bundle B should be resolved by:

- reading the persisted bundle JSON
- inspecting `normalized_request.filters.target_ids`
- matching the target id to the selected branch target id

### 9.3 Downstream Lineage Mapping

Citation packs, evidence reports, exports, context packets, and later deterministic artifacts should be resolved by source linkage fields inside the persisted artifact bodies, not by filename ordering.

If two candidate artifacts exist, the mapping layer should prefer the one whose explicit source linkage matches the upstream artifact id/checksum of the branch or shared parent node.

## 10. Shared Downstream Mapping Rules

### 10.1 `export_package`

Must resolve from the single persisted export-package artifact whose source exports map to both Branch A export and Branch B export.

### 10.2 `context_packet_package`

Must resolve from the persisted context packet whose `source_family` indicates package-derived input.

### 10.3 `context_packet_export_a` And `context_packet_export_b`

Must resolve from the two persisted context packets whose `source_family` indicates evidence-report-export input and whose source descriptors map back to the Branch A export and Branch B export respectively.

### 10.4 `context_dossier`

Must resolve from the single dossier whose source packets are the two export-derived packets, not the package-derived packet.

## 11. Validate-Only Gate Mapping Rule

The `validate_only_gates` node should materialize from:

- summary field: `gate_results`
- runtime path:
  - `gate_reports\*.json`

The node should summarize:

- number of gates present
- whether all gates passed
- per-gate script/report metadata available in details

## 12. Mismatch Rules

The mapping layer must support mismatch states without crashing.

### 12.1 Missing Advertised Report Refs

If `run_detail.report_refs` advertises files that are not present on disk:

- mark the run warnings and relevant node warnings as `mismatch`
- preserve the advertised ref in details
- preserve the missing-on-disk fact in details
- do not silently drop the ref

### 12.2 Known Verified Mismatch In The Golden Run

For the verified run `d6be0fff-bbd7-468a-9b00-7103d5995494`, the planning set should treat these as known mismatches:

- advertised `artifact_dedup_report` missing on disk
- advertised `checkpoint_history` missing on disk
- advertised `event_log` missing on disk

The implementation should expect and render this mismatch state.

## 13. Strict Filesystem Tree Identity Rules

The tree must be a strict filesystem tree, but tree ids should not be raw paths.

### 13.1 Tree Id Rule

Each tree node should use a deterministic opaque id derived from the review-root-relative path.

Recommended pattern:

- `tree::<sha256(relative_path)>`

### 13.2 Display Path Rule

The browser payload may include:

- root-relative display paths
- display names

The browser should not require raw absolute paths for identity.

Absolute paths may remain available in file details payloads because the UI is an internal review tool, but the tree model itself should not depend on them.

## 14. Structured Summary Rules

Every file details payload should expose a small structured summary when available.

### 14.1 Summary By File Class

Examples:

- `run_summary`
  - selected count
  - downloaded count
  - failed count
- `artifact_ingestion_run`
  - processed targets
  - outcome counts
- `content_index_run`
  - indexed content units
  - failure count
- `evidence_bundle`
  - total hits
  - branch target ids
- `evidence_citation_pack`
  - total citations
- `evidence_report`
  - total sections
  - total citations
- `evidence_report_export`
  - format id
  - media type
- `evidence_report_export_package`
  - source export count
  - total citations
- `context_packet`
  - source family
  - total facts
  - total constraints
- `context_dossier`
  - source packet count
  - total facts
  - total constraints
- `deterministic_insight_artifact`
  - total findings
- `deterministic_challenge_artifact`
  - total challenges
  - disposition counts
- `deterministic_challenge_review_packet`
  - review item count
  - acknowledgement count
  - blocker count
- `gate_report`
  - passed
  - report path

## 15. Degrade-Visibly Rule

If a node cannot be mapped cleanly:

- keep the canonical node visible
- mark it `missing` or `mismatch`
- include warnings in the details payload
- do not remove the node to make the diagram look clean

## 16. Completion Standard

These rules are complete for v1 only if an implementer can answer:

- how runs become reviewable
- how disabled runs are classified
- how each canonical node gets its artifact(s)
- how branch A and branch B are identified
- how mismatches are surfaced instead of hidden

