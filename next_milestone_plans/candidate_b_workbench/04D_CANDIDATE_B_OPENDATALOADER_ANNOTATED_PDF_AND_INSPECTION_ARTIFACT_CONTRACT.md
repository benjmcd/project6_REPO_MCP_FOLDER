# 04D - Candidate B OpenDataLoader Annotated PDF and Inspection Artifact Contract

## Purpose

Freeze the narrowest additive artifact contract for the separate Candidate B inspection surface.

Status note:

- this document froze the artifact posture before implementation
- the current branch code now requests and retains annotated PDF output and exposes it through the separate additive Candidate B Trace surface

This doc does **not** admit Candidate B into the normal review runtime model.
It defines how ODL-native inspection artifacts are retained and surfaced without pretending they are owner-path runtime artifacts.

---

## A. Hard current-state anchor

Current committed `main` already supports:

- Candidate B workbench execution through `tests/support_nrc_aps_candidate_b_opendataloader.py`
- Candidate B bundle generation through `tools/run_nrc_aps_candidate_b_compare.py`
- Candidate B compare consumption through `backend/app/services/review_nrc_aps_workbench_compare.py`

The current additive lane now:

- requests annotated PDF output from the ODL runner
- retains annotated PDF refs in `compare.json`
- exposes a Candidate B-specific inspection route and page
- adds Candidate B deep links alongside baseline and Candidate A trace links

---

## B. Package-capability evidence note

Repo authority for the installed package pin remains:

- `tests/requirements_nrc_aps_candidate_b_opendataloader.txt`

Local audit evidence on 2026-04-13 confirmed that the currently pinned `opendataloader-pdf==2.0.0` package exposes:

- CLI output format `pdf`
- wrapper semantics named `generate_annotated_pdf`

That evidence is operator-local rather than tracked repo authority.
Implementation-day preflight must revalidate that the installed pinned package still exposes that output mode before any code assumes annotated PDF availability.

---

## C. Frozen inspection-artifact decision

The first additive Candidate B inspection lane must treat annotated PDF output as:

- an ODL-native inspection artifact
- bundle-scoped
- fixture-scoped
- read-only
- non-equivalent to owner-path `visual_page_refs`

It must **not** be framed as:

- a replacement for current baseline/Candidate A visual artifacts
- proof that Candidate B should be admitted into `visual_lane_mode`
- a reason to widen the current document-trace contract

---

## D. Canonical retained path contract

For a run root:

- `tests/reports/cb-compare-<run_id>/`

the canonical annotated PDF path must be:

- `tests/reports/cb-compare-<run_id>/raw/annotated/<fixture_id>.pdf`

Hard rules:

- do not rely on the raw external package default filename as a durable repo contract
- if ODL emits a differently named PDF, the support harness must canonicalize it into the stable path above
- do not write annotated PDFs into runtime storage roots, fixture source roots, or API-facing persisted namespaces

---

## E. Compare-report field contract

For each `documents[*].candidate_b` entry in `compare.json`, the inspection lane adds:

- `annotated_pdf_ref`
- `annotated_pdf_sha256`
- `annotated_pdf_status`

Field semantics:

- `annotated_pdf_ref`
  - repo-relative POSIX-style path
  - null when unavailable
- `annotated_pdf_sha256`
  - SHA256 of the canonicalized annotated PDF
  - null when unavailable
- `annotated_pdf_status`
  - exact first-pass values:
    - `present`
    - `missing`

Existing raw artifact refs remain in place:

- `raw_json_ref`
- `raw_json_sha256`
- `raw_markdown_ref`
- `raw_markdown_sha256`

Do not nest these under a new composite object in the first pass.
Keeping them flat is the narrower change because the current compare bundle and compare service already consume the existing flat fields.

---

## F. Inspection-surface read contract

The Candidate B inspection service may read only:

- validated bundle metadata from:
  - `compare.json`
  - `proof.json`
  - `retain.json`
- validated raw artifacts referenced by those bundle payloads

It must not:

- accept arbitrary raw artifact paths from the browser
- infer fixture paths from document titles
- walk raw directories client-side

All file reads must remain:

- bundle-scoped
- fixture-scoped
- validated against the exact discovered bundle root

---

## G. Retention and provenance posture

Annotated PDFs remain document-derived content.

Default rule:

- retain them under the approved run-scoped raw root
- do not commit them by default
- hash them in the retention manifest

Any decision to commit annotated PDFs into tracked history requires a separate explicit approval.
That decision is not implied by the inspection lane itself.

---

## H. Fail-closed rules

The first inspection lane must fail closed if any of the following occur:

- the pinned package no longer exposes annotated PDF output capability at preflight time
- the canonicalized `raw/annotated/<fixture_id>.pdf` file is missing after a run that requested it
- `compare.json` carries an annotated PDF ref outside the validated run root
- the browser requests a fixture not present in the validated bundle
- the browser requests a bundle id that does not resolve to an exact discovered allowlisted bundle root

Unavailable annotated PDF output should surface as explicit unavailability,
not as a silent fallback to the baseline/Candidate A document-trace model.
