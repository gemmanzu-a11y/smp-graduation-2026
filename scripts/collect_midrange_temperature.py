import requests,certifi,pandas as pd,io,json,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
s=None
root=Path('1120gradpj/data/raw/kma_midrange_temperature');out=Path('shared_datasets/kma_midrange_temperature_seoul');out.mkdir(exist_ok=True,parents=True)
receipts=[]
def collect(month):
 s=requests.Session()
 year=month.year
 start=month.start_time.strftime('%Y%m%d');end=min(month.end_time.strftime('%Y%m%d'),'20261117')
 raw=root/f'temperature_{month}.csv'
 p=dict(pgmNo='646',elementCds='WT',stnIds='_108',startDt=start,endDt=end,lrgClssCd='WTF',mddlClssCd='WTF04',serviceSe='F00102',dataFormCd='F00502',menuNo='635',fileType='csv')
 if not raw.exists():
  r=s.post('https://data.kma.go.kr/data/weatherReport/downloadMrfDataCSV.do',data=p,timeout=60,verify=certifi.where());r.raise_for_status()
  file=r.text.strip()
  if not file.startswith('/n027/') or not file.endswith('.csv'):raise RuntimeError('Unexpected file response: '+r.text[:80])
  r=s.post('https://data.kma.go.kr/download/fileDownload.do',data={'file':file},timeout=60,verify=certifi.where());r.raise_for_status()
  assert not r.content.lstrip().startswith(b'<'), 'Unexpected HTML'
  raw.write_bytes(r.content)
 d=pd.read_csv(raw,encoding='cp949');assert '최저기온' in d and '최고기온' in d
 assert set(d['발표시각'].str[:7])=={str(month)}, 'Returned month does not match request: '+str(month)
 seoul=d[d['도시'].eq('서울')].copy();assert len(seoul)>0
 seoul.insert(0,'issued_at_kst',pd.to_datetime(seoul['발표시각'],format='%Y-%m-%d %H시').dt.tz_localize('Asia/Seoul').map(lambda x:x.isoformat()))
 seoul.insert(1,'target_date',pd.to_datetime(seoul['예보시각']).dt.strftime('%Y-%m-%d'))
 for output_month,rows in seoul.groupby(seoul.issued_at_kst.str[:7]):
  dest=out/f'temperature_{output_month}.csv';rows.to_csv(dest,index=False,encoding='utf-8-sig');assert dest.stat().st_size<5*1024*1024
 receipt=dict(month=str(month),source_rows=len(d),seoul_rows=len(seoul),source_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),params=p)
 return receipt

if __name__ == '__main__':
 with ThreadPoolExecutor(max_workers=1) as pool:
  for receipt in pool.map(collect,pd.period_range('2023-01','2026-11',freq='M')):
   receipts.append(receipt)
   (out/'collection_receipts.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+'\n')
   print(json.dumps(receipt,ensure_ascii=False),flush=True)
