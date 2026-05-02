# Layer3 Progress UI Spec

## Purpose

This file defines how an external render surface, including a Claude Cowork artifact,
should present the bounded Layer3 APS progress chain.

The manifest and board already define truth and prose. This file exists so a renderer
does not have to guess how to turn that truth into a stable interface.

## Proven Failure Modes To Avoid

Do not repeat these patterns:
- embedding a hardcoded manifest snapshot inside artifact HTML and then calling it live
- refreshing only the repo files while leaving the artifact itself stale
- requiring JavaScript to populate the milestone table or other primary content
- requiring Mermaid to understand what is done, what is current, and what is still deferred
- flattening done, current focus, candidate next work, and deferred scope into one undifferentiated view

## Canonical Inputs

Render from these in order:
1. `next_milestone_plans/layer3_progress_manifest.json`
2. `next_milestone_plans/layer3_progress_board.md`
3. `next_milestone_plans/layer3_progress_refresh_spec.md`

GitHub PR state remains authority for merged versus open.
The UI must not override authority.

## Hard Render Rules

- The artifact must remain understandable with HTML and CSS alone.
- JavaScript may enhance interaction, but it must not be required for:
  - summary counts
  - milestone rows
  - current focus
  - Layer 3 workbench current decision
  - Layer 3 workbench slice register
  - candidate next consumers
  - deferred scope
  - deferred activation criteria
- Mermaid is optional enhancement only.
- If Mermaid fails, there must be no loss of meaning.
- If the artifact cannot read refreshed files at render time, the scheduled refresh must rewrite the artifact itself from current manifest data.
- Do not present candidate next consumers as though they are already the current implementation lane.
- Do not present a deferred item as a candidate or current focus unless its manifest-declared activation conditions are satisfied.
- Render `layer3_workbench_current_decision` separately from `next_required_decision`; the later APS family settlement is not itself a workbench execution or next-slice admission.
- Render `layer3_workbench_slices` as a structured workbench register; do not make users infer PR `#184`, `#194`, `#199`, `#205`, `#207`, `#212`, `#213`, `#216`, `#218`, `#222`, docs `44`/`45`, the PR `#227` result-review implementation state, docs `46`/`47` result-review UI planning state, PR `#232` result-review UI implementation state, docs `48`/`49` package-review preview planning state, PR `#235` package-review preview implementation state, docs `50`/`51` package-construction planning state, PR `#238` package-construction implementation state, PR `#241` docs `52`/`53` package-review submit planning state, PR `#243` package-review submit implementation state, PR `#245`/`#247` rendered package-review UI and fallback-hardening state, docs `54`/`55` handoff/export preparation planning state, PR `#251`/`#252` backend/API prepare-only implementation and hardening state, docs `56`/`57` rendered handoff/export preparation UI planning state, PR `#256` rendered handoff/export prepare-only UI implementation state, docs `58`/`59` APS handoff dispatch governance state, PR `#260`/`#261`/`#263` backend/API APS handoff dispatch implementation/hardening state, docs `60`/`61` rendered APS handoff dispatch UI planning state, PR `#266` rendered APS handoff dispatch UI implementation state, docs `62`/`63` external export/download readiness planning state, PR `#269` backend/API external export/download readiness implementation state, docs `64`/`65` rendered external export/download readiness UI planning state, PR `#275` rendered external export/download readiness UI implementation state, docs `66`/`67` external export/download delivery planning state, docs `70`/`71` AnalysisMethod registry governance state, PR `#316` current-methods registry implementation state, `72_L3_DESCRIPTIVE_SUMMARY_FREEZE.md` / `73_L3_DESCRIPTIVE_SUMMARY_CONTRACT.md` descriptive-summary governance state, PR `#411` lower-level descriptive-summary method support, PR `#417` single-item Gate C admission state, doc `77` associated-cohort requirements, docs `78`/`79` service-governance state, PR `#424` explicit service-only associated-cohort implementation state, PR `#425` exact-request hardening state, docs `80`/`81` selected-pass cohort execution governance state, PR `#432` selected-pass cohort execution-start/result-status implementation state, or any future branch-only package, handoff/export, APS handoff UI, external export/download, Gate C admission, cohort, or method-expansion implementation candidate only from prose.

