"""Collect all 2023–2025 mainland load forecasts; repair observed load from real samples only.
No model fit, no interpolation, no overwrite of original hourly_dataset/power_hourly files.
"""
from pathlib import Path
import concurrent.futures as futures
import hashlib
import json
import re
import sys
import time
import threading
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from smp_forecast.http import Client,items_from,write_json,now
OUT=ROOT/'data/processed/section_a'
REPORT=ROOT/'reports/section_a_completion_20261118.json'
EXPECTED=pd.date_range('2023-01-01','2025-12-31 23:00',freq='h',tz='Asia/Seoul')
PARAMS=lambda day:dict(beginDate=day,endDate=day,editYn='N')


def parse_5min(payload):
    rows=[]
    for block,stamp in re.findall(r'(c1\s*=.*?)gridData.push\(\{"year":"([^"\n]+)"',payload.decode('utf-8'),re.S):
        fields=dict(re.findall(r'(c\d+)\s*=\s*textFormmat\("([^"]*)",\s*0\)',block))
        row={'timestamp':pd.Timestamp(stamp,tz='Asia/Seoul')}
        for target,key in [('supply_mw','c1'),('demand_mw','c2'),('reserve_mw','c5'),('reserve_rate_pct','c6')]:
            row[target]=pd.to_numeric(fields.get(key,'').replace(',',''),errors='coerce')
        rows.append(row)
    frame=pd.DataFrame(rows,columns=['timestamp','supply_mw','demand_mw','reserve_mw','reserve_rate_pct'])
    if len(frame):
        if frame.timestamp.duplicated().any():raise ValueError('duplicate source timestamp')
        if not frame.timestamp.dt.minute.mod(5).eq(0).all():raise ValueError('off-grid source timestamp')
        frame=frame.sort_values('timestamp')
    return frame


def old_raw(day):
    endpoint='https://epsis.kpx.or.kr/epsisnew/selectEkgeEpsMepRealGridAjax.ajax'
    ident=hashlib.sha256(json.dumps([endpoint,PARAMS(day)],sort_keys=True).encode()).hexdigest()[:16]
    folder=ROOT/'data/raw/power_5m';marker=folder/(ident+'.json')
    if not marker.exists():return b''
    m=json.loads(marker.read_text());body=(folder/m['raw']).read_bytes()
    if hashlib.sha256(body).hexdigest()!=m['sha256']:raise ValueError('old raw hash mismatch')
    return body


