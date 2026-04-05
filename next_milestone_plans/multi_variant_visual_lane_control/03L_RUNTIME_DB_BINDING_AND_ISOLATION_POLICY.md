# 03L Runtime DB Binding and Isolation Policy

## Verified live evidence

`backend/tests/test_review_nrc_aps_runtime_db.py` verifies:

- runtime DB session lookup by run
- binding/session correctness
- session closure behavior
- read-only behavior
- schema validation
- per-runtime session isolation

## Current policy

Runtime DB binding/discovery behavior is baseline-locked in the first integrated selector pass.

## Why

Even if selector changes are local to PDF visual-lane logic, review/runtime tooling depends on stable runtime bindings and safe per-runtime isolation.

## First-pass rule

Do not change:
- how a run resolves to a runtime binding,
- read-only expectations for runtime sessions,
- runtime DB schema expectations,
- per-runtime session isolation guarantees.

## Experimental policy

Experimental runs must remain out-of-band from default baseline runtime binding unless and until a later explicit decision reopens that scope.
