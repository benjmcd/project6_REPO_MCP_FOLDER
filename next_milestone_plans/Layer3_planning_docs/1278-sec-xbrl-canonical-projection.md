# 1278 - SEC XBRL Canonical Projection Artifact

## Target

`sec_xbrl_canonical_projection_artifact_validate_only_v1`

## Purpose

This slice adds the validate-only canonical projection artifact after the canonical comparability diagnostic.

The projection sources each projected value from the governed Arelle sidecar internal value store through `effective_value` and `resolved_fact_id`. CompanyFacts is used only as a period-aware validation oracle. This preserves the authority chain needed for a standardized filing data product instead of making the external aggregation API the value source.

## Scope

Files:

- `backend/app/services/layer3_sec_xbrl_canonical_concepts.py`
- `diagnostics/assessment/sec-xbrl-canonical-projection.py`
- `diagnostics/assessment/sec-xbrl-canonical-projection-report.json`
- `backend/tests/test_sec_xbrl_canonical_projection.py`

The existing Slice 1 resolver remains compatible. `_inline_confirmation` now returns the matching `resolved_fact_id` and `effective_value` when present, while retaining the existing `confirmed` field used by the comparability path.

## Projection Rules

- Derive the primary taxonomy from sidecar filing namespaces, not from CompanyFacts presence.
- Derive the primary FY period from standard non-dimensional sidecar facts, with a `dei:DocumentPeriodEndDate` cross-check when available.
- Select sidecar facts by primary-taxonomy source order, FY period, non-dimensional shape, and reviewed canonical source mapping.
- Read the projected value from the sidecar value store.
- Carry complete provenance for every projected fact: resolved fact, sidecar receipt, value-store hash, and dataset version.
- Validate projected facts against CompanyFacts period-aware; `oracle_absent` is retained as coverage gain and excluded from the confirmed-rate denominator.
- Preserve explicit total-to-parent fallback and divided-unit handling.

## Guardrails

- Runtime defaults remain off.
- This is validate-only: no live SEC network, no Arelle invocation, no value reveal, no runtime artifact generation, and no default/config change.
- Existing Slice 1 behavior and committed reports remain unchanged.
- The committed projection report is redacted summary evidence only: hashes, counts, coverage, provenance-presence booleans, concept identifiers, reason codes, and identity residual magnitudes.
- The slice does not claim production readiness, default-on readiness, final financial-statement semantics, statement assembly, linkbase relationship extraction, or FX comparability.

## Deferred Slices

Statement assembly remains deferred until linkbase relationship emission is available from the Arelle tool path. FX/scale normalization remains deferred until an authoritative rate source and rate provenance model are selected.

## Validation

Required validation before merge:

- focused canonical projection tests
- existing canonical comparability tests
- focused SEC XBRL tests
- projection diagnostic report generation
- JSON validation for the committed report and progress manifests
- `tools/l3-progress-check.py`
- `git diff --check`
- redaction scan over added or changed files, with the committed report checked for absence of raw values and authority identifiers
