# Visual-Content Canonical Downstream Contract Analysis

## Context

Analysis pass to determine the smallest correct canonical downstream contract for preserve-eligible visual content. All upstream lanes through DB persistence + API exposure are completed and frozen. The question is whether the current representation is adequate for practical visual-content recovery, and what the correct next contract should be.

---

## 1. TASK INTERPRETATION

1. **Interpretation:** Determine whether the current `visual_page_refs` contract — combined with coexisting blob/linkage references — constitutes a practically recoverable visual-content representation, or whether materialized visual artifacts are needed.
2. **Key assumptions:** Upstream lanes frozen. `visual_page_refs` persists to DB and is API-exposed. `blob_ref` is a stable path to the original PDF.
3. **Decision:** Choose between metadata-only recovery, reference-carrying, artifact-carrying, or hybrid contract.
4. **Evidence path:** Static inspection of visual_page_refs shape, blob storage pattern, API response shape, existing artifact patterns.

---

## 2. LIVE CURRENTNESS SNAPSHOT

| File | Modified | SHA256 prefix | Lines |
|------|----------|---------------|-------|
| `nrc_aps_document_processing.py` | 2026-03-24T13:43:38 | `15c2899e` | 962 |
| `connectors_nrc_adams.py` | 2026-03-24T16:22:33 | `d999f212` | 3633 |
| `nrc_aps_artifact_ingestion.py` | 2026-03-21T22:33:00 | `ac5b38d7` | 599 |
| `nrc_aps_content_index.py` | 2026-03-24T17:01:04 | `ae1de381` | 1095 |
| `models.py` | 2026-03-24T17:00:32 | `d91cd34f` | 687 |
| `api.py` | 2026-03-24T17:01:18 | `13330f21` | 1060 |

All scoped service files: py_compile OK

**Q1: Completed lanes current?** YES
**Q2: Any regression?** NO

---

## 3. CURRENT SEMANTIC CONTRACT EXTRACTION

| Layer | Current representation meaning/shape | Evidence |
|-------|--------------------------------------|----------|
| Document processing | `_capture_visual_page_ref()` returns `{page_number, visual_page_class, status, width, height}` — pure page-level metadata. No image file, no artifact ref, no rendering parameters. | doc_processing.py:85-95 |
| Connector handoff | Passed through unchanged via `.get("visual_page_refs", [])`. Blob ref carried separately in `download.blob_ref`. | connectors_nrc_adams.py:2618, 2657 |
| Content-index payload | Defensive-copied list of dicts at `payload["visual_page_refs"]`. Blob ref at `payload["blob_ref"]`. Both in same payload. | content_index.py:542, 536 |
| DB persistence | `ApsContentDocument.visual_page_refs_json` (Text column, JSON-serialized list). `ApsContentLinkage.blob_ref` (String, absolute filesystem path to original PDF). Both in DB. | models.py:547, 603 |
| API exposure | `ConnectorRunContentUnitOut.visual_page_refs: list[dict]` and `.blob_ref: str | None` coexist in same response. | api.py:451, 460 |

**Key observation:** `visual_page_refs` is a **metadata-only page annotation**. The actual visual content is not materialized anywhere. However, `blob_ref` (stable path to original PDF) coexists in the same API response, making theoretical recovery possible.

---

## 4. RECOVERABILITY PATH ANALYSIS

| Recoverability element | Present now? | Evidence | Adequate for practical downstream use? | Quality-preserving? |
|------------------------|-------------|----------|---------------------------------------|---------------------|
| Original PDF blob | YES — `blob_ref` in ApsContentLinkage + API | models.py:603, api.py:451 | YES — blob is content-addressed, no cleanup/expiry | YES — original PDF preserved byte-for-byte |
| Page number of visual pages | YES — `visual_page_refs[].page_number` | doc_processing.py:90 | YES — identifies exact page | N/A |
| Page dimensions | YES — `width`, `height` in visual_page_refs | doc_processing.py:93-94 | PARTIAL — useful for rendering but not sufficient alone | N/A |
| Rendering DPI / format parameters | **NO** — not stored anywhere | Absent from visual_page_refs and all payloads | **NO** — consumer must guess or choose own parameters | **UNKNOWN** — quality depends on chosen DPI |
| Pre-rendered page image | **NO** — no image materialized during processing | doc_processing.py:636-654 only captures metadata | **NO** — requires re-rendering from PDF | **DEPENDS** — re-rendering from vector PDF is lossless conceptually, but raster content in PDF may lose quality if DPI differs from original |
| Visual artifact ref (stable pointer to stored image) | **NO** — no such ref exists | No `visual_artifact_ref` field anywhere | **NO** — no pre-materialized image to dereference | N/A |
| Blob availability guarantee | IMPLICIT — content-addressed, no cleanup | artifact_ingestion.py:191-206, no expiry code found | ADEQUATE — blob persists indefinitely | YES |
| Recovery utility function | **NO** — no function does (blob_ref + page_number) → image | No such function in codebase | **NO** — consumer must implement recovery themselves | DEPENDS on implementation |

