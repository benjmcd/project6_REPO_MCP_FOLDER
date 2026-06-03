# 1279 - SEC XBRL Canonical Coverage Breadth

## Target

`sec_xbrl_canonical_coverage_breadth_validate_only_v1`

## Purpose

This slice adds an additive coverage-breadth pass after canonical projection. It matures the 22-concept headline canonical registry by deriving missing noncurrent balance-sheet concepts from governed Total minus Current inputs, then records redacted sector-class coverage evidence without claiming filing-wide canonicalization.

## Scope

Files:

- `backend/app/services/layer3_sec_xbrl_canonical_concepts.py`
- `diagnostics/assessment/sec-xbrl-canonical-coverage-breadth.py`
- `diagnostics/assessment/sec-xbrl-canonical-coverage-breadth-report.json`
- `backend/tests/test_sec_xbrl_canonical_coverage_breadth.py`

The existing Slice 0, Slice 1, and Slice 2 behaviors remain intact. The new derivation is a post-pass sibling to the existing total-to-parent fallback and does not change the existing fallback or committed Slice 1 and Slice 2 reports.

## Derivation Rules

- Derive `NoncurrentAssets[total]` only when `TotalAssets[total]` and `CurrentAssets[total]` are both resolved.
- Derive `NoncurrentLiabilities[total]` only when `TotalLiabilities[total]` and `CurrentLiabilities[total]` are both resolved.
- Do not derive when the Current input is absent. Filings whose sector structure lacks a classified current/noncurrent split remain legitimately absent for this industrial-family concept.
- Mark derived facts with `status="derived"` and `mapping_method="derived_total_minus_current"`.
- Preserve dual-input provenance by carrying both source resolved fact identifiers internally.
- In projection, require the derived fact to carry the same sidecar receipt, value-store hash, and dataset version authority as both source inputs before counting provenance as complete.

## Coverage Evidence

The committed coverage-breadth report is validate-only and redacted. It records per-sector-class aggregate counts, concept-level direct/derived/absent counts, coverage rates including derivation, and the sector-structure limitation. It does not contain issuer identities, source accessions, period dates, source URLs, local storage roots, raw filing text, or financial values.

The report frames coverage as headline canonical coverage by sector class. It does not claim whole-filing coverage, production readiness, final financial-statement semantics, cross-company currency comparability, or statement assembly.

## Sector-Family Design

The long-term governed product needs sector-conditioned canonical families. The current 22-concept family is an industrial/commercial headline schema. Financial-sector statement structures need a separate canonical family selected by issuer industry or SIC evidence, with concepts that match those statements instead of forcing an industrial current/noncurrent and cost-of-sales shape.

This slice documents that direction only. It does not implement sector-aware concept-family selection, financial-sector concept families, linkbase-driven statement assembly, or FX normalization.

## Guardrails

- Under 1317, Arelle fact-authority cutover is admitted default-on; live SEC network, value reveal, and controlled value-reveal submit remain default-off.
- This is validate-only: no live SEC network, no Arelle invocation, no value reveal, no runtime artifact generation, and no config change beyond the already-admitted 1317 cutover posture.
- Existing Slice 0, Slice 1, and Slice 2 behavior and tests remain unchanged.
- The committed coverage report is redacted summary evidence only.
- Sector-conditioned canonical families, statement assembly, linkbase relationship extraction, FX/scale normalization, provider/model/RAG/auth behavior, and default-on readiness remain deferred.

## Validation

Required validation before merge:

- focused coverage-breadth tests
- existing canonical projection and comparability tests
- focused SEC XBRL tests
- coverage-breadth diagnostic report generation
- JSON validation for the committed report and progress manifests
- `tools/l3-progress-check.py`
- `git diff --check`
- redaction scan over added or changed files, with the committed report checked for absence of issuer identities, source accessions, period dates, source URLs, local paths, raw values, and raw authority identifiers
