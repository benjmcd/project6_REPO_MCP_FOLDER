# Layer 3 Mockup Theme Shell Implementation Proof

Status: current-branch rendered UI implementation proof for `layer3_mockup_workbench_theme`.

```yaml
selected_runtime_mode: rendered_mockup_theme_shell_fixture_projection
entry_freeze: 269_MOCKUP_THEME_ENTRY_FREEZE.md
implementation_branch: codex/l3-mockup-theme-shell
live_behavior_change: true
route_api_behavior_change: false
model_migration_service_behavior_change: false
selected_theme_target: layer3_mockup_workbench_theme
selected_first_slice: mockup_theme_shell_and_fixture_projection
target_route_family: /review/layer3
fixture_scenario: semiconductor_infrastructure_auto_supply_chain
server_state_mapping_preserved: true
browser_storage_policy: presentation_cache_only_no_durable_authority
contextual_text_box_policy: collapsible_help_or_demo_annotation_not_required_always_visible
implemented_surfaces:
  - backend/app/review_ui/static/layer3.html
  - backend/app/review_ui/static/layer3.css
  - backend/app/review_ui/static/layer3.js
  - backend/tests/test_layer3_page.py
  - e2e/layer3-workbench.spec.js
  - next_milestone_plans/layer3-mockups/frames/manifest.json
blocked_runtime:
  - backend_api_behavior_change
  - backend_model_or_migration_change
  - backend_service_behavior_change
  - new_source_family_runtime
  - local_upload_or_local_directory_ingestion
  - web_connector_retrieval
  - rag_vector_retrieval
  - external_connector_destination_runtime
  - rendered_package_mutation_runtime
  - broad_qualitative_hybrid_rag_runtime
  - auth_security_behavior_change
  - full_mockup_durable_workflow_activation
  - frontend_only_durable_authority
```

## Implementation summary

This pass makes the selected mockup theme visible as a dedicated Layer 3 workbench theme without changing backend runtime behavior.

The implementation adds:

- A `Mockup Workbench` theme selector option backed by the exact `layer3_mockup_workbench_theme` preference value.
- A theme variant mapping that resolves the exact theme to the existing `workbench` base style while adding `data-theme-variant="layer3_mockup_workbench_theme"`.
- A static fixture-projection shell for the semiconductor infrastructure and auto supply-chain scenario.
- First-slice flow cards for Pre-3A, Gate B, Gate C, Sublayer 3A, Sublayer 3B, and Sublayer 3C.
- Explicit unavailable markers for future behavior instead of live controls.
- A collapsible acceptance-frame list populated from JS fixture metadata.
- Repo-local first-slice acceptance frame copies with SHA-256 metadata in `next_milestone_plans/layer3-mockups/frames/manifest.json`.
- A static `focus_on_these/sublayer3C.png` fixture projection with separate quantitative and qualitative execution lanes, Gate B ingress object stacks, unavailable/deferred objects, process notes, and generated-output cards.
- E2E assertions that the Sublayer 3C fixture projection is visible, non-interactive, and still creates no backend requests for blocked source, package, connector, or mockup runtime paths.
- E2E visual-acceptance proof that parses `next_milestone_plans/layer3-mockups/frames/manifest.json`, performs repo-local frame hash verification plus size checks for all seven frames, checks the selected `sublayer-c.png` dimensions, emits a layer3-mockup-theme-shell.png screenshot attachment, and verifies the rendered Sublayer 3C lane geometry against the selected frame mapping.
- Frame-specific fidelity improvements for `focus_on_these/sublayer3C.png`: centered `Sublayer 3C` / `Analysis Execution Environments` canvas title, exact quantitative/qualitative lane labels, and bracketed Gate B ingress stacks before the process arrows.

## Authority and non-fragility notes

The new theme does not create server authority, write durable workflow state, or introduce new API payloads. Browser storage remains a presentation preference store only. Unsupported future affordances are rendered as non-interactive unavailable labels, not buttons or forms.

The new exact theme value reuses the existing `workbench` rendering base through a theme variant. This keeps the CSS modular and avoids duplicating the already-tested live workbench visual system.

## Validation expectation

The pass is valid only if:

- `python .\tools\l3-progress-check.py` passes.
- `python -m pytest .\backend\tests\test_layer3_page.py` passes.
- JSON manifests parse.
- The targeted Playwright mockup theme test passes in headless Chromium and headed Chromium.
- The targeted Playwright mockup theme test emits a screenshot attachment for the dedicated mockup shell and validates the repo-local frame manifest before relying on rendered UI assertions.
- CI remains green before merge.

## User-flow and PDF-location projection proof addendum

This proof slice carries a bounded static projection for the mockup user-flow and PDF-location frames inside `layer3_mockup_workbench_theme`. The section is `#mockup-userflow-board` and maps the user natural-language query, manual/custom specification, located PDF evidence cards, Pre-3A, Sublayer 3A, Sublayer 3B, Sublayer 3C, and traceable output-review sequence into the dedicated theme without adding rendered buttons, new backend calls, or durable browser-owned workflow authority.

The added repo-local frame is `next_milestone_plans/layer3-mockups/frames/pdf-location.png`, copied from `C:\Users\benny\Downloads\layer3mockups\example-use-case-location-in-pdf.png`; the Downloads path remains provenance only. Playwright now verifies eight repo-local visual acceptance frames, the `#mockup-userflow-board` data-source attributes, five user-flow stages, two PDF evidence sheets, headed/headless screenshot attachment, and the existing no-backend-widening API-request guard.

## Sublayer 3A/3B projection proof addendum

This proof slice adds `#mockup-sublayers-ab-board` for `focus_on_these/sublayer3A_and_sublayer3B.png`. The board renders a static Sublayer 3A Gate B material ledger with 20 ingress objects, a Sublayer 3B Gate C grouping field, seven quantitative objects, seven qualitative objects, and six hybrid/mixed objects. The projection is visual/theme-only and adds no rendered buttons, backend API calls, source expansion, execution runtime, or browser-owned durable authority.

Playwright now verifies the Sublayer 3A/3B frame source, the 20-object ledger, the 7/7/6 typed grouping split, a three-column desktop board layout, the `layer3-mockup-sublayers-ab-board.png` screenshot attachment, and the existing no-backend-widening request guard.

## Mockup theme responsive proof addendum

This proof slice adds mobile responsive acceptance for `layer3_mockup_workbench_theme`. Playwright verifies the dedicated mockup theme at a 390 px viewport, keeps the shell, user-flow board, Sublayer 3A/3B board, and Sublayer 3C lanes visible, proves no horizontal viewport overflow, and confirms the user-flow board, Sublayer 3A/3B board, user-flow stage row, and both Sublayer 3C lane bodies collapse to one-column layouts.

The proof remains static/theme-only: it adds no backend route, API, model, migration, service, source runtime, connector/destination dispatch, package mutation, broad qualitative/hybrid/RAG runtime, full durable mockup activation, or browser-owned durable authority.