- Render `82_COHORT_RESULT_REVIEW_FREEZE.md`/`83_COHORT_RESULT_REVIEW_CONTRACT.md` as planning-only selected-pass associated-cohort result-review governance over the exact PR `#432` path; do not render them as live result review, UI, package, handoff, export, schema/runtime/source, connector, qualitative/hybrid/RAG/vector, or full mockup activation.

## Required Visual Sections

Render these sections in this order:

1. `Program State Summary`
   - show summary cards for:
     - done now on `main`
     - current focus
     - workbench slice records
     - candidate next consumers
     - deferred scope
   - use manifest `summary_counts` and `next_required_decision`

2. `Current Focus`
   - render the `next_required_decision` block as the most visually prominent active or closure section
   - if `next_required_decision.state` is not `settled`, treat it as the most visually prominent non-complete section
   - if `next_required_decision.state` is `settled`, render a closure card instead of a next-lane card
   - include:
     - title
     - why now
     - must-not-skip rules or reopen conditions

3. `Layer 3 Workbench Current Decision`
   - render `layer3_workbench_current_decision`
   - make the scope boundary visible: workbench-only and separate from the APS `next_required_decision`
   - include:
     - current live state
     - required conditions before the next functional slice
     - default next candidate, if present, as candidate-only and not admitted
     - must-not-skip rules

4. `Layer 3 Workbench Slice Register`
   - render `layer3_workbench_slices` as a stable table or grouped list
   - include:
     - slice id/title
     - state
     - governing docs
     - key PRs
     - exact live scope or explicit non-goals
  - render docs `46`/`47` as planning-only result-review UI governance, PR `#232` as the separate live bounded `/review/layer3` result-review UI implementation, docs `48`/`49` as planning-only package-review preview governance with no live package construction or handoff, PR `#235` as live only for read-only package-review preview inspection, docs `50`/`51` as planning-only package-construction governance by themselves, PR `#238` as live only for bounded backend package construction by itself, PR `#241` docs `52`/`53` as planning-only package-review submit/decision governance, PR `#243` as current-main live backend-only package-review submit behavior by itself, PR `#245` as current-main live bounded rendered package-review UI behavior with no handoff/export, PR `#247` as fallback hardening inside that same rendered UI boundary only, docs `54`/`55` as planning-only handoff/export preparation governance by themselves, PR `#251` as current-main live bounded backend/API prepare-only handoff/export behavior, PR `#252` as blocker-vocabulary/session-summary hardening, docs `56`/`57` as planning-only rendered handoff/export preparation UI governance by themselves, PR `#256` as current-main live bounded rendered handoff/export prepare-only UI behavior with no APS/export/download/dispatch/artifact/package-mutation widening, docs `58`/`59` as APS handoff dispatch governance by themselves, PR `#260` as current-main live bounded backend/API APS handoff dispatch behavior, PR `#261` as malformed-provenance/unexpected-kind fail-closed authority hardening inside that same backend/API boundary, PR `#263` as APS handoff package-row allowlist hardening inside that same backend/API boundary, docs `60`/`61` as planning-only rendered APS handoff dispatch UI governance by themselves, PR `#266` as current-main live bounded rendered APS dispatch UI behavior, docs `62`/`63` as planning-only external export/download readiness governance by themselves, PR `#269` as current-main live bounded backend/API external export/download readiness behavior with no rendered browser download control, public/signed URL, connector dispatch, destination selection, generic downstream dispatch, package mutation/reconstruction, additional row family, schema/runtime/source widening, rendered UI activation, or full mockup activation, docs `64`/`65` as planning-only rendered external export/download readiness UI governance by themselves, PR `#275` as current-main live bounded rendered external export/download readiness UI behavior with no rendered browser download control, public/signed URL, file streaming, connector dispatch, destination selection, generic downstream dispatch, package mutation/reconstruction, additional row family, schema/runtime/source widening, or full mockup activation, docs `66`/`67` as planning-only external export/download delivery governance with no live endpoint or rendered download control by themselves, PR `#278` as current-main live bounded backend/API same-origin delivery, docs `68`/`69` as planning-only rendered delivery UI governance by themselves, PR `#282` as current-main live bounded rendered external export/download delivery UI, PR `#285`/`#286` as review hardening inside that same delivery UI/API boundary with no public/signed URL/connector/destination/generic dispatch widening, docs `78`/`79` as associated-cohort service governance by themselves, PR `#424` as current-main live service-only associated-cohort descriptive materialization through `materialize_pass_entry(...)` only when `formation_basis_json["requested_method_name"] == "descriptive_summary"`, PR `#425` as exact-request hardening inside that same service path, docs `80`/`81` as selected-pass associated-cohort execution-start/result-status governance, PR `#432` as current-main live bounded backend/API selected-pass associated-cohort execution-start/result-status with no UI/result-review/package/handoff/export/source/schema/runtime widening, `82_COHORT_RESULT_REVIEW_FREEZE.md`/`83_COHORT_RESULT_REVIEW_CONTRACT.md` as planning-only future result-review governance over that exact PR `#432` selected-pass associated-cohort path with no live result review by themselves, and future branch-only package, handoff/export, APS handoff UI, external export/download, selected-pass cohort implementation, API/UI, source/schema/runtime, qualitative/hybrid/RAG/vector, or broader associated-cohort implementation candidates as branch-local until merged-main authority confirms them
   - keep the register visually separate from the APS milestone table because it is a workbench lineage overlay, not a 29-milestone APS count change

