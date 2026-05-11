# Layer 3 Theme Contracts

Status: planning/control contract for cross-theme Layer 3 readiness.

This document defines the presentation/runtime boundary for Layer 3 themes. It does not make Claude a live theme and does not add backend or frontend behavior.

## Theme Classification

| Theme or surface | Current status | Runtime authority | Next required decision |
| --- | --- | --- | --- |
| `system` | live shared theme preference | `/review/layer3` live runtime | maintain parity proof |
| `light` | live shared theme preference | `/review/layer3` live runtime | maintain parity proof |
| `dark` | live shared theme preference | `/review/layer3` live runtime | maintain parity proof |
| `workbench` | live Layer 3-specific theme | `/review/layer3` live runtime | maintain parity proof |
| `claude` selector option | live redirect only | redirects to static prototype | decide prototype-only vs live admission |
| `/review/layer3/static/claude.html` | static prototype/sample-state surface | no live Layer 3 API authority | separate implementation freeze before live use |

## Page Classification

| Page | Current Layer 3 role | Theme relevance | Boundary |
| --- | --- | --- | --- |
| `/review/layer3` | live Layer 3 workbench | primary theme-complete target | can drive current supported pipeline |
| `/review/layer3/static/claude.html` | static prototype | visual/design reference only | not a live pipeline page |
| `/review/nrc-aps` and subpages | upstream review surfaces | shared theme context only | not Layer 3 workbench authority |
| `/review/analyst-insight` | adjacent review surface | future cross-page consistency | not current Layer 3 pipeline authority |
| test harness routes under `/__test/layer3/*` | setup only | no user-facing theme | may seed authority for tests only |

## Cross-Theme Runtime Contract

Themes may change only presentation:

- colors, spacing, layout density, responsive arrangement, and focus styling;
- labels or visible grouping only when the same operation remains clear and accessible;
- route location only when the route is explicitly classified as live or prototype.

Themes must not change:

- API route selection or payload fields;
- source IDs, source classes, or materialization authority;
- DB rows read or written;
- artifacts read or written;
- package contents, handoff state, provider state, connector state, or delivery semantics;
- auth/security behavior;
- durable authority source.

Browser state may hold form draft, UI focus, theme preference, and recovery hints. Browser state is never source authority, package authority, provider authority, connector authority, or final workflow authority.

## Extensibility Contract

Theme extensibility is presentation-only until a later freeze says otherwise. A new theme must bind to the same route state, endpoint sequence, source IDs, readiness payloads, artifact references, package identifiers, and stop reasons as the standard workbench. Any theme-specific adapter must be a thin mapping layer for DOM structure, selectors, labels, or visual affordances, not a parallel workflow or a second source of runtime truth.

Scalability depends on shared contracts rather than copied flows. Future pages or themes must reuse the existing source/material/Gate B/Gate C/plan/execution/package/handoff/export progression wherever the route is admitted. If a page cannot reuse that progression, classify it as prototype, manual, or deferred instead of partially claiming live parity.

Non-fragile proof requires stable selectors, server-returned identifiers, deterministic source setup, headed and headless evidence where browser behavior is relevant, and explicit negative assertions for forbidden controls. Do not accept proof that relies on local storage alone, fixture row order, incidental timing, viewport-specific visibility, or sample text that appears authoritative.

## Claude-Specific Boundary

Claude is currently a static prototype. A live Claude implementation is not admitted until a future freeze answers all of these:

1. Is Claude a route-specific skin of `/review/layer3`, or a separate live route using the same API driver?
2. Which DOM selectors remain stable across standard and Claude themes?
3. Which prototype sections map to live API state, and which must be removed or kept sample-only?
4. How is "User Manual / Custom Specification" populated only from real corpus-linked authority?
5. What is the exact fail-closed behavior when live state does not contain a prototype field?
6. Which headed/headless screenshots and request-shape assertions prove parity?

Recommended answer for the next pass: keep Claude prototype-only until the existing live themes have a complete parity proof. Then admit Claude only as a presentation layer over the existing server-authoritative pipeline, not as a separate browser-owned workflow.

## User Manual And Custom Specification Rule

No theme may populate a user-manual, custom-specification, notes, or context field with fabricated or decorative text. Such fields must be:

- empty;
- explicitly sample/prototype-only on a prototype route; or
- populated from server-authoritative corpus/session/package/handoff state with a visible provenance label.

For a live Claude theme, this means any "User Manual / Custom Specification" area must either be absent, empty, or tied to real selected corpus/source/session state. It must not contain generic sample instructions that appear to be associated with the corpus.

## Negative Invariants

All theme/page work must keep these absent unless a separate freeze admits them:

- local upload, local-directory ingestion, broad file upload, drag-and-drop ingestion;
- arbitrary local path input or path traversal;
- web connector retrieval, real connector invocation, destination selection, destination write;
- source adapter registry and new source classes;
- RAG/vector retrieval or index creation;
- provider-public URL, public proxy URL, provider network write, provider object-store write;
- package mutation, reconstruction, supersession, replacement, or payload rewrite;
- hidden LLM planning, prompt/model controls, full mockup activation;
- auth/security behavior changes;
- frontend-only durable authority.

## Acceptance Criteria For Theme Readiness

A theme/page is "Layer 3 pipeline ready" only when:

- it is classified as live, not prototype;
- it can select or consume the same server-authoritative source IDs as the standard workbench;
- it drives the same API path through the maximum currently admitted workflow;
- DB and artifact assertions are proven outside browser state;
- headed and headless browser evidence shows visible, selectable, non-overlapping controls;
- forbidden controls and side effects remain absent;
- the proof names the exact route, theme, selected source classes, completed steps, and stop point.
