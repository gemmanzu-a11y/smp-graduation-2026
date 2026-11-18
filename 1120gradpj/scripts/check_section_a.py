"""Section A: bounded live API probes + complete local coverage audit; no model fitting."""
from pathlib import Path
import concurrent.futures
import json
import sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from smp_forecast.http import Client,items_from,write_json,now
from smp_forecast.collect import parse_power
OUT=ROOT/'data/processed/section_a'
OUT.mkdir(parents=True,exist_ok=True)

def audit_local():
    f=pd.read_csv(ROOT/'data/processed/power_hourly.csv')
    f.timestamp=pd.to_datetime(f.timestamp,utc=True).dt.tz_convert('Asia/Seoul')
    expected=pd.date_range('2023-01-01','2025-12-31 23:00',freq='h',tz='Asia/Seoul')
    selected=f[f.timestamp.between(expected.min(),expected.max())].copy()
    if selected.timestamp.duplicated().any():raise ValueError('Duplicate historical demand timestamp')
    aligned=selected.set_index('timestamp').reindex(expected)
    missing=aligned[aligned.demand_mw.isna()].copy();missing.index.name='timestamp'
    missing.to_csv(OUT/'actual_demand_missing_hours.csv')
    yearly=[]
    for year,g in aligned.groupby(aligned.index.year):
        yearly.append(dict(year=int(year),expected_hours=len(g),valid_hours=int(g.demand_mw.notna().sum()),missing_hours=int(g.demand_mw.isna().sum())))
    return dict(start=str(expected.min()),end=str(expected.max()),expected_hours=len(expected),stored_rows=len(selected),valid_hours=int(aligned.demand_mw.notna().sum()),missing_hours=int(aligned.demand_mw.isna().sum()),missing_pct=float(aligned.demand_mw.isna().mean()*100),missing_timestamp_hours=len(expected.difference(pd.DatetimeIndex(selected.timestamp))),incomplete_or_missing_value_hours=int(selected.demand_mw.isna().sum()),yearly=yearly,unit='MW',aggregation='mean of twelve 5-minute current-load readings; incomplete hours remain NaN',geography='EPSIS displayed load; mainland-only scope not independently established')


def probe(client,test):
    kind,value=test
    try:
        if kind=='forecast':
            b,m=client.fetch('section_a_forecast','https://apis.data.go.kr/B552115/SmpWithForecastDemand/getSmpWithForecastDemand',dict(date=value,numOfRows=100,pageNo=1,dataType='json'),'KPX_SERVICE_KEY',refresh=True)
            rows,total=items_from(b);land=[r for r in rows if r.get('areaName')=='육지']
            frame=pd.DataFrame(land)
            if len(frame):
                frame['mlfd']=pd.to_numeric(frame.mlfd,errors='raise')
                hours=pd.to_numeric(frame.hour,errors='raise').astype(int)
                if hours.duplicated().any() or not hours.between(1,24).all():raise ValueError('Bad forecast hours')
                frame['timestamp']=pd.to_datetime(frame['date'],format='%Y%m%d').dt.tz_localize('Asia/Seoul')+pd.to_timedelta(hours-1,unit='h')
                frame.to_csv(OUT/f'demand_forecast_{value}.csv',index=False)
            return dict(kind=kind,date=value,http=200,total_rows=total,mainland_rows=len(land),hours=sorted(int(r['hour']) for r in land),fields=sorted(set().union(*(r.keys() for r in land))) if land else [],sample=land[:1],status='received' if land else 'normal_empty',receipt=m)
        if kind=='holiday':
            b,m=client.fetch('section_a_holidays','https://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo',dict(solYear=value,numOfRows=100,pageNo=1,_type='json'),'KPX_SERVICE_KEY',refresh=True)
            rows,total=items_from(b)
            if len(rows)!=total:raise ValueError('Holiday pagination incomplete')
            clean=[]
            for r in rows:
                if not all(k in r for k in ['locdate','isHoliday','dateName']):raise ValueError('Missing holiday fields')
                clean.append(dict(date=pd.to_datetime(str(r['locdate']),format='%Y%m%d').strftime('%Y-%m-%d'),name=r['dateName'],isHoliday=r['isHoliday'],source='KASI getRestDeInfo',official_api_verified=True))
            pd.DataFrame(clean).to_csv(OUT/f'holidays_official_{value}.csv',index=False)
            return dict(kind=kind,year=value,http=200,rows=len(clean),total=total,fields=sorted(set().union(*(r.keys() for r in rows))) if rows else [],sample=clean[:2],status='received' if clean else 'normal_empty',receipt=m)
        b,m=client.fetch('section_a_actual','https://epsis.kpx.or.kr/epsisnew/selectEkgeEpsMepRealGridAjax.ajax',dict(beginDate=value,endDate=value,editYn='N'),post=True,refresh=True)
        frame=parse_power(b);frame=frame[frame.timestamp.dt.strftime('%Y%m%d')==value]
        frame.to_csv(OUT/f'demand_actual_{value}.csv',index=False)
        return dict(kind=kind,date=value,http=200,hourly_rows=len(frame),valid_hours=int(frame.demand_mw.notna().sum()),five_minute_samples=int(frame.samples_5m.sum()),sample=frame[['timestamp','demand_mw','samples_5m']].head(1).astype(str).to_dict('records'),status='received',receipt=m)
    except Exception as e:
        return dict(kind=kind,date_or_year=value,status='failed',reason=str(e) if isinstance(e,(RuntimeError,ValueError)) else type(e).__name__)


