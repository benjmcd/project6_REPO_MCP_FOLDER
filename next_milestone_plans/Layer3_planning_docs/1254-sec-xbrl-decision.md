# SEC XBRL Adapter Decision

```yaml
milestone: sec_edgar_xbrl_processor_adapter_and_source_fidelity_assessment_v1_part2
decision: hybrid_arelle_extraction_companyfacts_crosscheck_existing_repo_spine
recommended_next_target: sec_edgar_arelle_resolved_fact_authority_sidecar_v1
supersedes_selected_posture: sec_edgar_statement_role_quality_profile_rendered_detail_ui_v1
runtime_mutation_performed: false
api_ui_gate_b_product_mutation_performed: false
parser_expansion_performed: false
adapter_runtime_implemented: false
adr_written: true
```

## Inputs

This decision consumes the real-corpus measurement from `49731e2b`:

```text
10-K: 438/643 production-vs-Arelle facts
8-K: 23/23
20-F: 2019/5000 plus fact-material bridge mismatch
6-K: 0/0, no inline XBRL markers
40-F: 43/43
6-K: 0/0, no inline XBRL markers
headline: POOR, 2523/5709 Arelle facts captured
```

## Decision

Use Arelle extraction as a standards-aware sidecar resolved-fact authority, keep SEC CompanyFacts as an accession-scoped standardized cross-check, and preserve the existing repo spine for governed acquisition, retained bytes, redaction, package/review/handoff, archive, and operator inspection.

Do not continue rendered semantic-profile detail work before the sidecar extraction slice. Do not attempt custom-only hardening as the primary path.

## Platform Fit

The sidecar does not create a new Layer 3 source shape. It emits a governed resolved-fact authority receipt that Layer 3 consumes through existing `dataset_version` materialization for typed fact rows. Any SEC-only source shape should be treated as debt unless a later operator/product review proves it is necessary.

## First Implementation Slice

Target:

```text
sec_edgar_arelle_resolved_fact_authority_sidecar_v1
```

Scope:

```text
1. Read retained SEC source-artifact bytes by existing receipt authority.
2. Run Arelle in an isolated subprocess with cache/config outside the repo and synced workspace.
3. Emit redacted resolved-fact authority JSON and sidecar receipt.
4. Compare resolved count against current regex fact authority.
5. Record CompanyFacts accession cross-check for standardized us-gaap/dei facts.
6. Do not mutate Layer 3 product, Gate B, package, API, UI, or default runtime scope.
```

Proof:

```text
10-K coverage moves toward 643 Arelle facts.
20-F coverage moves toward 5000 Arelle facts and no longer depends on regex reconstruction.
8-K and 40-F remain at parity.
Raw values, URLs, paths, storage roots, tickers, accessions, and source bytes are not exposed.
l3-progress-check.py remains PASS.
l3-target-selection-validate.py --expect frozen remains PASS.
```

Non-goals:

```text
final financial-statement semantics
cross-company comparability
Candidate B routing for SEC
runtime product/package/Gate B/API/UI changes
RAG/model/provider/auth behavior
external code copied into repo
```

## Artifacts

```text
diagnostics/assessment/sec-xbrl-design.md
diagnostics/assessment/sec-xbrl-adr.md
diagnostics/assessment/sec-xbrl-report.json
diagnostics/assessment/sec-xbrl-corpus.json
```

## Stop Posture

Stop after this decision pass. The next pass may implement only the bounded sidecar slice if explicitly authorized.
