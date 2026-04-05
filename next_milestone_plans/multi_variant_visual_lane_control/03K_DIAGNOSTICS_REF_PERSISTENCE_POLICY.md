# 03K Diagnostics Ref Persistence Policy

## Verified live evidence

`backend/tests/test_diagnostics_ref_persistence.py` verifies:

1. diagnostics refs persist on both document and linkage rows
2. cross-run overwrite of a shared content/document row must not leak the wrong diagnostics ref into another run's serialization
3. absent linkage diagnostics ref must return `None`, not incorrectly fall back to a document-level value

## Current policy

Diagnostics-ref behavior is baseline-locked in the first integrated selector pass.

## Why

Selector introduction changes processing internals. If diagnostics-ref persistence semantics drift, downstream review/runtime tooling can become inconsistent even when the outward extraction contract appears unchanged.

## First-pass rule

Do not change:
- which surfaces persist diagnostics refs,
- how linkage-vs-document precedence works,
- cross-run safety behavior,
- serializer expectations around absent linkage diagnostics refs.

## Experimental policy

Experimental runs may generate diagnostics out-of-band, but must not silently alter baseline diagnostics-ref persistence semantics or baseline serializer expectations.