def collect_forecasts():
    client=Client();limited=threading.Event();statuses=[];frames=[];days=pd.date_range('2023-01-01','2025-12-31',freq='D')
    def one(day):
        date=day.strftime('%Y%m%d')
        params=dict(date=date,numOfRows=100,pageNo=1,dataType='json')
        endpoint='https://apis.data.go.kr/B552115/SmpWithForecastDemand/getSmpWithForecastDemand'
        identity=hashlib.sha256(json.dumps([endpoint,params],sort_keys=True).encode()).hexdigest()[:16]
        cached=(ROOT/'data/raw/section_a_forecast'/(identity+'.json')).exists()
        if limited.is_set() and not cached:
            return dict(date=date,status='not_attempted_rate_limit'),None
        try:
            body,receipt=client.fetch('section_a_forecast','https://apis.data.go.kr/B552115/SmpWithForecastDemand/getSmpWithForecastDemand',params,'KPX_SERVICE_KEY')
            rows,total=items_from(body)
            land=[r for r in rows if r.get('areaName')=='육지']
            if len(land)!=24:
                body,receipt=client.fetch('section_a_forecast','https://apis.data.go.kr/B552115/SmpWithForecastDemand/getSmpWithForecastDemand',params,'KPX_SERVICE_KEY',refresh=True)
                rows,total=items_from(body);land=[r for r in rows if r.get('areaName')=='육지']
            if total>100:raise ValueError('pagination needed')
            f=pd.DataFrame(land)
            if len(f)==0:return dict(date=date,status='normal_empty'),None
            hours=pd.to_numeric(f.hour,errors='raise').astype(int)
            if len(f)!=24 or sorted(hours.tolist())!=list(range(1,25)):raise ValueError('incomplete 24-hour mainland block')
            if not f['date'].astype(str).eq(date).all():raise ValueError('response target date mismatch')
            values=pd.to_numeric(f.mlfd,errors='raise')
            if not np.isfinite(values).all() or not (values>0).all():raise ValueError('invalid mlfd')
            f=pd.DataFrame(dict(timestamp=pd.Timestamp(day,tz='Asia/Seoul')+pd.to_timedelta(hours-1,unit='h'),
                target_date=day.strftime('%Y-%m-%d'),source_hour=hours,demand_forecast_mw=values,
                geography='mainland',source='KPX SmpWithForecastDemand mlfd',
                retrieved_at=receipt['first_received_at'],source_sha256=receipt['sha256']))
            f['historical_published_at']=pd.NA
            return dict(date=date,status='complete',rows=24,sha256=receipt['sha256']),f
        except Exception as exc:
            if 'HTTP 429' in str(exc):limited.set()
            return dict(date=date,status='failed',reason=str(exc) if isinstance(exc,(RuntimeError,ValueError)) else type(exc).__name__),None
    with futures.ThreadPoolExecutor(max_workers=3) as pool:
        for i,(status,frame) in enumerate(pool.map(one,days),1):
            statuses.append(status)
            if frame is not None:frames.append(frame)
            if i%25==0 or i==len(days):
                write_json(OUT/'forecast_collection_progress.json',dict(at=now(),processed=i,total=len(days),complete=sum(r['status']=='complete' for r in statuses),failures=[r for r in statuses if r['status']!='complete']))
                print('FORECAST',i,'/',len(days),'complete',sum(r['status']=='complete' for r in statuses),flush=True)
    all_rows=pd.concat(frames,ignore_index=True).sort_values('timestamp') if frames else pd.DataFrame(columns=['timestamp','demand_forecast_mw'])
    if all_rows.timestamp.duplicated().any():raise ValueError('duplicate combined forecasts')
    all_rows.to_csv(OUT/'demand_forecast_mainland_2023_2025.csv',index=False)
    absent=EXPECTED.difference(pd.DatetimeIndex(all_rows.timestamp))
    pd.DataFrame({'timestamp':absent}).to_csv(OUT/'demand_forecast_missing_hours.csv',index=False)
    write_json(OUT/'forecast_collection_status.json',statuses)
    return dict(expected_days=len(days),complete_days=sum(r['status']=='complete' for r in statuses),rows=len(all_rows),missing_hours=len(absent),failed_days=[r for r in statuses if r['status']!='complete'],publication_history='target-date archive only; first-publication/revision vintages unverified')


