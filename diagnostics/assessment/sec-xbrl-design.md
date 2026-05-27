# SEC XBRL Adapter Platform-Fit Design

```yaml
scope: no_runtime_design
input_measurement_commit: 49731e2b
strategy_a_status: committed_but_requires_trustworthy_extraction_adapter
strategy_b_status: deferred_for_final_semantics_and_comparability
runtime_mutation: false
api_ui_gate_b_product_mutation: false
parser_expansion: false
candidate_b_sec_routing: false
final_financial_statement_semantics: false
cross_company_comparability: false
```

## Measurement Basis

Real corpus measurement:

| form | production fact authority | Arelle facts | result |
| --- | ---: | ---: | --- |
| 10-K | 438 | 643 | missed 205 facts |
| 8-K | 23 | 23 | matched |
| 20-F | 2019 | 5000 | missed 2981 facts; fact-material bridge blocked |
| 6-K | 0 | 0 | no inline XBRL markers |
| 40-F | 43 | 43 | matched |
| 6-K | 0 | 0 | no inline XBRL markers |

Headline: production fact-authority coverage captured `2523/5709` Arelle facts across real filings. The misses are structural: hidden facts, continuations, unsupported marker shapes, unresolved contexts/units, and the text segment inventory cap. This falsifies custom regex extraction as adequate for flagship 10-K and 20-F product coverage.

## Options

| option | correctness against measured misses | product effect | cost/risk | tech debt if chosen/deferred |
| --- | --- | --- | --- | --- |
| A. Custom-only hardening | Could patch specific regex misses, but must reimplement iXBRL hidden facts, continuations, namespace variation, tuple/footnote edge cases, contexts, units, and dimensions. | Does not reliably fix the 10-K undercount or 20-F bridge mismatch without recreating a standards processor. | Low dependency cost, high correctness cost, high regression surface. | High. Every filing variation becomes repo-native parser debt. |
| B. Arelle validation-only | Detects divergence and can fail closed, but does not provide the missing fact inventory. | Does not fix product coverage; 10-K still has missing facts and 20-F still cannot bridge unless extraction changes. | Moderate dependency/CI cost, low product gain. | Medium-high. Useful as guardrail but inadequate as the product authority. |
| C. Arelle extraction | Extracts the same fact model used for the gold counts, including hidden/continued facts and resolved context/unit metadata where available. | Directly addresses 10-K undercount and 20-F fact-count mismatch by making product fact inventory come from resolved extraction. | Higher dependency/runtime cost; needs subprocess isolation, timeouts, cache control, Windows path discipline, and redaction. | Low if bounded as sidecar authority; medium if it mutates Layer 3 directly. |
| D. CompanyFacts-only | Good standardized us-gaap/dei accession cross-check, but incomplete for filing-level inventory, foreign forms, extensions, presentation order, nonstandard facts, and per-filing source fidelity. | Cannot fix 20-F coverage and cannot replace retained filing extraction. | Low dependency cost, network/rate policy cost. | High if treated as replacement; low if diagnostic cross-check. |
| E. Hybrid: Arelle extraction plus CompanyFacts cross-check plus existing repo spine | Arelle supplies resolved retained-filing facts; CompanyFacts cross-checks standardized facts by accession; repo spine keeps acquisition, receipts, redaction, package/review/handoff. | Fixes product fact coverage while preserving Layer 3 authority and honest non-admissions. | Highest initial integration cost, but narrowest long-term debt. | Lowest. Standards-aware extraction is isolated and Layer 3 contracts remain stable. |

Recommendation: choose E, implemented as C first with D as a bounded diagnostic cross-check. Validation-only is not enough because it does not repair product coverage. Custom-only is disproven by the measured 10-K and 20-F failures.

## Platform Fit

The adapter must not create a SEC-only Layer 3 source shape. It should create a governed upstream `resolved_fact_authority` sidecar receipt, then feed existing Layer 3 materialization through `dataset_version` for typed fact rows.

Mapping:

