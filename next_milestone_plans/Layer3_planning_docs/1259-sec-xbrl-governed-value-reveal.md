# 1259 - SEC XBRL Governed Value Reveal

## Target

`sec_edgar_arelle_governed_value_reveal_v1`

## Governing posture

This is Option 1, analysis-layer reveal. The existing default-off cutover flag remains the admission boundary. When the flag is off, the bridge stays on the regex authority path. When the flag is on, the bridge consumes the persisted Arelle resolved-fact sidecar and may materialize values into the internal `dataset_version` artifact only.

Operator surfaces, status projections, committed reports, and package/product surfaces must not expose raw values in this slice. Operator-facing governed value reveal is a separate follow-on slice.

## Value semantics

Arelle values are the authoritative internal value semantics for this path. The bridge materializes:

- `effective_value_text`: Arelle's canonical effective value after inline XBRL transform handling.
- `lexical_value_text`: the source lexical/as-reported body captured by the Arelle runner.
- `transform_sign`, `transform_scale`, `transform_decimals`, `transform_precision`, and `transform_format`: transform/provenance inputs carried alongside the value.
- concept, period, unit, and dimension fields already carried by the sidecar.

The legacy regex path's `value_text` is lexical and remains a known limitation while that path is retained for flag-off reversibility. The Arelle path must not overload `value_text` with effective values.

## Internal value store

This slice introduces a raw-value-at-rest store relative to the older regex path:

- store: `layer3.sec_edgar_arelle_resolved_fact_authority_internal_value_store.v1`
- location: gitignored Layer 3 storage under the Arelle sidecar receipt root
- lifecycle: tied to the owning sidecar receipt
- identity: bound by `sidecar_receipt_id`, `sidecar_receipt_hash`, and `value_store_hash`
- creation: gated by `layer3_sec_edgar_arelle_fact_authority_cutover_enabled`
- consumption: bridge flag-on only
- exposure: never included in operator/status/product/package surfaces or committed reports

The bridge never invokes Arelle synchronously. It fails closed if the sidecar receipt or internal value store is missing, stale, blocked, or lineage-mismatched.

## Non-admissions preserved

- no default-on cutover
- no operator-surface value exposure
- no final financial-statement semantics
- no cross-company comparability
- no Candidate B routing for SEC semantics
- no new Layer 3 source shape
- no Gate B/product/package/UI redesign

## Proof required

- focused tests for effective-value materialization, including scaled and signed facts
- sidecar value-store persistence and receipt redaction tests
- bridge flag-on materialization with values in internal CSV and no values in response/status
- flag-off bridge behavior unchanged
- fail-closed persisted-only sidecar/value-store behavior
- redaction scan over committed docs/reports
- standard Layer 3 progress and target-selection checks

## Next slice

`sec_edgar_arelle_operator_surface_gated_value_reveal_v1`

That slice may expose selected values to operators under a separate governed reveal policy. Corpus expansion remains a separate prerequisite before any default-on cutover.
