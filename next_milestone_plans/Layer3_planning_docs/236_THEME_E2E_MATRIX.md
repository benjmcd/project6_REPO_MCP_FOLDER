# Layer 3 Theme E2E Matrix

Status: planning/test architecture for bounded cross-theme Layer 3 proof.

This document defines the E2E proof shape needed before claiming that the Layer 3 pipeline is practically usable across admitted themes and pages. It is test planning only.

## Harness Rules

The harness must keep these responsibilities separate:

- source seeding and server-owned materialization setup;
- API flow driver;
- rendered UI driver;
- DB assertions;
- artifact/file assertions;
- forbidden side-effect assertions;
- browser/theme visual assertions.

The harness must use deterministic source IDs, deterministic content, stable hashes, stable selectors, and contract-returned artifact references. It must avoid incidental timestamp, row-order, path, viewport, and browser-local assumptions unless those are explicit contracts.

## Coverage Matrix

| Segment | API proof | UI proof on live themes | Claude proof today | Future Claude proof |
| --- | --- | --- | --- | --- |
| seed/materialize source authority | covered by backend/API and rendered materialize tests | covered on `/review/layer3` | not live | only after admission |
| source visibility/selection | covered by API candidates and Playwright | covered on live workbench | not live | required |
| preflight/source/material preview | covered by bounded E2E | covered on live workbench | not live | required |
| Gate B/Gate C | covered by backend/API and Playwright | covered on live workbench | not live | required |
| plan preview/approval | covered by backend/API and Playwright | covered on live workbench | not live | required |
| execution select/start | covered by bounded E2E and rendered tests | covered on live workbench | not live | required |
| result status/review | covered by backend/API and rendered tests | covered on live workbench | not live | required |
| package preview/commit/submit | covered by backend/API and rendered tests | covered on live workbench | not live | required |
| handoff/export prepare | covered by backend/API and rendered tests | covered on live workbench | not live | required |
| APS handoff dispatch | covered by backend/API and rendered tests | covered on live workbench | not live | required |
| external export/download prepare | covered by backend/API and rendered tests | covered on live workbench | not live | required |
| same-origin delivery | covered by backend/API and rendered tests where server `delivery_ui` admits it | covered on live workbench | not live | required where admitted |
| same-origin signed-reference | covered by backend/API and rendered tests | covered on live workbench | not live | required where admitted |
| provider-private prepare/status | backend/API-only | no rendered UI | not live | no rendered proof until separate UI freeze |

## Minimal Next Test Pass

The next test-only pass should prove parity across existing live themes, not Claude:

1. seed or materialize deterministic admitted source authority;
2. open `/review/layer3`;
3. drive the maximum supported rendered flow once using the canonical workbench path;
4. switch among `system`, `light`, `dark`, and `workbench` at stable phase boundaries;
5. assert request payload shape is unchanged by theme;
6. assert visible state, focus, disabled/enabled states, and delivery gates remain coherent;
7. assert forbidden controls remain absent;
8. run in headless and headed Chromium.

This pass should not add controls, routes, DTOs, models, migrations, services, source classes, provider behavior, connector behavior, package mutation, RAG/vector behavior, mockup activation, hidden LLM planning, or auth/security behavior.

## Future Claude Test Pass

If Claude is admitted as live:

1. create a live-Claude implementation freeze first;
2. define whether Claude shares `/review/layer3` or uses a separate live route;
3. map prototype sections to live API state or remove them from live mode;
4. prove the same source IDs drive the same API path;
5. assert no sample-state-only fields are presented as corpus state;
6. assert "User Manual / Custom Specification" is absent, empty, or corpus-linked;
7. assert request payload equality with the standard workbench;
8. assert DB/artifact state after major phases;
9. assert forbidden controls and side effects remain absent;
10. run headed and headless Chromium across desktop and mobile breakpoints.

## DB And Artifact Assertions

Browser tests should not be the durable authority for DB or artifact state. Cross-theme E2E proof should pair browser flow with backend assertions that confirm:

- materialization itself starts no Layer 3 flow;
- preflight/source/material/Gate B starts normal session state only at admitted steps;
- Gate C commits typing only when requested;
- plan approval does not start execution;
- execution start creates only admitted pass runs/artifacts;
- package commit writes only admitted package rows/files;
- handoff/export and APS dispatch write only admitted handoff/export state;
- same-origin delivery streams only existing server-owned artifacts;
- provider-private prepare/status, when tested, remains backend/API-only and fake-provider-only.

## Forbidden Side Effects

Every theme/page E2E pass must assert absence of:

- unsupported source expansion;
- local upload and local-directory ingestion;
- web connector retrieval;
- RAG/vector retrieval;
- provider-public URL generation;
- real connector invocation or destination write;
- broad package mutation/reconstruction;
- package payload rewrite outside admitted package commit behavior;
- hidden LLM planning;
- frontend-only durable authority;
- full mockup activation;
- auth/security behavior changes.

## Completion Standard

The project can claim theme-complete Layer 3 readiness only when every admitted live theme/page combination has:

- source setup proof;
- API request-shape proof;
- rendered interaction proof;
- DB/artifact proof;
- visual/focus proof;
- forbidden side-effect proof;
- exact stop point or delivery result;
- explicit classification for any non-live theme/page.
