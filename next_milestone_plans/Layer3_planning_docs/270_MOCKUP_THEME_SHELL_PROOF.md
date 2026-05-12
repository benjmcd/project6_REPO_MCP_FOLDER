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

## Authority and non-fragility notes

The new theme does not create server authority, write durable workflow state, or introduce new API payloads. Browser storage remains a presentation preference store only. Unsupported future affordances are rendered as non-interactive unavailable labels, not buttons or forms.

The new exact theme value reuses the existing `workbench` rendering base through a theme variant. This keeps the CSS modular and avoids duplicating the already-tested live workbench visual system.

## Validation expectation

The pass is valid only if:

- `python .\tools\l3-progress-check.py` passes.
- `python -m pytest .\backend\tests\test_layer3_page.py` passes.
- JSON manifests parse.
- The targeted Playwright mockup theme test passes in headless Chromium.
- CI remains green before merge.
