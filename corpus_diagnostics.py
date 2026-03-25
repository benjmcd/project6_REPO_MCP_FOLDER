"""
Corpus diagnostics for Phase 1/2 validation.
Processes all PDFs in data_demo/nrc_adams_documents_for_testing/
and emits distributions + representative page samples.
"""
import json
import sys
import os
from pathlib import Path
from collections import defaultdict

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.nrc_aps_document_processing import (
    process_document,
    _extract_embedded_image_candidates,
    _provisional_visual_class,
)
from app.services.nrc_aps_artifact_ingestion import processing_config_from_run_config
import fitz


DATA_DIR = Path(__file__).parent / "data_demo" / "nrc_adams_documents_for_testing"


def process_file(filepath: Path) -> dict:
    config = processing_config_from_run_config({"file_path": str(filepath), "pdf_path": str(filepath)})
    content = filepath.read_bytes()
    try:
        result = process_document(content=content, declared_content_type="application/pdf", config=config)
        return result
    except Exception as e:
        return {"error": str(e), "filepath": str(filepath)}


def extract_page_diagnostics(result: dict) -> list[dict]:
    """Extract per-page diagnostics from process_document result."""
    diagnostics = []
    for page in result.get("page_summaries", []):
        diag = {
            "page_number": page["page_number"],
            "unit_count": page.get("unit_count", 0),
            "source": page.get("source", ""),
            "ocr_attempted": page.get("ocr_attempted", False),
            "ocr_paths_taken": page.get("ocr_paths_taken", []),
            "quality_status": page.get("quality_status", ""),
            "searchable_chars": page.get("searchable_chars", 0),
            "page_native_quality_is_weak": page.get("page_native_quality_is_weak", False),
            # Phase 1 image candidates
            "candidate_count_approx": page.get("candidate_count_approx", 0),
            "total_image_area_approx": page.get("total_image_area_approx", 0.0),
            "max_image_width_approx": page.get("max_image_width_approx", 0.0),
            "max_image_height_approx": page.get("max_image_height_approx", 0.0),
            "raster_only_count_approx": page.get("raster_only_count_approx", 0),
            "text_block_bbox_area_ratio_sum_approx": page.get("text_block_bbox_area_ratio_sum_approx", 0.0),
            # Phase 2 visual class
            "visual_class_provisional": page.get("visual_class_provisional", ""),
            "drawing_density_proxy": page.get("drawing_density_proxy", 0),
            "raster_image_area_ratio_approx": page.get("raster_image_area_ratio_approx", 0.0),
            "vector_drawing_area_ratio_approx": page.get("vector_drawing_area_ratio_approx", 0.0),
            "max_single_candidate_area_ratio_approx": page.get("max_single_candidate_area_ratio_approx", 0.0),
        }
        diagnostics.append(diag)
    return diagnostics


def get_raw_image_candidates(filepath: Path, page_indices: list[int] | None = None) -> dict[int, dict]:
    """Extract raw image candidates directly from PDF for a specific page."""
    content = filepath.read_bytes()
    doc = fitz.open(stream=content, filetype="pdf")
    results = {}
    pages_to_check = page_indices if page_indices is not None else list(range(len(doc)))
    for pi in pages_to_check:
        if pi >= len(doc):
            continue
        page = doc[pi]
        text_dict = page.get_text("dict", sort=True)
        candidates_result = _extract_embedded_image_candidates(page, text_dict)
        # Also get visual class
        native_text = "\n".join(
            str(item.get("text") or "") 
            for item in (text_dict.get("blocks", []) or [])
            if item.get("type") == 0
        )
        visual = _provisional_visual_class(page, candidates_result, native_text)
        results[pi] = {
            "candidates": candidates_result,
            "visual": visual,
        }
    doc.close()
    return results


