# SEC XBRL Canonical Comparability Validate-Only Diagnostic

## Decision

Add `sec_xbrl_canonical_cross_company_comparability_validate_only_v1` as the next additive SEC XBRL diagnostic after the period-aware value oracle.

The diagnostic defines a reviewed 22-concept headline statement crosswalk across admitted standard taxonomies and emits only redacted comparability evidence. It does not fetch live data, invoke Arelle, reveal values, change runtime defaults, assemble statements, or claim production/default-on readiness.

## Scope

- Add a versioned canonical concept registry in `backend/app/services/layer3_sec_xbrl_canonical_concepts.py`.
- Add a validate-only diagnostic report writer in `diagnostics/assessment/sec-xbrl-canonical-comparability.py`.
- Add a committed redacted report at `diagnostics/assessment/sec-xbrl-canonical-comparability-report.json`.
- Add focused tests for crosswalk resolution, primary-taxonomy source preference, FY period scoping, total-to-parent basis fallback, legitimate absence, divided-unit support, internal identity residuals, and report redaction.

## Canonical Coverage Frame

The report measures `headline_canonical_resolved / headline_canonical_defined` only. It must not be described as whole-filing canonicalization or final financial-statement semantics.

The committed report may include:

- issuer hashes
- concept identifiers
- taxonomy-local source concept identifiers
- basis labels
- FY period class
- coverage counts
- residual magnitudes and tolerance booleans
- reason codes

The committed report must not include raw issuer identities, accessions, period dates, URLs, local paths, raw values, retained bytes, cache roots, or operator contact strings.

## Guardrails

- Runtime defaults stay off.
- Existing CompanyFacts value gates remain unchanged.
- The crosswalk is reviewed and deterministic; no heuristic broad concept matching is admitted.
- Primary-taxonomy source concepts are preferred before same-concept legacy-taxonomy history.
- Total-to-parent fallback is explicit in output through requested basis and resolved basis.
- Legitimately absent cells remain visible as absent, not silently excluded.
- Divided units are supported for per-share concepts.
- Statement identity residuals are diagnostic-only and redacted as magnitudes, not raw financial values.

## Deferred Slices

Canonical projection artifacts, statement assembly, and FX conversion remain deferred. Statement assembly requires linkbase relationship extraction. FX conversion requires a separate authoritative rate-source decision and rate provenance model.

## Validation

Required validation before merge:

- focused canonical comparability tests
- focused SEC XBRL tests
- diagnostic report generation
- JSON validation for the committed report and progress manifests
- `tools/l3-progress-check.py`
- `git diff --check`
- redaction scan over every added or changed artifact
