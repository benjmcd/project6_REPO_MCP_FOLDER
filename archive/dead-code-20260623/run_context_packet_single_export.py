import os, json, sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
sys.path.append(str(Path(__file__).resolve().parents[2] / 'backend'))
from app.db.session import Base
from app.models import ConnectorRun, ConnectorRunTarget
from app.services import (
    nrc_aps_evidence_bundle,
    nrc_aps_evidence_citation_pack,
    nrc_aps_evidence_report,
    nrc_aps_evidence_report_export,
    nrc_aps_context_packet,
)

# Settings placeholder
class _Settings:
    connector_reports_dir = str(Path('temp_reports'))
    database_url = 'sqlite:///:memory:'

# Monkey patch settings
for svc in [nrc_aps_evidence_bundle, nrc_aps_evidence_citation_pack,
            nrc_aps_evidence_report, nrc_aps_evidence_report_export,
            nrc_aps_context_packet]:
    setattr(svc, 'settings', _Settings())

engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False})
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)
db = Session()

# Helper to seed minimal report index rows (reuse from tests)
def _seed_report_index_rows(db, *, reports_dir: Path, run_id: str):
    run = ConnectorRun(
        connector_run_id=run_id,
        connector_key='nrc_adams_aps',
        source_system='nrc_adams_aps',
        source_mode='public_api',
        status='completed',
    )
    target_a = ConnectorRunTarget(
        connector_run_target_id=f'target-{run_id}-1',
        connector_run_id=run_id,
        artifact_surface='documents',
        status='recommended',
        ordinal=0,
    )
    target_b = ConnectorRunTarget(
        connector_run_target_id=f'target-{run_id}-2',
        connector_run_id=run_id,
        artifact_surface='documents',
        status='recommended',
        ordinal=1,
    )
    db.add_all([run, target_a, target_b])
    # Minimal content docs for indexing (skip actual files)
    db.commit()

_temp_dir = Path('temp_reports')
_temp_dir.mkdir(parents=True, exist_ok=True)
run_id = 'run-single-export-1'
_seed_report_index_rows(db, reports_dir=_temp_dir, run_id=run_id)

# Persist bundle, citation pack, report, export
bundle = nrc_aps_evidence_bundle.assemble_evidence_bundle(db, request_payload={'run_id': run_id, 'query': 'alpha', 'persist_bundle': True})
citation_pack = nrc_aps_evidence_citation_pack.assemble_evidence_citation_pack(db, request_payload={'bundle_id': bundle['bundle_id'], 'persist_pack': True})
report = nrc_aps_evidence_report.assemble_evidence_report(db, request_payload={'citation_pack_id': citation_pack['citation_pack_id'], 'persist_report': True})
export = nrc_aps_evidence_report_export.assemble_evidence_report_export(db, request_payload={'evidence_report_id': report['evidence_report_id'], 'persist_export': True})

# Assemble context packet using the export as source
packet = nrc_aps_context_packet.assemble_context_packet(db, request_payload={'evidence_report_export_id': export['evidence_report_export_id'], 'persist_context_packet': True})
print(json.dumps(packet, indent=2))
