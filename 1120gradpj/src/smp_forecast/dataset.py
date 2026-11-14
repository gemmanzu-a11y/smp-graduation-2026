"""Daily origins, 72 direct targets. Never use target-day realized observations.

Historical source publication vintages are unavailable: retrospective evaluation is
explicitly different from certified point-in-time operational forecasting.
"""
import json,hashlib
import numpy as np
import pandas as pd
from .http import ROOT,write_json,now
VARIABLES=['smp','demand_mw','reserve_rate_pct','solar_mwh','wind_mwh','temperature_c','solar_radiation_mj_m2','wind_ms']
def config():return json.loads((ROOT/'configs/experiment.json').read_text())
def read_time(name):
 f=pd.read_csv(ROOT/'data/processed'/name);f.timestamp=pd.to_datetime(f.timestamp,utc=True).dt.tz_convert('Asia/Seoul');return f

def build_hourly():
 smp=read_time('smp_hourly.csv');assert not smp.timestamp.duplicated().any()
 index=pd.date_range(smp.timestamp.min(),smp.timestamp.max(),freq='h');base=smp.set_index('timestamp')[['smp']].reindex(index);base.index.name='timestamp'
 for filename,cols in [('power_hourly.csv',['demand_mw','reserve_rate_pct']),('renewable_hourly.csv',['solar_mwh','wind_mwh']),('weather_hourly.csv',['temperature_c','solar_radiation_mj_m2','wind_ms'])]:
  path=ROOT/'data/processed'/filename
  if not path.exists():
   for c in cols:base[c]=np.nan
   continue
  f=read_time(filename).set_index('timestamp')
  if f.index.duplicated().any():raise ValueError('duplicate '+filename)
  for c in cols:base[c]=f[c].reindex(index) if c in f else np.nan
 base.to_csv(ROOT/'data/processed/hourly_dataset.csv')
 availability={c:dict(nonmissing=int(base[c].notna().sum()),missing=int(base[c].isna().sum()),first_valid=str(base[c].first_valid_index()),last_valid=str(base[c].last_valid_index())) for c in VARIABLES}
 write_json(ROOT/'reports/data_quality.json',dict(at=now(),rows=len(base),start=str(index.min()),end=str(index.max()),variables=availability,geography={'smp':'mainland','power':'EPSIS current-load display; mainland-only geographic scope not independently certified','renewable':'mainland market participants only; excludes nonmarket/BTM','weather':'equal mean of ASOS108/133/143/156/159/105; not population weighted'},fuel='Monthly LNG collected separately; unknown historical release dates excluded from model',calendar='See holiday_sources.json; fallback must not be called authenticated API data'))
 return base

def calendar_features(targets,origin,holidays):
 h=targets.hour.to_numpy();dow=targets.dayofweek.to_numpy();doy=targets.dayofyear.to_numpy();ahead=(targets.normalize()-origin.normalize()).days.to_numpy()
 return np.column_stack([ahead,h/23,np.sin(h*2*np.pi/24),np.cos(h*2*np.pi/24),np.sin(dow*2*np.pi/7),np.cos(dow*2*np.pi/7),np.sin(doy*2*np.pi/365.25),np.cos(doy*2*np.pi/365.25),(dow>=5).astype(float),[float(str(t.date()) in holidays) for t in targets]])

def sample(base,origin,cfg,holidays):
 lookback=cfg['lookback_hours'];seqtimes=pd.date_range(end=origin,periods=lookback,freq='h');targets=pd.date_range(origin.normalize()+pd.Timedelta(days=1),periods=72,freq='h');seq=[];source_max=[]
 for v in VARIABLES:
  lag=0 if v=='smp' else cfg['renewable_lag_hours'] if v in ('solar_mwh','wind_mwh') else cfg['observation_lag_hours']
  times=seqtimes-pd.Timedelta(hours=lag)
  assert times.max()<=origin
  seq.append(base[v].reindex(times).to_numpy(dtype=np.float32));source_max.append(times.max())
 sequence=np.column_stack(seq).astype('float32')
 # Same origin-day price profile is known only retrospectively; do not input tomorrow's SMP.
 prev=base.smp.reindex(origin.normalize()+pd.to_timedelta(targets.hour,unit='h')).to_numpy(dtype=np.float32)
 weekly_times=targets-pd.Timedelta(days=7);assert weekly_times.max()<=origin
 weekly=base.smp.reindex(weekly_times).to_numpy(dtype=np.float32)
 # Fuel enters only when an evidenced publication time <= origin exists, never by same-month join.
 fuel_value=np.nan;fuel_month_age=np.nan
 fuelpath=ROOT/'data/processed/fuel_monthly.csv'
 if fuelpath.exists():
  fuel=pd.read_csv(fuelpath);published=pd.to_datetime(fuel.publicly_released_at,utc=True,errors='coerce');eligible=fuel[published.notna() & (published<=origin.tz_convert('UTC'))]
  if not eligible.empty:
   row=eligible.sort_values('month').iloc[-1];fuel_value=float(row.lng_fuel_cost_krw_kwh);fuel_month_age=(origin.year-int(row.month[:4]))*12+origin.month-int(row.month[5:7])
 context=np.column_stack([calendar_features(targets,origin,holidays),prev,weekly,np.tile(np.mean(np.isnan(sequence),axis=0),(72,1)),np.full(72,fuel_value),np.full(72,fuel_month_age)])
 full=np.concatenate([np.tile(sequence.reshape(1,-1),(72,1)),context],axis=1).astype('float32')
 y=base.smp.reindex(targets).to_numpy(dtype=np.float32)
 meta=pd.DataFrame({'origin':origin,'timestamp':targets,'horizon_days':np.repeat([1,2,3],24),'hour':targets.hour,'baseline_last_origin_day':prev,'baseline_weekly':weekly,'latest_source_timestamp':max(source_max)})
 return sequence,context,full,y,meta

