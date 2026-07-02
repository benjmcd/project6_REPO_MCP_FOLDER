# A7 Chain CI Durability

## Scope

This Phase 4 slice is Tier-1: tests, synthetic fixtures, a design note, and minimal CI wiring only. It does not change runtime source, flags, defaults, schemas, migrations, redaction posture, or retained real SEC artifacts.

## Source Of Truth

The canonical A7 chain is the persisted receipt handoff already implemented in source:

1. `layer3_sec_edgar_real_filing_acquisition_connector` records connector authority.
2. `layer3_sec_edgar_html_inline_xbrl_parser` consumes connector and live source-artifact receipts.
3. `layer3_sec_edgar_html_inline_xbrl_fact_authority` derives the regex receipt used for lineage parity.
4. `layer3_sec_xbrl_sidecar` derives the Arelle sidecar receipt in an isolated subprocess boundary.
5. `layer3_sec_edgar_html_inline_xbrl_fact_material_bridge` consumes the sidecar receipt to create a `DatasetVersion` and materialization receipt.

Phase 4 tests exercise those service boundaries with synthetic complete-submission text and isolated runtime state. The live SEC acquisition path remains out of scope because this program forbids SEC egress; the synthetic connector receipt is written to the same receipt store and is consumed through the real reader.

## CI Proof

`backend/tests/test_sec_xbrl_a7_chain_ci_durability.py` adds two offline checks:

- a positive chain proof: parser receipt -> regex fact receipt -> sidecar receipt -> material bridge -> isolated SQLite `DatasetVersion` and materialization CSV;
- a fail-closed proof: when the bridge cutover is enabled and no persisted sidecar receipt is supplied, bridge execution blocks without regex fallback or synchronous Arelle invocation.

The positive test uses the existing synthetic A7 inline-XBRL fixture and a fake Arelle subprocess runner at the process boundary. It still verifies the persisted sidecar projection, default-off internal value store, redacted bridge response, empty materialized value columns, and server-owned provenance.

## Mutation Argument

The new tests fail if a future change breaks any of these chain links: connector/live artifact hash parity, parser receipt lineage, regex/sidecar lineage parity, sidecar-required bridge cutover, `DatasetVersion` persistence, materialization receipt creation, or raw-value redaction in the sidecar and CSV surfaces. A mutation that silently falls back to regex facts, invokes Arelle synchronously from the bridge, or drops the sidecar receipt requirement is caught by the fail-closed test.