**Recovery path summary:** A consumer CAN theoretically open `blob_ref` as a PDF, navigate to `page_number`, and render the page. But:
- No standard rendering parameters are specified
- No pre-materialized image exists
- No utility function provides this recovery
- The consumer must bring their own PDF library and rendering logic
- Quality depends entirely on the consumer's rendering choices

---

## 5. PROVENANCE / POSITION / COEXISTENCE ANALYSIS

| Provenance / coexistence element | Present now? | Evidence | Adequate? |
|----------------------------------|-------------|----------|-----------|
| Source document identity | YES — `content_id`, `accession_number`, `blob_sha256` in same response | api.py:432, 447, 456 | YES |
| Page number | YES — `visual_page_refs[].page_number` | doc_processing.py:90 | YES |
| Relative order among processed content | PARTIAL — `visual_page_refs` is ordered list; chunks have `page_start`/`page_end` | content_index.py:542, chunk fields | PARTIAL — visual refs and text chunks share page numbers but no explicit interleaving |
| Association to OCR/text content units | IMPLICIT — chunks have `page_start`/`page_end` that overlap with `visual_page_refs[].page_number` | api.py:441-442, 460 | PARTIAL — consumer can correlate by page number but no explicit link |
| Whole-page vs region-level origin | WHOLE-PAGE only — `width`/`height` are page dimensions, no sub-page coordinates | doc_processing.py:93-94 | ADEQUATE for current use — region-level is a later concern |
| Ability to retrieve/use visual content alongside OCR text | PARTIAL — both in same API response, correlated by page number, but visual content requires separate recovery | api.py:439, 460, 451 | PARTIALLY_ADEQUATE — the data is there but recovery is not turnkey |

---

## 6. SPECIMEN-LEVEL ADEQUACY CHECK

Using the test fixture from `test_visual_page_refs_roundtrips_through_search_response_surface`:

| Specimen layer | Actual value/shape | Practical utility | Retrieval path | Quality-preserving? | Verdict |
|----------------|-------------------|-------------------|----------------|---------------------|---------|
| visual_page_refs in API response | `[{"page_number": 3, "visual_page_class": "diagram_or_visual", "status": "preserved", "width": 612.0, "height": 792.0}]` | Identifies WHICH page has visual content and its dimensions | N/A — this is metadata, not content | N/A | PARTIALLY_ADEQUATE — good metadata, no content |
| blob_ref in API response | `"/path/to/content-rt.bin"` (absolute path to original PDF) | Provides source document for re-rendering | Open PDF → seek to page 3 → render | YES — original PDF is byte-identical | PARTIALLY_ADEQUATE — recovery possible but not turnkey |
| Combined recovery path | blob_ref + page_number 3 + width/height | Consumer can render page 3 from PDF at chosen DPI | `fitz.open(blob_ref)[2].get_pixmap(dpi=N)` | YES for vector content; DEPENDS for embedded raster | PARTIALLY_ADEQUATE |
| Pre-materialized image | **ABSENT** | N/A | N/A | N/A | INADEQUATE |

**Overall specimen verdict: PARTIALLY_ADEQUATE** — the system preserves enough metadata and source references for theoretical recovery, but no materialized visual artifact exists and no rendering contract is specified.

---

## 7. ADEQUACY / UTILITY AUDIT