| existing contract | fit |
| --- | --- |
| source artifact authority | Input is already-retained complete-submission source bytes and existing live-source-artifact receipt hashes. |
| parser/source family | Arelle adapter is a standards-aware processor family over retained SEC HTML/iXBRL primary documents. |
| `dataset_version` source shape | Reuse for resolved fact inventory rows, variables, concepts, context hashes, unit hashes, period fields, dimension/member hashes, source-order fields, and provenance columns. |
| `aps_content_document` source shape | Not used for fact rows. SEC narrative/document evidence can remain a separate document path if admitted later. |
| material preview / Gate B | Consume the materialized resolved-fact `dataset_version`; do not mutate Gate B or invent a SEC-specific material source. |
| package/review/handoff | Continue consuming the existing product/package spine after resolved facts become the fact authority input. |

Architecture quality bar:

- Modularity: subprocess adapter is separate from acquisition, current parser, fact material bridge, and product/package surfaces.
- Scalability: future standards processors can be added behind the same sidecar receipt contract.
- Fail-closed: unsupported filings, Arelle failures, count divergence, timeout, cache/network violations, and redaction failures block with diagnostics.
- Provenance stability: every emitted fact carries source-artifact receipt hash, primary-document hash, adapter receipt hash, concept, context/unit hashes, source order, and normalized source-family metadata.
- Backward compatibility: existing regex fact-authority remains readable and can be compared, but should not remain production extraction authority for admitted real iXBRL products.
- Bounded growth: first slice is extraction sidecar plus parity report only; no UI, package, Gate B, final semantics, or comparability.

SEC-only divergence to avoid: a new `sec_xbrl_fact_source` Layer 3 source shape would duplicate `dataset_version` tabular authority and make downstream packages SEC-specific. Treat that as debt unless a later operator review proves `dataset_version` cannot carry the resolved fact rows.

## Adapter Boundary

Input authority:

- existing connector receipt hash;
- existing live-source-artifact receipt id/hash;
- retained source artifact bytes read server-side;
- parser primary-document identity/hash where already available;
- no caller-provided paths, URLs, source bytes, or frontend authority.

Execution boundary:

- subprocess or CLI, not in-process mutation;
- cache/config directory outside the repo and synced workspace for local runs;
- no committed Arelle cache or extracted raw source;
- bounded timeout, memory/process kill policy, and max emitted facts;
- no direct Layer 3 mutation.

Output JSON contract:

- schema id and version;
- adapter mode and Arelle version hash;
- input authority hashes;
- resolved fact count;
- per-fact records with value hash/length only, not raw values;
- concept QName, namespace/prefix/local name;
- context id hash, unit id hash, period profile, decimals/precision/scale;
- dimension/member hash profiles;
- source order and source span hash if available;
- hidden/continued/standard/extension/unclassified flags;
- diagnostics for unsupported tuples, footnotes, continuations, duplicate/conflicting facts, and extraction warnings;
- stable `resolved_fact_authority_hash`.

Receipt model:

- sidecar receipt stored under settings storage;
- redacted response only;
- idempotent by input authority hash plus adapter version plus output hash;
- status endpoint later may expose counts/hashes/diagnostics only.

Migration:

- Arelle extraction should replace production fact extraction for admitted real iXBRL fact authority.
- Current custom regex output should remain as a comparison/diagnostic during migration, not as backfill authority.
- Backfilling only missed facts would leave two competing extraction sources and preserve the 20-F parity hazard.

20-F bridge mismatch resolution:

- The fact material bridge should consume the Arelle resolved-fact authority as the single fact inventory.
- Its reconstruction/parity check should compare against the resolved authority count and hash, not independently reconstruct with the regex pattern.
- The measured 20-F mismatch is therefore resolved by replacing extraction authority, not by weakening the bridge.

## First Slice

Target: `sec_edgar_arelle_resolved_fact_authority_sidecar_v1`

Scope:

- Add no-runtime design-to-runtime entry only when this ADR is accepted.
- Implement a subprocess Arelle extraction sidecar over retained source bytes.
- Emit redacted resolved-fact authority receipt and parity diagnostics against current regex authority.
- Run on the measured corpus and one expanded validation corpus.

Proof:

- 10-K coverage improves from 438/643 to near Arelle parity.
- 20-F emits a resolved-fact authority count near 5000 and no longer depends on regex reconstruction.
- 8-K and 40-F remain matched.
- CompanyFacts cross-check remains diagnostic and accession-scoped.
- All existing negative invariants remain false.

Non-goals:

- no final statement semantics;
- no cross-company comparability;
- no rendered UI;
- no Gate B/product/package mutation in first slice;
- no Candidate B routing;
- no raw values, URLs, paths, storage roots, or source bytes in committed artifacts.
