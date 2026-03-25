from app.db.session import SessionLocal
from app.models import ApsContentDocument, ApsContentLinkage, ApsContentChunk

def verify():
    db = SessionLocal()
    # Updated IDs based on folder names in Phase 7A run
    # 0000_0b52fb0f -> 0b52fb0f
    # 0001_062ac4e1 -> 062ac4e1
    # 0005_5bfbc83c -> 5bfbc83c
    # 0006_c6edcf2d -> c6edcf2d
    # 0008_7894c2b8 -> 7894c2b8
    # 0013_87fafb0a -> 87fafb0a
    ids = ['0b52fb0f', '062ac4e1', '5bfbc83c', 'c6edcf2d', '7894c2b8', '87fafb0a']
    
    print("\n" + "="*80)
    print("PHASE 8 HANDOFF VERIFICATION: 6-FILE SUBSET")
    print("="*80)
    
    for cid in ids:
        doc = db.query(ApsContentDocument).filter_by(content_id=cid).first()
        status = "PASSED" if doc else "FAILED"
        chunks = doc.chunk_count if doc else 0
        link = db.query(ApsContentLinkage).filter_by(content_id=cid).first()
        
        # Verify source provenance
        ref = link.content_units_ref if link else "MISSING"
        provenance_ok = "YES" if ref != "MISSING" and "run_20260314_010136" in ref else "NO"
        
        # Check specific chunk count for one doc
        # 0b52fb0f has 1045 lines in total, ordered_units count was visible in summary
        print(f"Content ID: {cid:10} | Stats: {status:7} | Chunks: {chunks:4} | Provenance: {provenance_ok:3} | Ref: {Path(ref).name if ref != 'MISSING' else 'N/A'}")

    # Aggregated stats
    total_docs = db.query(ApsContentDocument).count()
    total_chunks = db.query(ApsContentChunk).count()
    print("="*80)
    print(f"TOTAL DB STATE: Documents: {total_docs} | Chunks: {total_chunks}")
    print("="*80)

if __name__ == "__main__":
    from pathlib import Path
    verify()