def main():
    local=audit_local();client=Client()
    tasks=[('forecast',d) for d in ['20230101','20230701','20231231','20240101','20250101','20250701','20251231','20261118','20261119']]
    tasks += [('holiday',str(y)) for y in [2023,2024,2025,2026]]
    tasks += [('actual',d) for d in ['20230101','20250701','20251231','20261117']]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(lambda t:probe(client,t),tasks))
    for r in results:print(json.dumps({k:v for k,v in r.items() if k not in ['receipt','fields','sample','hours']},ensure_ascii=False),flush=True)
    official=[]
    for year in [2023,2024,2025]:
        file=OUT/f'holidays_official_{year}.csv'
        # Only use successful responses from this invocation, never a stale file.
        good=any(r.get('kind')=='holiday' and r.get('year')==str(year) and r.get('status')=='received' for r in results)
        if good:official.append(pd.read_csv(file))
    times=pd.date_range('2023-01-01','2025-12-31 23:00',freq='h',tz='Asia/Seoul')
    calendar=pd.DataFrame(dict(timestamp=times,hour=times.hour,weekday=times.dayofweek,month=times.month,is_weekend=(times.dayofweek>=5).astype(int)))
    calendar['season']=times.month.map({12:'winter',1:'winter',2:'winter',3:'spring',4:'spring',5:'spring',6:'summer',7:'summer',8:'summer',9:'autumn',10:'autumn',11:'autumn'})
    for name,values,period in [('hour',times.hour,24),('weekday',times.dayofweek,7),('month',times.month-1,12)]:
        calendar[name+'_sin']=np.sin(2*np.pi*np.asarray(values)/period);calendar[name+'_cos']=np.cos(2*np.pi*np.asarray(values)/period)
    calendar_status='calendar_only; official holiday incomplete'
    if len(official)==3:
        h=pd.concat(official,ignore_index=True);h.to_csv(OUT/'holidays_official_2023_2025.csv',index=False)
        dates=set(h.loc[h.isHoliday=='Y','date']);calendar['is_holiday']=times.strftime('%Y-%m-%d').isin(dates).astype(int)
        calendar_status='complete including official holidays; historical designation dates unverified'
    calendar.to_csv(OUT/'calendar_hourly_2023_2025.csv',index=False)
    report=dict(at=now(),scope='Section A only; live access sample is not full archive completeness',model_training_performed=False,credential_values_saved=False,actual_demand_local=local,api_probes=results,calendar=dict(rows=len(calendar),status=calendar_status,columns=list(calendar.columns)),notes=['API hour is interval end: hour 01 mapped to 00:00 start','Demand forecast API date is target date, not evidence of historical publication timestamp','No fallback calendar used','Current-load historical average is MW, not settlement MWh or total behind-the-meter demand'])
    write_json(ROOT/'reports/section_a_check_20261118.json',report)
    print('LOCAL',json.dumps(local,ensure_ascii=False),flush=True)
    print('CALENDAR',calendar_status,len(calendar),flush=True)

if __name__=='__main__':main()
