# 03E Variant Identity Visibility Policy

## Rule

Variant identity is internal-only in the first integrated pass.

## Allowed initially
- telemetry
- diagnostics
- bakeoff outputs
- comparison artifacts
- experiment manifests

## Forbidden initially
- public API fields
- report/export payloads
- review payload contracts
- artifact refs/paths/hashes
- default user-facing outputs
- persisted public-facing result surfaces
- default review/runtime discovery payloads
