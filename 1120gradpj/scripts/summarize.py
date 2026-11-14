import sys,json
from pathlib import Path
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from smp_forecast.training import scores
from smp_forecast.http import write_json,now
meta=pd.read_csv(ROOT/'data/processed/training_metadata.csv');data=np.load(ROOT/'data/processed/training_dataset.npz');meta['actual_smp']=data['y'].reshape(-1);metrics=[]
for file in sorted((ROOT/'models').glob('*/artifacts/metrics.csv')):
 if file.parents[1].name not in ['sarimax','lstm','xgboost','lightgbm']:continue
 f=pd.read_csv(file,dtype={'horizon_days':str});f['model']=file.parents[1].name;metrics.append(f)
for name,col in [('last_origin_day','baseline_last_origin_day'),('weekly','baseline_weekly')]:
 f=meta[meta.split.isin(['validation','test'])].copy();f['predicted_smp']=f[col];f=f[np.isfinite(f.predicted_smp)];m=pd.DataFrame(scores(f));m['model']=name;metrics.append(m)
if not metrics:raise SystemExit('No completed results')
summary=pd.concat(metrics,ignore_index=True);summary.to_csv(ROOT/'reports/model_comparison.csv',index=False)
# Rank on validation, never retrospectively choose model using test.
v=summary[(summary.split=='validation') & (summary.horizon_days=='all')].sort_values('MAE');write_json(ROOT/'reports/validation_selection.json',dict(at=now(),selected=v.iloc[0].model,selection_metric='validation pooled D+1..D+3 MAE',ranking=v.to_dict('records')))
test=summary[(summary.split=='test') & (summary.horizon_days!='all')].pivot(index='model',columns='horizon_days',values='MAE');print('TEST MAE (KRW/kWh)\n'+test.round(3).to_string())