| Adequacy dimension | Current state | Verdict | Why |
|--------------------|---------------|---------|-----|
| Provenance / page attribution | page_number, accession_number, content_id, blob_sha256 all present | ADEQUATE_NOW | Full provenance chain from page to source document |
| Recoverability of visual content | blob_ref + page_number exist but no materialized image or rendering contract | PARTIALLY_ADEQUATE | Recovery requires consumer to bring PDF library + choose DPI |
| Storage usefulness | Metadata in DB; source PDF persisted; no visual artifact stored | PARTIALLY_ADEQUATE | Source PDF preserved but page images not extracted |
| Downstream consumer usefulness | Consumer has metadata and can correlate with text, but cannot get image without PDF re-rendering | PARTIALLY_ADEQUATE | Usable for filtering/annotation but not for direct visual consumption |
| API/query usefulness | Can query "which documents have visual content" via visual_page_refs | ADEQUATE_NOW | Filtering and discovery work |
| Coexistence with OCR/text | Both in same response, correlated by page_number | ADEQUATE_NOW | Consumer can align visual refs with text chunks by page |
| Robustness / non-fragility | blob_ref is absolute path — breaks if storage moves; no redundancy for visual content | PARTIALLY_ADEQUATE | Content-addressed is good but absolute paths are brittle on relocation |
| Maintainability / extension headroom | visual_page_refs is a flexible list-of-dicts; easy to add fields | ADEQUATE_NOW | Adding visual_artifact_ref to each dict is straightforward |

**Overall: PARTIALLY_ADEQUATE** — the system has good metadata and provenance, but the visual content itself is not materialized. A consumer cannot obtain the actual image without implementing their own PDF-to-image rendering pipeline.

---

## 8. DESIGN CHOICE ANALYSIS

| Candidate contract | Utility | Size | Maintainability | Robustness | Extension headroom | Quality preservation | Verdict |
|--------------------|---------|------|-----------------|------------|-------------------|---------------------|---------|
| **1. Metadata-only + implicit source recovery** (current state) | LOW — consumer must implement recovery | 0 lines — already done | HIGH — nothing new | LOW — no explicit contract, no rendering standard | MEDIUM | DEPENDS on consumer | NOT_JUSTIFIED as final state |
| **2. Metadata + explicit source/blob/page refs in visual_page_refs** (enrich each ref with blob_ref echo + rendering params) | MEDIUM — makes recovery contract explicit but still requires consumer rendering | SMALL — ~10 lines to enrich the dict | HIGH | MEDIUM — still no materialized artifact | MEDIUM | DEPENDS on consumer | NOT_JUSTIFIED — blob_ref already in same response; echoing it into visual_page_refs adds redundancy without solving the core gap |
| **3. Metadata + materialized visual artifact refs** (render page images during processing, store content-addressed, add `visual_artifact_ref` to each visual_page_ref) | HIGH — consumer gets stable pointer to pre-rendered PNG; follows normalized_text_ref pattern exactly | MEDIUM — ~40-60 lines: render function + storage function + ref in dict + propagation | HIGH — follows existing `_write_normalized_text_blob` pattern | HIGH — image exists independently of blob availability; content-addressed | HIGH — can later add format variants, thumbnails, etc. | HIGH — rendered once at known DPI; stored without recompression | **BEST_NEXT_STEP** |
| **4. Eager materialized artifacts carried through pipeline** (image bytes in payload at every boundary) | MEDIUM — no dereference needed but bloats every payload | LARGE — binary data through JSON pipeline, base64 encoding, major refactor | LOW — complicates every boundary | MEDIUM | LOW — hard to extend | HIGH | PREMATURE |
| **5. Hybrid: on-demand materialization service** (store nothing eagerly; provide a service endpoint that renders on request) | MEDIUM — no upfront cost but adds latency and requires blob availability at render time | MEDIUM — new endpoint + rendering logic | MEDIUM — new service to maintain | LOW — depends on blob availability at query time | HIGH | DEPENDS — re-renders each time unless cached | PLAUSIBLE_BUT_LARGER — adds API surface; better as a later optimization |

---

## 9. NEXT-LANE OPTION SET

### Option 1: BOUNDED_MATERIALIZED_VISUAL_ARTIFACT — Page Image Extraction + Storage + Ref

