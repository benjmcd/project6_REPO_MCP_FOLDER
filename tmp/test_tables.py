import sys
from pathlib import Path
import fitz

def test_tables():
    sample_path = Path(r"C:\Users\benny\OneDrive\Desktop\Project6\data_demo\ML17123A319.pdf")
    doc = fitz.open(sample_path)
    
    print(f"Testing tables in: {sample_path.name}")
    for page in doc:
        tabs = page.find_tables()
        if tabs.tables:
            print(f"Page {page.number + 1}: Found {len(tabs.tables)} tables")
            for i, tab in enumerate(tabs.tables):
                print(f"  Table {i+1} bbox: {tab.bbox}")
                # Print a few rows
                rows = tab.extract()
                for r in rows[:3]:
                    print(f"    {r}")
        
    doc.close()

if __name__ == "__main__":
    test_tables()
