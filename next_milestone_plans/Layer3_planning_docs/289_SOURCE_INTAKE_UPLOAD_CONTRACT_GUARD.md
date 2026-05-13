# Source Intake Upload Contract Guard

Status: branch-local hardening entry for `source_intake_upload_contract_guard`.

implementation_branch: `codex/l3-source-intake-upload-guard`
live_behavior_change: true
runtime_family: `source_breadth_runtime`
selected_runtime_mode: `operator_single_upload_source_intake`
runtime_route: `POST /api/v1/layer3/source/intake/upload`
canonical_source_of_truth: `L3SourceIntakeRecord`

## Admitted hardening

Reject duplicate non-file multipart form fields before source-intake upload persistence.

The upload route previously received `form.multi_items()` and collapsed the non-file fields into a dictionary. That was functional for normal clients, but it allowed duplicate form keys to become last-write-wins ambiguity before the service contract was evaluated. This guard keeps the existing upload contract and changes only ambiguous duplicate-field handling to fail closed.

## Required behavior

- `normalise_source_intake_form_items(...)` owns multipart form-field normalization.
- Duplicate non-file form fields return `source_intake_duplicate_field`.
- `file` remains handled by FastAPI's `UploadFile` parameter and is not treated as a normal form field.
- Existing forbidden-field, unknown-field, idempotency, hash, storage-ref, inventory, and bounded-preview behavior remains unchanged.

## Explicit no-go surfaces

This hardening admits no:

- Generic source upload
- local path or local directory source authority
- web connector source expansion
- RAG or vector indexing
- package construction
- rendered source controls
- non-text binary preview
- unbounded runtime database behavior

## Verification expectation

Targeted verification for this guard is:

- `python ./tools/l3-progress-check.py`
- `python -m pytest ./backend/tests/test_layer3_source_intake.py ./backend/tests/test_layer3_source_boundary.py -q`

This guard is complete only when the API, service, tests, progress board, manifest, proof manifest, and checker agree that duplicate multipart fields fail closed without changing the admitted source-intake family.
