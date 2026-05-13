# Source Intake Inventory Read-only Freeze

Status: branch-local implementation entry for `source_intake_inventory_read_only`.

implementation_branch: `codex/l3-source-intake-hardening`
live_behavior_change: true
runtime_family: `source_breadth_runtime`
selected_runtime_mode: `operator_source_intake_inventory_read_only`
runtime_route: `GET /api/v1/layer3/source/intake/inventory`
canonical_source_of_truth: `L3SourceIntakeRecord`
writer_route: `POST /api/v1/layer3/source/intake/upload`

## Admitted use case

Expose a server-authoritative, read-only inventory over already persisted source-intake rows.

The endpoint may list safe metadata for `operator_uploaded_single_source` records that were created by the existing source-intake upload route. It must not read or return file bytes, expose absolute filesystem paths, enable operator-uploaded material preview, seed RAG/vector state, invoke web connectors, or broaden generic source upload semantics.

## Current authority chain

1. The upload route remains the only admitted writer for operator-uploaded single-source intake.
2. `L3SourceIntakeRecord` is the canonical runtime source of truth for source identity, hashes, provenance, freshness, storage pointer, status, and downstream eligibility.
3. The inventory route reads persisted rows and returns bounded metadata only.
4. The inventory route keeps `eligible_for_source_inventory: true` while keeping material preview, RAG/vector, connector, local path, broad upload, package, and unbounded runtime DB surfaces blocked.

## Response boundaries

The inventory response must include:

- `schema_id: layer3.source_intake_inventory.v1`
- `mode: operator_source_intake_inventory_read_only`
- `source_gate.canonical_source_of_truth: L3SourceIntakeRecord`
- `source_gate.writer_route: POST /api/v1/layer3/source/intake/upload`
- `source_gate.read_route: GET /api/v1/layer3/source/intake/inventory`
- `source_gate.no_file_bytes_returned: true`
- `source_gate.absolute_path_exposed: false`
- `source_gate.material_preview_enabled: false`
- per-record `storage_pointer.absolute_path_exposed: false`
- `downstream_eligibility.eligible_for_source_inventory: true`
- `downstream_eligibility.eligible_for_material_preview: false`
- `negative_invariants.web_connector_enabled: false`
- `negative_invariants.rag_vector_index_enabled: false`
- `negative_invariants.runtime_db_write_enabled: false`

## Rejected inputs

The inventory route must reject:

- any `source_family` other than `operator_uploaded_single_source`
- any `status` other than `recorded`
- any `limit` outside 1 through 100

## Explicit no-go surfaces

These remain deferred and require a later named freeze before implementation:

- operator-uploaded material preview
- RAG or vector indexing over uploaded source bytes
- generic `/sources/upload`
- local path or local directory source authority
- web connector source expansion
- package materialization from uploaded operator source
- UI browsing or preview controls for operator-uploaded material
- unbounded runtime database writes

## Verification expectation

Targeted verification for this freeze is:

- `python ./tools/l3-progress-check.py`
- `python -m pytest ./backend/tests/test_layer3_source_intake.py ./backend/tests/test_layer3_source_boundary.py -q`

This freeze is complete only when the endpoint, tests, progress board, manifest, proof manifest, and checker all agree that the route is read-only inventory and not a downstream materialization surface.
