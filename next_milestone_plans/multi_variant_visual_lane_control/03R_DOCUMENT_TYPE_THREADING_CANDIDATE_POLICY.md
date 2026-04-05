# 03R `document_type` Threading Candidate Policy

## Purpose

Record the current state of the `document_type` hypothesis without falsely promoting it to frozen selector design.

## Session-origin evidence

The attached session provides repo-grounded evidence that:

1. `_process_pdf(...)` consults `config.get("document_type")` in an advanced-document routing area.
2. A meaningful upstream `document_type` signal may already exist in source/reference material.
3. That signal may not yet be fully threaded into the processing-config path that reaches `process_document(...)`.

## Current status

### What is attractive about this candidate
- It suggests a more repo-native activation/control surface than inventing a totally foreign key.
- It may already align with document-routing logic rather than only with visual-lane logic.
- It could reduce the amount of selector-specific plumbing needed later.

### What is still not closed
- exact live threading path in the current execution context
- exact upstream source of truth
- whether this should remain a document-routing signal rather than become a selector signal
- whether using it for variant activation would over-couple two separate concerns

## Current policy

Treat `document_type` as:
- a **candidate activation surface**
- worthy of re-verification
- but **not** the frozen selector key
- and not a justification for skipping explicit selector activation design

## First-pass caution

If `document_type` is later used in any selector design, the project must still separately freeze:
- activation scope/lifetime
- OCR-vs-visual boundary
- experiment isolation behavior

`document_type` cannot replace those freezes.