def split_for(targets,cfg):
 lo=targets.min().date().isoformat();hi=targets.max().date().isoformat()
 if hi<=cfg['train_target_end']:return 'train'
 if lo>=cfg['validation_target_start'] and hi<=cfg['validation_target_end']:return 'validation'
 if lo>=cfg['test_target_start'] and hi<=cfg['test_target_end']:return 'test'
 return None

def build():
 cfg=config();base=build_hourly();holidays=set(pd.read_csv(ROOT/'data/processed/holidays.csv').date)
 starts=base.index.min().normalize()+pd.Timedelta(days=8);end=pd.Timestamp(cfg['test_target_end'],tz='Asia/Seoul')-pd.Timedelta(days=3)
 result={k:[] for k in ['sequences','contexts','x','y','metadata','daily_splits']};skipped=[]
 for day in pd.date_range(starts,end,freq='D'):
  origin=day+pd.Timedelta(hours=23);seq,context,x,y,meta=sample(base,origin,cfg,holidays);split=split_for(meta.timestamp,cfg)
  if split is None:continue
  if not np.isfinite(y).all() or not np.isfinite(x[:,:cfg['lookback_hours']*len(VARIABLES)]).any():skipped.append(str(day.date()));continue
  # At least an observed SMP input for each history slot. Exogenous NaN stays explicit.
  if not np.isfinite(seq[:,0]).all():skipped.append(str(day.date()));continue
  meta['split']=split;meta['day_id']=len(result['y']);result['sequences'].append(seq);result['contexts'].append(context);result['x'].append(x);result['y'].append(y);result['metadata'].append(meta);result['daily_splits'].append(split)
 X=np.concatenate(result['x']);Y=np.stack(result['y']);metadata=pd.concat(result['metadata'],ignore_index=True);seq=np.stack(result['sequences']);context=np.stack(result['contexts']);dailysplits=np.asarray(result['daily_splits']);daily_origin=np.asarray([str(t) for t in metadata.groupby('day_id',sort=True).origin.first()])
 names=[f'lagseq_{i:03d}_{v}' for i in range(cfg['lookback_hours']) for v in VARIABLES]+['horizon_days','target_hour','hour_sin','hour_cos','dow_sin','dow_cos','year_sin','year_cos','is_weekend','is_holiday','origin_day_smp_same_hour','weekly_smp_same_hour']+[v+'_history_missing_fraction' for v in VARIABLES]+['lng_fuel_cost_asof','lng_month_age']
 assert X.shape[1]==len(names);assert len(metadata)==Y.size
 # All models receive identical X. LSTM reshapes the same history block into a sequence.
 folder=ROOT/'data/processed';np.savez_compressed(folder/'training_dataset.npz',x=X,y=Y,sequences=seq,contexts=context,daily_splits=dailysplits,daily_origin=daily_origin)
 metadata.to_csv(folder/'training_metadata.csv',index=False);write_json(folder/'feature_names.json',names)
 fingerprint=hashlib.sha256(X.tobytes()+Y.tobytes()).hexdigest();write_json(ROOT/'reports/dataset_manifest.json',dict(at=now(),fingerprint=fingerprint,feature_count=len(names),lookback_hours=cfg['lookback_hours'],daily_samples=len(Y),hourly_target_rows=len(metadata),splits=metadata.groupby('split').size().to_dict(),origin_counts={str(k):int(v) for k,v in pd.Series(dailysplits).value_counts().items()},target_ranges={k:dict(first=str(g.timestamp.min()),last=str(g.timestamp.max()),origins=int(g.origin.nunique())) for k,g in metadata.groupby('split')},excluded_days=skipped,publication_status=cfg['historical_mode'],fuel_used=bool(np.isfinite(X[:,-2]).any()),target_future_realizations_used=False,config=cfg))
 # Future issue at the most recent completed daily 23:00 origin whose price profile exists.
 latest_day=base.smp.dropna().index.max().normalize();origin=latest_day+pd.Timedelta(hours=23);s,c,x,y,m=sample(base,origin,cfg,holidays)
 np.savez_compressed(folder/'latest_inputs.npz',x=x,sequences=s[None],contexts=c[None]);m.to_csv(folder/'latest_metadata.csv',index=False)
 print(json.dumps(dict(features=len(names),days=len(Y),rows=len(metadata),split_rows=metadata.groupby('split').size().to_dict(),latest_origin=str(origin)),ensure_ascii=False),flush=True)
 return X,Y,metadata
