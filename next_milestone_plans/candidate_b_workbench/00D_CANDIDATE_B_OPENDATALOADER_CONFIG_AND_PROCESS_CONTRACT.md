# 00D - Candidate B OpenDataLoader Config and Process Contract

## Purpose

Freeze the exact OpenDataLoader invocation/config/process contract for Candidate B v1.

Candidate B v1 is a **local Python-wrapper workbench comparator**.
It is not a CLI-subprocess lane, not a Node lane, not a Java/JAR lane, and not a hybrid lane.

v6 strengthens this doc by freezing more of the sensitive option surface,
adding batch-split rules,
and making output/image handling less implicit.

---

## A. Invocation method

Candidate B v1 must call OpenDataLoader via the Python wrapper only:
- `import opendataloader_pdf`
- `opendataloader_pdf.convert(...)`

Directly verified export/API posture from the exact `opendataloader-pdf==2.0.0` wheel inspected in this pass:
- `opendataloader_pdf.__all__ == ["run", "convert", "run_jar"]`
- `run(...)` is explicitly deprecated backward-compatibility surface only
- `run_jar(...)` exists but is not an approved v1 invocation path
- Candidate B v1 must use `convert(...)` only

Exact `convert(...)` signature posture verified from the wheel:
```python
convert(
    input_path,
    output_dir=None,
    password=None,
    format=None,
    quiet=False,
    content_safety_off=None,
    sanitize=False,
    keep_line_breaks=False,
    replace_invalid_chars=None,
    use_struct_tree=False,
    table_method=None,
    reading_order=None,
    markdown_page_separator=None,
    text_page_separator=None,
    html_page_separator=None,
    image_output=None,
    image_format=None,
    image_dir=None,
    pages=None,
    include_header_footer=False,
    hybrid=None,
    hybrid_mode=None,
    hybrid_url=None,
    hybrid_timeout=None,
    hybrid_fallback=True,
) -> None
```

No other invocation form is permitted in v1.

---

## B. Exact v1 config

Candidate B v1 must use exactly this logical config posture:

- `input_path=[<manifest-derived list of PDFs>]`
- `output_dir="tests/reports/nrc_aps_candidate_b_opendataloader_raw/<run_id>"`
- `format="json,markdown"`
- `quiet=False`
- `use_struct_tree=True`
- `reading_order="xycut"`
- `table_method="default"`
- `image_output="external"`
- `image_format="png"`
- `image_dir="tests/reports/nrc_aps_candidate_b_opendataloader_raw/<run_id>/images"`
- `include_header_footer=False`
- `keep_line_breaks=False`
- `replace_invalid_chars=" "`
- `pages` omitted unless a corpus amendment explicitly freezes a page subset
- `password` omitted unless the corpus manifest explicitly marks a password-protected control and the password-handling rule is frozen in the sidecar labels
- `content_safety_off` omitted so default safety filtering stays on
- `hybrid="off"`
- `hybrid_mode` omitted
- `hybrid_url` omitted
- `hybrid_timeout` omitted
- `hybrid_fallback` omitted

This is the only approved first-pass config.

---

## C. Process model

Because OpenDataLoader's Python path spawns the Java engine,
Candidate B v1 must prefer **batched multi-file conversion** rather than one process per file where practical.

Approved process model:
1. resolve the document list from the existing manifest-driven corpus
2. pass the whole list into one workbench conversion run when feasible
3. store all raw outputs under a single run-scoped output root
4. derive comparison summaries from those raw outputs afterward

### Controlled batch-split fallback
If one full-corpus batch fails for timeout/memory reasons,
a split is allowed only at whole-document boundaries.
The split plan must be recorded in the provenance block as:
- batch count
- file membership per batch
- reason for the split

Per-page cherry-picking is forbidden in v1.

---

## D. Struct-tree rule

`use_struct_tree=True` is mandatory in v1.

Reason:
Candidate B is explicitly meant to test a semantic/layout hypothesis.
If tagged PDFs exist in the corpus, Candidate B must actually exercise the tag-aware path.

If a document has no structure tree, the absence must be recorded in the Candidate B report.
It must not be silently treated as a success case for tag-aware extraction.

---

## E. Hybrid rule

Hybrid is forbidden in Candidate B v1.

That means:
- no `hybrid="docling-fast"`
- no `hybrid_mode="auto"` or `"full"`
- no backend URL
- no hybrid fallback path

If Candidate B only looks useful once hybrid is enabled,
then v1 has not proven its stated local-comparator hypothesis.

---

## F. Output rule

Candidate B v1 must generate:
- JSON outputs
- Markdown outputs

Candidate B v1 does **not** need HTML or PDF outputs for the first proof lane.
Those widen disk footprint without helping the primary comparison question.

Extracted images are allowed only under the approved run-scoped image directory.
They are comparison-support artifacts, not runtime outputs.

---

## G. Why this config is the right one

This config is the smallest one that tests:
- structure-tree usage
- semantic/layout extraction
- reading order
- table/list/heading handling
- image extraction references
- hidden-text filtering

without widening into hybrid or runtime integration.
