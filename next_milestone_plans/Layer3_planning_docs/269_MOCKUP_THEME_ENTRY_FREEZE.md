# Layer 3 Mockup Theme Implementation Entry Freeze

Status: current-main implementation-entry planning/control freeze for `mockup_theme_implementation_entry_freeze`.

This freeze admits no runtime behavior. It converts the selected pixel-perfect mockup workbench theme goal from `268_MOCKUP_THEME_FREEZE.md` into the narrowest safe implementation-entry contract for the next code pass.

```yaml
selected_planning_mode: mockup_theme_implementation_entry_freeze
entry_decision: implementation_entry_selected_planning_only_no_code
base_branch: main
implementation_branch: codex/l3-mockup-theme-entry-freeze
live_behavior_change: false
upstream_docs:
  - 268_MOCKUP_THEME_FREEZE.md
selected_product_operator_use_case: pixel_perfect_functional_layer3_mockup_workbench_theme
selected_theme_target: layer3_mockup_workbench_theme
target_route_family: /review/layer3
selected_first_slice: mockup_theme_shell_and_fixture_projection
implementation_type: rendered_theme_only_after_this_freeze
allowed_future_code_surfaces:
  - backend/app/review_ui/static/layer3.html
  - backend/app/review_ui/static/layer3.css
  - backend/app/review_ui/static/layer3.js
  - backend/tests/test_layer3_page.py
  - e2e/layer3-workbench.spec.js
  - next_milestone_plans/Layer3_planning_docs
  - next_milestone_plans/layer3_progress_board.md
  - next_milestone_plans/layer3_progress_manifest.json
  - next_milestone_plans/layer3_workbench_proof_manifest.json
  - tools/l3-progress-check.py
forbidden_future_code_surfaces_unless_refrozen:
  - backend/app/api
  - backend/app/models
  - backend/alembic
  - backend/app/services
  - backend/tests/test_layer3_api.py
  - .github/workflows
exact_mockup_frames_first_slice:
  - userflow/layer3_user-flow-overview1.png
  - userflow/layer3_user-flow-overview2.png
  - clear-screenshots/userflow_slide1.png
  - clear-screenshots/userflow_slide1_general-example.png
  - clear-screenshots/userflow_slide1_specific_usecase-example_zoomed-in.png
  - focus_on_these/sublayer3A_and_sublayer3B.png
  - focus_on_these/sublayer3C.png
deterministic_fixture_scenario: semiconductor_infrastructure_auto_supply_chain
contextual_text_box_policy: collapsible_help_or_demo_annotation_not_required_always_visible
server_state_mapping_required: true
mockup_visual_diff_required: true
headed_headless_required: true
theme_accessibility_required: true
browser_storage_policy: presentation_cache_only_no_durable_authority
implementation_entry_allowed_next: true
next_allowed_action: implement_mockup_theme_shell_and_fixture_projection
```

## Why this freeze exists

The mockups are now product authority for a dedicated Layer 3 workbench theme, but that does not make every mockup affordance implementation-ready. The immediate risk is over-activating target-state visuals as if they were live runtime authority.

This freeze prevents that by selecting one bounded rendered-theme slice:

- `mockup_theme_shell_and_fixture_projection`
- dedicated `layer3_mockup_workbench_theme`
- existing `/review/layer3` route family
- server-authoritative state projection only
- deterministic fixture content where current runtime cannot yet produce the visualized journey
- no backend/API/model/migration/service behavior change

The next code pass may implement the visual shell and fixture projection. It may not turn deferred source, connector, package mutation, broad qualitative/hybrid/RAG, auth/security, or full mockup runtime behavior live.

## First implementation slice

The next implementation pass is authorized only for a rendered theme shell and deterministic fixture projection. The theme should make the mockup journey usable as a workbench presentation and operator-orientation surface without pretending unsupported runtime behavior exists.

The first slice must include:

- A dedicated theme identity named `layer3_mockup_workbench_theme`.
- A dark browser-like workbench shell matching the selected mockup corpus direction.
- A natural-language/manual-spec area using the deterministic semiconductor infrastructure scenario.
- Compact source/context chips that visually match the mockup style while remaining server-derived or fixture-derived.
- Pre-3A, Gate B, Gate C, Sublayer 3A, Sublayer 3B, and Sublayer 3C visualization regions where those regions are present in the selected frames.
- Disabled or unavailable placeholders for unsupported affordances, with labels that clearly say the runtime is not admitted.
- Output/provenance cards only as fixture projection or existing server-derived projection, not as new runtime generation.

The first slice must not require a new route contract. If the existing static review UI cannot carry the selected theme without API or service changes, implementation must stop and the entry freeze must be revised.

