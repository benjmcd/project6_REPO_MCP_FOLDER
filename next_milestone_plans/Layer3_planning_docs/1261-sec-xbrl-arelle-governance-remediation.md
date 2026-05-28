# 1261 - SEC XBRL Arelle Governance Remediation

## Target

`sec_edgar_arelle_governance_remediation_v1`

## Scope

This slice restores conservative governance posture after the default-on and value-reveal merge sequence. It does not add SEC parsing, product, package, Gate B, RAG, provider, auth, or UI capability.

## Cutover Default

`backend/app/core/config.py` restores `layer3_sec_edgar_arelle_fact_authority_cutover_enabled` to default `False`. The Arelle resolved-fact bridge path remains implemented and test-covered, but callers must explicitly enable the flag when they need the sidecar authority path.

The relevant evidence is PR #1952 and `diagnostics/assessment/sec-xbrl-real-corpus-product-runner-report.json`. That report records a broad real-corpus runner with `arelle_cutover_current_default_enabled: false` at run time and a runtime-default decision. This remediation intentionally keeps the committed runtime default aligned with conservative default-off posture while the remaining governance evidence is reviewed.

## Value-Reveal Flag Enforcement

`layer3_sec_edgar_arelle_value_reveal_enabled` remains default `False`.

The operator product surface now evaluates reveal requests in this order:

1. No `value_reveal_*` fields: return the redacted default-surface value-reveal projection.
2. `value_reveal_*` fields present and reveal flag disabled: block with `sec_edgar_operator_product_surface_value_reveal_flag_disabled`.
3. `value_reveal_*` fields present and reveal flag enabled: continue the existing fail-closed sibling-endpoint boundary.

The sibling reveal endpoint already checks the same feature flag before request-schema, actor, confirmation, sidecar, dataset, or lineage evaluation.

## Audit Receipt

The persisted audit trail lives in `settings.storage_dir/layer3-sec-edgar-arelle-value-reveal/`. Successful sibling reveals write one server-owned receipt under the `receipts` subdirectory.

Receipt contents are hashes and structural metadata only:

- reveal receipt id, hash, and ref
- schema id and version
- actor hash only
- server time
- client request id hash
- idempotency key hash
- sidecar receipt hash
- dataset version hash
- parser, connector, source-artifact, primary-document, and bridge lineage hashes
- fact count
- fact inventory hash
- value inventory hash
- value reveal policy id
- value reveal scope
- value semantics
- redaction policy id
- negative invariants

The receipt never persists raw values, raw actor text, raw issuer identity, raw SEC URLs, local paths, storage roots, accessions, tickers, or contact strings. The runtime reveal response may return effective values to a confirmed caller; the audit receipt and status projection remain hashes-only.

Idempotency is bound to a stable hash over the client request id hash, sidecar receipt hash, dataset version hash, and actor hash. Repeating the same reveal request returns the same reveal receipt instead of writing another receipt.

If the audit receipt cannot be written, the reveal blocks and returns no values.

## Architecture Boundary

Live main implements governed value reveal as a sibling endpoint/service: `backend/app/services/layer3_sec_edgar_arelle_value_reveal.py`. The operator product surface does not reveal values directly; it only detects legacy `value_reveal_*` fields, enforces the deployment flag, and then fails closed to the sibling endpoint.

This differs from a surface-mode reveal design, but it is a deliberate defense-in-depth boundary. The default product surface stays redacted, while the reveal path has its own request schema, lineage verification, persisted audit receipt, idempotent replay, and redacted status projection.

The forward-only surface receipt hash basis can change when the redacted value-reveal projection changes. No cross-version replay is assumed.

## Gates Before Another Default-On Attempt

Before any future attempt to make the Arelle fact-authority cutover default-on again, the default-on packet should explicitly re-state:

- sidecar selected for every supported record
- product-path readiness across all validation chunks
- completeness aggregate and unexpected zero-inline handling
- CompanyFacts oracle coverage and mismatch framing
- no silent regex fallback while the flag is on
- no synchronous Arelle invocation in bridge, Gate B, product, or package paths
- no raw identity, SEC URL, local path, storage root, or contact disclosure

The CompanyFacts oracle should remain framed as an independent standardized-fact cross-check, not as a complete filing-level replacement.

## Non-Goals

- no default-on Arelle cutover
- no default-on value reveal
- no new Layer 3 source shape
- no bridge, Gate B, package, archive, or product redesign
- no parser expansion
- no final financial-statement semantics claim
- no cross-company comparability claim
- no Candidate B routing for SEC semantics
- no RAG, model, provider, auth, or mockup behavior
