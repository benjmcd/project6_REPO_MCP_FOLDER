# 00A — Candidate B OpenDataLoader Handoff and Decision Map

## Purpose

State the exact decision v6 is meant to support.

v6 is not deciding whether OpenDataLoader is “better than PyMuPDF” in the abstract.
It is deciding whether a **repo-aligned, workbench-only, non-interfering Candidate B comparator** should be opened against the current lower-layer NRC APS proof lane.

Scope note:
- this decision map governs the original Candidate B comparator decision only
- it does not supersede the separately reopened additive `Candidate B Trace` follow-on frozen later in this pack
- that follow-on still does not imply runtime admission or owner-path replacement

---

## Hard starting point

Candidate B starts from these already-frozen truths:
- the repo’s live lower-layer owner path is still PyMuPDF-based
- the lower-layer proof lane is already manifest-driven and named in the root README
- `nrc_aps_document_processing.py` still defines the owner-path classification / OCR / preserve-lane semantics
- `nrc_aps_artifact_ingestion.py` still forwards `process_document(...)` output into the wider ingestion path
- the current tests still enforce preserve-ref behavior, non-fatal visual-capture failure, and OCR fail-closed strictness

So Candidate B v1 cannot be a silent owner-path rewrite.
It can only be a **side-by-side comparator over the current proof harness**.

---

## Exact Candidate B v1 hypothesis

OpenDataLoader may provide useful comparison evidence on a bounded subset of questions that the current owner path does not optimize for directly, especially:
- tagged-PDF structure recovery
- heading/list/table visibility
- multi-column reading order evidence
- hidden-text/noise visibility

Candidate B v1 does **not** hypothesize superiority on:
- vector-driven visual significance
- preserve-lane ownership
- OCR strictness ownership
- outward artifact/ref semantics
- runtime NRC APS integration

---

## Why Candidate B should exist at all

Because the repo already exposes a lower-layer proof harness, Candidate B can be tested cheaply and honestly without widening runtime surfaces.
That makes it a valid comparison candidate even if it never becomes integrated.

The value of the experiment is therefore not “adopt OpenDataLoader no matter what.”
It is: determine whether OpenDataLoader adds narrow structural evidence that is useful enough to justify a later, separately frozen lane.

---

## Decision this pack supports

After the v6 proof sequence, the only allowed decisions are:
- `proceed_as_documented_workbench`
- `iterate_docs_only`
- `reject_or_defer`

No stronger decision is supported by v6.
In particular, v6 does **not** authorize:
- runtime selector admission
- `backend/requirements.txt` widening
- service-layer integration
- hybrid/docling adoption
- changes to current owner-path semantics

---

## Success standard for Candidate B v1

Candidate B v1 succeeds only if all of the following are true:
- it runs within the frozen execution envelope
- it produces the required workbench artifacts and provenance
- it stays within the allowed tests/report-only touch surface
- it preserves current lower-layer non-interference
- its reported value is tied to allowed gain classes and not to non-equivalent richer output alone

Anything weaker than that is not a real success.
