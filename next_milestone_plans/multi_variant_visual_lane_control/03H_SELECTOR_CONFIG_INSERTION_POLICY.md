# 03H Selector Config Insertion Policy

## Verified live evidence

### Evidence 1 — local document-processing config
`default_processing_config(...)` exists in `nrc_aps_document_processing.py`.

### Evidence 2 — run-config adapter
`backend/app/services/nrc_aps_artifact_ingestion.py` has:
- `processing_config_from_run_config(...)`
- forwards processing overrides into `default_processing_config(...)`
- then passes the result into `process_document(...)`

### Evidence 3 — request-config normalization tests
`backend/tests/test_nrc_aps_run_config.py` verifies that connector request-config normalization preserves processing overrides.

## Current policy

A future selector control should be introduced as part of the existing processing-override control plane rather than through an unrelated channel.

## Recommended insertion order

### First
Represent selector choice as a processing-level override that can be carried into `default_processing_config(...)`.

### Second
Where request-level orchestration is involved, align with the repo’s existing request-config normalization pattern rather than bypassing it.

## Important restraint

A second-opinion critique suggested using a concrete `variant` field immediately.
This pack does **not** adopt that as frozen implementation truth yet.
It is only a candidate control surface until explicitly frozen.

## Prior unresolved item (now closed)

The exact selector key name and normalization behavior was previously unresolved. It is now frozen as `visual_lane_mode` (see "Canonical key" section below and `03U`).


## Additional live nuance: control-key leakage risk

The live `_normalize_request_config(...)` implementation in `connectors_nrc_adams.py` explicitly separates control keys from query payload in lenient pass-through mode.

That means a future selector field must be designed not only for config propagation, but also for **query-payload exclusion**.

Use `03P_SELECTOR_CONTROL_KEY_AND_QUERY_PAYLOAD_LEAKAGE_POLICY.md` together with this document when freezing the selector key.


## Canonical key after this revision

Use `visual_lane_mode` as the canonical selector-processing control concept.

It should:
- be normalized like other enum-like controls,
- be treated as a processing control,
- be forwarded explicitly by `processing_config_from_run_config(...)`,
- default and fail closed to `baseline`.
