"""C fuel: exact workbook LNG + historical FRED vintages, no model fitting."""
from pathlib import Path
import importlib.util
import json
import sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from smp_forecast.http import Client,write_json,now
OUT=ROOT/'data/processed/section_c'
SERIES={
    'DCOILWTICO':('wti_usd_bbl','D'),
    'DCOILBRENTEU':('brent_usd_bbl','D'),
    'PNGASJPUSDM':('international_lng_usd_mmbtu','M'),
    'PCOALAUUSDM':('international_coal_usd_tonne','M'),
}


def module(name):
    path=ROOT/'models/sarimax'/(name+'.py')
    spec=importlib.util.spec_from_file_location('section_c_'+name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def fred_json(client,path,params,source='section_c_fred'):
    body,receipt=client.fetch(source,'https://api.stlouisfed.org/fred/'+path,dict(file_type='json',**params),'FRED_API_KEY')
    data=json.loads(body)
    if 'error_code' in data:raise ValueError('FRED error code '+str(data['error_code']))
    return data,receipt


def select_asof(history,asof):
    """Select the latest observed period among numeric values known on the requested date."""
    date=pd.Timestamp(asof).strftime('%Y-%m-%d')
    eligible=history[(history.realtime_start<=date)&(history.realtime_end>=date)&(history['date']<=date)].copy()
    eligible['numeric_value']=pd.to_numeric(eligible.value,errors='coerce')
    eligible=eligible[np.isfinite(eligible.numeric_value)]
    if eligible.empty:raise ValueError('No historical vintage available at '+date)
    latest_date=eligible['date'].max();latest=eligible[eligible['date']==latest_date]
    if latest.numeric_value.nunique()!=1:raise ValueError('Overlapping conflicting vintage intervals')
    chosen=latest.sort_values('realtime_start').iloc[-1]
    return dict(value=float(chosen.numeric_value),observation_date=chosen['date'],
        vintage_start=chosen.realtime_start,vintage_end=chosen.realtime_end,
        age_days=int((pd.Timestamp(date)-pd.Timestamp(chosen['date'])).days))


def bulk_history(client,series):
    rows=[];offset=0;receipts=[]
    while True:
        data,receipt=fred_json(client,'series/observations',dict(series_id=series,
            realtime_start='2022-12-25',realtime_end='2025-12-29',
            observation_start='2022-01-01',observation_end='2025-12-29',
            output_type=1,limit=100000,offset=offset))
        chunk=data.get('observations',[]);rows.extend(chunk);receipts.append(receipt)
        if len(rows)>=data['count']:break
        if not chunk:raise ValueError('Empty pagination before declared count')
        offset+=len(chunk)
    history=pd.DataFrame(rows)
    for col in ['date','realtime_start','realtime_end','value']:
        if col not in history:raise ValueError('Missing FRED vintage field '+col)
    if history.duplicated(['date','realtime_start','realtime_end']).any():raise ValueError('Duplicate FRED intervals')
    history.to_csv(OUT/f'{series}_vintage_intervals.csv',index=False)
    return history,receipts


def point_value(client,series,asof):
    # A direct independent snapshot validates the bulk interval reconstruction.
    data,receipt=fred_json(client,'series/observations',dict(series_id=series,
        realtime_start=asof,realtime_end=asof,observation_end=asof,
        sort_order='desc',limit=100),'section_c_fred_snapshots')
    history=pd.DataFrame(data.get('observations',[]))
    return select_asof(history,asof),receipt


def collect():
    OUT.mkdir(parents=True,exist_ok=True)
    client=Client();fuel=module('fuel');contract=module('contract')
    workbooks=list(ROOT.parent.glob('HOME_*.xlsx'))
    if len(workbooks)!=1:raise ValueError('Expected one supplied HOME fuel workbook')
    domestic,evidence=fuel.read_lng(workbooks[0])
    months=pd.period_range('2023-01','2025-12',freq='M').astype(str)
    if not set(months).issubset(domestic.month):raise ValueError('Required domestic LNG month absent')
    if not np.isfinite(domestic.domestic_lng_cost_krw_kwh).all():raise ValueError('Invalid LNG workbook value')
    domestic.to_csv(OUT/'domestic_lng_monthly.csv',index=False)
    write_json(OUT/'domestic_lng_source.json',evidence)
    hours=pd.date_range('2023-01-01','2025-12-31 23:00',freq='h',tz='Asia/Seoul')
    domestic_hourly=pd.DataFrame(dict(timestamp=hours,reference_month=hours.strftime('%Y-%m'),domestic_lng_cost_krw_kwh=fuel.fuel_for_targets(domestic,hours,pd.Timestamp('2022-12-31 23:00',tz='Asia/Seoul'))))
    domestic_hourly['availability_rule']='same target month supplied; conditional retrospective experiment'
    domestic_hourly.to_csv(OUT/'domestic_lng_hourly_2023_2025.csv',index=False)
    target_days=pd.date_range('2023-01-01','2025-12-31',freq='D',tz='Asia/Seoul')
    origins=target_days-pd.Timedelta(hours=1)
    asofs=(origins.normalize()-pd.Timedelta(days=2)).strftime('%Y-%m-%d')
    daily=pd.DataFrame(dict(forecast_origin=origins,fred_asof_date=asofs))
    metadata={};validations=[];series_reports={};latest=[]
    current_day=pd.Timestamp(now()).normalize()
    demo_origin=current_day+pd.Timedelta(hours=23)
    demo_asof=(current_day-pd.Timedelta(days=2)).strftime('%Y-%m-%d')
    for series,(feature,frequency) in SERIES.items():
        info,meta_receipt=fred_json(client,'series',dict(series_id=series))
        meta=info['seriess'][0]
        if meta['frequency_short']!=frequency:raise ValueError('Unexpected frequency for '+series)
        metadata[series]=dict(id=series,title=meta['title'],frequency=meta['frequency'],frequency_short=frequency,units=meta['units'],seasonal_adjustment=meta['seasonal_adjustment'],source_url='https://fred.stlouisfed.org/series/'+series,receipt=meta_receipt)
        history,receipts=bulk_history(client,series)
        chosen=[select_asof(history,date) for date in asofs]
        daily[feature]=[r['value'] for r in chosen]
        for key in ['observation_date','vintage_start','vintage_end','age_days']:
            daily[feature+'_'+key]=[r[key] for r in chosen]
        for date in ['2022-12-29','2024-07-01','2025-12-28']:
            direct,receipt=point_value(client,series,date);reconstructed=select_asof(history,date)
            if direct['observation_date']!=reconstructed['observation_date'] or not np.isclose(direct['value'],reconstructed['value'],rtol=1e-12,atol=1e-10):
                raise ValueError('Bulk/direct as-of mismatch: '+series+' '+date)
            validations.append(dict(series=series,asof=date,matched=True,value=direct['value'],observation_date=direct['observation_date'],receipt=receipt))
        current,receipt=point_value(client,series,demo_asof)
        latest.append(dict(series=series,feature=feature,unit=meta['units'],reference_origin=str(demo_origin),fred_asof_date=demo_asof,**current,receipt=receipt))
        series_reports[series]=dict(feature=feature,unit=meta['units'],frequency=meta['frequency'],raw_vintage_rows=len(history),origin_rows=len(daily),missing_values=int(daily[feature].isna().sum()),maximum_age_days=max(r['age_days'] for r in chosen),receipts=receipts)
        print(series,len(history),'vintage rows;',len(daily),'origins; missing',daily[feature].isna().sum(),flush=True)
    daily.to_csv(OUT/'international_fuel_by_origin_2023_2025.csv',index=False)
    write_json(OUT/'fred_metadata.json',metadata)
    write_json(OUT/'fred_asof_validation.json',validations)
    write_json(OUT/'latest_international_fuel_preview.json',latest)
    # All 72h target blocks entirely inside one split; purge split-crossing blocks.
    lookup=daily.set_index('forecast_origin');blocks=[]
    splits={'train':('2023-01-01','2024-12-31'),'validation':('2025-01-01','2025-06-30'),'test':('2025-07-01','2025-12-31')}
    for split,(start,end) in splits.items():
        for origin in contract.origins(start,end):
            targets=pd.date_range(origin+pd.Timedelta(hours=1),periods=72,freq='h')
            row=lookup.loc[origin]
            frame=pd.DataFrame(dict(forecast_origin=origin,target_timestamp=targets,split=split,
                horizon=np.arange(1,73),forecast_day=np.repeat([1,2,3],24),
                domestic_lng_cost_krw_kwh=fuel.fuel_for_targets(domestic,targets,origin),
                domestic_lng_reference_month=targets.strftime('%Y-%m'),fred_asof_date=row.fred_asof_date))
            for feature,_ in SERIES.values():
                for col in [feature]+[feature+'_'+k for k in ['observation_date','vintage_start','vintage_end','age_days']]:frame[col]=row[col]
            blocks.append(frame)
    combined=pd.concat(blocks,ignore_index=True)
    combined.to_csv(OUT/'fuel_forecast_inputs_2023_2025.csv',index=False)
    demo_targets=pd.date_range(demo_origin+pd.Timedelta(hours=1),periods=72,freq='h')
    demo=pd.DataFrame(dict(forecast_origin=demo_origin,target_timestamp=demo_targets,
        domestic_lng_reference_month='2026-10',domestic_lng_cost_krw_kwh=fuel.fuel_for_targets(domestic,demo_targets,demo_origin,'november_demo'),fred_asof_date=demo_asof))
    for row in latest:demo[row['feature']]=row['value']
    demo['status']='input preview only; not an issued model forecast'
    demo.to_csv(OUT/'november_demo_fuel_preview.csv',index=False)
    required=['domestic_lng_cost_krw_kwh']+[x[0] for x in SERIES.values()]
    if not np.isfinite(combined[required].to_numpy()).all():raise ValueError('Missing required combined fuel input')
    report=dict(at=now(),status='fuel_values_ready_under_agreed_assumptions',model_training_performed=False,credentials_saved=False,
        domestic=dict(**evidence,first_month=domestic.month.min(),last_month=domestic.month.max(),months=len(domestic),historical_required_months=len(months),historical_hourly_rows=len(domestic_hourly),missing_historical_months=0,policy='target-month LNG; historical disclosure availability unverified',november_demo_reference_month='2026-10',november_demo_value=float(demo.domestic_lng_cost_krw_kwh.iloc[0])),
        international=series_reports,asof_checks_passed=len(validations),daily_origins=len(daily),forecast_origins=int(combined.forecast_origin.nunique()),forecast_rows=len(combined),split_origins=combined.groupby('split').forecast_origin.nunique().to_dict(),latest_input_preview=latest,
        limitations=['Domestic target-month LNG is an explicit future-information exception; not a point-in-time operational accuracy claim','FRED D-2 date snapshots are a conservative date-level rule, not intraday release timestamps','Long unchanged monthly values are retained as actually available; age columns expose staleness','No KPX heat-unit API or two-month domestic lag used','This prepares C only; A/B/D and overall model gates remain separate'])
    write_json(ROOT/'reports/section_c_check_20261118.json',report)
    print('C READY',json.dumps(dict(domestic_months=len(domestic),daily_origins=len(daily),forecast_origins=report['forecast_origins'],forecast_rows=len(combined),asof_checks=len(validations)),ensure_ascii=False),flush=True)

if __name__=='__main__':collect()
