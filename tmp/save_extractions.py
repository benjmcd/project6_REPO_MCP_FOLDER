import sys
from pathlib import Path

# Add backend to sys.path
backend_path = Path(r"c:\Users\benny\OneDrive\Desktop\Project6\backend")
sys.path.insert(0, str(backend_path))

from app.services import nrc_aps_document_processing as dp

def save_extraction(file_path: Path, output_file: Path):
    with open(file_path, "rb") as f:
        content = f.read()
    result = dp.process_document(content=content, declared_content_type="application/pdf")
    text = result.get("normalized_text", "")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Saved: {output_file.name}")

def main():
    root = Path(r"C:\Users\benny\OneDrive\Desktop\Project6\data_demo\nrc_adams_documents_for_testing")
    tmp = Path(r"C:\Users\benny\OneDrive\Desktop\Project6\tmp")
    
    save_extraction(root / "handbook_documents_for_testing" / "ML24157A089.pdf", tmp / "extraction_handbook.txt")
    save_extraction(root / "weekly_information_report_documents_for_testing" / "SECY-25-0018 Weekly Information Report Week Ending March 7 2025.pdf", tmp / "extraction_weekly_report.txt")

if __name__ == "__main__":
    main()
