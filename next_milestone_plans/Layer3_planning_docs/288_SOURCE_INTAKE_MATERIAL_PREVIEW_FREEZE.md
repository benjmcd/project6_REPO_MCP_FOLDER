# Source Intake Material Preview Freeze

Status: branch-local implementation entry for `source_intake_material_preview_read_only`.

implementation_branch: `codex/l3-source-intake-preview`
live_behavior_change: true
runtime_family: `source_breadth_runtime`
selected_runtime_mode: `operator_source_intake_material_preview_read_only`
runtime_route: `GET /api/v1/layer3/source/intake/{source_intake_record_id}/preview`
canonical_source_of_truth: `L3SourceIntakeRecord`
writer_route: `POST /api/v1/layer3/source/intake/upload`
inventory_route: `GET /api/v1/layer3/source/intake/inventory`

## Admitted use case

Expose a bounded text preview for one already persisted operator-uploaded source-intake record.

The route may read the server-owned content-addressed file identified by `L3SourceIntakeRecord.storage_ref`, verify the file hash against `L3SourceIntakeRecord.content_sha256`, and return a bounded UTF-8 text preview for text-like media types only.

Hardening note: preview must normalize media-type parameters such as `text/plain; charset=utf-8` before admission checks and must stream hash/preview extraction instead of reading the entire source object into memory.

## Current authority chain

1. `POST /api/v1/layer3/source/intake/upload` remains the only admitted writer for operator-uploaded source-intake rows.
2. `L3SourceIntakeRecord` remains the canonical runtime authority for source identity, content hash, metadata hash, provenance, freshness, storage pointer, and status.
3. `GET /api/v1/layer3/source/intake/inventory` remains read-only metadata inventory.
4. `GET /api/v1/layer3/source/intake/{source_intake_record_id}/preview` is the only admitted operator-uploaded material preview surface.

## Response boundaries

The preview response must include:

- `schema_id: layer3.source_intake_material_preview.v1`
- `mode: operator_source_intake_material_preview_read_only`
- `source_gate.canonical_source_of_truth: L3SourceIntakeRecord`
- `source_gate.absolute_path_exposed: false`
- `source_gate.bounded_text_preview: true`
- `source_gate.rag_vector_index_enabled: false`
- `source_gate.web_connector_enabled: false`
- `source_gate.package_construction_enabled: false`
- `material_candidate.preview_text`
- `material_candidate.preview_char_count`
- `material_candidate.preview_truncated`
- `material_candidate.storage_pointer.absolute_path_exposed: false`
- `downstream_eligibility.eligible_for_material_preview: true`
- `downstream_eligibility.eligible_for_rag_vector_index: false`
- `negative_invariants.unbounded_material_preview_enabled_for_operator_upload: false`

## Rejected inputs

The preview route must reject:

- missing or unknown `source_intake_record_id`
- any row that is not `status: recorded`
- any row that is not `source_family: operator_uploaded_single_source`
- any `max_chars` outside 1 through 4000
- storage references outside the server-owned `raw/layer3-source-intake` segment
- missing storage objects
- content hash mismatch
- non-text-like media types

## Explicit no-go surfaces

These remain deferred and require a later named freeze before implementation:

- RAG or vector indexing over uploaded source bytes
- generic `/sources/upload`
- local path or local directory source authority
- web connector source expansion
- package materialization from uploaded operator source
- rendered UI browsing or preview controls for operator-uploaded material
- unbounded runtime database writes
- preview of non-text binary media

## Verification expectation

Targeted verification for this freeze is:

- `python ./tools/l3-progress-check.py`
- `python -m pytest ./backend/tests/test_layer3_source_intake.py ./backend/tests/test_layer3_source_boundary.py -q`

This freeze is complete only when the endpoint, source-boundary contract, tests, progress board, manifest, proof manifest, and checker agree that the route admits bounded text material preview only and does not admit broader source expansion.
