# NRC ADAMS Document Ingestion Architecture Report

This document outlines the current state and technical adequacy of the logic used for processing, ingestion, and OCR of documents retrieved from the NRC ADAMS systems.

## 1. Module Inventory

The ingestion pipeline is composed of three primary specialized modules:

| Module | Responsibility | Core Dependencies |
| :--- | :--- | :--- |
| `nrc_aps_media_detection.py` | Signature-based content typing and routing. | Standard Library |
| `nrc_aps_document_processing.py` | Orchestration of PDF, Image, ZIP, and Text logic. | `PyMuPDF (fitz)` |
| `nrc_aps_ocr.py` | Tesseract CLI execution and TSV coordinate parsing. | `Tesseract OCR` |

## 2. Core Implementation Strategy

### A. Layout-Aware PDF Parsing (`PyMuPDF`)
The system uses a **Layout-Aware Dictionary Pass** (`page.get_text("dict")`) to reconstruct line and block structures.
- **Feature**: Integrated `page.find_tables()` for primary table detection and Markdown conversion.

### B. Selective Hybrid OCR
Triggered for graphical elements (logos/stamps) or weak native text, using a word-difference heuristic to avoid redundancy.

### C. Multi-Page & Archive Support
Handles multi-page TIFFs via `fitz` and ZIP archives with recursive safety guards.

## 3. Critical Deficiencies / Architectural Gaps

Despite recent optimizations, the current `fitz` + `Tesseract` stack exhibits significant gaps when applied to specific NRC document classes:

> [!CAUTION]
> **Strike-Through Blindness**: `PyMuPDF` fails to natively distinguish strike-through annotations in "Technical Specification Amendments," leading to the ingestion of revoked/deleted regulations as active text.

> [!WARNING]
> **OCR Limitations**: `Tesseract` is inadequate for the handwritten margin notes and skewed fax stamps common in "Differing Professional Opinion (DPO)" and "Part 21" safety reports.

- **Financial Table Failures**: `PyMuPDF`'s `find_tables()` frequently fails on borderless, multi-line header tables found in "Decommissioning Funding Plans."
- **OOM Instability**: Layout-aware dictionary passes trigger Out-of-Memory (OOM) failures on 15,000+ page "Combined License Applications (COLAs)."

## 4. Proposed Revised Tech Stack (Evolution Roadmap)

To achieve true adequacy for the NRC ADAMS corpus, the following architectural evolution is required:

| Gap | Proposed Solution | Implementation Detail |
| :--- | :--- | :--- |
| **Strike-throughs** | **Annotation Parsing** | Explicitly parse PDF annotation streams for `/S /StrikeOut` flags. |
| **Messy/Handwritten OCR** | **Cloud Vision API** | Implement fallback to Cloud Vision for high-complexity handwritten documents. |
| **Borderless Tables** | **Camelot / Tabula** | Integrate lattice-based parsers for complex financial grid extraction. |
| **Extreme Document Size** | **Pagination Chunking** | Implement 500-page windowed processing to maintain memory safety. |

## 5. Conclusion

The current implementation provides a solid baseline for standard regulatory guidance and reports but is **Inadequate for high-fidelity legal/technical compliance** involving annotations, handwriting, or extreme-scale applications. Transitioning to the "Revised Tech Stack" defined in Section 4 is mandatory for full operational deployment.
