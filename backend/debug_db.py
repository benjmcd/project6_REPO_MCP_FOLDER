import sqlite3
import sys

run_id = sys.argv[1] if len(sys.argv) > 1 else '5cd56147-4b5b-4278-8b32-79b9b1b34db5'
conn = sqlite3.connect('method_aware.db')
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM connector_run_target WHERE connector_run_id = ?", (run_id,))
print(f"Targets for {run_id}: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM aps_content_linkage WHERE run_id = ?", (run_id,))
print(f"Linkages for {run_id}: {cur.fetchone()[0]}")

conn.close()
