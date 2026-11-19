"""Refresh two days of official public KMA CSVs without API credentials."""
from pathlib import Path
import hashlib,io,json,time
import pandas as pd
import requests
OUT=Path(__file__).resolve().parents[1]/'data/live_20261120';OUT.mkdir(parents=True,exist_ok=True)
for element,label in [('WT','temperature'),('WL','weather')]:
    try:
        params=dict(pgmNo='646',elementCds=element,stnIds='_108',startDt='20261118',endDt='20261119',lrgClssCd='WTF',mddlClssCd='WTF04',serviceSe='F00102',dataFormCd='F00502',menuNo='635',fileType='csv',rstView2='1')
        with requests.Session() as s:
            r=s.post('https://data.kma.go.kr/data/weatherReport/downloadMrfDataCSV.do',data=params,timeout=60);r.raise_for_status();name=r.text.strip()
            if not name.startswith('/n027/') or not name.endswith('.csv'):raise ValueError('Unexpected download response')
            r=s.post('https://data.kma.go.kr/download/fileDownload.do',data={'file':name},timeout=60);r.raise_for_status();b=r.content
        f=pd.read_csv(io.BytesIO(b),encoding='cp949')
        if f.empty:raise ValueError('Empty official CSV')
        issued=pd.to_datetime(f['발표시각'],format='%Y-%m-%d %H시').dt.tz_localize('Asia/Seoul')
        if not issued.dt.strftime('%Y%m%d').between('20261118','20261119').all():raise ValueError('Wrong issuance dates')
        (OUT/f'midrange_{label}_raw.csv').write_bytes(b)
        if element=='WT':
            f=f[f['도시'].eq('서울')].copy();f.insert(0,'issued_at_kst',pd.to_datetime(f['발표시각'],format='%Y-%m-%d %H시').dt.tz_localize('Asia/Seoul').map(lambda t:t.isoformat()));f.insert(1,'target_date',pd.to_datetime(f['예보시각']).dt.strftime('%Y-%m-%d'))
        else:
            target=pd.to_datetime(f['예보시각'].str[:10]);period=f['예보시각'].str[11:];mapping={'오전':'AM','오후':'PM','':'DAY'}
            if not period.isin(mapping).all():raise ValueError('Unknown forecast period')
            f=pd.DataFrame(dict(issued_at_kst=issued.map(lambda t:t.isoformat()),region=f['지역'],target_date=target.dt.strftime('%Y-%m-%d'),target_period=period.map(mapping),weather_text=f['예보'],precip_probability_pct=f['강수확률(%)']))
        if f.empty:raise ValueError('No requested region')
        f.to_csv(OUT/f'midrange_{label}.csv',index=False)
        receipt=dict(source='https://data.kma.go.kr/data/weatherReport/mrfList.do?pgmNo=646',params=params,received_at=pd.Timestamp.now(tz='Asia/Seoul').isoformat(),rows=len(f),latest_issued=f.issued_at_kst.max(),sha256=hashlib.sha256(b).hexdigest())
        (OUT/f'midrange_{label}_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2));print(label,receipt['rows'],receipt['latest_issued'],list(f),flush=True)
    except Exception as e:print(label,'failed',type(e).__name__,str(e)[:160],flush=True)
    time.sleep(1.2)
