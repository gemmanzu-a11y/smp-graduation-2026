"""Retest authorized KPX services without reusing prior response caches."""
import sys,concurrent.futures,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from smp_forecast.http import Client,items_from,ROOT,write_json,now
c=Client()
tests=[
 ('발전원별 발전량_2025','https://apis.data.go.kr/B552115/PvAmountByPwrGen/getPvAmountByPwrGen',dict(tradeYmd='20251001',numOfRows=100,pageNo=1,dataType='json')),
 ('발전원별 발전량_2026','https://apis.data.go.kr/B552115/PvAmountByPwrGen/getPvAmountByPwrGen',dict(tradeYmd='20260901',numOfRows=100,pageNo=1,dataType='json')),
 ('발전원별 발전량_최신표본','https://apis.data.go.kr/B552115/PvAmountByPwrGen/getPvAmountByPwrGen',dict(tradeYmd='20261101',numOfRows=100,pageNo=1,dataType='json')),
 ('발전원별 발전량 현황조회_GW','https://apis.data.go.kr/B552115/sumperfuel5m/getSumperfuel5m',dict(numOfRows=10,pageNo=1,dataType='json')),
 ('지역별 시간별 태양광 및 풍력 발전량_파일API','https://api.odcloud.kr/api/15065269/v1/uddi:76850689-e74c-402e-bfec-9142976b96c8',dict(page=1,perPage=2)),
 ('지역별 시간별 태양광 발전량 정보','https://apis.data.go.kr/B552115/PvAmountByLocHr/getPvAmountByLocHr',dict(tradeYmd='20260901',numOfRows=500,pageNo=1,dataType='json')),
 ('월간 연료비용 정보','https://apis.data.go.kr/B552115/FuelCost1/getFuelCost1',dict(day='202610',numOfRows=100,pageNo=1,dataType='json')),
 ('계통한계가격 및 수요예측','https://apis.data.go.kr/B552115/SmpWithForecastDemand/getSmpWithForecastDemand',dict(date='20261114',numOfRows=100,pageNo=1,dataType='json')),
]
def probe(t):
 name,url,p=t
 try:
  b,m=c.fetch('approval_recheck',url,p,'KPX_SERVICE_KEY',refresh=True)
  if 'odcloud' in url:
   o=json.loads(b);items=o.get('data',[]);total=o.get('totalCount',0);code=o.get('code',0)
   if code not in (0,None):raise RuntimeError('ODcloud code '+str(code))
  else:items,total=items_from(b);code=json.loads(b.decode('utf-8-sig')).get('response',{}).get('header',{})
  r=dict(service=name,status='data_received' if items else 'normal_response_no_data',http_status=m['http_status'],rows=len(items),total=total,result=code,sample=items[:2],receipt=m)
 except Exception as e:r=dict(service=name,status='failed',reason=str(e) if isinstance(e,RuntimeError) else type(e).__name__)
 print(json.dumps(r,ensure_ascii=False),flush=True);return r
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:r=list(pool.map(probe,tests))
write_json(ROOT/'reports/kpx_approval_recheck.json',dict(at=now(),credential_values_saved=False,scope='actual endpoint access check; account approval page not accessed',results=r))
