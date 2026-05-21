# 939 - Layer 3 Bounded Readiness Audit

## Status

Status: bounded readiness and mockup activation blocker audit for current main.

Doc: `939-readiness-audit.md`.

Predecessor current-main sync doc: `938-source-supersession-current-main-sync.md`.

Audit branch: `codex/l3-final-readiness-audit`.

Current main authority: `project6-origin/main` at `d3f70d409f760b08c53f7cd5cb6a79f4cc846e6c`.

Audit result: bounded trial-usable for the current-main-selected source-directory rendered path, but not ready for full mockup activation and not complete for the full long-term goal.

## Requirement Audit

| Requirement | Current-main evidence | Result |
| --- | --- | --- |
| Source-directory scan/status through material preview and Gate B | Focused rendered E2E `Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path`; `backend/tests/test_layer3_source_directory_vector_retrieval.py` | Live and operator-testable |
| Retrieval/context, qualitative analysis, package lifecycle, review, handoff/export | Same focused rendered E2E plus source-directory backend tests | Live in the bounded source-directory path |
| Package replacement/supersession | PR `#1562`, doc `937`, doc `938`, focused rendered E2E package supersession preview/replacement/commit assertions | Live in the bounded source-directory path |
| Same-origin delivery/status and internal webhook dispatch/status | Focused rendered E2E asserts same-origin delivery/status and internal webhook dispatch/status routes and rejects connector/provider/package-mutation paths | Live in the bounded source-directory path |
| Provider-public redacted delivery/use | Rendered E2E `Layer 3 workbench drives raw mixed rendered provider-private signed URL prepare status revoke and provider-public URL prepare status use revoke`; service `layer3_provider_public_url_delivery_use.py` returns redacted use decision with raw URL, network, byte streaming, connector dispatch, package mutation, source expansion, RAG/vector, and frontend durable authority disabled | Live for the admitted raw-mixed/provider-public rail |
| Source-directory provider-redacted delivery/use | `layer3_readiness_contract.py` classifies source-directory external export/download prepare/deliver/status as disabling provider URLs and signed URLs; source-directory focused E2E explicitly asserts no requests to provider-private or provider-public routes | Explicitly blocked for the source-directory path |
| Analysis Environment/status projection visibility | `layer3_analysis_environment_projection.py`; `backend/tests/test_layer3_analysis_environment_projection.py`; rendered page static proof; focused source-directory E2E asserts `analysis_environment_projection.v1`, `no_side_effects`, `export_ready`, and read-only rendered projection state | Read-only live projection |
| Critical mockup query/source setup journey | `#mockup-query-source-setup-projection`, page static proof, and headed/headless mockup E2E | Read-only live-state projection |
| Critical mockup PDF-location journey | `#mockup-pdf-location-projection` and headed/headless mockup E2E | Read-only server-state projection |
| Critical mockup Sublayers 3A/3B journey | `#mockup-sublayers-ab-projection`, page static proof, and headed/headless mockup E2E | Read-only live-state projection |
| Critical mockup Sublayer 3C execution-lanes journey | `#mockup-execution-lanes-projection`, page static proof, and headed/headless mockup E2E | Read-only live-state projection |
| Critical mockup output review/package/handoff journey | `#mockup-output-review-package-handoff-projection`, page static proof, and headed/headless mockup E2E | Read-only live-state projection |
| Full mockup activation and frontend-only durable authority | `test_layer3_mockup_boundary.py`, `test_layer3_preflight_request_contract.py`, rendered page static proof, and preflight API rejection of `full_mockup_activation` sentinels | Explicitly blocked |

## Validation Run

Validation run in this audit lane:

- `python -m pytest ./backend/tests/test_layer3_analysis_environment_projection.py ./backend/tests/test_layer3_mockup_boundary.py ./backend/tests/test_layer3_preflight_request_contract.py -q`: `7 passed`.
- `python -m pytest ./backend/tests/test_layer3_page.py -q`: `16 passed`.
- `python -m pytest ./backend/tests/test_layer3_source_directory_vector_retrieval.py -q`: `23 passed`.
- Headless Chromium focused source-directory path: `1 passed`.
- Headed Chromium focused source-directory path: `1 passed`.
- Headless Chromium provider-private/provider-public redacted-use path: `1 passed`.
- Headed Chromium provider-private/provider-public redacted-use path: `1 passed`.
- Headless Chromium mockup projection group: `8 passed`.
- Headed Chromium mockup projection group: `8 passed`.

## Readiness Decision

The bounded current-main source-directory path is trial-usable and operator-testable through:

1. source-directory scan/status;
2. material preview;
3. Gate B admission;
4. hybrid authority prepare;
5. retrieval/context;
6. qualitative analysis/status;
7. package commit and package review submit;
8. package supersession preview, replacement package-set authority, and package supersession commit;
9. handoff/export prepare;
10. external export/download prepare;
11. same-origin delivery/status;
12. internal webhook dispatch/status;
13. read-only Analysis Environment and mockup live-state projection.

The whole long-term goal is not yet complete because the objective names admitted redacted delivery/use inside the source-directory operator path, while current-main evidence proves provider-public redacted use only on the admitted raw-mixed/provider-public rail. Source-directory provider-private/provider-public delivery remains explicitly blocked by current source-directory readiness contracts and by the source-directory focused E2E negative route assertions.

This is not a runtime defect in the landed source-directory path. It is a product/authority blocker: either current-main authority must explicitly accept same-origin delivery as the selected source-directory delivery/use rail, or a separate source-directory provider-private/provider-public redacted-use bridge must be frozen and implemented.

## Non-Admission Boundary

This audit introduces no runtime behavior, rendered behavior, backend behavior, route/API/DTO/model/migration/service behavior, executable test behavior, production UI behavior, provider URL behavior, connector dispatch, source expansion, package mutation, browser-storage authority, frontend-only durable authority, auth/security expansion, or full mockup activation.

Full mockup activation remains `false`.

Frontend-only durable authority remains `false`.

## Next Posture

Next exact posture: `decide_source_directory_redacted_delivery_use_bridge_or_accept_same_origin_delivery_rail_before_full_mockup_activation`.
