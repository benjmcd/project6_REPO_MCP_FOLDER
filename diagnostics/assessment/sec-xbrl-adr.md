# ADR: SEC XBRL Resolved Fact Authority

```yaml
status: proposed
date: 2026-05-27
decision_scope: adapter_platform_fit_only
runtime_mutation: false
measured_input_commit: 49731e2b
recommended_option: hybrid_arelle_extraction_companyfacts_crosscheck_existing_repo_spine
```

## Context

The first real-corpus measurement proved that the governed SEC acquisition and retained-byte path can run, but the repo-native regex fact extraction is not adequate for flagship SEC filing products:

- 10-K: `438/643` production-vs-Arelle facts.
- 20-F: `2019/5000` production-vs-Arelle facts plus `sec_edgar_html_inline_xbrl_fact_material_bridge_fact_count_mismatch`.
- 8-K and 40-F: matched on low-fact examples.
- 6-K: no inline XBRL markers in the selected filings.

The observed misses are structural iXBRL features: hidden facts, continuations, unsupported marker shapes, unresolved contexts/units, and capped text segment inventory. They are not adequately explained by corpus flukes.

## Decision

Adopt a hybrid standards-aware path:

```text
Arelle extraction sidecar
plus SEC CompanyFacts accession cross-check
plus existing repo acquisition/provenance/product spine
```

Arelle extraction becomes the production resolved-fact authority for admitted real HTML/iXBRL fact inventory. CompanyFacts remains a primary standardized cross-check for us-gaap/dei facts by accession, not a filing-level replacement. The existing repo spine remains responsible for acquisition, retained source authority, redaction, receipts, material preview, Gate B, package/review/handoff, archive, and operator inspection.

Do not choose:

- custom-only hardening, because the 10-K and 20-F measurements show the repo would be reimplementing a standards processor;
- validation-only Arelle, because it detects under-counting but does not fix product fact coverage;
- CompanyFacts-only, because it is not a full filing-level extraction source and is weak on foreign forms, extensions, source order, and retained filing fidelity.

## Strategy A Restatement

Strategy A remains the governed SEC/EDGAR ingestion-integrity, provenance, and coverage product. But a pure custom-parser Strategy A is not shippable as a trustworthy coverage product for 10-K/20-F iXBRL. Trustworthy Strategy A now requires an extraction adapter for resolved fact authority while preserving non-admission of final financial-statement semantics and cross-company comparability.

Strategy B remains deferred for broader semantic resolution and comparability. The Arelle extraction sidecar is not a claim of final statement semantics; it is the minimum standards-aware extraction layer needed for coverage integrity.

## Platform-Fit Verdict

The adapter fits the multi-source Layer 3 architecture only if it remains upstream of Layer 3 source-shape admission:

- `resolved_fact_authority` is a sidecar receipt, not a new Layer 3 source shape.
- Resolved fact rows should materialize through existing `dataset_version` authority.
- Narrative SEC evidence remains separate and should not be forced into the fact dataset.
- A new SEC-only Layer 3 source shape is debt unless later proven necessary by operator/product evidence.

This aligns with the multi-ingest quality bar: modularity, fail-closed behavior, provenance stability, backward compatibility, and bounded growth.

## Adapter Boundary

Input:

- retained SEC source-artifact bytes;
- existing connector/live-source/parser authority hashes;
- no caller URL/path/bytes;
- no frontend durable authority.

Execution:

- subprocess/CLI boundary;
- dependency-only Arelle use;
- no external code copied into repo;
- cache/config outside the repo and synced workspace during local runs;
- timeout/resource caps;
- deterministic JSON output;
- fail closed on timeout, nonzero exit, malformed output, missing retained bytes, hash mismatch, or redaction violation.

Output:

- sidecar receipt with stable hash;
- resolved fact count;
- fact records with value hash/length only;
- concept/context/unit/period/dimension metadata;
- hidden/continued/extension/unclassified flags;
- duplicate/conflict diagnostics;
- no raw values, source bytes, URLs, local paths, storage roots, tickers, or accessions in committed artifacts.

Migration:

- Arelle replaces production extraction for admitted real iXBRL fact authority.
- Current regex extraction remains diagnostic/parity comparison until retired.
- Do not backfill misses into regex output; that keeps two competing authorities and preserves count mismatch risk.

## First Bounded Implementation Slice

Target: `sec_edgar_arelle_resolved_fact_authority_sidecar_v1`

Scope:

- implement the sidecar receipt over retained source bytes;
- emit redacted resolved-fact authority JSON;
- compare resolved count to current regex fact-authority count;
- use CompanyFacts as standardized accession cross-check only;
- validate against the six-filing measured corpus and a small expanded corpus.

Proof:

- 10-K moves from `438/643` toward Arelle parity;
- 20-F moves from `2019/5000` and bridge mismatch to a resolved-fact receipt near Arelle parity;
- 8-K and 40-F remain matched;
- no raw value/path/URL/storage root leakage;
- existing Layer 3 progress and target-selection checks remain green.

Non-goals:

- no runtime product/package/Gate B/UI changes in the first sidecar slice;
- no final financial-statement semantics;
- no cross-company comparability;
- no Candidate B routing for SEC;
- no RAG/model/provider/auth behavior.

## Risks

- Dependency and runtime cost: Arelle adds install/runtime overhead and must be isolated.
- Windows synced-workspace risk: cache/config and temp outputs must stay outside synced workspace and repo paths.
- CI risk: the first slice should avoid mandatory live network and use retained fixtures or explicitly gated local diagnostics.
- Performance risk: large filings need timeout and resource caps.
- Product risk: extraction parity is not statement semantics; UI/product copy must continue to say non-final semantics.

## License Note

The locally installed `arelle-release` package metadata reports `Apache-2.0`. Treat Arelle as a dependency behind the adapter boundary, not copied source. License review should be repeated before dependency admission in runtime/CI configuration.

## Sample-Size Caveat

The measured corpus is `n=6` filings across `3` issuer hashes. That is enough to reject custom regex adequacy for flagship iXBRL coverage, but not enough to certify the final adapter. Corpus expansion should be part of adapter validation, not a blocker to beginning the sidecar slice.
