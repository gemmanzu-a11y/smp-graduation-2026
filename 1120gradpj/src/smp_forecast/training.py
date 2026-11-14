"""Temporal comparison with train-only preprocessing; artifacts per model folder."""
import os
os.environ.setdefault('OMP_NUM_THREADS','4');os.environ.setdefault('OPENBLAS_NUM_THREADS','4');os.environ.setdefault('MPLCONFIGDIR',str(__import__('pathlib').Path(__file__).resolve().parents[2]/'data/matplotlib'))
import json,time,importlib.util,hashlib,platform
import numpy as np
import pandas as pd
import joblib
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error,root_mean_squared_error,r2_score
from .http import ROOT,write_json,now
from .dataset import config,VARIABLES
from .inference import input_gate

def algorithm(name):
 spec=importlib.util.spec_from_file_location('smp_algorithm_'+name,ROOT/'models'/name/'algorithm.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
class Preprocessor:
 def __init__(self,scale):self.imputer=SimpleImputer(strategy='median',keep_empty_features=True);self.scaler=StandardScaler() if scale else None
 def fit(self,x):
  self.all_missing_features=np.flatnonzero(np.isnan(x).all(axis=0)).tolist();z=self.imputer.fit_transform(x)
  if self.scaler:self.scaler.fit(z)
  return self
 def transform(self,x):
  z=self.imputer.transform(x)
  if self.scaler:z=self.scaler.transform(z)
  return np.asarray(z,dtype=np.float32)

def scores(frame):
 rows=[]
 for split,f in frame.groupby('split'):
  for h,g in [('all',f)]+[(str(int(h)),g) for h,g in f.groupby('horizon_days')]:
   y=g.actual_smp.to_numpy();p=g.predicted_smp.to_numpy();rows.append(dict(split=split,horizon_days=h,rows=len(g),origins=int(g.origin.nunique()),MAE=float(mean_absolute_error(y,p)),RMSE=float(root_mean_squared_error(y,p)),R2=float(r2_score(y,p))))
 return rows

def plot_results(frame,out,name):
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 plt.rcParams.update({'font.size':12,'axes.spines.top':False,'axes.spines.right':False})
 f=frame[frame.split=='test'];daily=f[f.horizon_days==1].groupby('origin').apply(lambda g:float(np.mean(np.abs(g.actual_smp-g.predicted_smp))),include_groups=False);origin=daily.sort_index().index[len(daily)//2];day=f[f.origin==origin]
 fig,ax=plt.subplots(figsize=(12,4));ax.plot(np.arange(72),day.actual_smp,label='Actual',color='#182f46');ax.plot(np.arange(72),day.predicted_smp,label=name,color='#008b80');ax.set(xlabel='Hours from next-day 00:00 (D+1 / D+2 / D+3)',ylabel='SMP (KRW/kWh)',title=f'{name}: origin {origin}');ax.legend();fig.tight_layout();fig.savefig(out/'example_72h.png',dpi=150);plt.close(fig)
 error=f.assign(abs_error=lambda x:abs(x.actual_smp-x.predicted_smp)).groupby(['horizon_days','hour']).abs_error.mean().reset_index();error.to_csv(out/'hourly_mae.csv',index=False)
 fig,ax=plt.subplots(figsize=(10,4))
 for h,g in error.groupby('horizon_days'):ax.plot(g.hour,g.abs_error,label=f'D+{h}')
 ax.set(xlabel='KST hour',ylabel='MAE (KRW/kWh)',title=name+' hourly errors');ax.legend();fig.tight_layout();fig.savefig(out/'hourly_mae.png',dpi=150);plt.close(fig)

def run(name):
 raise SystemExit('기존 부분 입력 학습기는 비활성화했습니다. 새 SARIMAX는 models/sarimax/train.py를 사용하세요. 다른 모델의 공통 입력 연결은 별도 작업입니다.')
 cfg=config();out=ROOT/'models'/name/'artifacts';out.mkdir(parents=True,exist_ok=True);started=time.monotonic();np.random.seed(cfg['seed'])
 data=np.load(ROOT/'data/processed/training_dataset.npz');x=data['x'];y=data['y'].reshape(-1);meta=pd.read_csv(ROOT/'data/processed/training_metadata.csv');splits=meta.split.to_numpy();train=splits=='train';validation=splits=='validation';test=splits=='test';assert train.any() and validation.any() and test.any()
 pre=Preprocessor(scale=name in ('lstm','linear_regression')).fit(x[train]);trainx=pre.transform(x[train]);valx=pre.transform(x[validation]);module=algorithm(name)
 print(name,'fit',trainx.shape,'validation',valx.shape,flush=True)
 if name=='lstm':model=module.Estimator(cfg['models'][name],cfg['lookback_hours'],len(VARIABLES),cfg['seed'],cfg['n_jobs']);model.fit(trainx,y[train],valx,y[validation]);model.save(out/'model.pt');write_json(out/'training_history.json',model.history)
 else:model=module.create(cfg['models'][name],cfg['seed'],cfg['n_jobs']);model.fit(trainx,y[train]);joblib.dump(model,out/'model.joblib',compress=3)
 # Persist reusable preprocessing as plain sklearn estimators, not local classes.
 joblib.dump(dict(imputer=pre.imputer,scaler=pre.scaler),out/'preprocessor.joblib')
 mask=validation|test;z=pre.transform(x[mask]);pred=model.predict(z);assert np.isfinite(pred).all();f=meta[mask].copy();f['actual_smp']=y[mask];f['predicted_smp']=pred;f['model']=name;f.to_csv(out/'predictions.csv',index=False);metrics=scores(f);pd.DataFrame(metrics).to_csv(out/'metrics.csv',index=False)
 # Round trip real saved model, 72 target block (not a fake estimator).
 restored=module.Estimator.load(out/'model.pt') if name=='lstm' else joblib.load(out/'model.joblib');np.testing.assert_allclose(restored.predict(z[:72]),pred[:72],rtol=1e-5,atol=1e-4)
 latest=np.load(ROOT/'data/processed/latest_inputs.npz');gate=input_gate(latest['x'],cfg['lookback_hours']);write_json(out/'latest_forecast_status.json',gate)
 if gate['can_predict']:
  future=pd.read_csv(ROOT/'data/processed/latest_metadata.csv');future['predicted_smp']=model.predict(pre.transform(latest['x']));future['model']=name;future['generated_at']=now();future['forecast_status']='research output; publication vintages unverified';future.to_csv(out/'latest_forecast.csv',index=False)
 else:
  for filename in ('latest_forecast.csv','inference_forecast.csv'):(out/filename).unlink(missing_ok=True)
 # A complete, reproducible 72-hour example remains available, clearly historical.
 reference=f[f.origin==f[f.split=='test'].origin.max()].copy();reference['forecast_status']='historical_test_replay';reference.to_csv(out/'reference_forecast.csv',index=False)
 plot_results(f,out,name)
 names=json.loads((ROOT/'data/processed/feature_names.json').read_text());importance=getattr(model,'feature_importances_',None)
 if importance is not None:pd.DataFrame(dict(feature=names,importance=importance)).sort_values('importance',ascending=False).to_csv(out/'feature_importance.csv',index=False)
 if name=='linear_regression':pd.DataFrame(dict(feature=names,coefficient=model.coef_)).to_csv(out/'coefficients.csv',index=False)
 elapsed=time.monotonic()-started;manifest=json.loads((ROOT/'reports/dataset_manifest.json').read_text());record=dict(model=name,status='completed',generated_at=now(),seconds=elapsed,dataset_fingerprint=manifest['fingerprint'],parameters=cfg['models'][name],seed=cfg['seed'],train_rows=int(train.sum()),validation_rows=int(validation.sum()),test_rows=int(test.sum()),all_missing_training_features=[names[i] for i in pre.all_missing_features],metrics=metrics,model_selection='fixed hyperparameters; LSTM epoch selected on validation MAE only',saved_model_roundtrip='passed',historical_release_status=cfg['historical_mode'],fuel_used=manifest['fuel_used'],test_not_used_for_fit=True,latest_forecast_model='same frozen evaluation model; not refitted on test or 2026',python=platform.python_version())
 write_json(out/'run.json',record);print(name,'DONE',round(elapsed,2),'seconds',json.dumps([r for r in metrics if r['split']=='test'],ensure_ascii=False),flush=True);return record
