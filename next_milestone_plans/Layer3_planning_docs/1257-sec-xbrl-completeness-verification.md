# 1257 - SEC XBRL Arelle Completeness Verification

## Target

`sec_edgar_arelle_completeness_verification_v1`

## Decision Boundary

This slice independently verifies Arelle resolved-fact sidecar completeness before any fact-material bridge, Gate B, product, package, UI, archive, or runtime-default cutover.

The slice remains additive. It does not make the Arelle sidecar the production fact-authority input. The next gated production slice is `sec_edgar_arelle_fact_authority_input_cutover_v1`.

## Hardening Implemented

- The sidecar now stages every retained inline-XBRL document from the complete SEC submission, not only the primary document.
- The contained Arelle helper accepts multiple entry documents in one subprocess run and emits a single deterministic resolved-fact list with `entry_document_index`.
- The sidecar computes a namespace-bound raw inline-XBRL fact lower-bound count across all retained SEC submission documents before Arelle runs.
- If Arelle emits fewer facts than the independent raw lower-bound count, the sidecar fails closed with `arelle_independent_inline_fact_count_mismatch`.
- The sidecar records redacted per-document inline fact tallies, scanned document counts, loaded document counts, and count reconciliation state.

## Proof Summary

Combined report:

`diagnostics/assessment/sec-xbrl-completeness-report.json`

Source reports:

- `diagnostics/assessment/sec-xbrl-completeness-core-report.json`
- `diagnostics/assessment/sec-xbrl-completeness-expansion-report.json`
- `diagnostics/assessment/sec-xbrl-completeness-core-online-report.json`
- `diagnostics/assessment/sec-xbrl-completeness-expansion-online-report.json`

Corpus:

- Real filings measured: `12`
- Forms: `10-K`, `10-Q`, `20-F`, `40-F`, `6-K`, `8-K`
- Inline-fact filings: `10`
- Current regex fact-authority facts: `6810`
- Arelle resolved sidecar facts: `18156`
- Independent raw inline-XBRL facts: `18156`
- Recovered versus regex: `11346`
- Current regex production capture ratio: `37.5%`

Resolved DTS coverage:

- Concepts resolved from DTS: `18156`
- Concepts unresolved from DTS: `0`
- Period resolved: `15529`
- Unit resolved: `14010`
- Explicit dimension fact count: `9789`
- Typed dimension fact count: `2`

## 20-F Completeness Gate

- Production regex fact-authority count: `2019`
- Independent raw inline-XBRL fact count: `5000`
- Arelle resolved sidecar count: `5000`
- Count delta: `0`
- SEC documents scanned: `212`
- Inline documents found: `1`
- Loaded document count: `35`
- Concepts resolved from DTS: `5000`
- Concepts unresolved from DTS: `0`

The `5000` count is confirmed by an independent namespace-bound raw inline-XBRL count. It is not treated as an Arelle-side cap or staging truncation for this filing in this environment.

## Multi-Document Finding

The 40-F filing exposed a separate completeness defect:

- Production regex fact-authority count: `43`
- Prior primary-only Arelle count: `43`
- Independent raw inline-XBRL count across retained submission documents: `2670`
- Arelle resolved sidecar count after multi-entry loading: `2670`
- Recovered versus primary-only loading: `2627`

Per-document tally:

| Document index | Document type | Inline facts | Primary document |
| --- | --- | ---: | --- |
| `1` | `40-F` | `43` | `true` |
| `3` | `EX-99.2` | `2627` | `false` |

This finding means the earlier DTS slice confirmed stable counts for the documents it loaded, but it did not independently prove all inline documents were loaded.

## Taxonomy Coverage

The offline proof uses the pinned Arelle dependency and an external taxonomy/cache posture:

- Arelle dependency: `arelle-release==2.41.3`
- Cache/temp/config outside the repo and outside the synced workspace.
- Committed proof counts run offline from the external cache after one local online warmup.
- Covered families include SEC standard resources, US GAAP years, SRT years, country/currency/exchange resources, and IFRS taxonomy resources available in the external cache/package set.

Remaining unresolved DTS concepts in the measured corpus: `0`.

## Non-Admissions Preserved

- No fact-material bridge cutover.
- No Gate B, product, package, UI, archive, or runtime-default mutation.
- No Candidate B routing for non-PDF SEC semantics.
- No raw tickers, URLs, paths, storage roots, accessions, or fact values in committed reports.
- No final financial-statement semantics claim.
- No cross-company comparability claim.
- No Arelle import into app runtime.

## Caveats

This proves count completeness and DTS concept resolution for the measured 12-filing corpus. It does not prove final statement semantics, cross-company comparability, or product utility after cutover.

The 40-F added exhibit facts have low period/unit resolution in the current sidecar output. The cutover must preserve those diagnostics instead of silently presenting the expanded fact authority as fully resolved financial-statement semantics.

## Next Slice

`sec_edgar_arelle_fact_authority_input_cutover_v1`

Scope:

- Make the persisted Arelle resolved-fact authority receipt the fact-material bridge input under an explicit gated mode.
- Resolve the 20-F bridge fact-count mismatch by consuming the sidecar inventory instead of the regex inventory.
- Preserve the independent raw inline-XBRL lower-bound reconciliation guard.
- Preserve the regex fact authority as a parity diagnostic until cutover proof passes.
- Preserve all semantic and comparability non-admissions.

Proof required:

- 20-F bridge materializes without `sec_edgar_html_inline_xbrl_fact_material_bridge_fact_count_mismatch`.
- 10-K and 10-Q bridge counts match sidecar receipts.
- 40-F bridge consumes both inline document entries and matches `2670`.
- 8-K rows remain matched.
- 6-K zero-iXBRL rows remain honest zero-fact diagnostics.
- Period/unit/dimension unresolved states remain operator-visible diagnostics.
- Redaction and negative-invariant scans remain clean.