- **Objective:** During document processing, when a page is classified as preserve-eligible (`diagram_or_visual`), render it to PNG at a standard DPI, store it content-addressed following the `_write_normalized_text_blob` pattern, and add `visual_artifact_ref` + `visual_artifact_sha256` to the visual_page_ref dict.
- **Files:** `nrc_aps_document_processing.py` (render + store in `_capture_visual_page_ref`), `nrc_aps_content_index.py` or `nrc_aps_artifact_ingestion.py` (storage utility if separate), possibly `nrc_aps_safeguards.py` (if using existing write patterns)
- **Change shape:** ~40-60 lines: rendering function, content-addressed storage function, enriched visual_page_ref dict. No changes to DB schema, API schema, serialization, or any other downstream boundary (the new fields flow through existing list-of-dicts propagation automatically).
- **Why next:** This is the exact gap — visual content is identified but not materialized. Adding materialized artifacts makes the representation genuinely usable without requiring consumers to implement PDF rendering.
- **Why smallest:** Follows the exact existing pattern (`_write_normalized_text_blob`). No DB schema changes needed — the new refs live inside the existing `visual_page_refs_json` list-of-dicts. No API schema changes needed — `visual_page_refs: list[dict]` already carries arbitrary dict fields. The only change is in the production function and a new storage utility.
- **Risks:** Storage growth (one PNG per preserve-eligible page); rendering DPI choice affects file size and quality; fitz dependency already exists.

### Option 2: BOUNDED_VISUAL_REF_ENRICHMENT — Explicit Recovery Contract Without Materialization

- **Objective:** Add rendering parameters (standard DPI, format) to visual_page_refs and document the `blob_ref + page_number → image` recovery contract explicitly, without materializing images.
- **Files:** `nrc_aps_document_processing.py` (add `rendering_dpi`, `rendering_format` to dict)
- **Change shape:** ~5-10 lines
- **Why not first:** Does not solve the core gap. Consumer still must implement rendering. Only marginally better than current state.
- **Risks:** None, but provides limited value.

### Option 3: BOUNDED_ON_DEMAND_MATERIALIZATION_ENDPOINT — API-Side Rendering Service

- **Objective:** Add an API endpoint that takes (blob_ref, page_number, dpi) and returns rendered PNG.
- **Files:** `router.py`, new service function
- **Change shape:** ~50-80 lines
- **Why not first:** Larger scope (new API surface); depends on blob availability at query time; doesn't store rendered artifacts. Better as a later optimization after Option 1 establishes the standard rendered artifact.
- **Risks:** Latency; blob availability; compute cost per request.

---

## 10. DECISION

### Canonical Representation Decision (required — must not be left implicit)

**The source PDF page is canonical. The materialized PNG artifact is a derived convenience representation.**

Rationale:
- The original PDF page contains the authoritative visual content in its native format (vector, raster, or mixed)
- A rasterized PNG is a **derived representation** — PNG is lossless for the rendered raster output, but rasterization itself **may reduce fidelity** relative to vector/mixed source pages. This is an accepted tradeoff for downstream usability, not an equivalence claim.
- The source remains recoverable via `blob_ref` + `page_number` for any consumer that needs the original vector/mixed content
- The artifact exists as a **downstream-usable convenience layer** that eliminates the need for consumers to bring their own PDF rendering

### Dual Recovery Contract (required — must be explicit)

Both recovery paths MUST be preserved:
1. **Artifact ref (primary convenience path):** `visual_artifact_ref` → dereference to pre-rendered PNG. Use this first.
2. **Source-page recovery (authoritative fallback):** `blob_ref` + `page_number` → open source PDF, render page at desired quality. Use when artifact is unavailable or when original vector fidelity is needed.

**Retrieval precedence:** Artifact ref first; source-page recovery second.

### Recommended next lane: Option 1 — BOUNDED_MATERIALIZED_VISUAL_ARTIFACT

1. **What:** Render preserve-eligible pages to PNG during document processing, store content-addressed under a stable namespace such as `nrc_adams_aps/visual_pages/sha256/{hash}.png`, and expose that stable storage-relative/URI-style reference as the canonical `visual_artifact_ref` rather than a machine-local absolute path, add `visual_artifact_ref` and `visual_artifact_sha256` to each visual_page_ref dict. The rendered artifact is explicitly a derived whole-page rasterization, not a claim of equivalence with the source page.

2. **Why smallest justified:** Follows the exact existing pattern (`_write_normalized_text_blob` → `normalized_text_ref`).No structural DB/API schema changes are expected because the existing `visual_page_refs` list-of-dicts already persists and roundtrips; however, response-surface proof for the new artifact-related fields is still mandatory. The only new code is a rendering + storage function (~40-60 lines in document processing).

3. **Frozen:** All completed lanes — DB persistence, API exposure, serialization, content-index propagation, connector handoff. The visual_page_refs dict shape is extended (new fields added), not modified (existing fields unchanged).

