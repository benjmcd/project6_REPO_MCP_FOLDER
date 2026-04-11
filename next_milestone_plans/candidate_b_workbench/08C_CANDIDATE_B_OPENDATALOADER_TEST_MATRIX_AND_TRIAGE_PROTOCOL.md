# 08C — Candidate B OpenDataLoader Test Matrix and Triage Protocol

## Purpose

Define the exact failure buckets and triage order for Candidate B v1.

v6 adds explicit non-interference and execution-envelope buckets.

---

## A. Mandatory test families

1. environment / package preflight checks
2. corpus-resolution and label-freeze checks
3. Candidate B proof generation checks
4. Candidate B compare-report checks
5. output-root isolation checks
6. baseline re-proof / non-interference checks

---

## B. Failure buckets

### Bucket 1 — execution-envelope failure
- wrong Python / Java / package / invocation posture

### Bucket 2 — proof generation failure
- Candidate B cannot process one or more required corpus documents

### Bucket 3 — report/provenance failure
- required reports exist but are missing required provenance or retention data

### Bucket 4 — comparison semantics failure
- claimed gains are tied to non-equivalent richer output only
- vector or OCR controls are misreported as wins

### Bucket 5 — interference failure
- files outside the approved allowlist were touched
- outputs escaped the approved roots
- baseline proof no longer passes after Candidate B work

---

## C. Stop rules

Immediate stop on:
- Bucket 1
- Bucket 5

Bucket 2–4 may allow docs-only iteration only if the touch policy and baseline non-interference remain intact.

---

## D. Triage order

1. execution envelope
2. output isolation
3. baseline proof health
4. proof artifact completeness
5. comparison semantics
6. optional reviewer ergonomics / report polish
