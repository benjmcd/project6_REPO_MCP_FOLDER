import sys
from pathlib import Path
import fitz

def inspect_pdf_elements():
    sample_path = Path(r"C:\Users\benny\OneDrive\Desktop\Project6\data_demo\ML17123A319.pdf")
    doc = fitz.open(sample_path)
    
    print(f"Inspecting: {sample_path.name}")
    for page in doc:
        img_list = page.get_images(full=True)
        print(f"Page {page.number + 1}: {len(img_list)} images")
        
    doc.close()

if __name__ == "__main__":
    inspect_pdf_elements()
