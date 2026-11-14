import sys,json,re,concurrent.futures
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from smp_forecast.http import Client,items_from,write_json,ROOT,now
keys=json.loads(sys.stdin.readline()) if '--keys-stdin' in sys.argv else None
client=Client(keys)
tests=[
 ('smp_api','https://apis.data.go.kr/B552115/SmpWithForecastDemand/getSmpWithForecastDemand',dict(date='20261114',numOfRows=100,pageNo=1,dataType='json'),'KPX_SERVICE_KEY',False),
 ('generation_api','https://apis.data.go.kr/B552115/PvAmountByPwrGen/getPvAmountByPwrGen',dict(tradeYmd='20251001',numOfRows=100,pageNo=1,dataType='json'),'KPX_SERVICE_KEY',False),
 ('solar_api','https://apis.data.go.kr/B552115/PvAmountByLocHr/getPvAmountByLocHr',dict(tradeYmd='20251001',numOfRows=100,pageNo=1,dataType='json'),'KPX_SERVICE_KEY',False),
 ('generation_live_api','https://apis.data.go.kr/B552115/sumperfuel5m/getSumperfuel5m',dict(numOfRows=10,pageNo=1,dataType='json'),'KPX_SERVICE_KEY',False),
 ('holidays_api','https://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo',dict(solYear=2025,numOfRows=100,pageNo=1,_type='json'),'KPX_SERVICE_KEY',False),
 ('power_hourly_probe','https://epsis.kpx.or.kr/epsisnew/selectEkgeEpsMepRealGridAjax.ajax',dict(beginDate='20250101',endDate='20250102',editYn='N'),None,True),
 ('kma_period_probe','https://apihub.kma.go.kr/api/typ01/url/kma_sfctm3.php',dict(tm1='202501010000',tm2='202501022300',stn='108',help=1),'KMA_APIHUB_AUTH_KEY',False),
]
def f(t):
 name,url,p,key,post=t
 try:
  payload,m=client.fetch(name,url,p,key,post);result=dict(name=name,status='received',receipt=m)
  if name.endswith('api'):
   items,total=items_from(payload);result.update(rows=len(items),total=total,sample=items[:2])
  else:result.update(preview=payload.decode('utf-8',errors='replace')[:1800])
 except Exception as e:result=dict(name=name,status='failed',reason=str(e) if isinstance(e,RuntimeError) else type(e).__name__)
 print(json.dumps(result,ensure_ascii=False),flush=True);return result
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(f,tests))
write_json(ROOT/'reports/api_probes.json',dict(checked_at=now(),results=results))
