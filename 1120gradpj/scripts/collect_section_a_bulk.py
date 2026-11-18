"""Official annual downloads for load forecasts and a separate observed-demand candidate.
Uses the published KPX year-download form, not another API key or quota bypass.
"""
from pathlib import Path
from io import BytesIO
import hashlib
import http.cookiejar
import json
import re
import shutil
import ssl
import sys
import urllib.parse
import urllib.request
import certifi
import numpy as np
import pandas as pd
from openpyxl import load_workbook
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from smp_forecast.http import Client,write_json,now
from smp_forecast.collect import get_csv
OUT=ROOT/'data/processed/section_a'
RAW=ROOT/'data/raw/public_forecast_years'
EXPECTED=pd.date_range('2023-01-01','2025-12-31 23:00',freq='h',tz='Asia/Seoul')
NATIONAL_IDS={2023:'uddi:e0894814-0822-4a76-9558-e035f905fe7f',2024:'uddi:159ec977-0b24-4550-9308-bc5c851804f2',2025:'uddi:6ade08d2-0014-4d22-b10c-c811e3273c70'}


def parse_forecast_workbook(path,year):
    # KPX exports declare the wrong worksheet dimension A1; read all cells, not the read-only dimension.
    wb=load_workbook(path,read_only=False,data_only=True)
    if len(wb.sheetnames)!=1:raise ValueError('Unexpected sheets')
    sheet=wb.active;rows=list(sheet.values);wb.close()
    if '발전계획용 수요예측' not in str(rows[0][0]) or '육지' not in str(rows[0][0]):raise ValueError('Wrong workbook subject/geography')
    if list(rows[1][:25])!=['구분']+[f'{i}h' for i in range(1,25)]:raise ValueError('Unexpected forecast headers')
    records=[]
    for row in rows[2:]:
        if row[0] is None:continue
        day=pd.to_datetime(str(row[0]),format='%Y%m%d')
        if day.year!=year:raise ValueError('Workbook year mismatch')
        for h in range(1,25):
            value=float(row[h])
            if not np.isfinite(value) or value<=0:raise ValueError('Missing/nonpositive forecast')
            records.append(dict(timestamp=day.tz_localize('Asia/Seoul')+pd.Timedelta(hours=h-1),target_date=str(day.date()),source_hour=h,demand_forecast_mw=value,geography='mainland',source='KPX official annual mainland day-ahead load forecast',source_url='https://new.kpx.or.kr/xlsxdownload.es?act=pssinland&gubun=year',source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),historical_published_at=None))
    f=pd.DataFrame(records).sort_values('timestamp')
    expected=pd.date_range(f'{year}-01-01',f'{year}-12-31 23:00',freq='h',tz='Asia/Seoul')
    if not pd.DatetimeIndex(f.timestamp).equals(expected):raise ValueError('Incomplete or duplicate year')
    return f


def download_forecasts():
    RAW.mkdir(parents=True,exist_ok=True)
    jar=http.cookiejar.CookieJar()
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar),urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=certifi.where())))
    page='https://new.kpx.or.kr/pssInland.es?mid=a10606090100&device=pc'
    # Normal public form session. Do not save cookies/CSRF tokens in receipts.
    with opener.open(page,timeout=30) as response:html=response.read().decode('utf-8')
    csrf=re.search(r'name="_csrf"\s+value="([^"]+)"',html).group(1)
    annual_url='https://new.kpx.or.kr/xlsxdownload.es?act=pssinland&gubun=year'
    if 'act=pssinland&amp;gubun=year' not in html and 'act=pssinland&gubun=year' not in html:raise ValueError('Published annual export link changed')
    frames=[]
    for year in [2023,2024,2025]:
        path=RAW/f'mainland_demand_forecast_{year}.xlsx'
        if not path.exists():
            request=urllib.request.Request(annual_url,data=urllib.parse.urlencode(dict(issue_date=f'{year}-12-31',yy=year,_csrf=csrf)).encode(),headers={'Referer':page})
            with opener.open(request,timeout=45) as response:body=response.read()
            if body[:2]!=b'PK':raise ValueError('Annual export is not an XLSX workbook')
            path.write_bytes(body)
        f=parse_forecast_workbook(path,year);frames.append(f)
        write_json(RAW/f'{year}_receipt.json',dict(source=annual_url,parameters=dict(yy=year,issue_date=f'{year}-12-31'),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size,validated_at=now(),authentication='public website form; no API key'))
        print('Annual forecast',year,len(f),flush=True)
    annual=pd.concat(frames,ignore_index=True).sort_values('timestamp')
    if not pd.DatetimeIndex(annual.timestamp).equals(EXPECTED):raise ValueError('Forecast combined time coverage failure')
    main=OUT/'demand_forecast_mainland_2023_2025.csv'
    partial=OUT/'demand_forecast_mainland_api_partial_20261118.csv'
    if main.exists() and not partial.exists():shutil.copy2(main,partial)
    old=pd.read_csv(partial) if partial.exists() else pd.DataFrame()
    matched=0;maxdiff=None
    if len(old):
        old.timestamp=pd.to_datetime(old.timestamp,utc=True).dt.tz_convert('Asia/Seoul')
        paired=annual[['timestamp','demand_forecast_mw']].merge(old[['timestamp','demand_forecast_mw']],on='timestamp',suffixes=('_annual','_api'),validate='one_to_one')
        matched=len(paired);maxdiff=float(abs(paired.demand_forecast_mw_annual-paired.demand_forecast_mw_api).max())
        if matched!=len(old) or maxdiff>1e-9:
            annual.to_csv(OUT/'demand_forecast_annual_candidate_conflict.csv',index=False)
            raise ValueError('Public annual forecast differs from API: inspect revisions before substitution')
    annual['retrieved_or_validated_at']=now()
    annual.to_csv(main,index=False)
    pd.DataFrame({'timestamp':pd.DatetimeIndex([],tz='Asia/Seoul')}).to_csv(OUT/'demand_forecast_missing_hours.csv',index=False)
    return annual,dict(days=1096,hours=len(annual),missing_hours=0,api_overlap_hours=matched,max_absolute_difference_vs_api_mw=maxdiff,source='KPX official annual download',historical_publication_vintages_verified=False)


