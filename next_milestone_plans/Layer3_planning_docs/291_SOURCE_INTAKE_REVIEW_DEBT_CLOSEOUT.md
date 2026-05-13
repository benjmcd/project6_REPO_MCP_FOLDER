# Source Intake Review Debt Closeout

Status: branch-local implementation and proof for `source_intake_review_debt_closeout`.

Branch: `codex/l3-source-intake-closeout`

## Scope

This pass settles source-intake review debt discovered on prior merged PRs without admitting a new source family, new route, rendered source controls, connector behavior, package behavior, RAG/vector behavior, local path authority, or unbounded runtime DB behavior.

Canonical source of truth remains `L3SourceIntakeRecord`.

Runtime surfaces remain:

- `POST /api/v1/layer3/source/intake/upload`
- `GET /api/v1/layer3/source/intake/inventory`
- `GET /api/v1/layer3/source/intake/{source_intake_record_id}/preview`

## Review Comments Addressed

PR `#866` review debt:

- Inventory no longer echoes unbounded descriptions. New uploads reject `source_description` longer than 2000 characters, and inventory responses truncate legacy descriptions to 512 characters with `source_description_truncated` metadata.
- Malformed inventory limits such as `limit=abc` now enter the source-intake error contract and return `source_intake_inventory_limit_invalid` with HTTP 400 instead of FastAPI's default 422 validation body.

PR `#867` review debt:

- Parameterized media types were already addressed by PR `#868` through media-type parameter normalization before preview admission.
- Existing source-intake rows with stale persisted material-preview eligibility are normalized at response time so preview-capable recorded rows advertise `eligible_for_material_preview: true` and `material_preview_requires_later_freeze: false`.
- Upload and inventory `next_allowed_actions` no longer tell clients to wait for a later material-preview freeze; they now name bounded preview as available and reserve later-freeze wording for RAG, connector, package, and rendered-control expansion.

## Still Blocked

- Generic source upload
- broad file upload
- local directory ingestion
- local path authority
- web connector retrieval
- RAG/vector indexing
- package construction from uploaded source
- rendered source controls
- non-text binary preview
- unbounded runtime DB source reads or writes

## Proof

Targeted tests:

```powershell
python -m pytest .ackend	ests	est_layer3_source_intake.py .ackend	ests	est_layer3_source_boundary.py -q
```

Progress checker:

```powershell
python .	ools\l3-progress-check.py
```