def repair_actual():
    original=pd.read_csv(ROOT/'data/processed/power_hourly.csv')
    original.timestamp=pd.to_datetime(original.timestamp,utc=True).dt.tz_convert('Asia/Seoul')
    original=original.set_index('timestamp').reindex(EXPECTED)
    original.index.name='timestamp'
    missing=original.index[original.demand_mw.isna()]
    days=sorted(set(missing.strftime('%Y%m%d')));client=Client()
    def one(day):
        old=parse_5min(old_raw(day))
        status=dict(date=day,old_samples=len(old))
        try:
            b,m=client.fetch('section_a_actual_repair','https://epsis.kpx.or.kr/epsisnew/selectEkgeEpsMepRealGridAjax.ajax',PARAMS(day),post=True,refresh=True)
            fresh=parse_5min(b)
            if len(fresh):fresh=fresh[fresh.timestamp.dt.strftime('%Y%m%d')==day]
            status.update(status='received' if len(fresh) else 'normal_empty',new_samples=len(fresh),new_sha256=m['sha256'],retrieved_at=m['first_received_at'])
        except Exception as exc:
            fresh=pd.DataFrame(columns=old.columns)
            status.update(status='failed',reason=str(exc) if isinstance(exc,(RuntimeError,ValueError)) else type(exc).__name__)
        # New real observations take precedence; retain old observations missing from a fresh response.
        merged=pd.concat([old,fresh],ignore_index=True).drop_duplicates('timestamp',keep='last').sort_values('timestamp')
        return status,merged
    patched=original.copy();patched['quality']='original_complete_12_samples'
    patched.loc[patched.demand_mw.isna(),'quality']='unresolved'
    recovery=[];statuses=[];missing_points=[];reasons=[]
    with futures.ThreadPoolExecutor(max_workers=2) as pool:
        for i,(status,raw) in enumerate(pool.map(one,days),1):
            statuses.append(status)
            day=status['date'];day_missing=missing[missing.strftime('%Y%m%d')==day]
            for stamp in day_missing:
                required=pd.date_range(stamp,periods=12,freq='5min')
                have=raw.set_index('timestamp').reindex(required) if len(raw) else pd.DataFrame(index=required,columns=['supply_mw','demand_mw','reserve_mw','reserve_rate_pct'])
                valid=pd.to_numeric(have.demand_mw,errors='coerce').notna()
                for point in required[~valid]:missing_points.append(dict(timestamp=point,hour=stamp,date=day))
                if valid.all():
                    for col in ['supply_mw','demand_mw','reserve_mw','reserve_rate_pct']:
                        values=pd.to_numeric(have[col],errors='coerce')
                        patched.loc[stamp,col]=values.mean() if values.notna().all() else np.nan
                    patched.loc[stamp,'samples_5m']=12
                    patched.loc[stamp,'first_received_at']=status.get('retrieved_at')
                    patched.loc[stamp,'quality']='recovered_from_real_5min_samples'
                    recovery.append(dict(timestamp=stamp,date=day,demand_mw=float(patched.loc[stamp,'demand_mw']),new_sha256=status.get('new_sha256')))
                else:
                    reason='source_day_empty' if not len(raw) else 'all_12_samples_absent' if not valid.any() else 'partial_5min_samples'
                    patched.loc[stamp,'quality']=reason
                    reasons.append(dict(timestamp=stamp,date=day,valid_5min_samples=int(valid.sum()),missing_5min_samples=int((~valid).sum()),reason=reason,fetch_status=status['status']))
            if i%25==0 or i==len(days):
                write_json(OUT/'actual_repair_progress.json',dict(at=now(),processed=i,total=len(days),recovered_hours=len(recovery)))
                print('ACTUAL',i,'/',len(days),'recovered',len(recovery),flush=True)
    # Do not change any originally valid hourly demand value.
    known=original.demand_mw.notna()
    np.testing.assert_allclose(patched.loc[known,'demand_mw'],original.loc[known,'demand_mw'],rtol=0,atol=0)
    patched.to_csv(OUT/'demand_actual_2023_2025_repaired.csv')
    pd.DataFrame(recovery,columns=['timestamp','date','demand_mw','new_sha256']).to_csv(OUT/'actual_recovered_hours.csv',index=False)
    pd.DataFrame(reasons,columns=['timestamp','date','valid_5min_samples','missing_5min_samples','reason','fetch_status']).to_csv(OUT/'actual_unresolved_hours.csv',index=False)
    pd.DataFrame(missing_points,columns=['timestamp','hour','date']).to_csv(OUT/'actual_missing_5min_points.csv',index=False)
    write_json(OUT/'actual_repair_fetch_status.json',statuses)
    return dict(requeried_days=len(days),original_missing_hours=len(missing),recovered_hours=len(recovery),remaining_missing_hours=int(patched.demand_mw.isna().sum()),reason_counts=pd.Series([r['reason'] for r in reasons]).value_counts().to_dict(),interpolation_performed=False,original_valid_values_unchanged=True,failed_days=[r for r in statuses if r['status']=='failed'],unit='MW',aggregation='arithmetic mean of exactly twelve observed 5-minute samples',geography='EPSIS displayed current load; mainland-only scope not independently established')


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    with futures.ThreadPoolExecutor(max_workers=2) as pool:
        forecast=pool.submit(collect_forecasts);actual=pool.submit(repair_actual)
        forecast_result=forecast.result();actual_result=actual.result()
    result=dict(at=now(),seconds=time.monotonic()-started,status='complete' if forecast_result['missing_hours']==0 and actual_result['remaining_missing_hours']==0 else 'partial_remaining_source_gaps',forecast=forecast_result,actual=actual_result,model_training_performed=False,credential_values_saved=False)
    write_json(REPORT,result)
    print('FINAL',json.dumps(dict(status=result['status'],forecast_complete_days=forecast_result['complete_days'],forecast_missing_hours=forecast_result['missing_hours'],actual_recovered_hours=actual_result['recovered_hours'],actual_remaining_missing_hours=actual_result['remaining_missing_hours']),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
