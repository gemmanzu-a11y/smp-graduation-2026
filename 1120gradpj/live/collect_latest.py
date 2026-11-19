"""Bounded official-source refresh; credentials stay in local .env and memory."""
from pathlib import Path
import argparse,concurrent.futures,json,sys,re
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from smp_forecast.http import Client,items_from,now,write_json,FetchError
from smp_forecast.collect import parse_smp,parse_power,parse_weather,get_csv
OUT=ROOT/'data/live_20261120';OUT.mkdir(parents=True,exist_ok=True)

def keys():
    result={}
    p=ROOT/'.env'
    if p.exists():
        for line in p.read_text().splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                k,v=line.split('=',1);v=v.strip().strip('\"\'')
                if v:result[k.strip()]=v
    return result

def collect(task):
    name,kind,day=task;c=Client(keys());output=OUT/(name+'.csv')
    try:
        if kind=='smp':
            b,m=c.fetch('live_20261120_smp','https://epsis.kpx.or.kr/epsisnew/selectEkmaSmpShd.ajax',dict(beginDate='20261114',endDate='20261116',selYear='',selMonth='',selKind='land',locale=''),post=True)
            f=parse_smp(b)
        elif kind=='power':
            b,m=c.fetch('live_20261120_power','https://epsis.kpx.or.kr/epsisnew/selectEkgeEpsMepRealGridAjax.ajax',dict(beginDate=day,endDate=day,editYn='N'),post=True)
            f=parse_power(b);f=f[f.timestamp.dt.strftime('%Y%m%d')==day]
        elif kind=='asos':
            b,m=c.fetch('live_20261120_asos','https://apihub.kma.go.kr/api/typ01/url/kma_sfctm3.php',dict(tm1='202611140000',tm2='202611162300',stn='108',help=0),'KMA_APIHUB_AUTH_KEY')
            f=parse_weather(b,(108,))
        elif kind in ['demand','generation']:
            service='SmpWithForecastDemand/getSmpWithForecastDemand' if kind=='demand' else 'PvAmountByPwrGen/getPvAmountByPwrGen'
            params=dict(numOfRows=1000,pageNo=1,dataType='json');params['date' if kind=='demand' else 'tradeYmd']=day
            b,m=c.fetch('live_20261120_'+kind,'https://apis.data.go.kr/B552115/'+service,params,'KPX_SERVICE_KEY')
            rows,total=items_from(b)
            if total>1000:raise ValueError('Pagination required; refusing partial day')
            f=pd.DataFrame(rows)
            if len(f):
                if kind=='demand':
                    f=f[f.areaName.eq('육지')].copy();f['timestamp']=pd.to_datetime(f['date'].astype(str),format='%Y%m%d').dt.tz_localize('Asia/Seoul')+pd.to_timedelta(pd.to_numeric(f.hour)-1,unit='h');f['mlfd']=pd.to_numeric(f.mlfd,errors='raise')
                    if not f['date'].astype(str).eq(day).all():raise ValueError('Returned demand date differs from request')
                    if f.timestamp.duplicated().any():raise ValueError('Duplicate forecast hours')
                else:
                    f['timestamp']=pd.to_datetime(f.tradeYmd.astype(str),format='%Y%m%d').dt.tz_localize('Asia/Seoul')+pd.to_timedelta(pd.to_numeric(f.tradeNo)-1,unit='h');f['amgo']=pd.to_numeric(f.amgo,errors='raise')
                    if not f.tradeYmd.astype(str).eq(day).all():raise ValueError('Returned generation date differs from request')
                    if f.duplicated(['timestamp','fuelTpCd']).any():raise ValueError('Duplicate fuel-hour')
        elif kind=='fred':
            b,m=c.fetch('live_20261120_fred','https://api.stlouisfed.org/fred/series/observations',dict(file_type='json',series_id=day,realtime_start='2025-12-28',realtime_end='2026-11-17',observation_start='2025-01-01',observation_end='2026-11-17',output_type=1,limit=100000),'FRED_API_KEY')
            o=json.loads(b)
            if 'error_code' in o:raise ValueError('FRED service error '+str(o['error_code']))
            f=pd.DataFrame(o['observations'])
            if len(f)!=o['count']:raise ValueError('Incomplete FRED vintage intervals')
        else:raise ValueError('Unsupported task')
        if len(f):f.to_csv(output,index=False)
        return dict(task=name,status='collected' if len(f) else 'normal_empty',rows=len(f),file=str(output.relative_to(ROOT)),receipt=m)
    except Exception as e:
        # Never print request exceptions containing authenticated URLs.
        safe=str(e) if isinstance(e,(FetchError,ValueError)) else type(e).__name__
        for v in c.keys.values():safe=safe.replace(v,'[redacted]')
        return dict(task=name,status='failed',reason=safe)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--keyless-only',action='store_true');args=ap.parse_args()
    tasks=[('smp_recent','smp',None)]+[(f'power_{d}','power',d) for d in ['20261114','20261115','20261116']]
    if not args.keyless_only:
        tasks += [('asos_recent','asos',None)]
        tasks += [(f'{kind}_{d:%Y%m%d}',kind,f'{d:%Y%m%d}') for kind in ['demand','generation'] for d in pd.date_range('2026-11-09','2026-11-16')]
        tasks += [(series,'fred',series) for series in ['DCOILWTICO','DCOILBRENTEU','PNGASJPUSDM','PCOALAUUSDM']]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results=[]
        for result in pool.map(collect,tasks):
            results.append(result);print(json.dumps({k:v for k,v in result.items() if k!='receipt'},ensure_ascii=False),flush=True)
            write_json(OUT/('collection_keyless.json' if args.keyless_only else 'collection.json'),dict(collected_at=now(),tasks=results))
if __name__=='__main__':main()
