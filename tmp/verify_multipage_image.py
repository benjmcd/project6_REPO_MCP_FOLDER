import sys
import os
from io import BytesIO
from pathlib import Path
import fitz

# Add backend to sys.path
backend_path = Path(r"c:\Users\benny\OneDrive\Desktop\Project6\backend")
sys.path.insert(0, str(backend_path))

from app.services import nrc_aps_document_processing as dp

def test_multipage_image():
    # 1. Create a synthetic 2-page PDF and convert to TIFF-like stream for testing
    # fitz can render to TIFF if supported by build, but we'll use a PDF to simulate 
    # a multi-page image document that fitz can open.
    doc = fitz.open()
    page1 = doc.new_page()
    page1.insert_text((50, 50), "Page One Content")
    page2 = doc.new_page()
    page2.insert_text((50, 50), "Page Two Content")
    
    # We will pass this as if it's an image/tiff to test the fitz opening logic in _process_image
    stream = doc.tobytes()
    doc.close()

    print(f"Synthetic document created: {len(stream)} bytes")

    try:
        # We tell detect_media_type it's image/tiff so it routes to _process_image
        result = dp._process_image(
            content=stream,
            detection={"effective_content_type": "image/tiff", "sniffed_content_type": "image/tiff"},
            config=dp.default_processing_config({"ocr_enabled": True}),
            deadline=None
        )
    except Exception as e:
        print(f"FAILED: _process_image raised {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print(f"Page Count: {result.get('page_count')}")
    text = result.get('normalized_text', '')
    print(f"Extracted Text:\n---\n{text}\n---")
    
    if "Page One Content" in text and "Page Two Content" in text:
        print("SUCCESS: Multi-page image aggregation work.")
    else:
        print("FAILURE: Missing content from one or more pages.")
        sys.exit(1)

    assert result.get('page_count') == 2

if __name__ == "__main__":
    test_multipage_image()
