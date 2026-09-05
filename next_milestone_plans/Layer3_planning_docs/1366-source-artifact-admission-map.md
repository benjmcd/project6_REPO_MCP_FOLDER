# Source-Artifact Admission Map (1366)

## Erratum (2026-09-04, tracked-state reconciliation)

Current implementation authority is `project6-origin/main` at
`d9412188e9581302429112cc637e416fe666994f`. The July 13 second-key
`NOT-GRANTED` language remains the historical authority for that exact proposed
key, but it is obsolete as a blanket claim that all B1b-related implementation
is absent. Later main contains A0 promotion identity (#2486), connector-only
DatasetVersion handoff (#2489), adopted-external intake (#2490), default-off
public ScienceBase analysis (#2492), provenance-bound public values (#2493),
and the eligible-candidate cap correction (#2494).

Those source-presence facts do not retroactively approve the old second key,
close the old ballot, authorize connector-to-intake auto-trigger, or prove the
whole B1b program, an integrated production loop, scientific utility, or Phase
4/5/6 completion. Public analysis remains restricted to the new
`sciencebase/public_api` family and default-off; values require both public
flags, provenance co-display, and storage-reference exclusion. No support
policy, schema, default, status, runtime action, acquisition, or owner decision
is changed by this erratum. See
[MASTER_CONTEXT](../../docs/MASTER_CONTEXT.md#2026-09-04-current-state-reconciliation).

**Status:** Tier-1, DOCS-ONLY. Contract/reference doc for lane **M-ADMISSION-MAP** (Phase 0+1 of the source-artifact admission-spine program). Grounds against `project6-origin/main` tip `ee87e576`; all `file:line` anchors were verified live before authoring. No production-readiness, default-on, nonlocal-admission, live-pilot, or connector-source-default expansion is claimed. This doc **subsumes** the in-code registry `backend/app/services/layer3_aps_source_family.py:5` (`APS_ADMITTED_TABLE_SOURCE_FAMILIES`); it does not duplicate or supersede runtime behavior.

## 1. Purpose & authority

Define a single **admission spine** - the proof axis by which any source family's artifacts become Layer-3 material - and map each of the 9 program source families onto it; the current-posture table also carries the workbench-internal raw-mixed server-owned materialization row, an admitted provenance class (`_is_admitted_dataset_version_provenance`) documented for completeness and not a program source family. Connectors are acquisition/provenance adapters only; they may not own downstream normalization, Layer-3 preview, Gate B/C, 3C, or package/handoff state. This map records the current posture (what is provable today), the target posture (proposed per-family program pass/fail), the known seams, and the phased program to close the gap.

**Authority:** the owner admission-spine decision brief (preserved at `state/agent-inbox/decision-brief-2026-07-08.txt`, sha256 recorded in D32) plus the owner "proceed" authorization, recorded as decision D32 in `docs/program-context/02-decision-record.md`. The durable digest of that inbox-local brief is committed here and in D32: connectors are acquisition/provenance adapters, downstream admission must run through a shared source-artifact/content spine, IMF remains owner-gated, FAO/BTS remain deferred, and Phases 0-7 define the authorized sequencing. This map is a documentation/proof instrument, **not** a support-matrix change: the ladder rungs below are never `config/support_matrix.yaml` statuses (the checker enforces exactly `{supported, experimental_default_off, simulation, unsupported}`).

## 2. Glossary (disambiguation of overloaded vocabulary)

**admission - three distinct senses:**
- **admission (material)** - the Gate-B / Gate-C material-admission boundary inside `backend/app/services/layer3_workbench.py`; the subject of this map.
- **admission (production)** - SEC/XBRL nonlocal *production* value-reveal admission (`docs/layer3-admission-runbook.md:1`, "Layer 3 SEC/XBRL Nonlocal Production Admission Runbook"). Out of scope here; pinned off in `support_matrix`.
- **the admission ladder / posture ladder** - this doc's per-artifact proof axis (Section 5). A documentation construct, never a runtime status.

**envelope - four distinct senses:**
- **admission envelope** - the shape-appropriate artifact envelope proposed at the `artifact_enveloped` rung (Section 3 taxonomy; target, not yet built).
- **authority envelope** - SEC EDGAR text-table authority selection/validation (`docs/nrc_adams/local_corpus_e2e_runbook.md:6675`, `:6772`; `backend/app/services/layer3_sec_edgar_authority_envelope.py`; planning doc `next_milestone_plans/Layer3_planning_docs/1115-sec-edgar-text-table-authority-envelope-selection.md:1`). Unrelated to the admission envelope.
- **IMF envelope-pin** (D31) and **response/BLS-terms envelope** - connector-side response artifacts, unrelated to admission.

**connector - two senses:** connector (acquisition/provenance) vs connector (dispatch/egress). Only the acquisition sense feeds the admission spine.

**package_handoff_admitted collision:** the ladder rung of this name (Section 5) is a service-level admission surface. It must not be conflated with the live JSON keys `context_packet_package_handoff_admitted` (`backend/app/services/layer3_aps_context_packet_package_handoff.py:224`) and `evidence_report_export_package_handoff_admitted` (`backend/app/services/layer3_aps_report_export_package_handoff.py:354`), which are payload flags, not admission states.

## 3. Envelope taxonomy (the "admission envelope" namespace)

The owner brief names five envelope classes as the shared admission contract at the `artifact_enveloped` rung. **None exist in code today** (zero hits on main for any of these names) - all five are GREENFIELD targets, namespaced under "admission envelope" to avoid the Section 2 overloads:

| Envelope class | Intended shape | Status |
|---|---|---|
| `ArtifactEnvelope` | base class: single fetched artifact + provenance + content hash | GREENFIELD |
| `VirtualArtifactEnvelope` | API-response/record artifacts with no single source file (JSON/SDMX records) | GREENFIELD |
| `TabularArtifactEnvelope` | tabular payloads (CSV/XLSX/report-row) with column-shape declaration | GREENFIELD |
| `SourceDirectoryArtifactEnvelope` | operator source-directory files (wraps the existing L3-native intake) | GREENFIELD |
| SEC/XBRL envelope | filing-set artifacts under the staged-redaction posture | GREENFIELD (as an *admission* envelope) |

Reference implementation to study, not reuse: the SEC/XBRL **authority-envelope** chain (`backend/app/services/layer3_sec_edgar_authority_envelope.py` + `docs/nrc_adams/local_corpus_e2e_runbook.md:6675`/`:6772` + planning doc 1115) demonstrates a validated artifact-contract pattern in this codebase, but it lives in a different namespace (text-table authority selection) and is not an admission envelope.

## 4. Processor profiles (13)

Processor profiles are content-shape processing contracts, orthogonal to source families. Candidate B is a **processor profile**, not connector-owned - the current entanglement (Section 8 inventory #4) is a defect, not the target contract.

| Profile | State | Anchor |
|---|---|---|
| `pdf_document` | EXISTS | NRC APS document pipeline; PDF default resolution in `backend/app/services/nrc_aps_document_processing.py:145-148` |
| `pdf_candidate_b` | EXISTS | default PDF engine, `backend/app/services/nrc_aps_document_processing.py:145-148` and `:484-486` |
| `tabular_csv_xlsx` | EXISTS | connector CSV/XLSX ingestion paths |
| `json_api_record` | EXISTS | JSON API connector record handling |
| `xml_xbrl_sec` | EXISTS | SEC/XBRL offline lane |
| `archive_bounded` | EXISTS | bounded archive handling |
| `unsupported_fail_closed` | EXISTS | existing fail-closed behavior |
| `ocr_image` | EXISTS | the 13th profile, beyond the owner brief's 12 (**omitted by the brief**); recorded for completeness |
| `sdmx_csv` | PARTIAL | connector-owned, `backend/app/services/connectors_oecd.py:600` |
| `report_row_text` | PARTIAL | `backend/app/services/connectors_cftc_cot.py:410` |
| `time_series` | PARTIAL | output-family only |
| `source_directory_file` | PARTIAL | L3-native intake, not yet profile-formalized |
| `text_markdown` | GREENFIELD | - |

Rows whose Anchor column is prose-only describe behavioral/multi-site surfaces with no single `file:line` anchor; locate them by identifier at execution time rather than inventing a line citation.

## 5. The admission ladder (rungs grounded in runtime surfaces)

Nine rungs. Each is a proof position on the spine, evidenced by an existing route/service/table (or explicitly marked NONE-YET as a target).

| Rung | Route | Service anchor | Backing table(s) |
|---|---|---|---|
| `connector_runtime_only` | none (connector-internal) | `connectors_bls.py` (`SOURCE_SYSTEM="bls_v1"` `backend/app/services/connectors_bls.py:52`, provenance `db.add(DatasetSourceProvenance(...))` `:613`); `connectors_worldbank.py` `SOURCE_SYSTEM` `backend/app/services/connectors_worldbank.py:48`, provenance `:598` | `DatasetSourceProvenance` |
| `dataset_version_materialized_legacy` | none (analysis-time) | `backend/app/services/analysis.py:207` `recommend_analysis()` -> `db.get(DatasetVersion, ...)` `:208` | `DatasetVersion` |
| `artifact_enveloped` | NONE-YET (target) | - (Section 3 taxonomy) | - |
| `normalized_content_admitted` | NONE-YET (target) | - | - |
| `layer3_preview_admitted` | `POST /material-preview` `backend/app/api/layer3/__init__.py:11276` | `material_preview` `backend/app/services/layer3_workbench.py:2034`, gated by `_is_admitted_dataset_version_provenance` `:1147` | read-projection over `DatasetVersion` / `DatasetSourceProvenance` |
| `gate_b_admitted` | `POST /gate-b/decision` `backend/app/api/layer3/__init__.py:11342` | `gate_b_decision` `backend/app/services/layer3_workbench.py:2177` -> `layer3_gate_b_state.py` | `L3GateBIdempotencyKey`, `L3SelectionManifest` |
| `gate_c_admitted` | `POST /gate-c/preview` `backend/app/api/layer3/__init__.py:11360` | `gate_c_preview` `backend/app/services/layer3_workbench.py:2693` writes only when `commit_typing=true` (`:2701-2704`) -> `materialize_typing_entry` / `backend/app/services/layer3_typing_entry.py:430` | `L3TypingRecord` (write), `L3MaterialSnapshot` (read) |
| `3c_admitted` | `POST /analysis-product/generate` `backend/app/api/layer3/__init__.py:11827` | `layer3_analysis_product_generation.generate_analysis_product` (imported `backend/app/api/layer3/__init__.py:11843`, called `:11853`) | `L3AnalysisProduct`, `L3AnalysisProductEvidenceLink` |
| `package_handoff_admitted` | split package/handoff route modules exist (`backend/app/api/layer3/__init__.py:12214-12215`; `handoff.py:68`; `package.py:58`) | service-level session-completion side effect in `backend/app/services/layer3_aps_context_packet_package_handoff.py` and `backend/app/services/layer3_aps_report_export_package_handoff.py` | `L3OutputPackage`, `L3ReconciliationRecord` |

`dataset_version_materialized_legacy` is a **pre-existing** plane (public connectors -> `Dataset`/`DatasetVersion` consumed at `backend/app/services/analysis.py:208`). It is documented, not endorsed: **prohibited as a NEW target** for any family. `package_handoff_admitted` is a **service-level** surface: split package/handoff HTTP modules are registered, but this rung tracks the session-completion package/handoff side effect rather than a single generic admission route. Material-preview producer functions on main are exactly 3: `layer3_workbench.material_preview` (`backend/app/services/layer3_workbench.py:2034`), `layer3_source_intake.source_intake_material_preview` (`backend/app/services/layer3_source_intake.py:415`), and `layer3_source_directory_material_admission.source_directory_material_preview` (`backend/app/services/layer3_source_directory_material_admission.py:85`); other entry bridges, including SEC iXBRL and Candidate B, are wrappers converging on these producers.

## 6. Current posture (only rungs provable today)

`config/support_matrix.yaml` carries exactly 32 capability entries, enforced by the exact-count assertion `capability_count == 32` in `backend/tests/test_layer3_support_matrix_runtime_contract_exhaustive.py:46`; the ladder rungs in this map are never support-matrix statuses.

| Family | `support_matrix` id / status | Persists today | Highest rung provable today |
|---|---|---|---|
| NRC APS | no dedicated core id; `ocr_external_engine` (exp-off), `nrc_aps_replay_corpus_gate` (sim) | fs receipt (`backend/app/services/nrc_aps_artifact_ingestion.py:223-233`, no DB row) + legacy bridge (`backend/app/services/nrc_aps_dataset_bridge.py:365-376`) | **`layer3_preview_admitted`** - only family whose provenance is admitted at the gate (`source_system=="nrc_adams_aps"`, `backend/app/services/layer3_workbench.py:1154`), reached via the dataset-bridge materialization (Section 8 inventory #1) |
| ScienceBase/MCS | `sciencebase_public_connector_slice` - supported | CSV ingest materializes dataset/version (`backend/app/services/connectors_sciencebase.py:2318-2365`), plus `DatasetExternalIdentity` (`:1962`) and `DatasetSourceProvenance` (`:2528-2531`) | `dataset_version_materialized_legacy` |
| Senate LDA | `senate_lda_anonymous_connector_slice` - supported | `DatasetVersion` (`backend/app/services/connectors_senate_lda.py:489-501`), `DatasetExternalIdentity` (`:438-440`) | `dataset_version_materialized_legacy` |
| World Bank | `worldbank_indicators_anonymous_connector_slice` - supported | `DatasetVersion`, `DatasetExternalIdentity` (`backend/app/services/connectors_worldbank.py:522`) plus dataset construction (`:540-543`) | `dataset_version_materialized_legacy` |
| BLS v1 | `bls_v1_anonymous_connector_slice` - supported | `DatasetVersion`, `DatasetExternalIdentity` (`backend/app/services/connectors_bls.py:586`) plus dataset/version construction (`:597`, `:605`) | `dataset_version_materialized_legacy` |
| OECD SDMX | `oecd_sdmx_anonymous_connector_slice` - supported | `DatasetVersion`, `DatasetExternalIdentity` (`backend/app/services/connectors_oecd.py:661`) plus dataset/version construction (`:680`, `:689`) | `dataset_version_materialized_legacy` |
| CFTC COT | `cftc_cot_anonymous_connector_slice` - supported | `Dataset`/`DatasetVersion` (`backend/app/services/connectors_cftc_cot.py:592-634`) | `dataset_version_materialized_legacy` |
| SEC/XBRL | many ids, **none** supported (exp-off + sim); production/egress pinned false | offline staged-redaction value store (`backend/app/services/layer3_sec_xbrl_offline_evidence_loader.py:160-180`), companyfacts acquire-and-stage (`backend/app/api/layer3/source_sec_edgar.py:234`) | `layer3_preview_admitted` -> `gate_c_admitted` **only in simulation/offline** form |
| raw-mixed server-owned materialization | no dedicated capability id; workbench-internal admitted family | `raw_mixed_materialized` provenance is admitted by `_is_admitted_dataset_version_provenance` (`backend/app/services/layer3_workbench.py:1148-1153`) and proved by `test_dataset_version_candidates_include_server_owned_raw_mixed_materialization` (`backend/tests/test_layer3_workbench.py:2156`) | `layer3_preview_admitted` |
| source-directory | **no** capability id | `L3SourceDirectoryIngestionBatch`/`File` (`backend/app/models/models.py:2288`/`:2323`) - L3-native, no legacy bridge; dedicated material preview route at `backend/app/api/layer3/source_ingestion.py:1590-1605` | `gate_b_admitted` via `SOURCE_DIRECTORY_FILE_SOURCE_CLASS` validation in `gate_b_decision` (`backend/app/services/layer3_workbench.py:2239-2241`) |

Key asymmetry: the 6 public connectors are **hard-refused** at `/material-preview` (Section 7, seam basis) and therefore sit at `dataset_version_materialized_legacy`; NRC APS, raw-mixed server-owned materialization, source-directory, and offline SEC/XBRL already reach admitted Layer 3 material surfaces today.

## 7. Target posture (proposed per-family program pass/fail)

| Family | Program disposition | Target rung |
|---|---|---|
| **NRC APS** | **Classification-only reference implementation** - no refactor target in Phase 1. Phase 2 introduces a behavior-neutral facade only. | keep `layer3_preview_admitted` (parity-proven) |
| **SEC/XBRL** | **Classification-only reference implementation** - no refactor target in Phase 1. | unchanged (offline/sim) |
| **World Bank** | Pilot -> PASS | `artifact_enveloped` + `layer3_preview_admitted` |
| **BLS v1** | Pilot -> PASS | `artifact_enveloped` + `layer3_preview_admitted` |
| **OECD SDMX** | Pilot -> PASS | `artifact_enveloped` + `layer3_preview_admitted` |
| **CFTC COT** | Pilot -> PASS | `artifact_enveloped` + `layer3_preview_admitted` |
| **ScienceBase/MCS** | Pilot -> PASS (deepest agent-executable) | `gate_b_admitted` |
| **Senate LDA** | **Optional** pilot | `artifact_enveloped` (if pursued) |
| **source-directory** | **Already-admitted reference** - no target | `gate_b_admitted` (as-is) |
| IMF | Owner-gated (D31); no target | - |
| FAO / BTS | Deferred; keyed sources and OPEC excluded | - |

## 8. Bypass / entanglement inventory (targets for Phase 7 guard, not this lane)

1. NRC ADAMS dataset-bridge -> generic preview (`backend/app/services/nrc_aps_dataset_bridge.py:365-376`).
2. SEC EDGAR acquisition connector owns `pdf_candidate_b_page_evidence` roles (`backend/app/services/layer3_sec_edgar_real_filing_acquisition_connector.py:839-851`).
3. SEC bespoke text-table / live / iXBRL bridges.
4. Candidate-B bundle/runtime bridges.
5. companyfacts acquire-and-stage (`backend/app/api/layer3/source_sec_edgar.py:234`).
6. source-directory hybrid/vector lanes (`backend/app/api/layer3/source_ingestion.py:1614-1801`).
7. Egress dispatch entry (record-only but load-bearing for the outbox chain).
8. Internal webhook connector.

## 9. Known seams (current-behavior defects, documented not fixed)

1. **Provenance-less fallback labels itself admitted.** `backend/app/services/layer3_workbench.py:1756-1761`: when `aps_provenance` is empty, the fallback dict self-labels `"admission_state": "admitted_dataset_version"` unconditionally.
2. **Only the newest provenance row is gate-checked.** `backend/app/services/layer3_workbench.py:1171` raises only on `rows[0]` (newest per `created_at.desc()`), so older non-admitted rows are never re-checked.
3. **Gate B has no `dataset_version` decision-basis re-validation.** `gate_b_decision` validates only `source_intake` (`backend/app/services/layer3_workbench.py:2224`) and `source_directory` (`:2241`); no `validate_dataset_version_gate_b_decision_basis` exists - the fence is preview-side only.
4. **Unknown parser family labeled ADMITTED.** `backend/app/services/layer3_aps_source_family.py:141-144`: an unrecognized `parser_family` returns `source_family:"unknown_aps_dataset_version"` with `admission_state:"admitted_materialized_dataset_version"`.

### 9a. Three-fixture pinning-test plan

Characterization/pinning tests (no behavior change), named per `test_layer3_bounded_e2e.py` conventions, to lock current labeling so Phase-2+ refactors are provably neutral:
- `test_layer3_admission_map_provenanceless_fallback_pins_current_label` - pins seam 1.
- `test_layer3_admission_map_newest_row_only_gate_pins_current_behavior` - pins seam 2.
- `test_layer3_admission_map_unknown_parser_family_pins_admitted_label` - pins seam 4.

### 9b. Gate-B basis-validation hardening (scheduled Phase 2/3, not this lane)

Add `validate_dataset_version_gate_b_decision_basis` so Gate B re-validates the `dataset_version` decision basis (closes seam 3). Deferred out of the Phase-1 docs lane; carried as a Phase 2/3 code item behind pinning coverage.

## 10. Phase plan (acceptance criteria + tier declarations)

| Phase | Scope | Tier | Acceptance criteria |
|---|---|---|---|
| **0** | Authority check + family/seam inventory | Tier-1 | Inventory + this map drafted; anchors verified live. |
| **1** | This docs lane (5 tracked files) | **Tier-1 DOCS-ONLY** | 5 files land; every anchor verified against live main; zero code/behavior change; `support_matrix` untouched. |
| **2** | Neutral NRC APS facade | Tier-1 (code, behavior-neutral) | Bidirectional coupling handled (`backend/app/services/layer3_workbench.py:54` import of `nrc_aps_artifact_ingestion`; schema-ID checks `:1575`/`:1582`/`:1616`/`:1693`); 3 pinning tests (Section 9a) green; parity proof; no `support_matrix` change. |
| **3** | ScienceBase direct-envelope pilot | **Tier-2 (declared in advance)** | `L3SourceIntakeRecord` CheckConstraints (`backend/app/models/models.py:2256-2260`) force a migration; migration reviewed; ScienceBase reaches `gate_b_admitted` with proof chain. |
| **4** | Shape pilots WB/BLS/OECD/CFTC (+LDA optional) | Tier-2 | Each family reaches `artifact_enveloped` + `layer3_preview_admitted`; connectors relinquish downstream ownership. |
| **5** | Admission proofs by claimed posture | Tier-1/2 | Per-family proof-reconstruction chain reproduces the claimed rung. |
| **6** | 3C/package proof for one named operator workflow | Tier-2 | One workflow proven end-to-end through `3c_admitted` + `package_handoff_admitted`. |
| **7** | Static/CI guard | Tier-1/2 | **Lands with the FIRST pilot (not last).** Guard rejects new `dataset_version_materialized_legacy` targets and connector-owned admission state. |

## 11. Non-goals

No connector sweep; no keyed sources; OPEC excluded; no IMF work without a fresh owner grant (D31 posture: envelope-grant execution stops on policy signals, not workarounds); no live request without a D27-class arming record; egress posture unchanged (D27/D31); no RAG; no nonlocal/production admission; no schema change without proof (Phase 3's migration is the declared exception); no forcing NRC APS semantics onto other families; connector `supported` status != admission.

## 12. Relation to existing docs and the in-code registry

- **`backend/app/services/layer3_aps_source_family.py:APS_ADMITTED_TABLE_SOURCE_FAMILIES`** (`admission_state="admitted_materialized_dataset_version"`) is the runtime authority for APS family labeling. This map **subsumes** it as the human-readable contract: the registry stays the single source of truth in code; the map explains it, exposes seam 4, and forbids duplicating its tuple in docs.
- **`docs/layer3-admission-runbook.md`** - SEC/XBRL nonlocal *production* admission (Section 2 disambiguation). Distinct instrument; nothing in this map alters it.
- **`docs/public-connectors-journey.md`** - the connector-program narrative for the 6 public connectors; this map supplies the admission axis that journey doc does not cover.
- **Support-matrix 8-surface rule** - any future capability change (Phases 2+) must touch all eight assert surfaces: `config/support_matrix.yaml`, `scripts/support_matrix_constants.py`, `scripts/support_matrix_check.py`, `scripts/support_matrix_runtime_contract_audit.py`, `backend/tests/test_support_matrix.py`, `backend/tests/test_layer3_support_matrix_runtime_contract_exhaustive.py`, `docs/support-matrix-local-expert.md`, and the README front door (rule recorded at `docs/campaign-records/2026-07-07-source-candidates.md:459`). **Line-anchor trap:** anchors into these surfaces drift with every capability landing - cite by identifier/marker, never by hard-coded line number, and re-derive any line anchor live before use.

## Erratum (2026-07-08, M-ADMISSION-MAP-FIXES)

Stage-2 audit `M-ADMISSION-MAP-ADVERSARIAL` finding F1 identified a count-fidelity defect between this document and the lane-source embedded specification: the prose described 9 source families while the current-posture table also carried the review-added raw-mixed server-owned materialization row and the source-directory `gate_b_admitted` posture.

PR #2469's in-review refinements are preserved as code-true: the raw-mixed current-posture row is admitted by `_is_admitted_dataset_version_provenance`, and the source-directory `gate_b_admitted` posture remains documented. This erratum reconciles the family-count prose, discloses the exactly 3 material-preview producer functions on main, and discloses the exactly 32 support-matrix capability entries with their runtime-contract assertion.

Supersession scope: this erratum supersedes only the prior family-count prose and adds only the producer-count and capability-count disclosures above. It does not alter any other runtime, target-posture, phase, non-goal, support-matrix, or production-readiness claim in this document.

## Erratum (2026-07-09, M-ADMISSION-DOCS)

This D26 erratum is the current currency boundary for this map. The original
grounding line against `project6-origin/main` tip `ee87e576` remains true only
for the original authoring snapshot; current Lane B authority is
`e31f5ebd5dcc0ae7820252d04cf47db4946d6743`. Because the 2026-07-08 erratum
already cites later #2469 refinements, skim readers must treat this document as
current only through the dated errata rather than over-trusting the original
status line.

Material-preview producer functions on current main are exactly 4, not exactly
3: `app.services.layer3_workbench:material_preview`,
`app.services.layer3_source_intake:source_intake_material_preview`,
`app.services.layer3_source_directory_material_admission:source_directory_material_preview`,
and
`app.services.layer3_connector_source_intake:connector_source_intake_material_preview`.
Any future gate must re-run the producer-count check independently instead of
inheriting this prose.

ScienceBase/MCS current posture and the target-row shorthand are superseded by
the connector source-intake Gate-B result. The Gate-B decision `next_state` is
`connector_source_intake_gate_b_admitted`. Separately, the connector Gate-B
material-admission mode is `connector_source_intake_gate_b_material_admission`.
These are distinct symbols: the mode string is not the next_state, and neither
should be collapsed to generic `gate_b_admitted` wording.

Gate B now validates `source_intake`, `source_directory`, and
connector-source-intake decision bases. The connector-source-intake validator
was delivered with the ScienceBase/MCS envelope. The function
`validate_dataset_version_gate_b_decision_basis` remains legitimately absent:
Phases 2 and 3 are closed, connector-intake validation was delivered, and the
dataset-version validator remains the Section 9b seam rather than an unexecuted
Phase 2/3 code item.

This does not bless the dataset-version Gate-B seam as an end-state. It
reclassifies the seam as Section 9b residual or future hardening outside the
closed Phase 2/3 execution record.

Phase execution status is superseded as follows: Phase 2 is EXECUTED in PR
#2471 / `e413d2df7cf0adeda2fd538bc4a3a2f87a5cfcc2`; Phase 3 is EXECUTED in PR
#2472 / `e31f5ebd5dcc0ae7820252d04cf47db4946d6743`; Phase 7 is EXECUTED in PR
#2472 / `e31f5ebd5dcc0ae7820252d04cf47db4946d6743`. Phase 4, Phase 5, and Phase
6 are not claimed executed by this erratum.

The closed Phase 3 schema authority is the connector source-intake table,
`L3ConnectorSourceIntakeRecord`, introduced by migration
`0056_layer3_connector_source_intake_record` and modeled at
`backend/app/models/models.py`. This supersedes the stale Phase 3 acceptance-row
pointer to `L3SourceIntakeRecord` constraints for rollback and follow-up
tracing.

Phase 7 closure means the first-pilot static/CI guard delivered in #2472: the
exact material-preview producer registry and wrapper classification guard. It
does not claim every future family-specific guard extension has already been
built; future Phase 4 guard work must remain compatible with the same rule that
connectors do not own downstream admission state.

The future WB/BLS/OECD/CFTC shape-pilot target posture is no longer generic
`artifact_enveloped` + `layer3_preview_admitted`. Those future pilots should
distinguish artifact envelope from connector source-intake Gate-B admission:
their connector path targets `next_state`
`connector_source_intake_gate_b_admitted` with mode
`connector_source_intake_gate_b_material_admission` where both labels are
needed. This updates the target posture only; it does not claim Phase 4 has
landed.

This supersedes the Section 10 Phase 4 acceptance criteria for WB/BLS/OECD/CFTC
where they still name the old `artifact_enveloped` + `layer3_preview_admitted`
pair as sufficient. Future Phase 4 acceptance must include the connector
source-intake Gate-B target above while preserving the separate artifact
envelope requirement.

## Erratum (2026-07-13, M-ADMISSION-SPINE-B1-RECORD)

This is the current currency boundary for planning doc 1366 through
`project6-origin/main` `56c56e77ebe435c3a9f035f47de2d8611efee7d7`.
After the 2026-07-09 erratum, PR #2473 /
`cdc832d9cbfba5b0485ed0cca0c2a79854605044` published the admission-spine
closure record, PR #2474 / `2b7973d72e65661acc30c3ec88791fe1c88061e0`
closed the Lane A admission-guard gaps, PR #2475 /
`4439b1de50d85b2bc72bd92fa8e54717b7e9d500` added the bounded B1a connector
vertical-loop proof, and PR #2476 /
`56c56e77ebe435c3a9f035f47de2d8611efee7d7` allowed only guarded loopback
sockets for that proof.

The B1a result is bounded. It does not prove an integrated connector-originated
loop, analytical utility, Phase 4 shape-pilot completion, Phase 5 proof-
reconstruction completion, Phase 6 named workflow completion, production
readiness, or B1b implementation.

The target B1b identity semantics are now settled but not implemented:

- The complete 58-disposition v1 enumeration is
  `RATIFIED-EXACTLY-AS-PROPOSED`. The outer tuple remains
  (`source_family`, `content_sha256`); the inner identity-metadata hash remains
  (`connector_key`, `sciencebase_item_id`, canonical full `media_type`) under
  version `layer3.connector_source_intake.identity_metadata.v1` and the
  canonicalization/null/version rules recorded in D33.
- The precedence rule is `RATIFIED-AS-PROPOSED`: the first successfully
  committed approved receipt wins; an equivalent approval reuses it; a
  divergent Gate-B decision returns dedicated `409`
  `promotion_identity_decision_conflict` with zero mutation and requires
  explicit owner supersession; a non-approved decision mints no receipt and
  occupies no identity.
- Persistence shape is a ratified design only. No implementation, schema, ORM,
  migration, runtime, build dispatch, B1b build PR, or B1b build merge is
  authorized by this erratum.

The sole remaining B1b owner gate is an explicit second key. It is
`NOT-GRANTED`; future intent is `INTENDED-NON-AUTHORIZING`; `WITHHELD` is
`NOT-CLAIMED`.

`B1A-PASS; B1B-BLOCKED-ON-OWNER; INTEGRATED-LOOP-NOT-PROVEN; LOOP-NOT-RUN-superseded-by-run; SCHEMA-NOT-CHANGED.`

Supersession scope: this erratum supersedes earlier current-currency and open-
owner-frontier wording only for the #2473-#2476 chain, the bounded B1a result,
the two ratified target-semantics questions, and the remaining explicit-second-
key gate. It preserves every earlier erratum and makes no Phase 4/5/6 or B1b
implementation claim.
