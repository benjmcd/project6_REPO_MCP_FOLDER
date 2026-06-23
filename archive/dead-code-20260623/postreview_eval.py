from __future__ import annotations
import io, json, os, sys, zipfile, random
from pathlib import Path
import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
ROOT = Path('/mnt/data/repo_work')
BACKEND = ROOT / 'backend'
sys.path.insert(0, str(BACKEND))
os.environ['DATABASE_URL'] = 'sqlite:///./postreview_eval.db'
os.environ['STORAGE_DIR'] = str(BACKEND / 'app' / 'storage_postreview_eval')
from main import app
from app.api.deps import get_db
from app.db.session import Base
engine = create_engine('sqlite:///./postreview_eval.db', connect_args={'check_same_thread': False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)
zips = [Path('/mnt/data/Salient_Commodity_Data_Release_Grouped.zip'), Path('/mnt/data/mcs2024.zip'), Path('/mnt/data/mcs2025.zip')]
salient=[]; other=[]
for zpath in zips:
    with zipfile.ZipFile(zpath) as zf:
        for name in zf.namelist():
            if not name.lower().endswith('.csv'):
                continue
            rec={'archive':zpath.name,'file':name,'bucket':'salient' if 'salient' in name.lower() else 'other'}
            (salient if rec['bucket']=='salient' else other).append(rec)
random.seed(0)
other_sample=random.sample(other, min(25,len(other)))
selected=salient+other_sample
print('selected', len(selected), 'salient', len(salient), 'other_sample', len(other_sample), flush=True)
results=[]
for idx,item in enumerate(selected, start=1):
    if idx%20==0:
        print('progress', idx, '/', len(selected), flush=True)
    zpath=Path('/mnt/data')/item['archive']
    with zipfile.ZipFile(zpath) as zf:
        data=zf.read(item['file'])
    row=dict(item)
    resp=client.post('/api/v1/sources/upload', files={'file': (Path(item['file']).name, io.BytesIO(data), 'text/csv')}, data={'name':Path(item['file']).stem,'description':item['file'],'domain_pack':'commodity'})
    row['upload_status']=resp.status_code
    if resp.status_code!=200:
        row['error']=resp.text; results.append(row); continue
    p=resp.json(); dataset_id=p['dataset_id']; version_id=p['dataset_version_id']
    pr=client.post(f'/api/v1/datasets/{dataset_id}/versions/{version_id}/profile', json={'detect_seasonality': True, 'detect_stationarity': True})
    row['profile_status']=pr.status_code
    if pr.status_code!=200:
        row['error']=pr.text; results.append(row); continue
    profiles=pr.json(); row['stationarity_tested_count']=sum(1 for x in profiles if x.get('stationarity_hint') not in (None,'not_tested'))
    rr=client.post(f'/api/v1/datasets/{dataset_id}/versions/{version_id}/transformations/recommend')
    row['recommend_status']=rr.status_code
    if rr.status_code!=200:
        row['error']=rr.text; results.append(row); continue
    recs=rr.json(); steps=[{'variable_name':r['variable_name'],'method_name':r['recommended_method'],'parameters':{},'rationale':r['rationale']} for r in recs[:min(5,len(recs))]]
    if steps:
        ar=client.post(f'/api/v1/datasets/{dataset_id}/versions/{version_id}/transformations/apply', json={'version_label':'scaled_v1','rationale':'eval','steps':steps})
        row['transform_status']=ar.status_code
        if ar.status_code!=200:
            row['error']=ar.text; results.append(row); continue
        transformed_version_id=ar.json()['output_dataset_version_id']
    else:
        row['transform_status']=204; transformed_version_id=version_id
    an=client.post('/api/v1/analysis-runs', json={'dataset_version_id': transformed_version_id, 'method_name': 'cross_correlation', 'goal_type': 'exploratory', 'parameters': {'max_lag': 2}, 'annotation_window_id': None})
    row['analysis_status']=an.status_code
    if an.status_code==200:
        a=an.json(); row['artifact_count']=len(a['artifacts']); row['caveat_count']=len(a['caveats']); row['assumption_count']=len(a['assumptions']); row['route_reason']=a['route_reason']
    else:
        row['error']=an.text
    results.append(row)

df=pd.DataFrame(results)
out_base=Path('/mnt/data/postreview_eval')
df.to_csv(str(out_base)+'.csv', index=False)
Path(str(out_base)+'.json').write_text(json.dumps(results, indent=2))
summary=[]
summary.append(f"total={len(df)}")
for col in ['upload_status','profile_status','recommend_status','transform_status','analysis_status']:
    if col in df.columns:
        summary.append(f"{col}="+json.dumps({int(k):int(v) for k,v in df[col].fillna(-1).astype(int).value_counts().sort_index().to_dict().items()}))
summary.append('bucket_success='+df.groupby('bucket')[['upload_status','analysis_status']].apply(lambda g: {'upload_200':int((g.upload_status==200).sum()),'analysis_200':int((g.analysis_status==200).sum()),'n':int(len(g))}).to_json())
Path(str(out_base)+'_summary.txt').write_text('\n'.join(summary))
print('\n'.join(summary), flush=True)
