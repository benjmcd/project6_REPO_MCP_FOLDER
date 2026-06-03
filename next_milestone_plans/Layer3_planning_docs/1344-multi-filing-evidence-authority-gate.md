# 1344 SEC XBRL multi-filing evidence authority gate

Target: `sec_xbrl_multi_filing_evidence_authority_gate_v1`.

This slice defines the validate-only multi-filing evidence authority gate. It
does not repair filings, read operator storage, acquire sources, invoke Arelle,
persist production rows, or claim production readiness.

## Purpose

The offline proof path currently has credible evidence for the FIZZ 10-K path,
but FIZZ 10-Q and CCJ authority remain blocked by missing or incomplete
authority metadata. A production-admission path must not treat one clean filing
as broad evidence authority.

The gate therefore requires a redacted evidence matrix with the named S1 filing
scope ready before production-admission review can treat multi-filing authority as
satisfied. Three arbitrary ready filings are not sufficient.

## Required S1 filing scope

The default required filing handles are:

- `fizz-10k-proof`;
- `fizz-10q-proof`;
- `ccj-10k-proof`.

The gate must fail closed when any required handle is missing or blocked, even if
the input contains three other ready-looking filings.

## Required ready filing evidence

Each ready filing entry must provide hash-only authority handles:

- `proof_source_report_hash`;
- `proof_result_hash`;
- `sidecar_receipt_hash`;
- `value_store_hash`;
- `companyfacts_payload_hash`.

Each ready filing must prove:

- operator evidence files were read;
- single-transaction persistence was claimed by the proof;
- redaction containment passed;
- public evidence is hash/count/state-only.

Each ready filing must also prove the negative invariants:

- raw evidence was not committed;
- raw CompanyFacts was not committed;
- raw storage was not committed;
- source acquisition was not performed;
- Arelle was not invoked;
- network was not performed;
- value reveal was not performed;
- production database was not touched;
- production readiness was not claimed.

## Current blocked posture

The expected current matrix is:

- FIZZ 10-K: can become ready after the atomic proof diagnostic is run and
  redacted proof evidence is recorded;
- FIZZ 10-Q: blocked until authority metadata is repaired;
- CCJ 10-K: blocked until authority metadata and sidecar evidence are repaired.

This is intentional. The gate should make the blocked status explicit rather
than hiding it behind a narrative roadmap.

## Production-admission relationship

The production-admission gate expects this gate's ready response as
`evidence_authority_matrix`. It requires:

- `status=sec_xbrl_multi_filing_evidence_authority_ready`;
- `ready=true`;
- `ready_filing_count` at or above the admission threshold;
- every required S1 filing handle ready;
- `raw_evidence_committed=false`.

Even when this gate is ready, it still reports:

- `validate_only=true`;
- `source_acquisition_performed=false`;
- `arelle_invoked=false`;
- `network_performed=false`;
- `value_reveal_performed=false`;
- `production_database_touched=false`;
- `production_readiness_claimed=false`.

This prevents overclaiming while keeping the real-evidence milestone explicit.
