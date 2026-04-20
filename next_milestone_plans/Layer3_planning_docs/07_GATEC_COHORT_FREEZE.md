# 07 GateC Cohort Freeze

## Purpose and authority note

This document freezes the bounded write-enabled Gate C quantitative associated/cohort continuation contract after the already-landed quantitative single-item pass slice.
The bounded quantitative associated/cohort continuation governed by this freeze has now landed on current `main`.

It answers one question only:
- what exact bounded quantitative associated/cohort continuation was admitted without reopening qualitative, cross-modal, comparative, route/UI, runtime DB, reconciliation, packaging, or APS handoff scope

It is not:
- a broad orchestration rewrite
- a general cohort-engine framework
- a qualitative or hybrid execution freeze
- a public route-family freeze
- a workbench/UI freeze
- a reconciliation or packaging lane

Applied authority order for this document:
1. live repo code and live tests on current `main`
2. the external canonical Layer 3 planning corpus
3. the active repo-local REV2 Phase 1A control spine
4. `04_GATEC_ENTRY_FREEZE.md`
5. `05_GATEC_IMPLEMENTATION_FREEZE.md`
6. `06_GATEC_PASS_FREEZE.md`
7. historical Phase 1A REV1 artifacts as context only

Primary-planning citation note:
- `P` citations whose path segment begins `layer3_primary_planningdocs/` refer to the external canonical Layer 3 planning corpus at `C:\Users\benny\OneDrive\Desktop\Layer3\layer3_primary_planningdocs`.
- Those files are external planning authority, not repo-local implementation truth.
- Repo-local implementation truth still comes from the cited `R|...` paths in the current repo/worktree.

Evidence basis: `P|layer3_primary_planningdocs/05_LAYER3_SUBLAYER2_ORCHESTRATION_AND_PASS_EXECUTION.md|Single-item and associated/cohort passes are both first-class|28-28`; `P|layer3_primary_planningdocs/05_LAYER3_SUBLAYER2_ORCHESTRATION_AND_PASS_EXECUTION.md|Associated/cohort pass definition|116-118`; `P|layer3_primary_planningdocs/05_LAYER3_SUBLAYER2_ORCHESTRATION_AND_PASS_EXECUTION.md|Default v1 posture includes one associated/cohort pass family|154-156`; `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Quantitative plane reuse only for dataset-version-compatible or explicitly shaped sets|76-76`; `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Recommended v1 reuse depth and explicit shaped-input contract|109-121`; `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Quantitative associated/cohort requires coherent shaping and strong set traceability|173-174`; `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Exact shaped-input schema remains an implementation-entry question|201-203`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|First implementation slice includes one associated/cohort pass family|114-115`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Success criteria includes one associated/cohort pass family executing|172-172`; `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Runtime DB remains read-only boundary|76-83`; `R|backend/app/services/layer3_typing_entry.py|Current associated_cohort set formation and quantitative/qualitative typing basis|16-25`; `R|backend/app/services/layer3_typing_entry.py|SUPPORTED_TYPING_RULES and finalized-session gating|65-106`; `R|backend/app/services/layer3_typing_entry.py|Current group/set formation rules including associated_cohort|263-347`; `R|backend/app/services/layer3_pass_entry.py|Current single-item-only Gate C pass admission|191-256`; `R|backend/app/services/layer3_pass_entry.py|Current plan payload and single-item pass identity|331-345`; `R|backend/app/services/layer3_pass_entry.py|Current pass-entry owner surface and fail-closed no-admissible-set behavior|534-546`; `R|backend/app/services/analysis.py|Quantitative plane is dataset_version_id-centric and loads dataframe/version metadata directly|87-113`; `R|backend/app/services/analysis.py|run_analysis loads a dataset version directly through load_version_dataframe|541-571`; `R|backend/app/services/dataframe_io.py|Repo-local dataset-version load and persist helpers|1-39`; `R|backend/app/services/transforms.py|Existing transformed dataset version creation over dataframe payloads|89-146`; `R|backend/app/services/ingest.py|Existing dataset/version creation and persistence helpers|67-153`; `R|backend/tests/test_layer3_typing_entry.py|Current proof includes associated_cohort formation only at typing level|185-268`; `R|backend/tests/test_layer3_pass_entry.py|Current proof admits single-item quantitative sets and excludes non-admitted cohorts|164-360`

## Frozen tranche

