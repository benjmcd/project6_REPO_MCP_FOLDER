# 1256 - SEC XBRL Arelle DTS Confirmation

## Superseded Completeness Note

This document is retained as the `sec_edgar_arelle_dts_confirmation_v1` record. Its count-completeness conclusion is superseded by `1257-sec-xbrl-completeness-verification.md`, which independently reconciles raw inline-XBRL counts against the Arelle sidecar and identifies a 40-F multi-inline-document undercount that this slice did not catch.

## Target

`sec_edgar_arelle_dts_confirmation_v1`

## Decision Boundary

This slice confirms and hardens the additive Arelle resolved-fact authority sidecar before any fact-material bridge, Gate B, product, package, UI, archive, or runtime-default cutover.

The slice does not rewire downstream consumers. The next gated production slice remains `sec_edgar_arelle_fact_authority_input_cutover_v1`.

## DTS Provisioning

- Arelle remains an optional pinned subprocess dependency: `arelle-release==2.41.3`.
- Taxonomy packages are supplied by operator environment only.
- Taxonomy package files and Arelle cache/temp state must live outside the repo and outside the synced workspace.
- Missing package/cache configuration fails closed.
- The committed DTS counts were produced offline from the external cache after one local cache warmup for missing standard DTS resources.
- The direct IFRS 2024 package was not available in this environment, but the needed 2024 standard DTS resources were resolved from the external cache.
- No Arelle import into app runtime is admitted.

## Hardening Implemented

- Complete-submission staging now writes all retained SEC submission documents into the isolated Arelle working directory.
- Primary document selection uses retained document content hash, not filename hash.
- SEC complete-submission XML wrapper whitespace/envelope is stripped only for staged XML/XSD documents so Arelle can build the DTS; retained source bytes are unchanged.
- The helper resolves concepts through the Arelle DTS concept map by namespace/local-name when fact object identity does not carry `fact.concept`.
- The sidecar records taxonomy package load state, package hashes, loaded document count, and DTS resolved/unresolved concept coverage.

## Proof Summary

Combined report:

`diagnostics/assessment/sec-xbrl-dts-report.json`

Source reports:

- `diagnostics/assessment/sec-xbrl-sidecar-core-report.json`
- `diagnostics/assessment/sec-xbrl-sidecar-expansion-report.json`
- `diagnostics/assessment/sec-xbrl-dts-core-report.json`
- `diagnostics/assessment/sec-xbrl-dts-expansion-report.json`
- `diagnostics/assessment/sec-xbrl-dts-online-report.json`

Corpus:

- Real filings measured: `12`
- Forms: `10-K`, `10-Q`, `20-F`, `40-F`, `6-K`, `8-K`
- Current regex fact-authority facts: `6810`
- No-DTS Arelle facts: `15529`
- DTS-loaded Arelle facts: `15529`
- DTS count delta: `0`
- Recovered versus regex: `8719`
- Current regex production capture ratio: `43.9%`

Resolved DTS coverage:

- Concepts resolved from DTS: `15159`
- Concepts unresolved from DTS: `370`
- Concept DTS resolution ratio: `97.6%`
- Period resolved: `15529`
- Unit resolved: `14010`
- Explicit dimension fact count: `9789`
- Typed dimension fact count: `2`
- Max loaded document count: `35`

20-F gate:

- No-DTS Arelle fact count: `5000`
- DTS-loaded Arelle fact count: `5000`
- DTS count delta: `0`
- Loaded document count: `35`
- Concepts resolved from DTS: `5000`
- Concepts unresolved from DTS: `0`

This confirms that the observed `5000` 20-F count is not a no-DTS artifact or primary-document-only undercount in this environment.

## Non-Admissions Preserved

- No fact-material bridge cutover.
- No Gate B, product, package, UI, archive, or runtime-default mutation.
- No Candidate B routing for non-PDF SEC semantics.
- No raw tickers, URLs, paths, storage roots, accessions, or fact values in committed reports.
- No final financial-statement semantics claim.
- No cross-company comparability claim.

## Next Slice

`sec_edgar_arelle_fact_authority_input_cutover_v1`

Scope:

- Make the persisted Arelle resolved-fact authority receipt the fact-material bridge input under an explicit operator-gated mode.
- Resolve the 20-F bridge fact-count mismatch by consuming the sidecar inventory instead of the regex inventory.
- Keep the regex fact authority as a parity diagnostic until cutover proof passes.
- Preserve all semantic and comparability non-admissions.

Proof required:

- 20-F bridge materializes without `sec_edgar_html_inline_xbrl_fact_material_bridge_fact_count_mismatch`.
- 10-K and 10-Q bridge counts match sidecar receipts.
- 8-K and 40-F remain matched.
- 6-K zero-iXBRL rows remain honest zero-fact diagnostics.
- Redaction and negative-invariant scans remain clean.
