# 1255 - SEC XBRL Arelle Resolved-Fact Authority Sidecar

## Target

`sec_edgar_arelle_resolved_fact_authority_sidecar_v1`

## Decision Boundary

This slice is additive only. It emits a governed local sidecar resolved-fact authority from already-retained SEC source-artifact bytes and records parity diagnostics. It does not mutate the regex fact-material bridge, Gate B, product, package, UI, archive, or runtime defaults.

## Runtime Shape

- Input authority: existing SEC HTML/iXBRL parser receipt plus retained live source-artifact bytes.
- Adapter execution: isolated Arelle subprocess/CLI, pinned to `arelle-release==2.41.3`.
- Output authority: local gitignored sidecar receipt with raw fact values retained for later governed reveal.
- Committed/report projection: counts, hashes, resolved structural semantics coverage, parity only; fact values remain redacted.
- CompanyFacts role: accession-scoped standardized cross-check diagnostic only.
- Taxonomy posture: the follow-up DTS confirmation slice `1256-sec-xbrl-dts-confirmation.md` admits external cached taxonomy package/cache provisioning for the sidecar and confirms DTS-loaded counts before cutover.
- License/security posture: Arelle is pinned as an optional Apache-2.0 dependency behind the subprocess adapter; supply-chain and license review must be repeated before any CI or runtime-default admission.

## Proof Summary

Combined real-corpus report:

- Real filings measured: `12`
- Forms: `10-K`, `10-Q`, `20-F`, `40-F`, `6-K`, `8-K`
- Current regex fact-authority facts: `6810`
- Arelle resolved sidecar facts: `15529`
- Recovered versus regex: `8719`
- Current regex production capture ratio: `43.9%`
- CompanyFacts standardized cross-check facts: `2664`

Resolved structural coverage:

- Period resolved: `15529`
- Unit resolved: `14010`
- Explicit dimension fact count: `9789`
- Typed dimension fact count: `2`
- Hidden fact count: `204`
- Continued fact count: `203`

Per-filing report:

`diagnostics/assessment/sec-xbrl-sidecar-report.json`

## Non-Admissions Preserved

- No final financial-statement semantics claim.
- No cross-company comparability claim.
- No Candidate B routing for non-PDF SEC semantics.
- No bridge, Gate B, product, package, UI, archive, or default extraction cutover.
- No raw tickers, URLs, paths, storage roots, accessions, or fact values in committed reports.
- No Arelle import into app runtime.

## Follow-Up Slice

`sec_edgar_arelle_dts_confirmation_v1` is recorded in `1256-sec-xbrl-dts-confirmation.md`.

After that confirmation, the next gated production slice is:

`sec_edgar_arelle_fact_authority_input_cutover_v1`

Scope:

- Make the Arelle resolved-fact sidecar the fact-material bridge input under an explicit operator-gated mode.
- Resolve the 20-F `sec_edgar_html_inline_xbrl_fact_material_bridge_fact_count_mismatch` by consuming the sidecar count/inventory instead of the regex inventory.
- Keep the regex fact authority as a parity diagnostic until the cutover proof passes.
- Preserve all non-admissions until product-level semantic utility is separately proven.

Proof required:

- The 20-F sidecar row materializes through the bridge without fact-count mismatch.
- 10-K and 10-Q bridge counts match sidecar receipts.
- 8-K and 40-F remain matched.
- 6-K zero-iXBRL rows remain honest zero-fact diagnostics.
- Redaction and negative-invariant scans remain clean.
