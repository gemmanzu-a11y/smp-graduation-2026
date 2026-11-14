"""Refresh inference artifacts from existing weights; never refit or change test predictions."""
import sys,json,subprocess,os
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from smp_forecast.inference import input_gate
from smp_forecast.http import write_json,now
from smp_forecast.training import algorithm
from smp_forecast.dataset import config
cfg=config()
if len(sys.argv)==1:
 for name in cfg['models']:
  subprocess.run([sys.executable,__file__,name],check=True,env={**os.environ,'OMP_NUM_THREADS':'4','OPENBLAS_NUM_THREADS':'4'})
 raise SystemExit(0)
latest=np.load(ROOT/'data/processed/latest_inputs.npz');gate=input_gate(latest['x'],cfg['lookback_hours'])
for name in sys.argv[1:]:
 p=ROOT/'models'/name/'artifacts';write_json(p/'latest_forecast_status.json',dict(**gate,checked_at=now()))
 if not gate['can_predict']:
  for filename in ('latest_forecast.csv','inference_forecast.csv'):(p/filename).unlink(missing_ok=True)
 f=pd.read_csv(p/'predictions.csv');ref=f[f.origin==f[f.split=='test'].origin.max()].copy();ref['forecast_status']='historical_test_replay';ref.to_csv(p/'reference_forecast.csv',index=False)
 # Reload each actual serialized estimator and verify an offline 72-hour reference.
 d=np.load(ROOT/'data/processed/training_dataset.npz');meta=pd.read_csv(ROOT/'data/processed/training_metadata.csv');idx=meta.origin==ref.origin.iloc[0];x=d['x'][idx.to_numpy()];pre=joblib.load(p/'preprocessor.joblib');z=pre['imputer'].transform(x);z=pre['scaler'].transform(z) if pre['scaler'] else z;z=np.asarray(z,dtype=np.float32);m=algorithm(name).Estimator.load(p/'model.pt') if name=='lstm' else joblib.load(p/'model.joblib');np.testing.assert_allclose(m.predict(z),ref.predicted_smp.to_numpy(),rtol=1e-5,atol=1e-4)
 r=json.loads((p/'run.json').read_text());r['latest_forecast_status']=gate['status'];r['latest_forecast_model']='blocked: complete solar/wind history absent; reference_forecast.csv is historical test replay';r['historical_reference_roundtrip']='passed';r['source_code_sha256']={str(file.relative_to(ROOT)):__import__('hashlib').sha256(file.read_bytes()).hexdigest() for file in [ROOT/'models'/name/'algorithm.py',ROOT/'src/smp_forecast/dataset.py',ROOT/'src/smp_forecast/training.py']};write_json(p/'run.json',r);print(name,'reference PASS; latest',gate['status'],flush=True)
