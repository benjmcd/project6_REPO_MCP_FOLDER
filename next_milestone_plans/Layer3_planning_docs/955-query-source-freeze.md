# Layer 3 Query Source Setup Activation Entry Freeze

Status: no-runtime single-journey activation-entry freeze for `query_source_setup_existing_controls_activation_entry_freeze`.

Freeze doc: `955-query-source-freeze.md`.

Predecessor selection doc: `954-post-final-readiness-next-phase-selection-freeze.md`.

Current-main checkpoint before freeze: `8d56880f Freeze Layer 3 post-readiness next phase`.

Freeze branch: `codex/l3-single-journey-freeze`.

Selected journey: `query_source_setup`.

Selected journey classification: `interactive_live`.

Selected activation slice: `query_source_setup_interactive_live_classification`.

Rendered projection surface: `#mockup-query-source-setup-projection`.

Full mockup program activation selected now: `false`.

Frontend-only durable authority selected now: `false`.

Runtime behavior introduced by this freeze: `false`.

Rendered behavior introduced by this freeze: `false`.

Backend behavior introduced by this freeze: `false`.

Route/API/DTO/model/migration/service behavior introduced by this freeze: `false`.

Executable test behavior introduced by this freeze: `false`.

Implementation-entry allowed by this freeze alone: `false`.

## Current-Main Basis

Current main classifies `query_source_setup` through `backend/app/services/layer3_mockup_activation_readiness.py::build_mockup_activation_readiness` as `interactive_live`.

The selected journey is the best first activation-entry freeze because it is already the first admitted readiness slice, starts the operator path, and has a narrower authority surface than the output review/package/handoff cluster.

The freeze preserves the existing distinction:

- existing query/source setup controls are live only through server-owned APIs;
- `#mockup-query-source-setup-projection` remains a read-only projection of current state;
- full mockup activation remains blocked;
- browser storage and frontend-only durable state remain non-authoritative.

## Route/API Authority Boundary

Admitted existing server-owned route/API authority for this journey is limited to:

- `GET /api/v1/layer3/bootstrap`;
- `POST /api/v1/layer3/preflight`;
- `POST /api/v1/layer3/source-preview`;
- `POST /api/v1/layer3/material-preview`;
- `POST /api/v1/layer3/source/intake/upload`;
- `GET /api/v1/layer3/source/intake/inventory`;
- `GET /api/v1/layer3/source/intake/{source_intake_record_id}/preview`;
- `POST /api/v1/layer3/source/ingestion/server-configured-directory/scan`;
- `GET /api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}`;
- `POST /api/v1/layer3/source/ingestion/server-configured-directory/material-preview`;
- `POST /api/v1/layer3/gate-b/decision`;
- `GET /api/v1/layer3/session/{session_id}`.

Those routes are authority only for the already admitted controls and state readers. They do not become broad full-mockup program authority.

The rendered mockup projection must not call these routes directly. It remains a read-only reader of existing state from:

- `State.preflight`;
- `State.sourcePreview`;
- `State.materialPreview`;
- source-intake rendered control state;
- source-directory rendered control state;
- `State.sessionSummary`;
- `State.bootstrap.mockup_activation_readiness`.

## Rollback/Disable Behavior

Rollback is the current bounded readiness posture:

- `full_mockup_activation_enabled: false`;
- `frontend_only_durable_authority_enabled: false`;
- `raw_provider_exposure_enabled: false`;
- `connector_provider_write_enabled: false`;
- `broad_source_model_rag_expansion_enabled: false`;
- `#mockup-query-source-setup-projection` remains read-only and can return to unavailable projection state;
- existing source/query controls remain backed only by the server-owned route/API contracts above;
- no browser-local state becomes durable authority.

Any later implementation must be reversible to this state without deleting or mutating authoritative records.

## Proof Matrix

Before any later implementation claims more than this freeze, proof must include:

| Requirement | Required evidence |
| --- | --- |
| Current-main journey classification | `query_source_setup` is `interactive_live` in `mockup_activation_readiness` |
| Read-only mockup projection | `#mockup-query-source-setup-projection` issues no `postJson`, `getJson`, `fetch`, upload, Gate B, package, handoff, connector, provider, storage, or file-byte behavior |
| Server-owned route/API controls | Existing query/source setup controls use only the admitted route/API authority listed in this doc |
| Rollback/disable | Bootstrap/readiness keeps full mockup activation and frontend-only durable authority false |
| Negative provider/security invariant | No raw provider URL, token, path, object ref, credential, signed URL, public URL, local file path, file bytes, or browser file becomes visible or durable |
| Browser proof | Headed and headless Chromium agree for the selected journey before any interactive expansion |
| Progress guard | `python ./tools/l3-progress-check.py` passes after manifests and this freeze are updated |

## No-Go Boundaries

This freeze does not admit:

- full mockup program activation;
- new interactive controls inside `#mockup-query-source-setup-projection`;
- route/API/DTO/model/migration/service widening;
- source adapter/source family expansion;
- raw provider URL, token, object, path, credential, signed URL, public URL, local file path, file bytes, or browser file exposure;
- connector/provider writes;
- package lifecycle, handoff/export, delivery/use, internal webhook, replacement, or supersession expansion;
- RAG/vector/model-provider expansion;
- auth/security behavior changes;
- frontend-only durable authority;
- browser storage as authority;
- hidden LLM planning or execution side effects.

## Stop Conditions

Stop before implementation if:

- current main no longer classifies `query_source_setup` as `interactive_live`;
- product authority requires full mockup activation instead of one journey and no full activation freeze exists;
- rollback cannot return to the current bounded readiness posture;
- the projection would need to call server routes directly instead of reading existing state;
- any read-only mockup projection would gain controls without a named server-owned route/API contract;
- browser storage or frontend-only durable state would become authoritative;
- raw provider/path/token/object/credential/public URL/signed URL/local path/file-byte exposure is required;
- headed and headless browser proof diverges;
- `python ./tools/l3-progress-check.py` cannot prove the freeze terms.

## Next Posture

Next exact posture: `current_main_sync_query_source_setup_activation_entry_freeze_then_select_next_single_journey`.

After this freeze is current-main synced, the next admitted move is to choose the next single journey from current-main evidence. Full mockup activation remains blocked unless explicit product authority and current-main evidence admit a later governed full-activation freeze.
