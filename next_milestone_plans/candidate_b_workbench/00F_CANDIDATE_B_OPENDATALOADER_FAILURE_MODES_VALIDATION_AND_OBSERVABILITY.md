# 00F — Candidate B OpenDataLoader Failure Modes, Validation, and Observability

## Purpose

Define what counts as failure,
what must be observed,
and what must force Candidate B v1 to stop.

v6 adds explicit stop conditions for execution-envelope drift and output-surface violations.

---

## A. Failure taxonomy

### Execution-envelope failures
- missing Java runtime
- wrong Python interpreter / wrong repo runtime target
- package version mismatch
- package hash mismatch when hash verification is in scope
- unsupported invocation mode

### Workbench failures
- ODL conversion failure on one or more corpus documents
- inability to write durable proof/compare artifacts
- inability to inventory raw outputs

### Comparison failures
- claims of value tied only to richer output that has no repo-equivalent significance
- mishandling of vector-control or OCR-control classes
- post-hoc label changes after results were seen

### Interference failures
- writes outside the approved output roots
- service-layer file edits
- backend dependency-surface edits
- `project6.ps1` edits
- changes to current lower-layer truth files in v1

---

## B. Validation gates

Candidate B v1 must pass all of these:
1. repo/runtime preflight
2. baseline lower-layer proof pass
3. Candidate B workbench proof run
4. allowed-surface touch check
5. baseline lower-layer proof re-run
6. final compare/decision review

---

## C. Observability requirements

Every Candidate B run must emit enough evidence to answer:
- which package/version/hash was executed
- which corpus files were processed
- which regime labels were applied before running
- where raw outputs were written
- whether any output escaped the approved roots
- whether baseline proof remained passing after Candidate B ran

---

## D. Exact stop / reject conditions

Stop or reject immediately if any of the following occurs:
- hybrid/docling/backend widening becomes required
- the package/version/hash posture cannot be made explicit
- output is written outside approved Candidate B roots
- current lower-layer proof fails before Candidate B starts
- current lower-layer proof fails after Candidate B runs
- current owner-path files are edited or relied on as mutable surfaces
- vector-heavy controls are reported as wins rather than limitations/non-equivalences
- OCR-owner-path outcomes are diluted or redefined

---

## E. Exact proceed criteria

Candidate B may proceed only if:
- the execution envelope is explicit and reproducible
- all outputs remain isolated
- all required reports exist with provenance
- the baseline proof remains passing before and after the Candidate B run
- reported gains are narrow, honest, and tied to allowed structural evidence classes

---

## F. Anti-overclaim rule

Candidate B may not claim “better parsing” as a general conclusion.
It may only claim evidence on the exact bounded dimensions documented in the crosswalk and comparison semantics docs.
