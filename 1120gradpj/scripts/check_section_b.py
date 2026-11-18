"""Section B access/coverage audit, preserving original data; no model fitting."""
from pathlib import Path
import concurrent.futures
import json
import sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from smp_forecast.http import Client,items_from,write_json,now
OUT=ROOT/'data/processed/section_b'
OUT.mkdir(parents=True,exist_ok=True)
EXPECTED=pd.date_range('2023-01-01','2025-12-31 23:00',freq='h',tz='Asia/Seoul')


def local_quality():
    renew=pd.read_csv(ROOT/'data/processed/renewable_hourly.csv')
    renew.timestamp=pd.to_datetime(renew.timestamp,utc=True).dt.tz_convert('Asia/Seoul')
    if renew.timestamp.duplicated().any():raise ValueError('Duplicate renewable timestamps')
    f=renew.set_index('timestamp').reindex(EXPECTED)
    renew_report={}
    for col in ['solar_mwh','wind_mwh']:
        missing=f.index[f[col].isna()]
        renew_report[col]=dict(expected_hours=len(f),valid_hours=int(f[col].notna().sum()),missing_hours=len(missing),missing_timestamps=[str(x) for x in missing[:48]],minimum=float(f[col].min()),maximum=float(f[col].max()))
    f.to_csv(OUT/'renewable_mainland_2023_2025.csv',index_label='timestamp')
    p=pd.read_csv(ROOT/'data/processed/section_a/demand_actual_2023_2025_repaired.csv')
    p.timestamp=pd.to_datetime(p.timestamp,utc=True).dt.tz_convert('Asia/Seoul')
    p=p.set_index('timestamp').reindex(EXPECTED)
    cols=['supply_mw','demand_mw','reserve_mw','reserve_rate_pct','samples_5m','quality']
    p[cols].to_csv(OUT/'supply_reserve_2023_2025.csv',index_label='timestamp')
    reserve={col:dict(expected_hours=len(p),valid_hours=int(p[col].notna().sum()),missing_hours=int(p[col].isna().sum()),unit='%' if col=='reserve_rate_pct' else 'MW') for col in ['supply_mw','reserve_mw','reserve_rate_pct']}
    good=p[['supply_mw','demand_mw','reserve_mw']].notna().all(axis=1)
    identity=p.loc[good,'supply_mw']-p.loc[good,'demand_mw']-p.loc[good,'reserve_mw']
    reserve['identity_check']=dict(compared_hours=int(good.sum()),mean_absolute_difference_mw=float(abs(identity).mean()),maximum_absolute_difference_mw=float(abs(identity).max()),note='Raw reported reserve retained; differences are flagged, not overwritten by derived values.')
    return renew_report,reserve


def probe(t):
    kind,date=t;c=Client()
    try:
        if kind=='generation':
            b,m=c.fetch('section_b_generation','https://apis.data.go.kr/B552115/PvAmountByPwrGen/getPvAmountByPwrGen',dict(tradeYmd=date,numOfRows=1000,pageNo=1,dataType='json'),'KPX_SERVICE_KEY',refresh=True)
            rows,total=items_from(b)
            if len(rows)<total:raise ValueError('Incomplete pagination; do not infer complete day')
            f=pd.DataFrame(rows)
            if len(f):
                hours=pd.to_numeric(f.tradeNo,errors='raise').astype(int)
                if not hours.between(1,24).all():raise ValueError('Unexpected generation hour')
                f['timestamp']=pd.to_datetime(f.tradeYmd,format='%Y%m%d').dt.tz_localize('Asia/Seoul')+pd.to_timedelta(hours-1,unit='h')
                f['amgo']=pd.to_numeric(f.amgo,errors='raise')
                f.to_csv(OUT/f'generation_{date}.csv',index=False)
            return dict(kind=kind,date=date,http=200,status='received' if rows else 'normal_empty',rows=len(rows),total=total,fuels=sorted(f.fuelTpCd.unique().tolist()) if len(f) else [],hours_per_fuel=f.groupby('fuelTpCd').size().to_dict() if len(f) else {},sample=rows[:2],receipt=m)
        base=(pd.Timestamp(date)-pd.Timedelta(days=1)).strftime('%Y%m%d')
        b,m=c.fetch('section_b_solar_forecast','https://apis.data.go.kr/B552070/forecastService/oamsFile31',dict(baseDate=base,predDate=date,apiType='JSON',pageNo=1,numOfRows=1000),'KPX_SERVICE_KEY',refresh=True)
        rows,total=items_from(b)
        # EWP root response header/body is handled by items_from as well.
        if len(rows)<total:raise ValueError('Incomplete pagination')
        f=pd.DataFrame(rows)
        result=dict(kind=kind,baseDate=base,predDate=date,http=200,status='received' if rows else 'normal_empty',rows=len(rows),total=total,receipt=m)
        if len(f):
            for col in ['baseDate','baseTime','predDate','hh','city','solgenKpx','icsrPred','temp','ws']:
                if col not in f:raise ValueError('Missing EWP field '+col)
            if f.duplicated(['baseDate','baseTime','predDate','hh','city']).any():raise ValueError('Duplicate EWP forecast keys')
            f.to_csv(OUT/f'solar_forecast_{date}.csv',index=False)
            land=f[~f.city.str.contains('제주')].copy()
            land['solgenKpx']=pd.to_numeric(land.solgenKpx,errors='raise')
            hourly=land.groupby(['baseDate','baseTime','predDate','hh'],as_index=False).solgenKpx.sum()
            hourly.to_csv(OUT/f'solar_forecast_mainland_{date}.csv',index=False)
            result.update(cities=sorted(f.city.unique().tolist()),hours=sorted(f.hh.astype(int).unique().tolist()),mainland_hour_rows=len(hourly),fields=list(f.columns),sample=rows[:1])
        return result
    except Exception as e:
        return dict(kind=kind,date=date,status='failed',reason=str(e) if isinstance(e,(RuntimeError,ValueError)) else type(e).__name__)


def main():
    renew,reserve=local_quality()
    tasks=[('generation',d) for d in ['20230101','20240101','20250101','20260901','20261117']]
    tasks += [('solar_forecast',d) for d in ['20230102','20240102','20250102','20250702','20261118','20261119']]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(probe,tasks))
    for r in results:print(json.dumps({k:v for k,v in r.items() if k not in ['receipt','sample','fields','cities','hours_per_fuel']},ensure_ascii=False),flush=True)
    write_json(ROOT/'reports/section_b_check_20261118.json',dict(at=now(),model_training_performed=False,scope='B supply: API samples plus full existing historical coverage audit',renewables=renew,supply_reserve=reserve,api_probes=results,credentials_saved=False))
    print('RENEWABLES',json.dumps(renew,ensure_ascii=False),flush=True)
    print('RESERVE',json.dumps(reserve,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
