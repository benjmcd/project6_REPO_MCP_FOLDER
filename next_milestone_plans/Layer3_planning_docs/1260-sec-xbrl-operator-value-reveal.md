# 1260 - SEC XBRL Operator Value Reveal

## Target

`sec_edgar_arelle_operator_surface_gated_value_reveal_v1`

## Governing posture

This is Option 2, operator-surface gated reveal. It exposes a capped sample of already-materialized Arelle effective values from existing `dataset_version` rows. It does not acquire filings, run Arelle, change the bridge authority input, alter Gate B decisions, redesign product/package surfaces, or enable any default-on SEC behavior.

The reveal is explicit, receipt-bound, and reversible:

- caller must request `sec_edgar_operator_surface_gated_value_reveal_v1`
- caller must set the confirmation field
- response is capped to the admitted maximum
- source identity, URLs, local paths, accessions, tickers, storage roots, and provider fields remain redacted
- final financial-statement semantics and cross-company comparability remain non-admitted

## Reveal scope

The first admitted surface scope is intentionally narrow:

- standard `us-gaap` / `dei` numeric facts only
- non-dimensional rows only
- Arelle cutover bridge receipts only
- values read from the persisted bridge `dataset_version`, not by synchronously invoking Arelle
- effective canonical values only; lexical raw values remain hidden behind hashes and lengths

Extension, dimensional, non-numeric, and statement-assembled values are deferred until their operator use and disclosure policy are proven.

## Retention and lifecycle

The operator product-surface receipt can contain the capped governed value reveal when the operator explicitly requests it. That receipt is a value-bearing operator artifact and its lifecycle is tied to the operator product-surface receipt. The broader internal value store remains tied to the Arelle sidecar receipt, as documented in `1259-sec-xbrl-governed-value-reveal.md`.

No committed report or planning artifact may contain real issuer identity, raw SEC URLs, local paths, storage roots, accessions, tickers, or uncapped corpus values.

## Non-admissions preserved

- no default-on Arelle cutover
- no new Layer 3 source shape
- no bridge, Gate B, package, archive, or product decision redesign
- no final financial-statement semantics
- no cross-company comparability
- no Candidate B routing for SEC semantics
- no RAG, model, provider, auth, or mockup behavior

## Proof required

- flag-off/no-request path returns no values
- explicit reveal request returns only the capped standard numeric non-dimensional sample
- revealed value uses Arelle effective canonical semantics
- lexical value remains hidden except for hash/length
- namespace and source identity are hashed or categorized, not exposed as raw URLs or paths
- existing bridge cutover tests remain green
- standard Layer 3 progress and target-selection checks remain green

## Next slice

`sec_edgar_arelle_default_on_corpus_expansion_gate_v1`

Before any default-on cutover, expand the real filing corpus and re-run extraction, CompanyFacts correctness, redaction, and operator utility proof across heterogeneous 10-K, 10-Q, 20-F/40-F, 8-K, and extension-heavy filings.
