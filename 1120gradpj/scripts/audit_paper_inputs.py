"""Bounded data-feasibility audit; no fitting or changes to existing experiments."""
import sys,os,json,re,concurrent.futures
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from smp_forecast.http import Client,items_from,ROOT,write_json,now
from smp_forecast.collect import get_csv
c=Client()
tests=[
 ('paper_demand_today','https://apis.data.go.kr/B552115/SmpWithForecastDemand/getSmpWithForecastDemand',dict(date='20261114',numOfRows=100,pageNo=1,dataType='json'),'KPX_SERVICE_KEY',False),
 ('paper_demand_tomorrow','https://apis.data.go.kr/B552115/SmpWithForecastDemand/getSmpWithForecastDemand',dict(date='20261115',numOfRows=100,pageNo=1,dataType='json'),'KPX_SERVICE_KEY',False),
 ('paper_demand_past','https://apis.data.go.kr/B552115/SmpWithForecastDemand/getSmpWithForecastDemand',dict(date='20250101',numOfRows=100,pageNo=1,dataType='json'),'KPX_SERVICE_KEY',False),
 ('paper_solar_2026','https://apis.data.go.kr/B552115/PvAmountByLocHr/getPvAmountByLocHr',dict(tradeYmd='20261101',numOfRows=500,pageNo=1,dataType='json'),'KPX_SERVICE_KEY',False),
 ('paper_ewp_forecast','https://apis.data.go.kr/B552070/forecastService/oamsFile31',dict(baseDate='20261113',predDate='20261114',apiType='JSON',pageNo=1,numOfRows=10),'KPX_SERVICE_KEY',False),
 ('paper_kma_forecast','https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstInfoService_2.0/getVilageFcst',dict(base_date='20261113',base_time='2300',nx=60,ny=127,dataType='JSON',numOfRows=1000,pageNo=1),'KMA_APIHUB_AUTH_KEY',False),
 ('paper_bid_monthly','https://epsis.kpx.or.kr/epsisnew/selectEkmaBddBft.ajax',dict(selYear='N',selRegion='1'),None,True),
]
def probe(t):
 name,url,p,key,post=t
 try:
  payload,m=c.fetch(name,url,p,key,post,refresh=True);r=dict(name=name,status='received',receipt=m)
  if name=='paper_bid_monthly':
   text=payload.decode();r.update(periods=re.findall(r'"Period":"([^\"]+)"',text)[:5],preview=text[:1400],resolution='monthly or annual only; not hourly bidding vintages')
  else:
   rows,total=items_from(payload);r.update(rows=len(rows),total=total,sample=rows[:2])
   if name.startswith('paper_demand'):
    land=[row for row in rows if row.get('areaName')=='육지'];r['mainland_rows']=len(land);r['mainland_hours']=sorted({int(row['hour']) for row in land});r['forecast_fields']=['mlfd','jlfd','slfd'];r['target_dates']=sorted({str(row.get('date')) for row in rows})
 except Exception as e:r=dict(name=name,status='failed',reason=str(e) if isinstance(e,RuntimeError) else type(e).__name__)
 print(json.dumps(r,ensure_ascii=False),flush=True);return r
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(probe,tests))
try:
 f,m=get_csv(c,'15069337','uddi:424ba271-f215-4fca-b313-e17d2cf9afc5');f.to_csv(ROOT/'data/processed/paper_renewable_capacity_source.csv',index=False);r=dict(name='paper_capacity_file',status='received',rows=len(f),columns=list(f.columns),sample=f.head(2).to_dict('records'),first_date=str(f.iloc[:,0].min()),last_date=str(f.iloc[:,0].max()),receipt=m);print(json.dumps(r,ensure_ascii=False),flush=True);results.append(r)
except Exception as e:results.append(dict(name='paper_capacity_file',status='failed',reason=str(e) if isinstance(e,RuntimeError) else type(e).__name__))
write_json(ROOT/'reports/paper_input_probes.json',dict(at=now(),model_training_performed=False,results=results))
