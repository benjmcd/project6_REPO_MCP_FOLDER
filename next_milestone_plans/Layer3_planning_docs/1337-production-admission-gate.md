# 1337 SEC XBRL production admission gate

Target: `sec_xbrl_production_admission_gate_v1`.

This slice adds an explicit validate-only gate for the final Layer 3 SEC XBRL
production-admission decision. It does not admit production. It defines what
must be proven before a later human/release decision can even review production
admission.

## Gate inputs

The gate accepts only hash/count/state evidence:

- offline evidence proof capability;
- single-transaction persistence proof;
- redaction containment proof;
- multi-filing evidence authority matrix;
- operator API contract gate;
- operator authority resolver gate;
- operator UI controls gate;
- controlled value reveal gate;
- rollback and monitoring gate;
- runbook gate;
- targeted validation gate.

Raw storage payloads, CompanyFacts payloads, local paths, SEC URLs, accessions,
raw values, and raw resolved-fact identifiers are not admitted as public gate
evidence.

## Current implementation

The service `layer3_sec_xbrl_production_admission_gate.py` returns:

- `layer3_sec_xbrl_production_admission_blocked` until every required gate is
  proven;
- `layer3_sec_xbrl_production_admission_review_ready` only when every required
  gate is proven;
- `production_admission_admitted=false` in all cases.

The gate is intentionally a review-readiness surface, not a production switch.
It leaves runtime defaults, API route enablement, rendered UI enablement, value
reveal, and production database mutation disabled.

A separate production release decision gate must bind to this gate's
`admission_basis_hash` before any controlled release decision can be considered
review-ready. Admission review readiness is therefore necessary but not
sufficient for release.

## Why this matters

The previous slices could prove local capability and transaction-safety
progress, but they did not provide a single place where readiness claims were
forced to account for all critical requirements. This gate prevents the project
from using a narrow proof, such as one FIZZ 10-K run or one atomic rollback test,
as a broad production-readiness claim.

## Remaining required evidence

- Validate the atomic offline orchestrator and proof-capability tests.
- Run the FIZZ 10-K proof-capability diagnostic through the atomic path.
- Repair FIZZ 10-Q and CCJ 10-K evidence authority and produce a multi-filing matrix.
- Freeze and implement the operator API contract through the atomic service.
- Prove the operator authority resolver maps only server-owned handles to ready
  multi-filing authority evidence and fails closed for unknown/raw references.
- Build UI controls against the admitted API surface.
- Prove controlled value reveal authorization and redaction behavior.
- Add rollback and monitoring evidence for production operations.
- Add runbooks for failed diagnostics, rollback, reveal incidents, and admission
  denial.
- Run targeted validation and full relevant SEC XBRL regression coverage.

Only after those items have direct evidence should the production-admission gate
report review-ready. Even then, this gate still does not turn on production; it
only supports a separate release decision.
