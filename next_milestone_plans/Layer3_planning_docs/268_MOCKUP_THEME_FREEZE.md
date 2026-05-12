# Layer 3 Mockup Theme Freeze

Status: current-main planning/control freeze for `pixel_perfect_mockup_workbench_theme_freeze`.

```yaml
selected_planning_mode: pixel_perfect_mockup_workbench_theme_freeze
entry_decision: named_mockup_theme_goal_selected_planning_only
base_branch: main
implementation_branch: codex/l3-mockup-theme-freeze
live_behavior_change: false
upstream_docs:
  - 238_LAYER3_THEME_TO_FULL_PIPELINE_SYNTHESIS.md
  - 265_FULL_MOCKUP_NAMED_JOURNEY_PACKET.md
  - 267_POST_REENTRY_NAMED_PACKET_CLOSEOUT.md
selected_product_operator_use_case: pixel_perfect_functional_layer3_mockup_workbench_theme
selected_theme_target: layer3_mockup_workbench_theme
target_route_family: /review/layer3
activation_mode: dedicated_theme_planning_only
pixel_perfect_requirement: selected
functional_requirement: selected_except_contextual_text_boxes
contextual_text_box_policy: classify_as_help_or_nonproduction_annotation_before_implementation
visual_acceptance_corpus_required: true
server_authority_requirement: required
browser_storage_policy: no_durable_authority
visual_diff_required: true
headed_headless_required: true
responsive_accessibility_required: true
implementation_entry_allowed_next: false
next_required_boundary: implementation_entry_freeze_for_dedicated_mockup_theme_before_code
```

## Purpose

This freeze records the product/UX intent that the Layer 3 workbench should be able to operate as a pixel-perfect functional rendition of the mockup set under its own dedicated Layer 3 workbench theme.

It corrects the weaker earlier posture that treated the mockups only as target-state design/specification inputs and explicitly did not require pixel-perfect reproduction. That prior posture was safe for avoiding overclaiming, but it is now incomplete because the intended product direction is stronger: the mockup visual language should become an implementation target, not just inspiration, once a separate implementation-entry freeze defines the exact technical slice.

This document still admits no runtime behavior. It names the goal and the acceptance boundary; it does not implement the theme, route changes, API changes, state changes, source expansion, RAG/vector behavior, package mutation, connector/destination behavior, auth/security behavior, or browser-owned durable authority.

## Canonical visual acceptance corpus

The future mockup-theme implementation must treat the following paths as the visual/user-flow corpus to reconcile before code:

- `C:\Users\benny\Downloads\layer3mockups\example-use-case-location-in-pdf.png`
- `C:\Users\benny\Downloads\layer3mockups\doc_spec_file_layer3_preplanning.txt`
- `C:\Users\benny\Downloads\layer3mockups\layer3_mockup_file.svg`
- `C:\Users\benny\Downloads\layer3mockups\big_layer3-overview_bigview1.png`
- `C:\Users\benny\Downloads\layer3mockups\focus_on_these`
- `C:\Users\benny\Downloads\layer3mockups\clear-screenshots`
- `C:\Users\benny\Downloads\layer3mockups\userflow`

The corpus is design/product authority for layout, flow, visual hierarchy, and user-facing semantics. It is not server authority for data, state, persistence, execution, source admission, retrieval, package mutation, dispatch, delivery, or security.

## Selected UX target

The selected user-facing target is a dedicated `/review/layer3` workbench theme, `layer3_mockup_workbench_theme`, that visually and interactively follows the mockup flow:

- intent entry through natural-language query and manual/custom specification panels;
- source/topic/focus chips that remain distinguishable from server-authoritative source records;
- Pre-3A intake and discovery presentation;
- Sublayer 3A / Gate B material ledger, review, approval, denial, isolation, and validation presentation;
- Sublayer 3B / Gate C typing and unit/group/set formation presentation;
- Sublayer 3C quantitative, qualitative, and hybrid/mixed analysis-plane presentation;
- output grids for insights, facts, and data with provenance back to ingress objects;
- persistent context showing the submitted intent/source posture where it helps the operator follow the flow.

The theme should be pixel-perfect against the selected mockup frames where those frames define productive UI. It must remain functional and usable, not a static screenshot shell.

## Functional versus contextual elements

Functional UI elements include controls, cards, chips, gates, ledgers, arrows, sublayer boundaries, analysis-plane panels, execution state panels, output cards, provenance links, disabled states, and navigation/progression cues.

Contextual text boxes, explanatory side panels, and annotation blocks must be classified before implementation as one of:

- in-app help or collapsible explanation;
- onboarding/demo-only annotation;
- non-production documentation outside the live theme.

They should not be blindly copied as always-visible production UI unless the implementation-entry freeze selects them as live help or operator context.

## Non-fragility, modularity, and scalability requirements

The mockup theme must not fork workflow authority. The same server-authoritative `/review/layer3` state, request/response contracts, identifiers, forbidden-control behavior, and failure states must drive every admitted theme.

The implementation-entry freeze must preserve these constraints:

- theme-specific code may own presentation, layout, styling, and visual-diff fixtures;
- shared route/API payload shapes must not become theme-specific;
- browser state may cache presentation convenience only, never durable workflow authority;
- unsupported mockup regions must render as disabled, unavailable, or planning-only rather than fake controls;
- visual acceptance must use deterministic fixture state instead of seeded shared runtime state;
- headed and headless browser proof must cover the same target route and fixture state;
- responsive/accessibility behavior must be specified before claiming pixel-perfect production readiness;
- future source, connector, package, RAG, mockup, and auth/security expansions must remain separate owner surfaces unless a later freeze admits them.

## Required next implementation-entry freeze

A future implementation may proceed only after a separate freeze selects all of the following:

- theme id, selector behavior, and route integration for `layer3_mockup_workbench_theme`;
- exact mockup frames/screens to implement first;
- state-to-screen mapping from server workbench responses to mockup panels;
- deterministic fixture scenario derived from the semiconductor/federal-infrastructure user-flow example;
- classification of every explanatory/contextual text box;
- disabled-state policy for mockup-visible but runtime-blocked capabilities such as broad RAG/vector retrieval, broad qualitative/hybrid execution, external connector/destination writes, package mutation, and full auth/security behavior;
- visual-diff method, viewport matrix, tolerance policy, artifact naming, and expected screenshots;
- headed/headless proof and theme/accessibility proof obligations;
- no-go file/surface list for backend/API/model/migration/runtime behavior unless explicitly admitted.

## Non-admission statement

This freeze admits no runtime behavior, route/API/DTO/model/migration/service behavior, executable test behavior, rendered UI behavior, source adapter behavior, local upload, local-directory ingestion, web connector retrieval, RAG/vector retrieval, package mutation behavior, external connector/destination behavior, provider/public URL behavior, broad qualitative/hybrid/RAG behavior, full mockup activation, auth/security behavior, CI workflow change, Playwright configuration change, or frontend-only durable authority.

It selects the pixel-perfect functional mockup workbench theme as the next product/UX target to freeze for implementation. It does not implement that target.
