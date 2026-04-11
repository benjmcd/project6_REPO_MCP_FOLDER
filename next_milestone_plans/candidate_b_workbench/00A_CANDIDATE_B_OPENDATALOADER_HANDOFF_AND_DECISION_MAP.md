# 00A - Candidate B OpenDataLoader Handoff and Decision Map

## Purpose

State the exact decision this frozen pack is meant to support.

This pack does not decide whether OpenDataLoader is globally better than PyMuPDF.
It decides only whether a repo-aligned, workbench-only, non-interfering Candidate B comparator is justified against the current merged baseline.

## Hard starting point

Candidate B starts from these already-closed truths:
- the live integrated owner path remains PyMuPDF-based through `backend/app/services/nrc_aps_document_processing.py`
- `baseline` remains the default posture under `05P` and `05Q`
- `candidate_a_page_evidence_v1` remains the only admitted non-`baseline` value
- the PageEvidence Lane Class A work is closed, Pass 1 is complete, and Pass 2 is not needed on the current merged baseline
- the current tests still enforce preserve-ref behavior, non-fatal visual-capture failure, and OCR fail-closed strictness

Candidate B therefore cannot be a silent owner-path rewrite.
It can only be a side-by-side comparator over the current merged baseline.

## Exact Candidate B hypothesis

OpenDataLoader may provide useful comparison evidence on questions the current merged baseline does not optimize for directly, especially:
- tagged-PDF structure recovery
- heading/list/table visibility
- multi-column reading-order evidence
- hidden-text or layout-noise visibility

Candidate B does not hypothesize superiority on:
- preserve-lane ownership
- OCR strictness ownership
- runtime selector behavior
- outward artifact or reference semantics
- review, report, export, or API identity surfaces

## Why Candidate B should exist at all

The merged baseline is now stable enough that Candidate B can be evaluated honestly without widening runtime surfaces.
The lower-layer proof harness already exists, the admitted Candidate A path is already bounded, and the pinned Candidate A artifact already exists as a secondary comparison anchor.

The value of the experiment is not "adopt OpenDataLoader no matter what."
It is: determine whether OpenDataLoader adds narrow structural evidence that is useful enough to justify a later, separately frozen objective.

## Decision this pack supports

After a future Candidate B proof pass, the only allowed decisions are:
- `proceed_as_documented_workbench`
- `iterate_pack_then_retry`
- `reject_or_defer`
- `escalate_to_new_frozen_objective`

This pack does not authorize:
- runtime selector admission
- service-layer integration
- backend dependency widening
- hybrid or generic candidate framework adoption
- changes to current owner-path semantics

## Success standard

Candidate B succeeds only if all of the following are true:
- it runs within the frozen workbench-only execution envelope
- it produces the required proof, compare, and provenance artifacts
- it stays inside the approved tests/report-only touch surface
- it preserves lower-layer and admitted Candidate A non-interference
- any reported value is tied to allowed gain classes rather than to non-equivalent richer output alone
