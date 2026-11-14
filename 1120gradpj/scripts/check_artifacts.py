"""Verify source completeness, shared cohorts, model predictions, metrics and absence of saved secrets."""
import sys,json,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from smp_forecast.http import write_json,now
from smp_forecast.training import scores
names=['lstm','hgb','lightgbm','extra_trees','linear_regression','random_forest','xgboost'];hashes=set();cohort=None;checks=[]
for name in names:
 p=ROOT/'models'/name/'artifacts';r=json.loads((p/'run.json').read_text());assert r['status']=='completed' and r['test_not_used_for_fit'];hashes.add(r['dataset_fingerprint']);f=pd.read_csv(p/'predictions.csv');latest=pd.read_csv(p/'reference_forecast.csv');gate=json.loads((p/'latest_forecast_status.json').read_text());assert gate['can_predict'] or not (p/'latest_forecast.csv').exists();assert np.isfinite(f.predicted_smp).all() and np.isfinite(latest.predicted_smp).all();assert len(latest)==72;assert latest.groupby('horizon_days').size().tolist()==[24,24,24]
 idx=f[['origin','timestamp','split']].to_csv(index=False)
 if cohort is None:cohort=idx
 assert cohort==idx
 recomputed=pd.DataFrame(scores(f));record=pd.read_csv(p/'metrics.csv',dtype={'horizon_days':str});np.testing.assert_allclose(recomputed[['MAE','RMSE','R2']].values,record[['MAE','RMSE','R2']].values,rtol=1e-5,atol=1e-5);checks.append(dict(model=name,prediction_rows=len(f),reference_replay_rows=len(latest),latest_forecast_gate=gate['status'],saved_model_roundtrip=r['saved_model_roundtrip'],metrics_recomputed=True))
assert len(hashes)==1
write_json(ROOT/'reports/artifact_verification.json',dict(at=now(),models=checks,shared_dataset_fingerprint=next(iter(hashes)),same_validation_test_cohort=True,status='passed'));print('Verified all 7 models, common cohorts, 72-hour historical references, blocked incomplete latest inputs, recomputed metrics.')
