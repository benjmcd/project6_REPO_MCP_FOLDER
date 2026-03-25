import sys
from pathlib import Path

# Add backend to sys.path
backend_path = Path(r"c:\Users\benny\OneDrive\Desktop\Project6\backend")
sys.path.insert(0, str(backend_path))

from app.services import nrc_aps_document_processing as dp

def detail_analysis(file_path: Path, category: str):
    print(f"\n{'='*20} {category} {'='*20}")
    with open(file_path, "rb") as f:
        content = f.read()

    result = dp.process_document(
        content=content,
        declared_content_type="application/pdf"
    )

    text = result.get("normalized_text", "")
    print(f"Total Chars: {len(text)}")
    print(f"Table Found: {'Yes' if '|' in text else 'No'}")
    
    # Print snippets of table-like areas or structured lists
    print("\n--- Text Snippets ---")
    print(text[:1000]) # Beginning
    
    if "|" in text:
        idx = text.find("|")
        print("\n--- Table Snippet ---")
        print(text[idx:idx+500])

def main():
    root = Path(r"C:\Users\benny\OneDrive\Desktop\Project6\data_demo\nrc_adams_documents_for_testing")
    
    # Handbook
    detail_analysis(root / "handbook_documents_for_testing" / "ML24157A089.pdf", "HANDBOOK")
    
    # Weekly Report
    detail_analysis(root / "weekly_information_report_documents_for_testing" / "SECY-25-0018 Weekly Information Report Week Ending March 7 2025.pdf", "WEEKLY REPORT")

if __name__ == "__main__":
    main()
