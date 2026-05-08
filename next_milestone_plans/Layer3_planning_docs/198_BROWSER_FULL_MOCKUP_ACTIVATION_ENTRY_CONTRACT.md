# Browser Full Mockup Activation Entry Contract

Status: planning/control contract paired with `197_BROWSER_FULL_MOCKUP_ACTIVATION_ENTRY_FREEZE.md`.

This contract defines requirements for moving beyond the deferred `browser_full_mockup_activation_freeze` decision. It admits no full mockup activation, frontend-only durable state, browser-local persistence as authority, rendered UI control change, route, DTO, service behavior, model, migration, test behavior, source expansion, package mutation, provider/public URL runtime, connector/destination dispatch, broad qualitative/hybrid/RAG behavior, hidden LLM planning, full target-state mockup activation, or auth/security behavior change.

Doc `125` remains authority for mockups as target-state-only design/specification inputs. Existing rendered proof docs remain authority only for the server-authoritative controls they prove. Docs `184` through `196` remain the broader downstream/source/qualitative governance chain. This contract is the narrower post-PR #753 entry-decision layer for any full mockup or browser-state expansion.

## Authority Order

1. live `project6-origin/main` source, tests, models, migrations, routes, service code, static UI files, Playwright tests, and checker behavior;
2. `backend/app/services/layer3_mockup_boundary.py` and `backend/tests/test_layer3_mockup_boundary.py`;
3. rendered workbench static files and Playwright proofs for currently admitted server-backed controls;
4. `next_milestone_plans/layer3-mockups/assets.md` and `next_milestone_plans/layer3-mockups/mockup-spec.txt` as target-state inputs only;
5. `125_MOCKUP_TRUTH_STATE_FREEZE.md`;
6. rendered proof docs `151`/`152` and `155` through `183`;
7. downstream/source/qualitative entry docs `184` through `196`;
8. this contract and `197_BROWSER_FULL_MOCKUP_ACTIVATION_ENTRY_FREEZE.md`.

Planning prose, browser state, local storage, screenshots, mockup art, mockup text, copied URLs, manually clicked flows, and prior PR titles are not sufficient authority for runtime implementation.

## Entry Decision Contract

```yaml
entry_decision: deferred
selected_mode: null
runtime_status: not_implemented
live_mockup_truth_state: mockups_target_state_only
live_rendered_workbench_status: existing_server_authoritative_controls_only
live_browser_proof_status: bounded_headed_headless_proofs_for_admitted_paths
receipt_family: no_receipt_planning_only
```

The decision may change only in a later freeze if all of these are repo-confirmed: selected activation mode, source owner, route/API contract, server authority contract, durable state owner, browser storage policy, operator journey scope, theme/accessibility proof, headed/headless proof, negative invariant proof, no-cross-mode privilege escalation proof, and leakage policy.

## Allowed Future Modes

A later runtime freeze must choose exactly one of:

- `single_existing_rendered_control_extension`;
- `single_mockup_screen_read_only_projection`;
- `single_mockup_screen_server_authoritative_activation`;
- `full_mockup_program_activation`;
- `mockup_to_live_mapping_inventory_only`.

The selected mode must not rename frontend-only durable state, browser-local persistence, target-state mockup text, screenshots, or manually clicked browser state as server-authoritative runtime behavior.

## Request Contract For Later Runtime

A future request must be server-authority based. It may include or derive server-side selected mode, session/state refs, route/API refs, mockup source refs, deterministic hashes, idempotency key, and operator confirmation only if the future freeze admits those fields.

The request must not accept browser-local workflow state, local storage dumps, arbitrary local paths, screenshots as authority, mockup text as authority, external URLs to fetch, provider URLs, connector credentials, destination URLs, package mutation fields, prompt/model fields, auth/security overrides, or full program activation flags unless a later freeze explicitly admits one narrow server-authoritative mode.

## Response Contract For Later Runtime

A future response may expose only response-safe metadata admitted by the later freeze: selected mode, server state refs, route/API refs, mockup source refs, deterministic hashes, idempotency status, failure code, response-safe failure reason, and next actions.

The response must not expose local filesystem paths, browser storage secrets, credentials, bearer tokens, provider URLs, connector targets, destination targets, prompt text, model/provider internals, package payload bodies, auth internals, or frontend-only durable state as authority.

## Existing Runtime Compatibility Contract

This entry freeze must preserve existing browser/UI behavior:

- mockup files remain target-state design/specification inputs only;
- existing `/review/layer3` rendered controls remain bounded to current server-authoritative route/API behavior;
- existing headed/headless proofs remain proof for their admitted paths only;
- no browser or mockup surface may become durable authority for source selection, execution, package, handoff, export, provider/public URL, connector/destination, RAG/vector, hidden LLM, mockup, or auth/security behavior.

## Browser And Theme Contract

This entry freeze adds no rendered UI control. If a later freeze admits mockup or browser activation, it must preserve `light`, `dark`, and `workbench` theme behavior, prove headed and headless Chromium consistency, prove responsive layout and text containment, prove disabled and focus states, expose no local path/credential/provider/connector/destination/prompt authority in the browser, and avoid browser-state-only durable workflow truth.

## Test Contract For Later Runtime

Runtime or rendered implementation remains blocked until a later freeze names tests for disabled-by-default behavior, exact server authority binding, forbidden browser-local/mockup/source/package/connector/provider/RAG/prompt/auth fields, storage confinement, idempotency and concurrency, no unintended DB/file/package/provider/connector/destination side effects, no frontend-only durable authority, no path/credential/token/browser-storage leakage, headed/headless proof, and theme/accessibility coverage if UI changes are admitted.

## Checker Contract

`tools/l3-progress-check.py` should verify structural guardrails only: docs `197` and `198` exist and are referenced; entry decision is `deferred`; selected mode is null; runtime status is `not_implemented`; mockups remain target-state-only; existing rendered controls are acknowledged without being generalized; evidence ledger exists and unverified source owner, route/API contract, server authority, mockup-to-live mapping, operator journey, theme/accessibility proof, and frontend durable authority force deferral; exposure model exists and unknown values force deferral; capability isolation matrix exists and all new runtime flags remain false; negative invariants are present; docs do not claim full mockup activation is live; docs do not conflate existing rendered route/API proofs with full mockup activation or frontend-only durable authority.

The checker must not pretend to validate actual browser usability, full mockup operator completeness, visual design quality, accessibility conformance, theme fidelity, source-family semantics, auth/security posture, or route/API correctness in this planning-only pass.

## Stop Conditions

Stop and return to planning if a future implementation proposal tries to activate more than one browser/mockup mode, use mockup text/screenshots/browser state as durable authority, add rendered controls without headed/headless and theme proof, accept arbitrary local/browser storage input, mutate server state from browser-only authority, generate provider/public URLs, dispatch connectors/destinations, mutate packages, activate hidden LLM behavior, or alter auth/security behavior without a later freeze that explicitly admits that scope.
