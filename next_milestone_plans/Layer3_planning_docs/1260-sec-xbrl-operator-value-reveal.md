# 1260 - SEC XBRL Governed Value Reveal

## Target

`sec_edgar_arelle_governed_value_reveal_v1`

## Governing posture

This is Option 2, analysis-layer operator reveal. It adds a sibling governed value-reveal capability for persisted Arelle resolved-fact authorities and bridge-materialized `dataset_version` rows. The default operator product surface remains redacted and continues to report no raw values unless an operator performs an explicit reveal through the sibling endpoint.

The reveal is default-off, per-request, and audit-bound:

- `layer3_sec_edgar_arelle_value_reveal_enabled` defaults to `False`
- caller must provide `layer3.sec_edgar_arelle_value_reveal_request.v1`
- caller must bind both the sidecar receipt id/hash and the dataset version id/hash
- caller must provide an actor self-attestation and explicit reveal confirmation
- server verifies sidecar, bridge, source-artifact, parser, connector, and dataset lineage before returning values
- successful reveals write a persisted audit receipt with hashes only, not raw values or raw identity

The Arelle cutover flag remains separate and unchanged. This slice does not enable the cutover by default, run Arelle synchronously, change Gate B, redesign product/package behavior, or create a new Layer 3 source shape.

## Reveal scope

The admitted response exposes per-fact values and resolved structural semantics only after the explicit reveal request succeeds:

- effective canonical value
- lexical as-reported value
- transform inputs: sign, scale, decimals, precision, and format
- resolved period fields
- resolved unit/currency fields
- explicit and typed dimensions
- concept QName, namespace, local name, and standard-vs-extension flags
- source order and per-fact identity hash

The response excludes raw SEC URLs, local paths, storage roots, accessions, raw tickers, contact strings, credentials, provider fields, and frontend durable authority. Existing default status and product-surface projections remain redacted.

Identity-like fact values are not revealed even when they are present in the resolved-fact authority. Concepts or values that indicate registrant name, ticker/trading symbol, contact/address, website/URL, tax id, or similar issuer identity are projected with empty value fields, a value hash, and an explicit redaction reason.

## Audit receipt

Each successful reveal persists a server-owned receipt under `settings.storage_dir` in the value-reveal receipt family. The receipt is idempotent by stable hashes of request id, sidecar receipt, dataset version, actor, fact inventory, and value inventory.

The audit receipt records:

- reveal receipt id/hash/ref
- actor hash only
- server time
- sidecar, dataset, parser, connector, source-artifact, and bridge lineage hashes
- fact count
- fact inventory hash
- value inventory hash
- redaction policy id
- negative invariant state

Audit receipt projections and committed artifacts contain hashes and counts only. Raw values appear only in the confirmed reveal response, transient UI render, and already-internal dataset materialization.

## Default surface boundary

The operator product surface remains the redacted inspection surface. Legacy in-surface `value_reveal_*` requests fail closed and direct operators to the sibling reveal endpoint. This prevents values from becoming a mode of the default product surface.

## Architecture boundary note

Live main implements reveal as a sibling endpoint/service, not as a value-returning mode of `operator_product_surface.py`. The operator product surface contains only a legacy compatibility detector for `value_reveal_*` request fields, and that path now checks `layer3_sec_edgar_arelle_value_reveal_enabled` first before failing closed to the sibling endpoint.

The standalone service `backend/app/services/layer3_sec_edgar_arelle_value_reveal.py` owns the persisted audit receipt, idempotent replay, lineage verification, and redacted status projection. Keeping reveal out of the default surface limits the blast radius if product-surface projection logic changes. The trade-off is that operators must use a separate explicit reveal call and correlate the audit receipt back to the redacted product surface. That is an intentional governance choice, not a defect. It can be revisited later if defense-in-depth or operator workflow evidence points to a better sibling-vs-surface boundary.

## Non-admissions preserved

- no default-on reveal
- no default-on Arelle cutover change
- no new Layer 3 source shape
- no bridge, Gate B, package, archive, or product decision redesign
- no synchronous Arelle invocation in request paths
- no final financial-statement semantics
- no cross-company comparability
- no Candidate B routing for SEC semantics
- no RAG, model, provider, auth, or mockup behavior
- no raw identity, URL, path, storage-root, or contact disclosure outside the governed value response

## Proof required

- flag-off reveal requests block with an explicit reason
- flag-on valid reveal returns effective values and resolved semantics for the bound filing
- audit receipt persists and replays idempotently for identical requests
- status projection for the audit receipt returns no raw values and no raw identity
- default product surface over the same filing returns no values
- legacy in-surface value reveal requests fail closed to the sibling endpoint
- identity-like fact values are redacted from reveal responses while preserving their value hash
- corrupted audit receipts fail closed when the stored hash no longer matches the receipt basis
- missing confirmation, missing actor, missing/invalid sidecar, missing/invalid dataset, lineage mismatch, forbidden request fields, and response-redaction violations are test-covered
- node syntax, Python compile, sidecar tests, bridge cutover tests, Layer 3 progress, and target-selection checks remain green

## Next slices

1. `sec_edgar_arelle_value_reveal_operator_exercise_v1`
   Validate the reveal workflow with operators against real persisted sidecar and dataset receipts before any deployment-wide reveal-flag enablement.

2. `sec_edgar_arelle_governance_remediation_followups_v1`
   Re-run the default-on decision only after the remediation evidence is reviewed: sidecar selection, product-path readiness, completeness aggregation, and CompanyFacts oracle coverage must be explicit and current.

3. `sec_edgar_arelle_value_reveal_default_enablement_gate_v1`
   Consider enabling the reveal flag only after audit-receipt review, redaction proof, operator utility evidence, and rollback posture are proven.
