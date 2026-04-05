# 03U Canonical Selector Config Key and Fail-Closed Policy

## Purpose

Freeze the selector-control concept so implementation does not invent an ad hoc key or an unsafe invalid-value behavior.

## Live evidence used

### Request-config normalization style
`connectors_nrc_adams._normalize_request_config(...)`:
- normalizes enum-like controls such as:
  - `mode`
  - `wire_shape_mode`
  - `run_mode`
  - `report_verbosity`
  - `sync_mode`
- invalid values fall back to safe defaults rather than throwing

### Processing-config forwarding style
`nrc_aps_artifact_ingestion.processing_config_from_run_config(...)`:
- forwards only an explicit whitelist of processing controls into `default_processing_config(...)`

### Processing-config shape
`nrc_aps_document_processing.default_processing_config(...)`:
- defines the processing-config defaults
- does not itself validate enum-like controls

## Canonical selector control

### Canonical key
`visual_lane_mode`

## Why this key

It matches the live processing-control naming style:

- snake_case
- domain-specific like:
  - `content_parse_max_pages`
  - `ocr_enabled`
  - `visual_render_dpi`

It is also scoped correctly:
- narrower than a generic `variant`
- aligned with the current first-pass target: the visual lane
- does not overclaim whole-pipeline or whole-project variant semantics

## Canonical default
`baseline`

## Canonical invalid/unapproved behavior
Fail closed to `baseline`.

## Meaning of fail closed

If the incoming value is:
- absent
- invalid
- unapproved for the current integrated phase
- or not explicitly allowed by the current selector registry/policy

then normalized selector behavior must become:

`visual_lane_mode = "baseline"`

with internal warning/lint/telemetry as appropriate.

## Why fail-closed is the right policy

The live repo already uses safe-default fallback for several enum-like controls.
For the first integrated phase, baseline is the only allowed normal-runtime behavior.
So fail-closed-to-baseline is the repo-aligned and safety-aligned behavior.

## Required insertion points once coding begins

1. `_normalize_request_config(...)`
   - preserve `visual_lane_mode`
   - treat it as a control key
   - exclude it from query payload construction

2. `processing_config_from_run_config(...)`
   - explicitly forward `visual_lane_mode`

3. `default_processing_config(...)`
   - define default `visual_lane_mode = "baseline"`

4. selector/seam entry point
   - consume normalized `visual_lane_mode`
   - treat non-baseline values according to current integrated-phase policy

## Current first-phase allowed-value interpretation

For the first integrated baseline-only phase:

- effective allowed runtime value: `baseline`

Non-baseline values may exist conceptually for future reopening or isolated experiments, but must not become active in normal integrated runtime during the first phase.

## Important restraint

This document freezes the canonical key and fail-closed policy conceptually.
It does **not** claim that non-baseline integrated runtime activation is now allowed.


## Insertion/consumption closure after this revision

The code-level path for `visual_lane_mode` is now fixed conceptually:

- normalize in `_normalize_request_config(...)`
- forward in `processing_config_from_run_config(...)`
- default in `default_processing_config(...)`
- first consume in `_process_pdf(...)` at the visual-preservation lane

See `03V_SELECTOR_KEY_INSERTION_AND_CONSUMPTION_MAP.md`.