5. `Completed Chain`
   - render the merged milestone chain as a visual rail or grouped sequence
   - each item should remain readable without JS
   - keep milestone order aligned with the manifest

6. `Milestone Table`
   - render a stable table in markup
   - do not rely on JS to create rows
   - include:
     - milestone title
     - state
     - governing doc
     - key PRs
     - short note

7. `Candidate Next Consumers`
   - render `next_required_decision.candidate_families`
   - if the list is empty under a `settled` packet, render an explicit `None active` message instead of inventing candidates
   - visually distinguish these from the current focus

8. `Deferred Scope`
   - render deferred items as a muted grouped grid or list
   - make it visually obvious these are not in the active lane

9. `Deferred Scope Activation Criteria`
   - render `deferred_scope_activation_contract`
   - include the contract purpose and distinction rules before the itemized entries
   - for each deferred item, render:
     - current boundary
     - candidate-next admission requirements
     - current-focus admission requirements
     - primary authority surfaces
   - keep this section below `Deferred Scope`
   - visually differentiate candidate-next gates from current-focus gates so the stricter threshold for active-lane admission is obvious

## Visual State Mapping

Use these colors consistently:
- `merged`: green
- `merged_with_open_docs_closeout`: green-olive or other clearly separate done-plus-followup state
- `open`: orange
- `planned`: amber
- `settled`: green-gray or other clearly closed-but-not-deferred state
- `deferred`: gray
- `branch_only`: blue or other clearly non-main state
- `branch_local_planning_only`: blue-lavender or other clearly non-main, non-live planning state
- `branch_local_live_bounded_read_only`: cyan-blue or other clearly non-main, read-only live-branch state
- `merged_live_bounded_read_only`: green-blue or other clearly current-main, read-only live bounded state
- `planning_only_result_status_freeze`: amber or other clearly planning-only result/status state; it must not look like live result review, package review, handoff, or export
- `merged_live_bounded_result_status`: green-blue or other clearly current-main, read-only result/status state; it must not look like result approval/rejection, package review, handoff, or export
- `planning_only_result_review_freeze`: amber or other clearly planning-only result-review state; it must not look like a live result-review endpoint, package review, handoff, or export
- `merged_live_bounded_result_review`: green or other clearly current-main bounded result-review state; it must not look like package review, package construction, handoff, or export
- `planning_only_result_review_ui_freeze`: amber or other clearly planning-only result-review UI state; it must not look like live UI behavior by itself, package review, handoff, or export
- `merged_live_bounded_result_review_ui`: green or other clearly current-main bounded result-review UI state; it must not look like execution selection/start UI, package review, handoff, or export
- `merged_live_bounded_read_only_package_review_preview`: green-blue or other clearly current-main, read-only live bounded package-preview state; it must not look like package construction, package-review submit/commit, handoff, or export
- `merged_live_bounded_package_construction_commit`: green or other clearly current-main, write-bounded package-construction state; it must not look like package-review submit/decision, handoff, or export
- `merged_live_bounded_execution_selection`: green-teal or other clearly current-main, write-bounded shell state; it must not look like running analysis, completed execution, results review, package review, or handoff
- `planning_only_package_construction_freeze`: amber or other clearly planning-only package-construction state; it must not look like live package construction, package-review submit/decision, handoff, or export
- `planning_only_package_review_submit_freeze`: amber or other clearly planning-only package-review submit/decision state; it must not look like live package-review submission, package payload mutation, handoff, or export
- `merged_live_bounded_package_review_submit`: green or other clearly current-main bounded backend state; it must not look like rendered UI activation, package payload mutation, handoff, or export
- `merged_live_bounded_package_review_submit_ui`: green or other clearly current-main bounded rendered package-review UI state; PR `#247` may be reflected only as stale-refresh fallback hardening inside this state. It must not look like handoff/export, package payload mutation, package reconstruction, or full mockup activation
- `planning_only_handoff_export_freeze`: amber-brown or other clearly planning-only handoff/export preparation state; it must not look like a live endpoint, APS dispatch, external export, physical artifact, `AnalysisArtifact`, package payload mutation, package reconstruction, or full mockup activation
- `merged_live_bounded_handoff_export_prepare`: green or other clearly current-main bounded backend/API prepare-only state; PR `#252` may be reflected only as blocker-vocabulary/session-summary hardening inside this state. It must not look like rendered UI activation, APS dispatch, external export, downstream dispatch, physical artifact, `AnalysisArtifact`, package payload mutation/reconstruction, or full mockup activation
- `planning_only_handoff_export_ui_freeze`: amber-brown or other clearly planning-only rendered UI state; it must not look like live UI behavior by itself, APS dispatch, external export/download, downstream dispatch, physical artifact, `AnalysisArtifact`, package payload mutation/reconstruction, source/schema/runtime widening, or full mockup activation
- `merged_live_bounded_handoff_export_prepare_ui`: green or other clearly current-main bounded rendered prepare-only UI state; it must not look like APS handoff, external export/download, downstream dispatch, destination selection, physical artifact, `AnalysisArtifact`, package payload mutation/reconstruction, source/schema/runtime widening, execution selection/start UI expansion, or full mockup activation
- `planning_only_aps_handoff_dispatch_freeze`: amber-brown or other clearly planning-only APS handoff dispatch governance state; it must not look like a live endpoint by docs alone, live UI control, external export/download, connector dispatch, destination selection, package mutation/reconstruction, source/schema/runtime widening, execution selection/start UI expansion, or full mockup activation
- `merged_live_bounded_aps_handoff_dispatch`: green or other clearly current-main bounded backend/API APS handoff dispatch state; PR `#261` may be reflected only as malformed-provenance and unexpected-package-kind fail-closed hardening inside this state, and PR `#263` may be reflected only as APS handoff package-row allowlist hardening inside this state. It must not look like rendered UI activation, external export/download, generic downstream dispatch, destination selection, package mutation/reconstruction/rebuild/amendment, source/schema/runtime widening, execution selection/start UI expansion, qualitative/hybrid/RAG/vector execution, or full mockup activation
- `planning_only_aps_handoff_dispatch_ui_freeze`: amber-brown or other clearly planning-only rendered APS dispatch UI governance state; it must not look like live UI behavior by docs alone, backend behavior change, external export/download, generic downstream dispatch, connector dispatch, destination selection, package mutation/reconstruction, additional reconciliation rows, `AnalysisArtifact`, source/schema/runtime widening, execution selection/start UI expansion, qualitative/hybrid/RAG/vector execution, or full mockup activation
- `merged_live_bounded_aps_handoff_dispatch_ui`: green or other clearly current-main bounded rendered APS dispatch UI state. It must not look like backend behavior change, production APS owner-service replacement, external export/download, generic downstream dispatch, connector dispatch, destination selection, package mutation/reconstruction, additional reconciliation rows, `AnalysisArtifact`, source/schema/runtime widening, execution expansion beyond already admitted work, qualitative/hybrid/RAG/vector execution, or full mockup activation
- `planning_only_external_export_download_freeze`: amber-brown or other clearly planning-only external export/download readiness governance state; it must not look like a live endpoint, rendered browser download control, public/signed URL, connector dispatch, destination selection, generic downstream dispatch, package mutation/reconstruction, additional reconciliation/package/artifact rows, `AnalysisArtifact`, source/schema/runtime widening, execution expansion beyond already admitted work, qualitative/hybrid/RAG/vector execution, or full mockup activation
- `merged_live_bounded_external_export_download_readiness`: green or other clearly current-main bounded backend/API readiness state; it must not look like rendered browser download control, public/signed URL generation, connector dispatch, destination selection, generic downstream dispatch, package mutation/reconstruction, additional reconciliation/package/artifact rows, `AnalysisArtifact`, source/schema/runtime widening, rendered UI activation, qualitative/hybrid/RAG/vector execution, or full mockup activation
- `planning_only_external_export_download_readiness_ui_freeze`: amber-brown or other clearly planning-only rendered external export/download readiness UI governance state; it must not look like live UI behavior by docs alone, rendered browser download control, public/signed URL generation, file streaming, connector dispatch, destination selection, generic downstream dispatch, package mutation/reconstruction, additional reconciliation/package/artifact rows, `AnalysisArtifact`, source/schema/runtime widening, qualitative/hybrid/RAG/vector execution, or full mockup activation
- `merged_live_bounded_external_export_download_readiness_ui`: green or other clearly current-main bounded rendered readiness UI state; it must not look like rendered browser download control, public/signed URL generation, file streaming, connector dispatch, destination selection, generic downstream dispatch, package mutation/reconstruction, additional reconciliation/package/artifact rows, `AnalysisArtifact`, source/schema/runtime widening, qualitative/hybrid/RAG/vector execution, or full mockup activation
- `planning_only_external_export_download_delivery_freeze`: amber-brown or other clearly planning-only external export/download delivery governance state; it must not look like a live delivery endpoint, rendered download control, public/signed URL generation, connector dispatch, destination selection, generic downstream dispatch, package mutation/reconstruction, additional row family, `AnalysisArtifact`, schema/runtime/source widening, qualitative/hybrid/RAG/vector expansion, or full mockup activation
- `merged_live_bounded_external_export_download_delivery`: green or other clearly current-main bounded backend/API same-origin delivery state, including PR `#289` lock-release hardening when current-main metadata records it. It must not look like rendered download control activation, public/signed URL generation, connector dispatch, destination selection, generic downstream dispatch, package mutation/reconstruction, additional row family, `AnalysisArtifact`, schema/runtime/source widening, qualitative/hybrid/RAG/vector expansion, or full mockup activation
- `planning_only_external_export_download_delivery_ui_freeze`: amber-brown or other clearly planning-only rendered external export/download delivery UI governance state; it must not look like live UI behavior by docs alone, public/signed URL generation, connector dispatch, destination selection, generic downstream dispatch, package mutation/reconstruction, additional row family, `AnalysisArtifact`, schema/runtime/source widening, qualitative/hybrid/RAG/vector expansion, or full mockup activation
- `merged_live_bounded_external_export_download_delivery_ui`: green or other clearly current-main bounded rendered delivery UI state, including PR `#285`/`#286` review hardening when current-main metadata records it. It must not look like public/signed URL generation, connector dispatch, destination selection, generic downstream dispatch, package mutation/reconstruction, additional row family, `AnalysisArtifact`, schema/runtime/source widening, qualitative/hybrid/RAG/vector expansion, or full mockup activation
- `planning_only_analysis_method_registry_governance`: amber or other clearly planning-only registry-governance state; it must not look like registry implementation, new method admission, execution behavior change, source/schema/runtime widening, UI activation, qualitative/hybrid/RAG/vector expansion, or full mockup activation
- `merged_live_bounded_analysis_method_registry`: green or other clearly current-main support-guardrail state for exactly the existing `cross_correlation`, `decomposition`, and `structural_break` methods; it must not look like new method admission, execution behavior change, source/schema/runtime widening, UI activation, qualitative/hybrid/RAG/vector expansion, or full mockup activation
- `live_bounded_descriptive_summary_method`: green or other clearly current-main lower-level method-support state for PR `#411`; it must not look like associated-cohort admission, UI activation, source/schema/runtime widening, package/handoff/export behavior, qualitative/hybrid/RAG/vector expansion, or full mockup activation
- `live_bounded_descriptive_summary_gatec_single_item`: green or other clearly current-main single-item Gate C admission state for PR `#417`; it must not look like associated-cohort admission, UI activation, source/schema/runtime widening, package/handoff/export behavior, qualitative/hybrid/RAG/vector expansion, or full mockup activation
- `planning_only_descriptive_summary_cohort_requirements`: amber or other clearly planning-only requirements state for associated-cohort `descriptive_summary`; it must not look like live associated-cohort admission, selected-pass workbench breadth, UI activation, source/schema/runtime widening, package/handoff/export behavior, qualitative/hybrid/RAG/vector expansion, or full mockup activation
- `planning_only_descriptive_summary_cohort_service_freeze`: amber or other clearly planning-only service-contract state for docs `78`/`79`; after PR `#424`/`#425`, this state must still not look like selected-pass workbench breadth, UI activation, source/schema/runtime widening, package/handoff/export behavior, qualitative/hybrid/RAG/vector expansion, or full mockup activation
- `live_bounded_descriptive_summary_cohort_service`: green or other clearly current-main service-only associated-cohort state for PR `#424` plus PR `#425` exact-request hardening; it must be limited to `materialize_pass_entry(...)` with exact `formation_basis_json["requested_method_name"] == "descriptive_summary"` and must not look like selected-pass workbench breadth, UI activation, source/schema/runtime widening, package/handoff/export behavior, qualitative/hybrid/RAG/vector expansion, or full mockup activation
- `live_bounded_descriptive_summary_selected_pass_cohort_execution`: green or other clearly current-main backend/API selected-pass associated-cohort state for PR `#432`; it must be limited to exact execution-start/result-status behavior over existing selected-pass surfaces and must not look like UI activation, result review, package/handoff/export behavior, source/schema/runtime widening, qualitative/hybrid/RAG/vector expansion, or full mockup activation
- `planning_only_descriptive_summary_selected_pass_cohort_result_review`: amber or other clearly planning-only associated-cohort result-review governance state for `82_COHORT_RESULT_REVIEW_FREEZE.md`/`83_COHORT_RESULT_REVIEW_CONTRACT.md`; it must not look like live result review, UI activation, package/handoff/export behavior, source/schema/runtime widening, pass-entry changes, qualitative/hybrid/RAG/vector expansion, or full mockup activation
- `branch_live_bounded_package_review_submit_ui`: blue or other clearly branch-local bounded rendered UI state for future unmerged candidates only; it must not look like merged-main truth, handoff/export, package payload mutation, or full mockup activation

