# 03P Selector Control-Key and Query-Payload Leakage Policy

## Verified live evidence

`backend/app/services/connectors_nrc_adams._normalize_request_config(...)` has an explicit `control_keys` set used in `lenient_pass_through` mode.

That set currently excludes known processing controls such as:
- `content_sniff_bytes`
- `content_parse_max_pages`
- `content_parse_timeout_seconds`
- `ocr_enabled`
- `ocr_max_pages`
- `ocr_render_dpi`
- `ocr_language`
- `ocr_timeout_seconds`
- `content_min_searchable_chars`
- `content_min_searchable_tokens`
- content chunk controls
- report/safeguard/client-request controls

And `backend/tests/test_nrc_aps_run_config.py` verifies that processing controls are preserved in normalized config but excluded from `query_payload_inbound` in lenient pass-through mode.

## Why this matters

A future selector field is not safe merely because it is present in normalized config.

It must also be classified correctly as:
- a processing control,
- not a query payload field,
- not an outbound query leak in lenient pass-through mode.

## Current policy

Any future selector control must satisfy **both**:

1. it is preserved through the run-config → processing-config path, and
2. it is excluded from `query_payload_inbound` and any equivalent outbound query surface where processing controls do not belong.

## Required freeze questions

Before implementation, explicitly freeze:

1. the exact selector key name,
2. whether that key belongs in normalized config,
3. whether it must be added to the `control_keys` exclusion set,
4. whether any parallel connector/request mappers must also exclude it from query payload construction.

## First-pass rule

Do not introduce a selector key that can accidentally leak into query payloads for lenient pass-through operation.


## Canonical key after this revision

The canonical selector control key is:
- `visual_lane_mode`

So the required exclusion rule is now explicit:
- `visual_lane_mode` must be treated as a control key
- and must not leak into `query_payload_inbound` / lenient pass-through query payload construction.
