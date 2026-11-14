"""Predict with a saved model without training. Offline by default; receipts stay explicit."""
import sys,argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from smp_forecast.training import algorithm
from smp_forecast.http import now,write_json
from smp_forecast.inference import input_gate
from smp_forecast.dataset import config,build_hourly,sample
p=argparse.ArgumentParser();p.add_argument('--model',choices=['lstm','lightgbm','xgboost'],required=True);p.add_argument('--origin',help='Reference origin in KST, e.g. 2026-11-13T23:00:00+09:00. Not an actual past issuance claim.');a=p.parse_args();out=ROOT/'models'/a.model/'artifacts'
if a.origin:
 origin=pd.Timestamp(a.origin);origin=origin.tz_localize('Asia/Seoul') if origin.tzinfo is None else origin.tz_convert('Asia/Seoul')
 if origin.hour!=23 or origin.minute!=0:raise SystemExit('Origin must be daily 23:00 KST')
 base=build_hourly()
 if origin>base.index.max():raise SystemExit('Refresh source history before using this origin; no future input fabrication.')
 hol=set(pd.read_csv(ROOT/'data/processed/holidays.csv').date);_,_,x,_,meta=sample(base,origin,config(),hol)
else:x=np.load(ROOT/'data/processed/latest_inputs.npz')['x'];meta=pd.read_csv(ROOT/'data/processed/latest_metadata.csv')
gate=input_gate(x,config()['lookback_hours']);write_json(out/'inference_status.json',gate)
if not gate['can_predict']:
 (out/'inference_forecast.csv').unlink(missing_ok=True)
 print(json.dumps(gate,ensure_ascii=False,indent=2));raise SystemExit(2)
pre=joblib.load(out/'preprocessor.joblib');imputer=pre['imputer'];z=imputer.transform(x);z=pre['scaler'].transform(z) if pre['scaler'] else z;z=np.asarray(z,dtype=np.float32);m=algorithm(a.model).Estimator.load(out/'model.pt') if a.model=='lstm' else joblib.load(out/'model.joblib');meta['predicted_smp']=m.predict(z);meta['model']=a.model;meta['generated_at']=now();meta['forecast_status']='research output; not certified point-in-time issue';filename=out/'inference_forecast.csv';meta.to_csv(filename,index=False);print(filename);print(meta.groupby('horizon_days').predicted_smp.agg(['min','mean','max']).round(3))