4. **Adequacy gap resolved:** Transforms the contract from "metadata marker + implicit source recovery" to "metadata + stable derived-artifact ref + explicit dual recovery contract (artifact-first, source-fallback)." A consumer can dereference `visual_artifact_ref` to get a usable image, or fall back to `blob_ref` + `page_number` for original-fidelity source access.

5. **Does the current representation produce what we intend downstream?** PARTIALLY — metadata and source provenance are good. The visual content itself is not materialized. After this lane, it will be (as a derived convenience artifact with explicit source fallback).

---

## 11. IMPLEMENTATION-READY NEXT ACTION CONTRACT

**A. Next-pass mode:** BOUNDED_MATERIALIZED_VISUAL_ARTIFACT_IMPLEMENTATION

**B. Files/symbols to touch:**
- `backend/app/services/nrc_aps_document_processing.py`:
  - New function: `_write_visual_page_artifact(*, artifact_storage_dir, page, page_number, config)` — renders page to PNG, stores it content-addressed, and returns a downstream-safe canonical artifact reference plus `{visual_artifact_sha256, ...}`. The internal filesystem path may be used for writing, but must not be the canonical downstream-visible reference.
  - Modify `_capture_visual_page_ref()` or the caller block (lines 644-654): add artifact rendering + merge artifact refs into the visual_page_ref dict
  - The `process_document()` function already receives `config` with rendering params; add standard `visual_render_dpi` (default 150 or 200)
- Prefer implementing the artifact write helper inside `nrc_aps_document_processing.py` unless direct codebase evidence shows an existing shared storage utility pattern that should be reused. Touch `nrc_aps_artifact_ingestion.py` only if reuse is clearly cleaner and does not broaden the lane.

