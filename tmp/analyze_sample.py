import sys
import json
import os
from pathlib import Path

# Add backend to sys.path
backend_path = Path(r"c:\Users\benny\OneDrive\Desktop\Project6\backend")
sys.path.insert(0, str(backend_path))

from app.services import nrc_aps_document_processing as dp

def analyze_sample():
    sample_path = Path(r"C:\Users\benny\OneDrive\Desktop\Project6\data_demo\ML17123A319.pdf")
    if not sample_path.exists():
        print(f"ERROR: Sample file not found at {sample_path}")
        sys.exit(1)
        
    with open(sample_path, "rb") as f:
        content = f.read()
        
    print(f"Processing sample: {sample_path.name} ({len(content)} bytes)")
    
    try:
        result = dp.process_document(
            content=content,
            declared_content_type="application/pdf",
            config=dp.default_processing_config({"ocr_enabled": True})
        )
    except Exception as e:
        print(f"FAILED: process_document raised {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    # Inspect top-level results
    print(f"\n--- Execution Results ---")
    print(f"Document Class:     {result.get('document_class')}")
    print(f"Effective Type:     {result.get('effective_content_type')}")
    print(f"Page Count:         {result.get('page_count')}")
    print(f"Quality Status:     {result.get('quality_status')}")
    print(f"Extractor Family:   {result.get('extractor_family')}")
    print(f"Normalized Chars:   {result.get('normalized_char_count')}")
    
    # Check page summaries for OCR vs Native
    summaries = result.get("page_summaries", [])
    native_count = sum(1 for s in summaries if s.get("source") == "native")
    ocr_count = sum(1 for s in summaries if s.get("source") == "ocr")
    print(f"Pages (Native):     {native_count}")
    print(f"Pages (OCR):        {ocr_count}")
    
    print("\n--- Page Summaries ---")
    for s in summaries[:5]: # First 5 pages
        print(f"Page {s['page_number']}: Source={s.get('source')}, Units={s.get('unit_count')}, Quality={s.get('quality_status')}")
    
    print("\n--- Page 1 Units ---")
    page1_units = [u for u in result.get("ordered_units", []) if u.get("page_number") == 1]
    for u in page1_units:
        print(f"Unit Kind: {u.get('unit_kind')}, Text Snippet: {u.get('text')[:50]}...")
    
    text = result.get("normalized_text", "")
    print("\n--- Table Extraction Check ---")
    if "|" in text:
        # Find first table occurrence
        table_index = text.find("|")
        print(f"Table found at offset {table_index}. Snippet:")
        print(text[table_index:table_index+1000])
    else:
        print("No tables (Markdown format) found in the full text.")

    snippet_path = Path(r"C:\Users\benny\OneDrive\Desktop\Project6\tmp\ML17123A319_output_snippet.txt")
    with open(snippet_path, "w", encoding="utf-8") as f:
        f.write(text[:5000]) # First 5000 chars
    print(f"\nOutput snippet saved to: {snippet_path}")

if __name__ == "__main__":
    analyze_sample()
