# 1258 - SEC XBRL Fact Authority Input Cutover

## Target

`sec_edgar_arelle_fact_authority_input_cutover_v1`

## Decision Boundary

This slice makes the persisted Arelle resolved-fact sidecar the SEC HTML/iXBRL fact-material bridge authority input under an explicit default-off flag.

The slice is the first production data-flow change after the Arelle sidecar proof. It does not enable the flag by default and does not change Gate B decision logic, product, package, UI, archive, or runtime defaults.

## Runtime Change

- Added `LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_CUTOVER_ENABLED`, default `false`.
- With the flag off, the bridge continues to consume the regex fact-authority receipt.
- With the flag on, the bridge requires an explicit persisted Arelle sidecar receipt id and hash.
- The bridge does not invoke Arelle synchronously.
- The bridge verifies sidecar, parser, source artifact, and regex fact-authority lineage before accepting the sidecar.
- The bridge fails closed on missing sidecar authority or lineage mismatch; it does not silently fall back to regex authority when the flag is on.
- The regex fact-authority path remains present for fallback/comparison while the cutover remains gated.

## Materialization

The bridge still reuses `dataset_version`; no new Layer 3 source shape is created.

When the flag is on, dataset rows materialize resolved structural fields from the sidecar:

- concept QName, namespace, local name, standard/extension flags, DTS resolution flag;
- context id and unit id;
- period type/start/end/instant/forever/resolved;
- unit measures, currency, numerator, denominator, resolved;
- explicit and typed dimensions;
- hidden/continued flags and footnote count.

Fact values remain redacted in exposed and committed artifacts. The local dataset stores `value_hash`, `value_length`, and `value_redacted=true`; `value_text` remains empty for the sidecar cutover path.

## Proof Summary

Cutover report:

`diagnostics/assessment/sec-xbrl-bridge-cutover-report.json`

Measured corpus:

- Real filings: `12`
- Inline bridge-ready filings: `10`
- Zero-inline filings: `2`
- Flag-on bridge facts: `18156`
- Sidecar resolved facts: `18156`
- Bridge/sidecar count match: `true`
- Blocked rows: `0`
- Required typed fields present for ready rows: `true`
- Raw values detected in dataset rows: `false`

Key filing gates:

| Form | Production regex facts | Arelle sidecar facts | Flag-on bridge facts | Result |
| --- | ---: | ---: | ---: | --- |
| `20-F` | `2019` | `5000` | `5000` | Mismatch resolved by sidecar replacement |
| `40-F` | `43` | `2670` | `2670` | Multi-document facts materialized |

The two zero-inline `6-K` filings remain explicit `not_applicable_no_inline_xbrl` rows rather than fabricated materializations.

## Fail-Closed Coverage

Focused API tests cover:

- flag-off bridge behavior through the existing regex authority path;
- flag-on bridge behavior with persisted Arelle sidecar authority;
- flag-on missing sidecar receipt blocks with `arelle_sidecar_receipt_required`;
- flag-on lineage mismatch rejects with `sec_edgar_html_inline_xbrl_fact_material_bridge_arelle_sidecar_lineage_mismatch`;
- bridge request path does not call the Arelle subprocess runner.

The existing sidecar tests remain green and preserve Arelle-absent fail-closed behavior for sidecar creation.

## Non-Admissions Preserved

- The cutover flag remains default off.
- No Arelle import into app runtime.
- No synchronous Arelle execution in bridge, Gate B, product, package, or UI request paths.
- No new Layer 3 source shape.
- No Gate B decision-logic redesign.
- No product, package, UI, archive, or default-scope redesign.
- No value unredaction.
- No final financial-statement semantics claim.
- No cross-company comparability claim.
- No Candidate B routing for non-PDF SEC semantics.
- No RAG/vector/model/provider/auth behavior.

## Next Slice

Recommended next slice:

`sec_edgar_arelle_governed_value_reveal_v1`

Scope:

- define the governed policy for revealing selected fact values to operators;
- preserve default redaction until operator authority admits a reveal;
- bind revealed values to existing sidecar and bridge receipts;
- keep report/committed artifacts hash-only;
- preserve non-admission of final statement semantics and cross-company comparability.

Parallel or following validation slice before default enable:

`sec_edgar_arelle_cutover_corpus_expansion_v1`

Scope:

- expand the cutover proof beyond the current 12 filings;
- include more 10-K/10-Q/foreign/exhibit-heavy cases;
- require bridge count parity, typed-field presence, and redaction proof before considering default-on admission.