## Exact frames for first-slice visual acceptance

The full corpus remains design context, but the first implementation slice is accepted against this narrower frame set:

- `userflow/layer3_user-flow-overview1.png`
- `userflow/layer3_user-flow-overview2.png`
- `clear-screenshots/userflow_slide1.png`
- `clear-screenshots/userflow_slide1_general-example.png`
- `clear-screenshots/userflow_slide1_specific_usecase-example_zoomed-in.png`
- `focus_on_these/sublayer3A_and_sublayer3B.png`
- `focus_on_these/sublayer3C.png`

This selection is intentionally smaller than the full mockup corpus because the next pass needs a stable visual target, not an open-ended design reconstruction. Additional frames can be admitted later only by a follow-up freeze or proof update.

## Contextual text-box policy

The mockup corpus contains text boxes that explain, contextualize, or annotate the intended experience. The next implementation must classify each such box before rendering it as persistent UI.

Allowed classifications:

- `functional_control`: the box is an actual operator affordance and must be backed by server state or an explicit fixture contract.
- `collapsible_help`: the box explains the flow and may be available as help, onboarding, or contextual disclosure.
- `demo_annotation`: the box is presentation-only and must not appear as always-visible production UI unless the implementation records why it is needed.
- `not_admitted`: the box describes unsupported future behavior and must be disabled, hidden behind help, or marked unavailable.

The default classification is `collapsible_help_or_demo_annotation_not_required_always_visible`. Nothing in the mockups should become durable product state merely because it appears as explanatory text.

## Server-state and browser-storage mapping

The next pass must preserve the existing authority boundary:

- Server identifiers and existing server responses remain the only authoritative source for session, source, plan, execution, package, handoff, and output state.
- Browser storage may cache presentation preferences only.
- Browser storage must not become durable workflow authority.
- The deterministic fixture may fill visual gaps for the semiconductor scenario, but it must be named as fixture projection in code/tests/proof.
- Unsupported mockup regions must render as disabled or unavailable instead of silently simulating a live backend capability.

The browser storage policy for this pass is `presentation_cache_only_no_durable_authority`.

## Visual, responsive, and accessibility proof obligations

The implementation pass after this freeze must produce proof at the rendered UI layer, not just static code inspection.

Required proof:

- Headed Chrome proof for the dedicated theme.
- Headless Chrome proof for the dedicated theme.
- Visual diff or screenshot comparison artifacts against the selected frame set, with explicit tolerances or documented non-pixel-perfect deltas.
- Desktop viewport proof first, because the selected corpus is desktop-workbench dominant.
- Responsive stacked-layout proof for smaller widths.
- Keyboard navigation over admitted controls.
- Contrast and non-color-only status labeling.
- No interactive control that depends on unsupported backend/API behavior unless it is disabled or explicitly marked unavailable.

The first implementation pass may define the exact diff tooling, but it may not skip visual proof entirely.

## Forbidden next-pass surfaces unless refrozen

The next implementation pass must not touch these surfaces unless a fresh freeze proves the widening is necessary:

- `backend/app/api`
- `backend/app/models`
- `backend/alembic`
- `backend/app/services`
- `backend/tests/test_layer3_api.py`
- `.github/workflows`

The next implementation pass also must not admit:

- New source-family runtime.
- Local upload or local-directory ingestion.
- Web connector retrieval.
- RAG/vector retrieval.
- External connector invocation or destination writes.
- Rendered package mutation controls.
- Package payload rewriting or reconstruction.
- Broad qualitative/hybrid/RAG execution.
- Auth/security runtime changes.
- Hidden LLM planning.
- Full mockup activation as durable workflow runtime.
- Browser-owned workflow authority.

## Stop conditions

Implementation must stop and return to planning/control if any of these are true:

- The existing `/review/layer3` static UI cannot support a dedicated theme without backend/API changes.
- Pixel-perfect structure requires a new server contract rather than fixture projection or existing state projection.
- A mockup frame implies live behavior that is not admitted by current runtime authority.
- The next pass cannot distinguish fixture projection from server-authoritative state.
- Headed/headless proof would require changing Playwright or CI behavior outside the admitted surfaces.
- Accessibility/responsive requirements conflict with exact visual replication and need a product decision.

## Self-audit conclusion

This is the narrowest coherent entry point after `268_MOCKUP_THEME_FREEZE`: it honors the user's selected pixel-perfect functional mockup theme direction while preserving non-fragility, modularity, and scalability by keeping runtime authority server-owned, constraining code surfaces, naming deterministic fixture boundaries, and requiring visual/headed/headless proof before claiming the theme is implemented.