The bounded write-enabled Gate C continuation slice was frozen and has now landed as:
- `Gate C continuation = internal quantitative associated/cohort shaping and pass entry for dataset-version-backed cohorts only`
- extend the existing `l3_analysis_plan` / `l3_pass_run` surfaces already landed by the single-item pass slice
- preserve the already-landed Phase 1A, typing/unit, and single-item pass behavior exactly as they are
- admit only quantitative `associated_cohort` sets that can be shaped into one explicit dataset-version-like quantitative payload without semantic distortion
- no qualitative cohort execution
- no hybrid, cross-modal, or comparative pass execution
- no route/UI widening
- no runtime DB writes or runtime DB migrations
- no reconciliation, packaging, APS handoff, or consumer widening
- no direct collapse onto `AnalysisRun` as Layer 3 truth
- no internal HTTP self-calls

Hard rule:
- do not reinterpret this tranche as permission to solve the broader qualitative, hybrid, comparative, or workbench problem

## Canonical starting point

The live repo already has five distinct surfaces that this slice had to respect:

1. `Current Gate C typing/unit truth`
- `backend/app/services/layer3_typing_entry.py`
- `backend/tests/test_layer3_typing_entry.py`

2. `Current Gate C single-item pass-entry truth`
- `backend/app/services/layer3_pass_entry.py`
- `backend/tests/test_layer3_pass_entry.py`

3. `Existing quantitative engine family`
- `backend/app/services/analysis.py`
- `backend/app/models/models.py` for `AnalysisRun` and adjacent artifact rows

4. `Existing dataset-version persistence helpers`
- `backend/app/services/dataframe_io.py`
- `backend/app/services/transforms.py`
- `backend/app/services/ingest.py`

5. `Read-only runtime and adjacent helper boundaries`
- `backend/app/services/review_nrc_aps_runtime_db.py`
- `backend/app/services/market_data_integration.py`
- `backend/app/services/market_data_validation.py`
- `backend/app/services/market_insight_ai.py`

Frozen reading of that starting point:
- typing already proves that `associated_cohort` can exist as durable Layer 3 ledger truth
- pass entry currently proves only quantitative `single_item` execution
- the quantitative plane already knows how to operate on a `dataset_version_id`, not on raw multi-unit Layer 3 cohorts
- the repo already has generic helpers for persisting a dataframe as a dataset version, but no Layer 3-owned cohort-shaping contract yet
- this freeze makes that shaped-input bridge explicit instead of leaving ad hoc multi-unit coercion inside pass execution

## Frozen Gate C cohort continuation decisions

### 1. Admitted set posture

The bounded continuation lane may admit only `l3_analysis_set` rows where:
- `set_type == "associated_cohort"`
- `formation_basis_json["analysis_modality"] == "quantitative"`
- cohort cardinality is at least `2`
- every member analysis unit is atomic and references exactly one `l3_material_snapshot`
- every member snapshot has `source_shape == "dataset_version"`
- every member snapshot exposes a real `dataset_version_id` in `source_identity_json`
- every referenced dataset version exists and has a readable `storage_ref`

Hard exclusions remain:
- qualitative `associated_cohort`
- mixed-modality or hybrid `associated_cohort`
- `single_item`, `cross_modal`, and `comparative` sets for this continuation lane
- cohorts that would require runtime DB context as mutable execution state

### 2. First-v1 shaped-input contract

The first admitted quantitative cohort path is frozen narrowly:
- every source dataset version must expose a non-null time column
- every source dataset version must expose exactly one admitted non-time numeric measure series for cohort shaping
- the shaped cohort payload must be formed by exact UTC time-key alignment only
- no interpolation
- no resampling
- no gap-filling
- no imputation
- no heuristic column picking across multiple numeric measures

Frozen first-v1 shaped dataframe contract:
- one time column
- one numeric series column per admitted analysis unit
- each numeric series column name must be stable and machine-derived from the source `analysis_unit_id`
- one explicit mapping manifest must record at minimum:
  - `column_name`
  - `analysis_unit_id`
  - `material_snapshot_id`
  - `dataset_version_id`
  - `descriptor_id`

Hard rule:
- if a cohort cannot be shaped by exact timestamp intersection into that contract without semantic distortion, exclude or fail closed instead of coercing it through the quantitative plane

### 3. Persistence and provenance posture

The bounded lane may reuse the existing dataset-version persistence substrate only in this bounded way:
- create one derived dataset-version-like payload for the shaped cohort
- persist it through the existing repo-local dataset/version helpers rather than inventing a second storage system
- preserve Layer 3 plan/pass truth in `l3_analysis_plan` and `l3_pass_run`
- record how the shaped dataset version maps back to the original Layer 3 units and snapshots