**C. Behaviors to prove:**
1. Preserve-eligible pages produce visual_page_ref dicts containing `visual_artifact_ref` (a storage-stable, downstream-safe artifact reference, not a machine-local absolute filesystem path) and `visual_artifact_sha256`
2. The materialized PNG file exists in the artifact store and is resolvable from `visual_artifact_ref` using the configured storage-root/backend rules after processing.
3. The resolved artifact bytes match `visual_artifact_sha256`
4. The PNG is rendered at the standard DPI; stored as PNG (lossless for the raster output)
5. The `visual_artifact_ref` propagates through content-index payload → DB → API automatically (no changes needed — it's inside the existing list-of-dicts)
6. Failed rendering degrades gracefully (status="visual_capture_failed", no artifact ref, non-fatal)
7. All existing tests continue to pass
8. **Dual recovery contract preserved:** Both `visual_artifact_ref` (convenience) and source recovery path (`blob_ref` + `page_number`) remain available in API response. Neither is removed or replaced.
9. **Response-surface roundtrip proof:** The new artifact-related fields (`visual_artifact_ref`, `visual_artifact_sha256`, `visual_artifact_dpi`, `visual_artifact_format`, `visual_artifact_semantics`) must be explicitly proven to roundtrip through payload → DB → API response on at least one real caller-facing path. Do not rely on implicit propagation of the existing `list[dict[str, Any]]` shape without direct test proof.

**C.1. Artifact contract requirements (non-negotiable):**

**C.1.a. Canonical artifact-reference contract (non-negotiable):**
- `visual_artifact_ref` must be the canonical downstream-visible reference to the materialized visual artifact.
- It must be storage-stable and portable across machines/processes/environments to the extent the artifact store itself is portable.
- It must NOT be a machine-local absolute filesystem path in the downstream contract.
- It should be a storage-relative reference, artifact key, or URI-like identifier that can be resolved by downstream code using configured storage-root rules.
- The implementation may use absolute local paths internally during write-time, but those paths are implementation detail only and must not be the downstream contract.
- The reference must be sufficient to locate the exact artifact bytes when combined with the configured artifact storage root/backend.

Each visual_page_ref dict for a successfully materialized page MUST contain:
- `page_number` — source page number (already present)
- `visual_page_class` — classification (already present)
- `status` — "preserved" (already present)
- `width`, `height` — source page dimensions (already present)
- `visual_artifact_ref` — canonical storage-stable reference to the materialized PNG artifact (NEW). This must NOT be a machine-local absolute filesystem path as part of the downstream contract. If a local absolute path is needed internally during processing/storage, treat it only as an implementation detail and do not expose it as the canonical downstream-visible reference.
- `visual_artifact_sha256` — SHA256 of the PNG bytes (NEW)
- `visual_artifact_dpi` — rendering DPI used (NEW)
- `visual_artifact_format` — "png" (NEW)
- `visual_artifact_semantics` — "whole_page_rasterization" (NEW) — explicitly declares this is a whole-page rendered output, not true embedded-image extraction

The coexisting response fields (`blob_ref`, `blob_sha256`, `accession_number`, `content_id`, `page_start`/`page_end` on chunks) preserve:
- Source document identity
- Stable blob/source reference
- Page number correlation with OCR/text content

**C.2. Quality / fidelity rules (non-negotiable):**
- Render to PNG (lossless for the rasterized output — does NOT claim equivalence with source vector/mixed content)
- Use a standard DPI (150 or 200 — configurable via `config["visual_render_dpi"]`)
- Content-addressed storage ensures no duplicate writes and immutable artifact references
- Original PDF blob remains untouched — source recovery path always available as authoritative fallback
- Do NOT describe the PNG as "preserving original visual fidelity" — it is a derived convenience representation
- This lane is **whole-page only**. Preserve-eligible visual content is materialized as a whole-page rasterization of the source page. Region-level extraction, crop semantics, and sub-page artifact generation are explicitly out of scope for this lane.
- The artifact contract must preserve usable association to coexisting OCR/text content at minimum via:
  - source document identity
  - page number
  - stable artifact reference
  - coexistence with existing downstream page/chunk context

- No change in this lane may break the ability to correlate visual artifacts with text-derived content by document/page context.

**C.3. Failure semantics (non-negotiable):**
- If visual artifact materialization succeeds, the visual_page_ref entry must include:
  - `status: "preserved"`
  - `visual_artifact_ref`
  - `visual_artifact_sha256`
  - the agreed artifact metadata fields
- If visual artifact materialization fails, the visual_page_ref entry must:
  - remain present for provenance/accounting
  - use `status: "visual_capture_failed"`
  - omit `visual_artifact_ref`
  - omit `visual_artifact_sha256`
  - preserve page-level provenance fields already established upstream
- Failure must remain non-fatal to overall document processing.
- Existing failure/degradation signaling must remain additive and compatible with current tests/semantics.

**D. Invariants unchanged:**
- All upstream processing logic unchanged (classification, OCR, text extraction)
- visual_page_refs list-of-dicts shape: existing fields (`page_number`, `visual_page_class`, `status`, `width`, `height`) unchanged — new fields are additive
- DB schema unchanged — new fields flow through existing `visual_page_refs_json` Text column
- API schema unchanged — new fields flow through existing `list[dict[str, Any]]` type
- All existing serialization/deserialization unchanged
- All existing tests continue to pass
- `blob_ref` and `blob_sha256` remain in API response — source recovery path is never removed
- Source PDF blob is never modified by the rendering process
- OCR/text content flows are completely untouched
- Page-number correlation between visual_page_refs and text-derived chunk/content-unit context (including existing page_start/page_end semantics where present) is preserved.
- No change in this lane may make visual artifacts harder to align with OCR/text-derived content by source document + page context.
- This lane must remain whole-page oriented; it must not introduce ambiguous region-level semantics.

**E. Stop conditions:**
- Preserve-eligible pages produce materialized PNG artifacts with stable refs
- visual_artifact_ref roundtrips through payload → DB → API
- PNG quality is adequate (standard DPI, lossless format)
- Failed rendering is non-fatal
- All existing + new tests pass

**F. Why smallest:** This follows the exact existing artifact pattern (`_write_normalized_text_blob` → `normalized_text_ref`). No DB migration. No API schema change. No serialization change. The only new code is rendering + storage in document processing (~40-60 lines). The new fields automatically propagate through the entire existing pipeline because `visual_page_refs` is already a `list[dict[str, Any]]`.

---

## 12. FINAL STATUS

**VISUAL_CONTENT_RECOVERY_CONTRACT_ANALYSIS_COMPLETE**

---

## Note on Batch Decomposition

This is a single coherent analysis pass, not a parallelizable implementation task. The recommended next lane (BOUNDED_MATERIALIZED_VISUAL_ARTIFACT_IMPLEMENTATION) is a single bounded change (~40-60 lines in 1-2 files) that does not warrant further decomposition.