State labels should remain visible in text, not color alone.

## Layout Guidance

### Desktop

- center the artifact in a readable max-width frame
- use a distinct top summary band
- keep the current focus card above the completed chain
- use flat, information-dense layout rather than decorative dashboard chrome

### Mobile

- stack summary cards vertically
- let the completed chain wrap into rows
- keep milestone rows readable without horizontal overflow where possible

## Content Priority

The user should understand this in under ten seconds:
1. what is already done on `main`
2. what the current focus is
3. what the Layer 3 workbench current decision is
4. which workbench slices are planning-only versus live bounded implementation
5. what the next bounded consumer candidates are
6. what is still explicitly deferred
7. what each deferred item would need before it could stop being deferred

If a renderer has to choose between visual flourish and certainty, prefer certainty.

## Implementation Guidance For Cowork

Preferred approach:
- generate primary sections as static HTML from the refreshed manifest
- use CSS for layout and state styling
- use JS only for non-essential polish such as expand-collapse or filters

Acceptable optional enhancement:
- add Mermaid only as a duplicate visualization of an already-readable static section

Unacceptable approach:
- store a stale `const manifest = ...` snapshot in artifact HTML without rewriting that artifact during refresh
- hide the milestone table behind DOM-building JS
- make the only progress diagram depend on Mermaid
