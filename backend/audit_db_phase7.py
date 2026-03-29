import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database import SessionLocal
from app.models.models import ConnectorRunTarget

db = SessionLocal()

print("== Targets and their media types ==")
non_pdf = []
targets = db.query(ConnectorRunTarget).all()
for t in targets:
    src_ref = t.source_reference_json or {}
    blob_ref = t.blob_reference_json or {}
    
    media_type = blob_ref.get("content_type")
    if not media_type:
        media_type = (src_ref.get("aps_normalized") or {}).get("media_type")
        
    print(f"Target: {t.id}, Run ID: {t.connector_run_id}, Media: {media_type}")
    if media_type != "application/pdf":
        non_pdf.append(t)
        
print(f"\nFound {len(non_pdf)} non-PDF targets.")

print("\n== Checking downstream usage ==")
# In this app, downsteam usage might be dataset rows, annotation windows, etc.
# Are any of the review_nrc_aps routes fetching downstream usage? No, not yet.
# Is downstream usage populated in `trace_completeness.has_downstream_usage`? 
# In `review_nrc_aps_document_trace.py`: "has_downstream_usage": False.
# If I look at the DB schema, maybe there are DatasetRow or AnalysisArtifact.
from app.models.models import AnalysisArtifact, DatasetSourceProvenance
has_analysis = db.query(AnalysisArtifact).count()
has_provenance = db.query(DatasetSourceProvenance).count()
print(f"AnalysisArtifact rows: {has_analysis}")
print(f"DatasetSourceProvenance rows: {has_provenance}")

