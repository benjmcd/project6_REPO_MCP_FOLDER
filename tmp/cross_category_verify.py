import sys
from pathlib import Path
import hashlib
from typing import Any

# Add backend to sys.path
backend_path = Path(r"c:\Users\benny\OneDrive\Desktop\Project6\backend")
sys.path.insert(0, str(backend_path))

from app.services import nrc_aps_document_processing as dp

def process_and_report(file_path: Path, category: str):
    print(f"\n{'='*20} {category} {'='*20}")
    print(f"File: {file_path.name}")
    
    if not file_path.exists():
        print(f"ERROR: File not found at {file_path}")
        return

    with open(file_path, "rb") as f:
        content = f.read()

    try:
        result = dp.process_document(
            content=content,
            declared_content_type="application/pdf",
            config=dp.default_processing_config({"ocr_enabled": True})
        )
    except Exception as e:
        print(f"FAILED: {e}")
        return

    print(f"Document Class:     {result.get('document_class')}")
    print(f"Page Count:         {result.get('page_count')}")
    print(f"Quality Status:     {result.get('quality_status')}")
    print(f"Normalized Chars:   {result.get('normalized_char_count')}")
    
    summaries = result.get("page_summaries", [])
    native_count = sum(1 for s in summaries if s.get("source") == "native")
    ocr_count = sum(1 for s in summaries if s.get("source") == "ocr")
    print(f"Pages (Native):     {native_count}")
    print(f"Pages (OCR):        {ocr_count}")
    
    text = result.get("normalized_text", "")
    print(f"Table Found:        {'Yes' if '|' in text else 'No'}")
    
    # Check for supplementary OCR (hybrid path)
    has_supplement = any(u.get("unit_kind") == "ocr_image_supplement" for u in result.get("ordered_units", []))
    print(f"Hybrid OCR Supplement: {'Yes' if has_supplement else 'No'}")

def main():
    root = Path(r"C:\Users\benny\OneDrive\Desktop\Project6\data_demo\nrc_adams_documents_for_testing")
    
    targets = [
        (root / "handbook_documents_for_testing" / "ML24157A089.pdf", "HANDBOOK"),
        (root / "regulatory_guidance_documents_for_testing" / "ML17123A319.pdf", "REGULATORY GUIDANCE"),
        (root / "weekly_information_report_documents_for_testing" / "SECY-25-0018 Weekly Information Report Week Ending March 7 2025.pdf", "WEEKLY REPORT")
    ]
    
    for path, cat in targets:
        process_and_report(path, cat)

if __name__ == "__main__":
    main()