def main():
    pdf_files = sorted(DATA_DIR.rglob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files\n")

    # Distributions
    total_pages = 0
    pages_with_candidates = 0
    pages_with_zero_xref = 0
    visual_class_counts = defaultdict(int)
    pages_both_fallback_and_hybrid = 0
    pages_ocr_attempted_no_supplement = 0
    ocr_path_counts = defaultdict(int)
    quality_status_counts = defaultdict(int)
    
    all_page_diagnostics = []  # (filepath, page_diag)
    representative_pages = []  # collected for diversity

    for pdf_path in pdf_files:
        result = process_file(pdf_path)
        if "error" in result:
            print(f"ERROR {pdf_path.name}: {repr(result['error'])[:100]}")
            continue
        
        page_diags = extract_page_diagnostics(result)
        total_pages += len(page_diags)
        
        for pdi in page_diags:
            all_page_diagnostics.append((pdf_path.name, pdi))
            
            # Counts
            if pdi["candidate_count_approx"] > 0:
                pages_with_candidates += 1
            if any(c.get("xref") == 0 for c in pdi.get("candidates", [])):
                pages_with_zero_xref += 1
            
            visual_class_counts[pdi["visual_class_provisional"]] += 1
            quality_status_counts[pdi["quality_status"]] += 1
            
            # OCR paths
            paths = pdi.get("ocr_paths_taken", [])
            for path in paths:
                ocr_path_counts[path] += 1
            if "fallback" in paths and "hybrid" in paths:
                pages_both_fallback_and_hybrid += 1
            
            # OCR attempted no supplement
            if pdi["ocr_attempted"] and pdi["unit_count"] == 0:
                pages_ocr_attempted_no_supplement += 1
            
            # Collect representative pages
            vc = pdi["visual_class_provisional"]
            if len(representative_pages) < 40:
                representative_pages.append((pdf_path.name, pdi))

    # Print distribution table
    print("=" * 60)
    print("CORPUS DISTRIBUTION SUMMARY")
    print("=" * 60)
    print(f"Total pages processed:     {total_pages}")
    print(f"Pages with candidates > 0: {pages_with_candidates} ({100*pages_with_candidates/total_pages:.1f}%)")
    print(f"Pages with zero-xref:     {pages_with_zero_xref} ({100*pages_with_zero_xref/total_pages:.1f}%)")
    print()
    print("Visual class distribution:")
    for vc, count in sorted(visual_class_counts.items(), key=lambda x: -x[1]):
        print(f"  {vc:30s}: {count:4d} ({100*count/total_pages:.1f}%)")
    print()
    print("OCR path counts:")
    for path, count in sorted(ocr_path_counts.items(), key=lambda x: -x[1]):
        print(f"  {path:30s}: {count}")
    print()
    print(f"Pages with both fallback AND hybrid: {pages_both_fallback_and_hybrid}")
    print(f"Pages OCR attempted but no supplement: {pages_ocr_attempted_no_supplement}")
    print()
    print("Quality status distribution:")
    for qs, count in sorted(quality_status_counts.items(), key=lambda x: -x[1]):
        print(f"  {qs:20s}: {count}")
    print()

    # Print representative pages - diverse selection
    print("=" * 60)
    print("REPRESENTATIVE PAGE DIAGNOSTICS")
    print("=" * 60)
    
    # Select 8 diverse pages
    selected = []
    seen_classes = set()
    for fname, pdi in all_page_diagnostics:
        vc = pdi["visual_class_provisional"]
        if vc not in seen_classes:
            selected.append((fname, pdi))
            seen_classes.add(vc)
            if len(selected) >= 8:
                break
    
    # Add some specific known cases
    for fname, pdi in all_page_diagnostics:
        if len(selected) >= 12:
            break
        if (fname, pdi["page_number"]) not in [(s[0], s[1]["page_number"]) for s in selected]:
            selected.append((fname, pdi))

    for fname, pdi in selected:
        print(f"\nFile: {fname}  Page: {pdi['page_number']}")
        print(f"  source={pdi['source']}  ocr_attempted={pdi['ocr_attempted']}  ocr_paths={pdi['ocr_paths_taken']}")
        print(f"  quality_status={pdi['quality_status']}  searchable_chars={pdi['searchable_chars']}")
        print(f"  page_native_quality_is_weak={pdi['page_native_quality_is_weak']}")
        print(f"  --- Image Candidates ---")
        print(f"  candidate_count_approx={pdi['candidate_count_approx']}")
        print(f"  total_image_area_approx={pdi['total_image_area_approx']}")
        print(f"  max_image_width_approx={pdi['max_image_width_approx']}")
        print(f"  max_image_height_approx={pdi['max_image_height_approx']}")
        print(f"  raster_only_count_approx={pdi['raster_only_count_approx']}")
        print(f"  text_block_bbox_area_ratio_sum_approx={pdi['text_block_bbox_area_ratio_sum_approx']:.4f}")
        print(f"  --- Visual Class ---")
        print(f"  visual_class_provisional={pdi['visual_class_provisional']}")
        print(f"  drawing_density_proxy={pdi['drawing_density_proxy']}")
        print(f"  max_single_candidate_area_ratio_approx={pdi['max_single_candidate_area_ratio_approx']:.4f}")
        print(f"  total_image_area_ratio_approx={pdi['total_image_area_ratio_approx']:.4f}")

    # Now do a deeper dive on a few specific pages to show candidate records
    print("\n" + "=" * 60)
    print("DEEP DIVE: CANDIDATE RECORDS FOR SPECIFIC PAGES")
    print("=" * 60)
    
    # Find pages with zero-xref candidates
    zero_xref_pages = [(f, p) for f, p in all_page_diagnostics if p.get("candidate_count_approx", 0) == 0]
    print(f"\nPages with candidate_count_approx == 0: {len(zero_xref_pages)}")
    
    # Find pages with high drawing density
    high_drawing = sorted(all_page_diagnostics, key=lambda x: x[1].get("drawing_density_proxy", 0), reverse=True)[:5]
    print(f"\nTop drawing density pages:")
    for fname, pdi in high_drawing:
        print(f"  {fname} p{pdi['page_number']}: drawing_density_proxy={pdi['drawing_density_proxy']} visual_class={pdi['visual_class_provisional']}")
    
    # Find pages with high image area
    high_image = sorted(all_page_diagnostics, key=lambda x: x[1].get("max_single_candidate_area_ratio_approx", 0), reverse=True)[:5]
    print("\nTop image area ratio pages:")
    for fname, pdi in high_image:
        print(f"  {fname} p{pdi['page_number']}: max_single_ratio={pdi['max_single_candidate_area_ratio_approx']:.4f} visual_class={pdi['visual_class_provisional']}")

    # Check trace consistency - run trace on a few pages and show raw output
    print("\n" + "=" * 60)
    print("TRACE VALIDATION: raw trace output samples")
    print("=" * 60)
    
    # Pick 4 diverse pages
    trace_samples = []
    for fname, pdi in all_page_diagnostics:
        if len(trace_samples) >= 4:
            break
        trace_samples.append((fname, pdi["page_number"] - 1))  # 0-indexed
    
    for fname, page_idx0 in trace_samples:
        pdf_path = DATA_DIR / fname
        if not pdf_path.exists():
            continue
        content = pdf_path.read_bytes()
        doc = fitz.open(stream=content, filetype="pdf")
        if page_idx0 >= len(doc):
            doc.close()
            continue
        page = doc[page_idx0]
        trace = page.get_text("trace")
        lines = trace.splitlines()
        l_count = sum(1 for l in lines if l.strip() == "l")
        c_count = sum(1 for l in lines if l.strip() == "c")
        other = len([l for l in lines if l.strip() and l.strip() not in ("l", "c")])
        print(f"\n{fname} page {page_idx0+1}: total trace lines={len(lines)}, l={l_count}, c={c_count}, other={other}")
        if other > 0:
            sample_other = [l for l in lines if l.strip() and l.strip() not in ("l", "c")][:3]
            print(f"  sample other lines: {sample_other}")
        doc.close()


if __name__ == "__main__":
    main()
