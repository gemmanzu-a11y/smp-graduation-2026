"""Run the frozen E3 SARIMAX on a new, explicitly timestamped input snapshot.
No fitting, silent source substitution, or future SMP use. Original results untouched.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT.parent;sys.path.insert(0,str(ROOT/'src'))
from smp_forecast import common_v3 as c
from smp_forecast.http import write_json
OUT=ROOT/'data/live_20261120';SHARED=WORK/'SMP_SHARED_DATA/versions'/c.VERSION
ORIGIN=pd.Timestamp('2026-11-19 23:00',tz=c.TZ);CUTOFF=ORIGIN-pd.Timedelta(hours=72)
MODEL_ROOT=OUT/'frozen_model'

def read(path,index='timestamp'):
    f=pd.read_csv(path);f.index=c.times(f.pop(index));return f

def load_inputs():
    manifest=json.loads((SHARED/'manifest.json').read_text());features=manifest['context_features']
    old=read(SHARED/'hourly.csv');grid=pd.date_range(old.index.min(),CUTOFF-pd.Timedelta(hours=1),freq='h',tz=c.TZ)
    raw=old[c.HISTORY].reindex(grid);raw.index.name='timestamp';original=raw.loc[:'2025-12-31'].copy()
    def assign(frame,key,source):
        vals=pd.to_numeric(frame[source],errors='coerce');idx=frame.index.intersection(grid);idx=idx[idx.year>=2026]
        raw.loc[idx,key]=vals.reindex(idx)
    sp=read(ROOT/'data/processed/smp_hourly.csv');new=read(OUT/'smp_recent.csv');sp=pd.concat([sp,new]);sp=sp[~sp.index.duplicated(keep='last')].sort_index();assign(sp,'smp','smp')
    power=pd.concat([read(ROOT/'data/processed/power_hourly.csv'),*[read(p) for p in sorted(OUT.glob('power_*.csv'))]]);power=power[~power.index.duplicated(keep='last')].sort_index()
    for key,col in [('demand_actual','demand_mw'),('reserve_mw','reserve_mw'),('reserve_pct','reserve_rate_pct')]:
        power[col]=power[col].where(power.samples_5m.eq(12));assign(power,key,col)
    weather=pd.read_csv(ROOT/'data/processed/weather_stations.csv');weather=weather[weather.station_id.eq(108)].copy();weather.index=c.times(weather.pop('timestamp'))
    p=OUT/'asos_recent.csv'
    if p.exists():weather=pd.concat([weather,read(p)])
    weather=weather[~weather.index.duplicated(keep='last')].sort_index();weather.index-=pd.Timedelta(hours=1)
    for key,col in [('temperature_c','temperature_c'),('wind_ms','wind_ms'),('irradiance_mj_m2','solar_radiation_mj_m2')]:assign(weather,key,col)
    for path in sorted(OUT.glob('demand_*.csv')):assign(read(path),'demand_forecast_history','mlfd')
    gens=[read(p) for p in sorted(OUT.glob('generation_*.csv'))]
    if gens:
        g=pd.concat(gens).reset_index(names='t');g=g.drop_duplicates(['t','fuelTpCd'],keep='last').pivot(index='t',columns='fuelTpCd',values='amgo')
        for fuel,key in [('LNG','generation_lng'),('원자력','generation_nuclear')]:
            if fuel in g:assign(g,key,fuel)
        if {'유연탄','무연탄'}.issubset(g):g['coal']=g[['유연탄','무연탄']].sum(axis=1,min_count=2);assign(g,'generation_coal','coal')
    # Do not invent a wind series from a solar-only API. 2026 annual renewable
    # observations are absent in the current source snapshot; frozen imputation
    # and missing flags retain this limitation explicitly.
    for key in ['wind_ms','irradiance_mj_m2','solar_actual','wind_actual','generation_lng','generation_coal','generation_nuclear']:raw[key]=raw[key].where(raw[key]>=0)
    pd.testing.assert_frame_equal(original,raw.loc[:'2025-12-31'])
    history=raw.ffill(limit=24)
    for col in c.HISTORY:
        im=manifest['imputation'][col];table=im['season_hour'];fallback=[table.get(str(((t.month%12)//3,t.hour)),im['global']) for t in grid]
        history[col]=history[col].fillna(pd.Series(fallback,index=grid));history[col+'_missing']=raw[col].isna().astype(float)
    if not np.isfinite(history.to_numpy()).all():raise ValueError('Nonfinite frozen-imputed history')
    return manifest,features,raw,history

class Context:
    def __init__(self,manifest,history):
        self.m=manifest;self.h=history;self.cache={};self.fred={}
        for series in ['DCOILWTICO','DCOILBRENTEU','PNGASJPUSDM','PCOALAUUSDM']:
            p=OUT/(series+'.csv')
            if not p.exists():raise ValueError('Required 2026 vintage source missing: '+series)
            self.fred[series]=pd.concat([pd.read_csv(ROOT/'data/processed/section_c'/f'{series}_vintage_intervals.csv'),pd.read_csv(p)],ignore_index=True)
        self.lng=pd.read_csv(ROOT/'data/processed/section_c/domestic_lng_monthly.csv').set_index('month').domestic_lng_cost_krw_kwh
        if '2026-10' not in self.lng:raise ValueError('October 2026 domestic LNG missing')
        self.temp=pd.read_csv(WORK/'shared_datasets/kma_midrange_temperature_seoul/all_seoul.csv')
        p=OUT/'midrange_temperature.csv'
        if p.exists():self.temp=pd.concat([self.temp,pd.read_csv(p)],ignore_index=True)
        self.weather=pd.concat([pd.read_csv(p) for p in (WORK/'shared_datasets/kma_midrange').glob('forecast_*.csv')],ignore_index=True)
        p=OUT/'midrange_weather.csv'
        if p.exists():self.weather=pd.concat([self.weather,pd.read_csv(p)],ignore_index=True)
        self.weather=self.weather[self.weather.region.eq('서울.인천.경기')].copy()
        for frame in [self.temp,self.weather]:frame['issued']=c.times(frame.issued_at_kst);frame['date']=pd.to_datetime(frame.target_date).dt.strftime('%Y-%m-%d');frame.sort_values('issued',inplace=True)
        self.tgroups={k:v for k,v in self.temp.groupby('date')};self.wgroups={k:v for k,v in self.weather.groupby('date')}
        holidays=pd.read_csv(ROOT/'data/processed/section_a/holidays_official_2026.csv')
        if not holidays.official_api_verified.all():raise ValueError('Unofficial 2026 holiday source')
        self.holidays=set(holidays.loc[holidays.isHoliday.eq('Y'),'date'])
    def build(self,origin,target):
        cutoff=origin-pd.Timedelta(hours=72);block=pd.DataFrame(index=target)
        for name,values,period in [('hour',target.hour,24),('weekday',target.dayofweek,7),('month',target.month-1,12)]:
            block[name+'_sin']=np.sin(2*np.pi*values/period);block[name+'_cos']=np.cos(2*np.pi*values/period)
        block['season']=target.month%12//3;block['weekend']=(target.dayofweek>=5).astype(float);block['holiday']=[float(t.strftime('%Y-%m-%d') in self.holidays) for t in target]
        # Existing exact monthly workbook, fixed October value in the November demo.
        months=target.strftime('%Y-%m')
        if any(month not in self.lng and month!='2026-11' for month in months):raise ValueError('Domestic LNG month not available')
        block['lng_domestic']=[float(self.lng[month if month in self.lng else '2026-10']) for month in months]
        asof=origin.normalize()-pd.Timedelta(days=2)
        for series,frame in self.fred.items():
            key=(series,str(asof.date()))
            if key not in self.cache:self.cache[key]=c.vintage_select(frame,asof)
            block[series]=float(self.cache[key].numeric)
        window=self.h.loc[(self.h.index>=cutoff-pd.Timedelta(hours=168))&(self.h.index<cutoff)]
        if len(window)!=168:raise ValueError('Insufficient causal history window')
        for col in c.HISTORY:
            block[col+'_last']=window[col].iloc[-1];block[col+'_mean24']=window[col].iloc[-24:].mean();block[col+'_mean168']=window[col].mean();block[col+'_missing_last']=window[col+'_missing'].iloc[-1]
        for col in ['mid_tmin','mid_tmax','mid_rain']:block[col]=np.nan
        block['mid_weather']=None
        for day in target.normalize().unique():
            mask=target.normalize()==day;date=str(day.date());tt=self.tgroups.get(date,pd.DataFrame());tt=tt[tt.issued<=origin] if len(tt) else tt
            if len(tt):
                chosen=tt.iloc[-1];block.loc[mask,'mid_tmin']=float(chosen['최저기온']);block.loc[mask,'mid_tmax']=float(chosen['최고기온']);block.loc[mask,'temperature_issued_at']=chosen.issued.isoformat()
            ww=self.wgroups.get(date,pd.DataFrame());ww=ww[ww.issued<=origin] if len(ww) else ww
            for period,hours in [('AM',target.hour<12),('PM',target.hour>=12)]:
                wm=mask&hours;allowed=ww[ww.target_period.isin([period,'DAY'])] if len(ww) else ww
                if len(allowed):
                    chosen=allowed.iloc[-1];block.loc[wm,'mid_rain']=chosen.precip_probability_pct;block.loc[wm,'mid_weather']=chosen.weather_text;block.loc[wm,'weather_issued_at']=chosen.issued.isoformat()
        for col in ['mid_tmin','mid_tmax','mid_rain']:
            block[col+'_missing']=block[col].isna().astype(float);block[col]=block[col].fillna(self.m['imputation'][col]['train_median'])
        vocab=self.m['weather_categories'];block['mid_weather_missing']=block.mid_weather.isna().astype(float);block['mid_weather_unknown']=(block.mid_weather.notna()&~block.mid_weather.isin(vocab)).astype(float)
        for n,category in enumerate(vocab):block['weather_category_'+str(n)]=block.mid_weather.eq(category).astype(float)
        return block

def run():
    OUT.mkdir(exist_ok=True);m,features,raw,h=load_inputs();ctx=Context(m,h)
    future_targets=pd.date_range(ORIGIN+pd.Timedelta(hours=1),periods=72,freq='h');future=ctx.build(ORIGIN,future_targets)
    # Mirror historical prepare(): most recent daily issuance for each state hour.
    f=pd.read_csv(SHARED/'forecast_inputs.csv',usecols=['forecast_origin','target_timestamp','actual_smp',*features]);f['forecast_origin']=c.times(f.forecast_origin);f['target_timestamp']=c.times(f.target_timestamp)
    past=f.sort_values('forecast_origin').drop_duplicates('target_timestamp',keep='last').set_index('target_timestamp').sort_index()
    appended=[]
    for day in pd.date_range(pd.Timestamp('2026-01-01',tz=c.TZ),ORIGIN.normalize(),freq='D'):
        origin=day-pd.Timedelta(hours=1);target=pd.date_range(day,periods=24,freq='h');block=ctx.build(origin,target);block['actual_smp']=raw.smp.reindex(target);appended.append(block)
    hourly=pd.concat([past,pd.concat(appended)])[['actual_smp',*features]]
    if not (hourly.index.to_series().diff().iloc[1:]==pd.Timedelta(hours=1)).all():raise ValueError('State exog time gap')
    prefix=hourly[hourly.index<CUTOFF];bridge=hourly.loc[CUTOFF:ORIGIN]
    if prefix.actual_smp.isna().any():raise ValueError('Actual SMP missing in state prefix; refusing synthetic SMP')
    if not np.isfinite(hourly[features].to_numpy()).all():raise ValueError('Nonfinite state exog')
    selection=json.loads((MODEL_ROOT/'config/selection_before_test.json').read_text())
    if selection['blending']!={'baseline':'baseline_weekly','alpha':.4} or selection['correction']['mode']!='none':raise ValueError('Unexpected adopted E3 policy')
    path=MODEL_ROOT/'models/final_model.npz';expected=json.loads((MODEL_ROOT/'config/final_artifact.json').read_text())['checkpoint_sha256'];digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if digest!=expected:raise ValueError('Frozen checkpoint hash mismatch')
    spec=importlib.util.spec_from_file_location('latest_sarimax',ROOT/'models/sarimax/algorithm_v3.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);model=module.Estimator.load(path)
    model.reset(prefix.actual_smp.to_numpy(),prefix[features].to_numpy(),prefix.index[-1]);x=np.vstack([bridge[features].to_numpy(),future[features].to_numpy()]);pred,_,steps=model.predict(x,ORIGIN,CUTOFF)
    refs=future_targets-pd.Timedelta(hours=168)
    if not ((refs+pd.Timedelta(hours=1))<=CUTOFF).all():raise ValueError('Weekly baseline crosses cutoff')
    weekly=raw.smp.reindex(refs).to_numpy()
    if not np.isfinite(weekly).all():raise ValueError('Missing genuine weekly SMP baseline')
    blended=.4*pred+.6*weekly
    created=pd.Timestamp.now(tz=c.TZ);status='preliminary' if created<ORIGIN else 'issued'
    rows=pd.DataFrame(dict(forecast_origin=ORIGIN,calculated_at=created,observed_cutoff=CUTOFF,target_timestamp=future_targets,horizon=np.arange(1,73),forecast_day=np.repeat([1,2,3],24),predicted_smp=blended,sarimax_prediction=pred,weekly_baseline=weekly,weekly_reference_timestamp=refs,prediction_status=status,actual_smp=np.nan))
    rows.to_csv(OUT/'predictions.csv',index=False);future[features].to_csv(OUT/'future_features.csv');raw.loc[CUTOFF-pd.Timedelta(hours=168):].to_csv(OUT/'recent_raw_history.csv')
    latest=raw.loc[(raw.index>=CUTOFF-pd.Timedelta(hours=168))&(raw.index<CUTOFF)]
    quality=[dict(variable=col,missing_hours=int(latest[col].isna().sum()),window_hours=168,missing_pct=round(float(latest[col].isna().mean()*100),2),last_source_time=None if raw[col].last_valid_index() is None else raw[col].last_valid_index().isoformat(),imputation='frozen Train median after <=24h causal fill') for col in c.HISTORY]
    fred=[dict(series=s,value=float(ctx.cache[(s,'2026-11-17')].numeric),observation_date=ctx.cache[(s,'2026-11-17')]['date'],vintage_start=ctx.cache[(s,'2026-11-17')].realtime_start,asof_date='2026-11-17') for s in ctx.fred]
    payload=dict(schema_version=1,status=status,mode='new_forecast',model_name='SARIMAX + weekly baseline',model_weight=.4,weekly_weight=.6,dataset_version=c.VERSION,forecast_origin=ORIGIN.isoformat(),calculated_at=created.isoformat(),observed_cutoff=CUTOFF.isoformat(),target_start=future_targets[0].isoformat(),target_end=future_targets[-1].isoformat(),model_sha256=digest,feature_count=len(features),bridge_hours=steps,domestic_lng=dict(reference_month='2026-10',value=float(ctx.lng['2026-10']),unit='KRW/kWh',policy='previous month demo; differs from conditional same-month historical evaluation'),fred=fred,quality=quality,forecast_missing={col:float(future[col+'_missing'].mean()) for col in ['mid_tmin','mid_tmax','mid_rain']},forecast_issued_values={col:sorted(future[col].dropna().unique().tolist()) if col in future else [] for col in ['temperature_issued_at','weather_issued_at']},warnings=['2026 accuracy has not been evaluated.','72h publication delay is an assumption, not verified per-source availability.','2026 renewable observations absent in snapshot; imputed values are not measurements.','Calculated before 23:00 is preliminary; planned origin is not actual calculation time.'],rows=[{k:(v.isoformat() if isinstance(v,pd.Timestamp) else None if pd.isna(v) else v) for k,v in row.items()} for row in rows.to_dict('records')])
    write_json(OUT/'forecast.json',payload)
    sources=[SHARED/'manifest.json',path,ROOT/'models/sarimax/algorithm_v3.py',*OUT.glob('*.csv')];write_json(OUT/'source_hashes.json',{str(p.relative_to(WORK)) if p.is_relative_to(WORK) else str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    np.savez_compressed(OUT/'frozen_inference_inputs.npz',state_y=prefix.actual_smp.to_numpy(),state_x=prefix[features].to_numpy(),future_x=x,weekly=weekly,state_last=prefix.index[-1].isoformat(),origin=ORIGIN.isoformat(),cutoff=CUTOFF.isoformat(),features=np.asarray(features))
    print(json.dumps(dict(status=status,calculated_at=created.isoformat(),targets=len(rows),feature_count=len(features),bridge_hours=steps,price_min=float(blended.min()),price_max=float(blended.max()),missing=quality),ensure_ascii=False),flush=True)
if __name__=='__main__':
    try:run()
    except (ValueError,FileNotFoundError) as e:write_json(OUT/'blockers.json',dict(status='blocked',reason=str(e),recorded_at=pd.Timestamp.now(tz=c.TZ).isoformat()));print('BLOCKED',str(e),flush=True);sys.exit(1)
