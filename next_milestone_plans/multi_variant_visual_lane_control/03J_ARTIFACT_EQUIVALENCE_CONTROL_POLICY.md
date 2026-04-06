# 03J Artifact Equivalence Control Policy

## Verified live evidence

`backend/tests/test_visual_artifact_pipeline.py` verifies a concrete artifact validation surface including:

- artifact file existence
- artifact file SHA-256 computation
- artifact metadata:
  - ref
  - SHA-256
  - DPI
  - format
  - semantics
- content-index roundtrip behavior

Current harness note:
- the live file now exposes pytest-collected artifact/persistence assertions while still retaining a script-style `main()` entrypoint for manual probe usage
- grouped canonical acceptance behavior for this surface is operational and tracked in `06C`, `06D`, and `06E`

## Minimum baseline-equivalence controls

For the baseline integrated path, selector bootstrap must preserve:

1. artifact file existence behavior
2. artifact ref stability semantics
3. file SHA-256 agreement where baseline behavior is expected to remain identical
4. `visual_artifact_dpi`
5. `visual_artifact_format`
6. `visual_artifact_semantics`
7. content-index roundtrip persistence/visibility of artifact metadata

## Current policy

### Baseline-only integrated pass
Treat all artifact behavior as baseline-locked.

### Experimental isolated runs
May produce separate outputs out-of-band, but those outputs must not be treated as baseline-equivalent or routed through baseline review/runtime discovery by default.

## Important restraint

A second-opinion critique suggested adding artifact variant tags.
This pack does **not** adopt public or persisted variant tagging as frozen truth in the first integrated pass, because that risks contract drift.
