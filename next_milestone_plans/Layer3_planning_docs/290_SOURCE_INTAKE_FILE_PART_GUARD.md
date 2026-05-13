# Source Intake File Part Guard

Status: branch-local implementation and proof for `source_intake_file_part_guard`.

Branch: `codex/l3-source-intake-file-guard`

## Scope

This pass hardens the existing `operator_single_upload_source_intake` runtime without admitting a new source family, route, rendered control, package behavior, connector behavior, RAG/vector behavior, or local path authority.

Canonical source of truth remains `L3SourceIntakeRecord`.

Runtime surface remains `POST /api/v1/layer3/source/intake/upload`.

Owner service remains `backend/app/services/layer3_source_intake.py`.

## Admitted Change

Duplicate multipart `file` parts now fail closed with `source_intake_duplicate_file_field` before file bytes are read or persisted.

The guard is intentionally located in `normalise_source_intake_form_items(...)` because that function receives `request.form().multi_items()` and can inspect the multipart field sequence before dictionary collapse hides ambiguity.

## Contract Guards

- duplicate `file` parts are ambiguous and rejected
- one `file` part remains owned by FastAPI `UploadFile`
- duplicate non-file field rejection remains unchanged
- forbidden-field and unknown-field rejection remains unchanged
- idempotency conflict rejection remains unchanged
- content hash, relative storage ref, inventory, and bounded-preview behavior remain unchanged

## Still Blocked

- generic source upload
- broad file upload
- local directory ingestion
- local path authority
- web connector retrieval
- RAG/vector indexing
- unbounded runtime DB source reads or writes
- package construction from uploaded source
- rendered source controls
- non-text binary preview

## Proof

Targeted tests:

```powershell
python -m pytest .\backend\tests\test_layer3_source_intake.py .\backend\tests\test_layer3_source_boundary.py -q
```

Progress checker:

```powershell
python .\tools\l3-progress-check.py
```
