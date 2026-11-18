"""Pinned, causal 72-hour research dataset shared by all four model families.

Raw measurements remain NaN. Model imputation is fitted on Train only.
Hourly indices label interval starts; only completed intervals enter history.
"""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT.parent
SHA='a90141b81ecd841c524eb75a72f4bcc4f39989f5'
VERSION='v3_'+SHA[:12]+'_lag72'
SOURCE=ROOT/'data/raw/team_training_snapshot'/SHA/'SMP_72H_INPUT_DATA'
OUT=WORK/'SMP_SHARED_DATA/versions'/VERSION
TZ='Asia/Seoul'
HISTORY=['smp','demand_actual','demand_forecast_history','generation_lng','generation_coal','generation_nuclear','solar_actual','wind_actual','reserve_mw','reserve_pct','temperature_c','irradiance_mj_m2','wind_ms']
GROUPS=dict(smp=0,demand_actual=1,demand_forecast_history=2,generation_lng=5,generation_coal=5,generation_nuclear=5,solar_actual=6,wind_actual=6,reserve_mw=7,reserve_pct=7,temperature_c=11,irradiance_mj_m2=11,wind_ms=11)

def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str)+'\n')

def times(values):
    dt=pd.to_datetime(values)
    return dt.dt.tz_localize(TZ) if dt.dt.tz is None else dt.dt.tz_convert(TZ)

def first(folder,name):return SOURCE/folder/name

