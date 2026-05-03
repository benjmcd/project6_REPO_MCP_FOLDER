# Phase P10A Closeout: APS-Derived Dataset UI Selection

Status: implemented on 2026-05-03.

## Scope

Phase P10A adds bounded Layer 3 workbench operator surfacing for APS-derived CSV bridge `DatasetVersion` records. It does not add new parser families, schema changes, migrations, Layer 3 typing-rule changes, document-trace changes, or mixed-source package semantics.

## Implemented Boundary

- `backend/app/services/layer3_workbench.py` exposes read-only APS-derived dataset-version candidates from existing `DatasetSourceProvenance` authority.
- `backend/app/api/layer3.py` adds `GET /api/v1/layer3/dataset-version-candidates` for that read-only candidate projection.
- `backend/app/review_ui/static/layer3.html`, `layer3.css`, and `layer3.js` add workbench controls for listed candidates and explicit pasted IDs.
- The workbench sends selected IDs to material preview as `dataset_version_ids`, preserving server-side material preview as the source-selection authority.
- The UI blocks entered dataset-version IDs when the `dataset_version` source class is not selected, avoiding silent client-side source-class widening.

## Validation

- `python -m pytest .\backend\tests\test_layer3_page.py .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_api.py -k "aps_dataset_version_candidates or dataset_version_candidates or first_slice_preview_openapi_contracts or layer3_page_route_serves_workbench_shell or layer3_static_assets_are_mounted"`: `5 passed, 84 deselected`.
- `python -m pytest .\backend\tests\test_layer3_page.py .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_api.py`: `89 passed`.
- `npm run test:e2e:chromium -- e2e/layer3-workbench.spec.js`: `8 passed`.
- `npm run test:e2e:headed -- e2e/layer3-workbench.spec.js`: `8 passed`.

## Caveats

- Pytest emitted the known Windows temp cleanup `PermissionError` after green results; process exit status was successful.
- The first Playwright command used a Windows backslash path and found no tests. Port cleanup was verified before rerunning with a forward-slash path.
- Candidate discovery is intentionally limited to APS-derived dataset versions with `DatasetSourceProvenance.source_system="nrc_adams_aps"`.
- Broader typed/refused/mixed source-family UI surfacing remains deferred until those families have server-backed parser/source authority.

## Next

The next implementation slice should not repeat APS-derived CSV dataset selection. Proceed with the next typed parser family or a broader Phase P10 UI expansion only when the target source family has a server-authoritative contract and fail-closed tests.
