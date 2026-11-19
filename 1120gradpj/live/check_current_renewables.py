"""Check the latest official annual regional file, without substituting solar-only data."""
from pathlib import Path
import sys,re,json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from smp_forecast.http import Client,write_json,now
from smp_forecast.collect import get_csv
OUT=ROOT/'data/live_20261120';c=Client()
try:
    b,receipt=c.fetch('live_20261120_renewable_catalog','https://www.data.go.kr/data/15065269/fileData.do')
    matches=re.findall(r"fn_fileDataDown\('15065269',\s*'([^']+)'",b.decode('utf-8'))
    if not matches:raise ValueError('Latest official download ID not found')
    f,source=get_csv(c,'15065269',matches[0]);f.columns=f.columns.str.strip()
    datecol=next(k for k in f if k in ['거래일자','거래일']);dates=pd.to_datetime(f[datecol]);latest=f[dates.dt.year.eq(2026)].copy()
    report=dict(checked_at=now(),source_page='https://www.data.go.kr/data/15065269/fileData.do',latest_download_id=matches[0],file_rows=len(f),source_date_min=str(dates.min()),source_date_max=str(dates.max()),rows_2026=len(latest),columns=list(f),receipt=source)
    if len(latest):latest.to_csv(OUT/'renewable_official_2026.csv',index=False)
    write_json(OUT/'renewable_current_source.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='receipt'},ensure_ascii=False),flush=True)
except Exception as e:
    write_json(OUT/'renewable_current_source.json',dict(checked_at=now(),status='failed',reason=str(e) if isinstance(e,ValueError) else type(e).__name__))
    print('renewables check failed:',str(e) if isinstance(e,ValueError) else type(e).__name__,flush=True)