Frozen provenance minimum:
- the shaped input manifest must be written to an explicit payload ref
- `l3_pass_run.input_payload_ref` for a cohort pass must point to that shaped-input manifest, not to one raw source snapshot
- `l3_pass_run.summary_json` must include:
  - `derived_dataset_version_id`
  - `source_dataset_version_ids_json`
  - `column_map_json`
  - `pass_scope`

Hard rule:
- the derived dataset version is execution context only
- it is not the new Layer 3 truth source
- it does not replace the original source snapshots, typing records, units, groups, or sets

### 4. Plan and pass posture

The bounded lane extends the existing pass-entry owner surface rather than replacing it.

Frozen pass-family expansion:
- keep the already-landed `single_item` path intact
- add one bounded `associated_cohort` pass family only for the shaped quantitative cohort contract above
- continue using `wrapped_quantitative_analysis` as the engine family

Frozen first-v1 plan behavior:
- one invocation may now admit both:
  - already-supported quantitative `single_item` sets
  - newly-supported quantitative `associated_cohort` sets
- `plan_json.planned_passes_json` must distinguish set type and pass scope explicitly
- `plan_json.excluded_sets_json` must carry machine-readable exclusion reasons for non-admitted cohorts

Minimum additional cohort exclusion reasons that must exist in this next lane:
- `cohort_not_quantitative`
- `cohort_member_not_single_snapshot`
- `cohort_source_shape_not_dataset_version`
- `cohort_measure_signature_not_admitted`
- `cohort_time_alignment_empty`
- `cohort_recommended_method_not_admitted`

### 5. Quantitative-plane reuse depth

The bounded lane may call the existing quantitative plane only after the cohort has been shaped into the frozen dataset-version-compatible contract.

Frozen reuse rule:
- `recommend_analysis(...)` and `run_analysis(...)` may operate on the derived cohort dataset version
- the lane must not widen `analysis.py` into a generic raw-cohort executor
- the lane must not describe this as direct `AnalysisRun` identity reuse

Expected first-v1 cohort pass posture:
- quantitative only
- associated/cohort only
- shaped dataset version only
- method selection remains bounded by the existing admitted wrapped quantitative method allowlist

### 6. Owner, touch, and proof posture

Frozen owner posture:
- owner module remains `backend/app/services/layer3_pass_entry.py`
- proof file remains `backend/tests/test_layer3_pass_entry.py`

Frozen expected touch envelope for the bounded write lane:
- `backend/app/services/layer3_pass_entry.py`
- `backend/tests/test_layer3_pass_entry.py`

Expected no-touch surfaces unless a repo-confirmed blocker proves otherwise:
- `backend/app/models/models.py`
- `backend/alembic/versions/*`
- `backend/app/api/router.py`
- `backend/app/schemas/api.py`
- `backend/main.py`
- `backend/app/services/analysis.py`
- `backend/app/services/review_nrc_aps_runtime_db.py`
- analyst-insight static assets and route modules

Frozen proof posture:
- extend the direct service-level pytest proof already used for `layer3_pass_entry.py`
- prove at minimum:
  - one quantitative associated/cohort set of at least two dataset-version-backed units shapes cleanly and executes
  - the shaped-input manifest records stable column-to-unit provenance
  - the existing quantitative single-item path still behaves the same
  - one incompatible cohort fails closed before execution
  - one cohort whose shaped dataset recommends an unsupported method fails closed
  - no route/UI/runtime DB widening occurs

## Explicit non-goals

Do not include in the bounded Gate C implementation lane:
- qualitative cohort execution
- hybrid, cross-modal, or comparative execution
- generic cohort resampling/interpolation policy
- analyst-insight route or page changes
- runtime DB writes, runtime DB migrations, or runtime-helper reuse as execution state
- reconciliation, packaging, APS handoff, or consumer admission
- a new public Layer 3 route family
- a new general-purpose dataframe-shaping framework outside the bounded Layer 3 pass-entry owner surface

## Stop conditions

Stop and reopen the freeze instead of improvising if the bounded write lane requires:
- edits to `backend/app/services/analysis.py`
- edits to `backend/app/models/models.py` or a new migration just to admit this cohort slice
- route, schema, or page changes
- runtime DB writes or runtime DB migrations
- qualitative or hybrid cohort execution
- interpolation, resampling, or gap-filling to make the cohort shape fit
- using a derived dataset version without explicit column-to-unit provenance mapping
- collapsing Layer 3 truth onto `AnalysisRun`

## Concise readiness judgment

Readiness judgment:
- ``This freeze was sufficient for the bounded write-enabled Gate C quantitative associated/cohort shaping and pass-entry lane that has now landed on current `main` ``
