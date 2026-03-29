import sqlite3
import json

conn = sqlite3.connect("C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/storage_test_runtime/lc_e2e/20260328_150207/lc.db")
c = conn.cursor()

c.execute("SELECT connector_run_target_id, connector_run_id, source_reference_json FROM connector_run_target")
non_pdf = 0
for row in c.fetchall():
    t_id, r_id, src_str = row
    src_ref = json.loads(src_str) if src_str else {}
    
    media_type = (src_ref.get("aps_normalized") or {}).get("media_type")
        
    print(f"Target: {t_id}, Run: {r_id}, Media: {media_type}")
    if media_type != "application/pdf":
        non_pdf += 1

print(f"\nTotal non-PDF targets: {non_pdf}")

c.execute("SELECT count(*) FROM dataset_row")
print(f"DatasetRow rows: {c.fetchone()[0]}")

c.execute("SELECT count(*) FROM dataset_source_provenance")
print(f"DatasetSourceProvenance rows: {c.fetchone()[0]}")

c.execute("SELECT count(*) FROM analysis_artifact")
print(f"AnalysisArtifact rows: {c.fetchone()[0]}")
