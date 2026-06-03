# 1280 - SEC XBRL Canonical Retained Coherence

## Target

`sec_xbrl_canonical_retained_coherence_validate_only_v1`

## Purpose

This slice adds the missing binding proof between the canonical SEC XBRL projection and the retained statement-classification fact view. It proves that every non-absent canonical projection fact is still present in the retained view by resolved fact authority, that qualified names agree, that each binding resolves through a single retained value-store projection, and that the retained view remains a strict superset carrying dimensional and issuer-extension facts that the canonical headline projection intentionally omits.

## Scope

Files:

- `backend/app/services/layer3_sec_xbrl_canonical_retained_coherence.py`
- `backend/app/services/layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.py`
- `diagnostics/assessment/sec-xbrl-canonical-retained-coherence.py`
- `diagnostics/assessment/sec-xbrl-canonical-retained-coherence-report.json`
- `backend/tests/test_sec_xbrl_canonical_retained_coherence.py`

Lineage B canonical concept resolution and projection behavior remains unchanged. Lineage A statement classification and material-bridge product behavior remains unchanged except for the new public retained-view accessor, which maps the existing statement-classification sidecar flattening function without changing its output shape.

## Binding Rules

- Direct canonical projection facts bind to retained facts by resolved fact authority.
- Derived canonical facts bind both source input facts used by the derivation.
- Direct facts require canonical `source_qname` to match retained `qualified_name`.
- Derived facts validate the input facts' retained qualified names instead of the derived row's null top-level source qname.
- Each bound fact must appear exactly once in the retained value-store projection.
- The retained view must be a strict superset and must retain dimensional and issuer-extension facts.
- Any missing binding fails the contract and is reported as a missing aggregate count rather than hidden.

## Evidence

The committed diagnostic report is redacted sector-class aggregate evidence only. It records the industrial/commercial reference class from the operator-run summary and reports:

- normalized canonical binding count
- bound count
- missing count
- qualified-name consistency count
- value-store reconciliation count
- retained dimensional and extension superset booleans
- contract booleans

The evidence covers the redacted operator-run issuers only. It does not claim all-sector coverage, all-filing coverage, sector-family readiness, final statement assembly, or persisted-store readiness.

## Guardrails

- Under 1317, Arelle fact-authority cutover is admitted default-on; live SEC network, value reveal, and controlled value-reveal submit remain default-off.
- This is validate-only: no live SEC network, no Arelle invocation, no value reveal, no source acquisition, no runtime artifact generation, no persistence, and no config change beyond the already-admitted 1317 cutover posture.
- Existing canonical concept resolution/projection logic and tests are not changed.
- Existing statement classification and material-bridge product behavior is not changed.
- Sector-conditioned canonical families, statement assembly, per-period projection, persisted store behavior, linkbase relationship extraction, FX/scale normalization, provider/model/RAG/auth behavior, and default-on readiness remain deferred.
- The committed report excludes issuer identities, accessions, period dates, URLs, local paths, raw financial values, raw resolved fact authorities, and raw retained total-fact counts.

## Validation

Required validation before merge:

- focused canonical-retained coherence tests
- existing canonical projection and coverage-breadth tests
- material-bridge and statement-classification suites
- diagnostic report generation
- JSON validation for the committed report and progress manifests
- `tools/l3-progress-check.py`
- `git diff --check`
- redaction scan over added or changed files, with the committed report checked for absence of issuer identities, source accessions, period dates, source URLs, local paths, raw values, raw resolved fact authorities, and raw retained total-fact counts