def collect_national_candidate():
    client=Client();frames=[];receipts=[]
    for year,uid in NATIONAL_IDS.items():
        raw,m=get_csv(client,'15065266',uid)
        raw.to_csv(OUT/f'national_actual_source_{year}.csv',index=False)
        date=pd.to_datetime(raw['날짜'],errors='coerce')
        for h in range(1,25):
            frames.append(pd.DataFrame(dict(timestamp=date+pd.Timedelta(hours=h-1),national_generation_demand_mwh=pd.to_numeric(raw[f'{h}시'],errors='coerce'))))
        receipts.append(dict(year=year,dataset='15065266',file_id=uid,sha256=m['sha256'],nondate_rows=int(date.isna().sum())))
    f=pd.concat(frames,ignore_index=True)
    f=f[f.timestamp.notna()].copy();f.timestamp=f.timestamp.dt.tz_localize('Asia/Seoul')
    f=f[f.timestamp.dt.year.between(2023,2025)].sort_values('timestamp')
    if not pd.DatetimeIndex(f.timestamp).equals(EXPECTED):raise ValueError('National candidate missing/duplicate hours')
    if not np.isfinite(f.national_generation_demand_mwh).all() or not f.national_generation_demand_mwh.gt(0).all():raise ValueError('National candidate missing/invalid values')
    f['source']='KPX 15065266 official nationwide generation-end demand';f['unit']='MWh';f['geography']='mainland and Jeju'
    f.to_csv(OUT/'national_generation_demand_candidate_2023_2025.csv',index=False)
    original=pd.read_csv(ROOT/'data/processed/power_hourly.csv');original.timestamp=pd.to_datetime(original.timestamp,utc=True).dt.tz_convert('Asia/Seoul')
    pair=f.merge(original[['timestamp','demand_mw']],on='timestamp',how='left');good=pair.demand_mw.notna()
    # Numeric comparison only: MWh over a one-hour slot corresponds to hourly average MW.
    diff=pair.loc[good,'national_generation_demand_mwh']-pair.loc[good,'demand_mw']
    return f,dict(hours=len(f),missing_hours=0,geography='nationwide incl Jeju',unit='MWh',provisional=True,indicator='generation-end demand for demand forecasting',compared_hours=int(good.sum()),mean_abs_difference_from_5min_average_mw=float(abs(diff).mean()),max_abs_difference_mw=float(abs(diff).max()),not_spliced_into_original=True,receipts=receipts)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    forecast,forecast_report=download_forecasts()
    actual,actual_report=collect_national_candidate()
    existing=pd.read_csv(OUT/'demand_actual_2023_2025_repaired.csv');existing.timestamp=pd.to_datetime(existing.timestamp,utc=True).dt.tz_convert('Asia/Seoul')
    calendar=pd.read_csv(OUT/'calendar_hourly_2023_2025.csv');calendar.timestamp=pd.to_datetime(calendar.timestamp,utc=True).dt.tz_convert('Asia/Seoul')
    # Distinct source concepts remain distinct columns; never silently fill one from the other.
    combined=calendar.merge(existing[['timestamp','demand_mw','quality']].rename(columns={'demand_mw':'epsis_current_load_hourly_mean_mw','quality':'epsis_current_load_quality'}),on='timestamp',validate='one_to_one').merge(forecast[['timestamp','demand_forecast_mw']],on='timestamp',validate='one_to_one').merge(actual[['timestamp','national_generation_demand_mwh']],on='timestamp',validate='one_to_one')
    combined.to_csv(OUT/'section_a_hourly_2023_2025.csv',index=False)
    report=dict(at=now(),forecast=forecast_report,actual_alternative=actual_report,rows=len(combined),model_training_performed=False,original_files_overwritten=False,credentials_saved=False,remaining_decisions=['Choose whether to retain EPSIS current-load average with unresolved gaps or formally adopt nationwide generation-end hourly demand as a whole series; do not mix source definitions.','Mainland-specific observed demand remains unconfirmed; nationwide candidate includes Jeju.'])
    write_json(ROOT/'reports/section_a_bulk_20261118.json',report)
    print(json.dumps(report,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
