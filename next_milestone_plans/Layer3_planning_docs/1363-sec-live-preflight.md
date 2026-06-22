# 1363 SEC Live Source Smoke Preflight

Target: `sec_live_source_artifact_manual_smoke_preflight_v1`.

Status: validate-only preflight.

## Purpose

This pass adds a validate-only readiness preflight for the already-selected
manual live SEC source-artifact smoke from
`1362-sec-live-source-manual-smoke-freeze.md`.

Runtime behavior introduced by this preflight: `false`.
Real SEC network request performed by this preflight: `false`.
Source artifact or receipt created by this preflight: `false`.

The preflight exists because the first operator-smoke attempt was blocked before
network access by missing operator SEC configuration. It makes that blocker
machine-checkable without weakening the selected sequence or pretending that a
live smoke succeeded.

## Preflight Surface

The preflight script is:

`diagnostics/assessment/sec-live-preflight.py`.

It inspects only local environment/configuration and current source files. It
does not import runtime settings in a way that can seed storage, does not call
the SEC client, does not create source artifacts, and does not read retained
filing bytes.

The preflight is ready only when all of these are true:

- `LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED=true`
- `LAYER3_SEC_EDGAR_USER_AGENT` is present and reported only by marker/length.
- CI runtime is not active.
- `STORAGE_EXPOSURE=disabled`.
- `STORAGE_DIR` is normalized like runtime settings, exists outside the repo
  and outside OneDrive, and passes a non-mutating writability check.
- `DATABASE_URL` is explicitly safe for this live SEC run, such as
  `sqlite:///:memory:` or an admitted external PostgreSQL URL; relative SQLite
  paths are normalized under `backend/`, repo/OneDrive SQLite paths are
  blocked, and malformed non-SQLite values are blocked.
- Rate/max-request/max-byte/timeout controls are within the admitted bounded
  range.
- One operator-approved smoke request identity is configured through
  `LAYER3_SEC_EDGAR_SMOKE_CIK`,
  `LAYER3_SEC_EDGAR_SMOKE_ACCESSION`,
  `LAYER3_SEC_EDGAR_SMOKE_FORM_TYPE`,
  `LAYER3_SEC_EDGAR_SMOKE_FILING_DATE`, and
  `LAYER3_SEC_EDGAR_SMOKE_OPERATOR_CONFIRMATION=true`.
- The configured smoke identity has no matching retained live-source receipt in
  the isolated storage root, so the next live smoke cannot pass as a cache-only
  replay.

The report returns only markers and bounded metadata for the User-Agent,
storage/database paths, and CIK/accession identity. It does not return raw SEC
URL, raw local path, raw User-Agent value, raw CIK/accession, or artifact bytes.

## Negative Invariants

No SEC network fetch, source-artifact creation, receipt creation, status
re-read, Arelle invocation, multi-filing enforcement, delivery/export/status,
provider delivery, nonlocal auth hardening, value reveal, default-on graduation,
config default change, support-matrix change, model/migration, redaction-posture
change, or production-readiness claim is admitted.

## Tier And Review

This is Tier-1 because it adds only a validate-only diagnostic and tests. It
does not change runtime route behavior, persistence, schema, defaults,
capability status, or redaction posture.

The real one-filing smoke remains Tier-2-adjacent because it will record
real-network evidence for a live egress surface. That next pass must still use
redacted/hash-only evidence and stop before Arelle/fact authority, multi-filing
authority, delivery/export/status, nonlocal auth hardening, or value-reveal
default-on graduation.

## Next Posture

Next posture:
`run_one_filing_live_source_artifact_smoke_with_redacted_hash_only_evidence`.