def causal_fill(raw):
    """Strictly forward fill, then frozen Train season/hour/global medians."""
    train=raw.loc[:'2024-12-31']
    season=(raw.index.month%12)//3
    keys=pd.MultiIndex.from_arrays([season,raw.index.hour])
    filled=raw.ffill(limit=24)
    parameters={}
    for col in raw:
        table=train[col].groupby([(train.index.month%12)//3,train.index.hour]).median()
        global_value=float(train[col].median())
        if not np.isfinite(global_value):raise ValueError('No Train values: '+col)
        fallback=pd.Series(table.reindex(keys).to_numpy(),index=raw.index).fillna(global_value)
        filled[col]=filled[col].fillna(fallback)
        parameters[col]={'global':global_value,'season_hour':{str(k):float(v) for k,v in table.items() if np.isfinite(v)}}
    return filled,parameters

def vintage_select(frame,asof):
    date=asof.strftime('%Y-%m-%d')
    x=frame[(frame.realtime_start<=date)&(frame.realtime_end>=date)&(frame['date']<=date)].copy()
    x['numeric']=pd.to_numeric(x.value,errors='coerce');x=x.dropna(subset=['numeric'])
    if x.empty:raise ValueError('No FRED vintage '+date)
    x=x[x['date']==x['date'].max()]
    if x.numeric.nunique()!=1:raise ValueError('Conflicting vintage')
    return x.sort_values('realtime_start').iloc[-1]

def night_flag(index):
    """NOAA approximate solar elevation at Seoul interval midpoint; no zero imputation."""
    t=index+pd.Timedelta(minutes=30);gamma=2*np.pi/365*(t.dayofyear-1+(t.hour-12)/24)
    eq=229.18*(.000075+.001868*np.cos(gamma)-.032077*np.sin(gamma)-.014615*np.cos(2*gamma)-.040849*np.sin(2*gamma))
    decl=.006918-.399912*np.cos(gamma)+.070257*np.sin(gamma)-.006758*np.cos(2*gamma)+.000907*np.sin(2*gamma)-.002697*np.cos(3*gamma)+.00148*np.sin(3*gamma)
    solar=t.hour*60+t.minute+eq+4*126.978-60*9
    angle=np.deg2rad(solar/4-180);lat=np.deg2rad(37.5714)
    elevation=np.arcsin(np.sin(lat)*np.sin(decl)+np.cos(lat)*np.cos(decl)*np.cos(angle))
    return (elevation<0).astype(float)

def build(generation_path=None, output_dir=None, dataset_version=None):
    OUT=Path(output_dir) if output_dir is not None else globals()['OUT']
    VERSION=dataset_version or globals()['VERSION']
    OUT.mkdir(parents=True,exist_ok=True)
    grid=pd.date_range('2023-01-01','2025-12-31 23:00',freq='h',tz=TZ)
    raw=pd.DataFrame(index=grid);raw.index.name='timestamp'
    provenance=[]
    def read(group,name):
        p=next(SOURCE.glob(f'{group:02d}_*'))/name
        provenance.append(p);return pd.read_csv(p)
    power=ROOT/'data/processed/power_hourly.csv';provenance.append(power)
    p=pd.read_csv(power);p.index=times(p.timestamp)
    raw['demand_actual']=p.demand_mw.where(p.samples_5m==12).reindex(grid)
    sp=ROOT/'data/processed/smp_hourly.csv';provenance.append(sp)
    s=pd.read_csv(sp);s.index=times(s.timestamp);raw['smp']=s.smp.reindex(grid)
    d=read(2,'mainland_demand_forecast_2023_2025.csv');d.index=times(d.timestamp)
    raw['demand_forecast_history']=d.demand_forecast_mw.reindex(grid)
    holidays=read(3,'03_kasi_holidays.csv')
    holiday_dates=set(pd.to_datetime(holidays.loc[holidays.isHoliday=='Y','locdate'].astype(str),format='%Y%m%d').dt.strftime('%Y-%m-%d'))
    if generation_path is not None:
        generation_path=Path(generation_path);provenance.append(generation_path)
        generation=pd.read_csv(generation_path);generation.index=times(generation.timestamp)
        if not generation.index.equals(grid):raise ValueError('Replacement generation grid differs')
        for source,key in [('lng_generation_mwh','generation_lng'),('coal_generation_mwh','generation_coal'),('nuclear_generation_mwh','generation_nuclear')]:
            raw[key]=pd.to_numeric(generation[source],errors='raise').reindex(grid)
            if not np.array_equal(raw[key].isna().astype(int),generation[source+'_missing']):raise ValueError('Generation mask mismatch')
    else:
        g=read(5,'api_generation_partial_2023_2025_merged_20261119.csv')
        g['t']=pd.to_datetime(g.tradeYmd.astype(str),format='%Y%m%d').dt.tz_localize(TZ)+pd.to_timedelta(pd.to_numeric(g.tradeNo)-1,unit='h')
        if g.duplicated(['t','fuelTpCd']).any():raise ValueError('Duplicate generation keys')
        wide=g.pivot(index='t',columns='fuelTpCd',values='amgo').reindex(grid)
        raw['generation_lng']=wide['LNG'];raw['generation_nuclear']=wide['원자력']
        raw['generation_coal']=wide[['유연탄','무연탄']].sum(axis=1,min_count=2)
    renew=[]
    for path in sorted((next(SOURCE.glob('06_*'))/'team_shared_originals').glob('renewable_source_*.csv')):
        provenance.append(path)
        r=pd.read_csv(path,encoding='utf-8-sig');r.columns=r.columns.str.strip()
        datecol=next(c for c in r if c in ['거래일','거래일자'])
        r['t']=pd.to_datetime(r[datecol]).dt.tz_localize(TZ)+pd.to_timedelta(pd.to_numeric(r['거래시간'])-1,unit='h')
        region=next(c for c in r if c in ['지역','지역명'])
        r=r[~r[region].astype(str).str.contains('제주')].copy()
        if '연료원' in r:
            value=next(c for c in r if '량(' in c)
            r[value]=pd.to_numeric(r[value],errors='coerce')
            for fuel,key in [('태양광','solar_actual'),('풍력','wind_actual')]:
                z=r[r['연료원'].astype(str).str.contains(fuel)]
                renew.append(pd.DataFrame({key:z.groupby('t')[value].sum(min_count=1),key+'_regional_missing':z.groupby('t')[value].apply(lambda x:float(x.isna().any()))}))
        else:
            for fuel,key in [('태양광','solar_actual'),('풍력','wind_actual')]:
                col=next(c for c in r if fuel in c)
                r[col]=pd.to_numeric(r[col],errors='coerce')
                renew.append(pd.DataFrame({key:r.groupby('t')[col].sum(min_count=1),key+'_regional_missing':r.groupby('t')[col].apply(lambda x:float(x.isna().any()))}))
    for key in ['solar_actual','wind_actual']:
        z=pd.concat([r for r in renew if key in r]).sort_index()
        if z.index.duplicated().any():raise ValueError('Overlapping renewable source versions')
        raw[key]=z[key].reindex(grid);raw[key+'_regional_missing']=z[key+'_regional_missing'].reindex(grid).fillna(1)
    reserve=read(7,'07_supply_reserve_mw_pct.csv');reserve.index=times(reserve.timestamp_kst)
    if reserve.index.duplicated().any():raise ValueError('Duplicate reserve timestamps')
    count=reserve.resample('h').size().reindex(grid,fill_value=0)
    for col,key in [('supply_reserve_mw','reserve_mw'),('supply_reserve_pct','reserve_pct')]:
        raw[key]=reserve[col].resample('h').mean().reindex(grid).where(count==12)
    lng=read(8,'08_domestic_lng_fuel_cost.csv')
    if not lng.unit.eq('KRW/kWh').all():raise ValueError('LNG unit mismatch')
    lngmap=lng.set_index('reference_month').value
    asos=read(11,'11_kma_asos_actuals.csv')
    if not asos.station_id.eq(108).all():raise ValueError('ASOS station mismatch')
    asos.index=times(asos.timestamp_kst)-pd.Timedelta(hours=1)
    for col,key in [('temperature_c','temperature_c'),('wind_speed_ms','wind_ms'),('solar_radiation_mj_m2','irradiance_mj_m2')]:
        vals=pd.to_numeric(asos[col],errors='coerce')
        if key!='temperature_c':vals=vals.where(vals>=0)
        else:vals=vals.where(vals.between(-60,60))
        raw[key]=vals.reindex(grid)
    raw['irradiance_night']=night_flag(grid)
    temp=read(12,'12_kma_midrange_temperature_seoul.csv');temp['issued']=times(temp.issued_at_kst)
    temp['date']=pd.to_datetime(temp.target_date).dt.strftime('%Y-%m-%d')
    temp=temp.sort_values('issued');temp_groups={k:v for k,v in temp.groupby('date')}
    weather=[]
    for path in sorted((WORK/'shared_datasets/kma_midrange').glob('forecast_*.csv')):
        provenance.append(path);w=pd.read_csv(path);weather.append(w[w.region=='서울.인천.경기'])
    weather=pd.concat(weather,ignore_index=True);weather['issued']=times(weather.issued_at_kst)
    weather['date']=pd.to_datetime(weather.target_date).dt.strftime('%Y-%m-%d')
    weather=weather.sort_values('issued');weather_groups={k:v for k,v in weather.groupby('date')}
    fred={}
    for group,series in [(9,'DCOILWTICO'),(9,'DCOILBRENTEU'),(10,'PNGASJPUSDM'),(10,'PCOALAUUSDM')]:
        path=next((next(SOURCE.glob(f'{group:02d}_*'))/'fred_vintage_source').glob(series+'*.json'))
        provenance.append(path);fred[series]=pd.DataFrame(json.loads(path.read_text())['observations'])
    filled,imputer=causal_fill(raw[HISTORY]);history=filled.copy()
    for c in HISTORY:history[c+'_missing']=raw[c].isna().astype(float)
    for c in ['irradiance_night','solar_actual_regional_missing','wind_actual_regional_missing']:history[c]=raw[c]
    blocks=[];excluded=[];origins=[]
    splits=[('train','2023-01-01','2024-12-31'),('validation','2025-01-01','2025-06-30'),('test','2025-07-01','2025-12-31')]
    for split,start,end in splits:
        for origin in pd.date_range(pd.Timestamp(start,tz=TZ)-pd.Timedelta(hours=1),pd.Timestamp(end,tz=TZ)-pd.Timedelta(days=2,hours=1),freq='D'):
            cutoff=origin-pd.Timedelta(hours=72)
            if cutoff-pd.Timedelta(hours=168)<grid[0]:
                excluded.append({'forecast_origin':str(origin),'split':split,'reason':'168h history before source start'});continue
            target=pd.date_range(origin+pd.Timedelta(hours=1),periods=72,freq='h')
            if raw.smp.reindex(target).isna().any():raise ValueError('Missing SMP target')
            block=pd.DataFrame({'forecast_origin':origin,'observed_cutoff':cutoff,'target_timestamp':target,'horizon':np.arange(1,73),'forecast_day':np.repeat([1,2,3],24),'split':split})
            block['actual_smp']=raw.smp.reindex(target).to_numpy()
            previous_day=cutoff.normalize()-pd.Timedelta(days=1)
            baseline_dates=previous_day+pd.to_timedelta(target.hour,unit='h')
            block['baseline_origin_day']=raw.smp.reindex(baseline_dates).to_numpy()
            block['baseline_weekly']=raw.smp.reindex(target-pd.Timedelta(hours=168)).to_numpy()
            if block[['baseline_origin_day','baseline_weekly']].isna().any().any():raise ValueError('Missing baseline')
            block['hour_sin']=np.sin(2*np.pi*target.hour/24);block['hour_cos']=np.cos(2*np.pi*target.hour/24)
            block['weekday_sin']=np.sin(2*np.pi*target.dayofweek/7);block['weekday_cos']=np.cos(2*np.pi*target.dayofweek/7)
            block['month_sin']=np.sin(2*np.pi*(target.month-1)/12);block['month_cos']=np.cos(2*np.pi*(target.month-1)/12)
            block['season']=target.month%12//3;block['weekend']=(target.dayofweek>=5).astype(float)
            block['holiday']=[float(t.strftime('%Y-%m-%d') in holiday_dates) for t in target]
            block['lng_domestic']=lngmap.reindex(target.strftime('%Y-%m')).to_numpy()
            asof=(origin.normalize()-pd.Timedelta(days=2));block['fred_asof_date']=asof.strftime('%Y-%m-%d')
            for series,vintages in fred.items():
                chosen=vintage_select(vintages,asof)
                block[series]=float(chosen.numeric);block[series+'_observation_date']=chosen['date']
                block[series+'_vintage_start']=chosen.realtime_start;block[series+'_vintage_end']=chosen.realtime_end
            for day in target.normalize().unique():
                mask=target.normalize()==day;date=day.strftime('%Y-%m-%d')
                tt=temp_groups.get(date,pd.DataFrame());tt=tt[tt.issued<=origin] if len(tt) else tt
                if len(tt):
                    chosen=tt.iloc[-1];block.loc[mask,'mid_tmin']=float(chosen['최저기온']);block.loc[mask,'mid_tmax']=float(chosen['최고기온']);block.loc[mask,'temperature_issued_at']=str(chosen.issued)
                ww=weather_groups.get(date,pd.DataFrame());ww=ww[ww.issued<=origin] if len(ww) else ww
                for period,hours in [('AM',target.hour<12),('PM',target.hour>=12)]:
                    wm=mask&hours;allowed=ww[ww.target_period.isin([period,'DAY'])] if len(ww) else ww
                    if len(allowed):
                        chosen=allowed.iloc[-1];block.loc[wm,'mid_rain']=chosen.precip_probability_pct;block.loc[wm,'mid_weather']=chosen.weather_text;block.loc[wm,'weather_issued_at']=str(chosen.issued)
            # Identical cutoff summaries for all 72 targets; raw missing masks remain available.
            window=history.loc[(history.index>=cutoff-pd.Timedelta(hours=168))&(history.index<cutoff)]
            for col in HISTORY:
                block[col+'_last']=window[col].iloc[-1];block[col+'_mean24']=window[col].iloc[-24:].mean();block[col+'_mean168']=window[col].mean()
                block[col+'_missing_last']=window[col+'_missing'].iloc[-1]
            blocks.append(block);origins.append(dict(forecast_origin=origin,observed_cutoff=cutoff,split=split))
    future=pd.concat(blocks,ignore_index=True)
    for col in ['mid_tmin','mid_tmax','mid_rain']:
        future[col]=pd.to_numeric(future.get(col),errors='coerce');future[col+'_missing']=future[col].isna().astype(float)
        median=future.loc[future.split=='train',col].median()
        if not np.isfinite(median):raise ValueError('Missing entire forecast field '+col)
        future[col+'_raw']=future[col];future[col]=future[col].fillna(median)
        imputer[col]={'train_median':float(median)}
    vocabulary=sorted(future.loc[future.split=='train','mid_weather'].dropna().unique())
    future['mid_weather_missing']=future.mid_weather.isna().astype(float)
    future['mid_weather_unknown']=(future.mid_weather.notna()&~future.mid_weather.isin(vocabulary)).astype(float)
    for n,category in enumerate(vocabulary):future['weather_category_'+str(n)]=future.mid_weather.eq(category).astype(float)
    excluded_cols=['horizon','forecast_day','actual_smp','baseline_origin_day','baseline_weekly']
    context=[c for c in future.select_dtypes(include='number') if c not in excluded_cols and not c.endswith('_raw')]
    for c in ['lng_domestic']:
        if future[c].isna().any():raise ValueError('Missing mandatory monthly fuel '+c)
    if not np.isfinite(future[context].to_numpy()).all():raise ValueError('Nonfinite future context')
    for col in ['temperature_issued_at','weather_issued_at']:
        issued=pd.to_datetime(future[col],utc=True);valid=issued.notna()
        assert (issued[valid]<=future.loc[valid,'forecast_origin']).all()
    assert ((future.target_timestamp-future.forecast_origin).dt.total_seconds()/3600==future.horizon).all()
    assert (future.observed_cutoff==future.forecast_origin-pd.Timedelta(hours=72)).all()
    # Save raw and model representations separately, never overwrite inputs.
    raw.to_csv(OUT/'hourly.csv');history.to_csv(OUT/'history_model.csv');future.to_csv(OUT/'forecast_inputs.csv',index=False)
    pd.DataFrame(origins).to_csv(OUT/'evaluation_origins.csv',index=False)
    future[['forecast_origin','target_timestamp','horizon','forecast_day','split']].to_csv(OUT/'evaluation_targets.csv',index=False)
    pd.DataFrame(excluded).to_csv(OUT/'excluded_origins.csv',index=False)
    hashes={str(p.relative_to(WORK)):hashlib.sha256(p.read_bytes()).hexdigest() for p in provenance}
    quality={'raw_missing':{c:int(raw[c].isna().sum()) for c in raw},'raw_rows':len(raw),'split_origins':pd.DataFrame(origins).groupby('split').size().to_dict(),'excluded_origins':len(excluded),'forecast_missing':{c:float(future[c+'_missing'].mean()) for c in ['mid_tmin','mid_tmax','mid_rain']},'checks':{'fixed_origin_cutoff':True,'issued_before_origin':True,'finite_model_arrays':True,'target_split_blocks':True},'generation_missing_by_year':raw[[c for c in raw if c.startswith('generation_')]].isna().groupby(raw.index.year).mean().to_dict()}
    manifest={'dataset_version':VERSION,'source_commit':SHA,'source_repository':'parksiwon22/gradproject','source_branch':'codex/smp-72h-data','history_features':list(history),'context_features':context,'all_groups':list(range(1,13)),'source_sha256':hashes,'weather_categories':vocabulary,'imputation':imputer,'observed_delay_hours':72,'smp_policy':'72h delay assumption, interval end <= cutoff','fuel_policy':'target-month LNG supplied conditional retrospective experiment','amgo_unit':'MWh; KPX AMGO definition and primary study DOI 10.7836/kses.2019.39.6.113; original API table does not label unit; annual CSV is NOT merged','reserve_aggregation':'mean only when 12 unique 5min rows; otherwise NaN','weather_time':'ASOS timestamps treated as interval end; label shifted -1h; TA/WS are end observations; SI accumulated hour','night_policy':'NOAA approximate solar elevation at interval midpoint <0; flag only; never turns missing SI to zero','fred_policy':'vintage intervals reconstructed asof origin calendar date minus 2 days'}
    if generation_path is not None:
        manifest['generation_override']=str(generation_path.relative_to(WORK))
        manifest['generation_policy']='2023/2025 whole annual market-energy CSVs; 2024 API; no within-year source splice; 2024 gaps retained'
        manifest['experiment_status']='follow-up after observing original 2025H2 test; no longer an untouched final holdout'
    dump(OUT/'manifest.json',manifest);dump(OUT/'quality_report.json',quality)
    features=[]
    units=['KRW/kWh','MW','MW','MWh','MWh','MWh','MWh','MWh','MW','%','degC','MJ/m2','m/s']
    for col,unit in zip(HISTORY,units):features.append(dict(variable=col,input_group=GROUPS[col],unit=unit,region='Seoul 108' if GROUPS[col]==11 else 'source scope; see report',frequency='hourly',lag_rule='interval end <= origin-72h',missing_rate=float(raw[col].isna().mean()),imputation='past ffill <=24h; Train season/hour median; Train global median',missing_indicator=col+'_missing',source_paths=';'.join(hashes)))
    for col in context:
        group=3 if col=='holiday' else 4 if col in ['hour_sin','hour_cos','weekday_sin','weekday_cos','month_sin','month_cos','season','weekend'] else 8 if col=='lng_domestic' else 9 if col in ['DCOILWTICO','DCOILBRENTEU'] else 10 if col in ['PNGASJPUSDM','PCOALAUUSDM'] else 12 if col.startswith(('mid_','weather_category_')) else next((GROUPS[c] for c in HISTORY if col.startswith(c+'_')),0)
        features.append(dict(variable=col,input_group=group,unit='see source definition',lag_rule='see manifest and source provenance',imputation='Train only',source_paths=';'.join(hashes)))
    pd.DataFrame(features).to_csv(OUT/'feature_manifest.csv',index=False)
    if set(range(1,13))-set(f['input_group'] for f in features):raise ValueError('Input group absent')
    (WORK/'SMP_SHARED_DATA/README.md').write_text('# Shared 72h SMP dataset\n\nFrozen version: '+VERSION+'\n\nRaw NaN values are in hourly.csv; history_model.csv contains causal Train-fitted imputations and masks. All four models must use the same evaluation files. Dataset files are local and git-ignored.\n')
    print(json.dumps(quality,ensure_ascii=False,default=str),flush=True)
    return OUT

def load(path=OUT):
    manifest=json.loads((path/'manifest.json').read_text())
    history=pd.read_csv(path/'history_model.csv');history.index=times(history.pop('timestamp'))
    future=pd.read_csv(path/'forecast_inputs.csv')
    for col in ['forecast_origin','observed_cutoff','target_timestamp']:future[col]=times(future[col])
    return history,future,manifest

def arrays(bundle,split,lookback):
    history,future,manifest=bundle;subset=future[future.split==split]
    hs=[];cs=[];ys=[]
    for origin,block in subset.groupby('forecast_origin',sort=True):
        cutoff=origin-pd.Timedelta(hours=72)
        index=pd.date_range(cutoff-pd.Timedelta(hours=lookback),periods=lookback,freq='h')
        assert index[-1]+pd.Timedelta(hours=1)<=cutoff
        hs.append(history.reindex(index)[manifest['history_features']].to_numpy())
        cs.append(block.sort_values('horizon')[manifest['context_features']].to_numpy())
        ys.append(block.sort_values('horizon').actual_smp.to_numpy())
    return tuple(np.asarray(x,dtype=np.float32) for x in [hs,cs,ys])

if __name__=='__main__':build()
