"""Official source collection; no credentials in files; no eval of source JavaScript."""
import re,json,calendar,concurrent.futures,sys,argparse
from io import BytesIO
import pandas as pd
import numpy as np
from .http import Client,ROOT,now,write_json,items_from,FetchError
OUT=ROOT/'data/processed'
def csv_write(frame,name):
 OUT.mkdir(parents=True,exist_ok=True);frame.to_csv(OUT/name,index=False)
def parse_smp(payload):
 text=payload.decode('utf-8');rows=[]
 pattern=r'((?:\s*c\d+\s*=\s*textFormmat\("[^"]*",count\);\s*)+)gridData.push\(\{"Date":"(\d{4}/\d{2}/\d{2})"'
 for block,date in re.findall(pattern,text):
  values=dict(re.findall(r'c(\d+)\s*=\s*textFormmat\("([^"]*)",count\)',block))
  if not all(str(h) in values for h in range(1,25)):raise ValueError('incomplete SMP day')
  for h in range(1,25):rows.append(dict(timestamp=pd.Timestamp(date,tz='Asia/Seoul')+pd.Timedelta(hours=h-1),smp=float(values[str(h)].replace(',',''))))
 f=pd.DataFrame(rows)
 if f.empty or f.timestamp.duplicated().any() or not np.isfinite(f.smp).all():raise ValueError('empty/duplicate/nonfinite SMP')
 return f.sort_values('timestamp')
def parse_power(payload):
 text=payload.decode('utf-8');rows=[]
 for block,ts in re.findall(r'(c1\s*=.*?)gridData.push\(\{"year":"([^"\n]+)"',text,re.S):
  fields=dict(re.findall(r'(c\d+)\s*=\s*textFormmat\("([^"]*)",\s*0\)',block));rows.append(dict(timestamp=pd.Timestamp(ts,tz='Asia/Seoul'),supply_mw=pd.to_numeric(fields.get('c1'),errors='coerce'),demand_mw=pd.to_numeric(fields.get('c2'),errors='coerce'),reserve_mw=pd.to_numeric(fields.get('c5'),errors='coerce'),reserve_rate_pct=pd.to_numeric(fields.get('c6'),errors='coerce')))
 f=pd.DataFrame(rows)
 if f.empty:raise ValueError('no 5-minute power data')
 if f.timestamp.duplicated().any():raise ValueError('duplicate 5-minute readings')
 f=f.set_index('timestamp').sort_index();hour=f.resample('h').mean();hour['samples_5m']=f.demand_mw.resample('h').count()
 # Mean power is MW, not an observed MWh settlement quantity. Do not expand daily peaks.
 hour.loc[hour.samples_5m!=12,['supply_mw','demand_mw','reserve_mw','reserve_rate_pct']]=np.nan
 return hour.reset_index()
def parse_weather(payload,stations):
 rows=[]
 for line in payload.decode('cp949',errors='replace').splitlines():
  if not re.match(r'^\d{12}\s',line):continue
  p=line.split()
  if len(p)<40:raise ValueError('truncated ASOS observation')
  stn=int(p[1])
  if stn not in stations:continue
  ta,wind,solar=float(p[11]),float(p[3]),float(p[-12])
  # TA=-9 C is valid; SI/WS=-9 are missing sentinels. Missing night SI stays NaN.
  ta=np.nan if ta in (-99,-999) else ta;wind=np.nan if wind<0 else wind;solar=np.nan if solar<0 else solar
  rows.append(dict(timestamp=pd.to_datetime(p[0],format='%Y%m%d%H%M').tz_localize('Asia/Seoul'),station_id=stn,temperature_c=ta,wind_ms=wind,solar_radiation_mj_m2=solar))
 f=pd.DataFrame(rows)
 if f.empty or f.duplicated(['timestamp','station_id']).any():raise ValueError('missing/duplicate ASOS rows')
 return f

def collect_smp(client,start,end):
 frames=[]
 for year in range(start.year,end.year+1):
  a=max(start,pd.Timestamp(f'{year}-01-01'));b=min(end,pd.Timestamp(f'{year}-12-31'))
  payload,m=client.fetch('smp_history','https://epsis.kpx.or.kr/epsisnew/selectEkmaSmpShd.ajax',dict(beginDate=a.strftime('%Y%m%d'),endDate=b.strftime('%Y%m%d'),selYear='',selMonth='',selKind='land',locale=''),post=True)
  f=parse_smp(payload);f['first_received_at']=m['first_received_at'];frames.append(f);print('SMP',year,len(f),flush=True)
 all=pd.concat(frames).sort_values('timestamp');csv_write(all,'smp_hourly.csv');return len(all)
def month_ranges(start,end):
 for s in pd.date_range(start.replace(day=1),end,freq='MS'):
  yield max(s,start),min(s+pd.offsets.MonthEnd(0),end)
def collect_power(client,start,end):
 errors=[]
 def one(day):
  p=dict(beginDate=day.strftime('%Y%m%d'),endDate=day.strftime('%Y%m%d'),editYn='N')
  try:
   payload,m=client.fetch('power_5m','https://epsis.kpx.or.kr/epsisnew/selectEkgeEpsMepRealGridAjax.ajax',p,post=True)
   f=parse_power(payload);f=f[f.timestamp.dt.date==day.date()];f['first_received_at']=m['first_received_at']
   if day.day==1:print('POWER checkpoint',day.strftime('%Y-%m'),flush=True)
   return f
  except Exception as e:
   errors.append(dict(date=str(day.date()),error=str(e) if isinstance(e,(FetchError,ValueError)) else type(e).__name__));return pd.DataFrame()
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:frames=list(pool.map(one,pd.date_range(start,end,freq='D')))
 frames=[f for f in frames if not f.empty]
 if not frames:raise ValueError('no power history retrieved')
 f=pd.concat(frames).sort_values('timestamp')
 if f.timestamp.duplicated().any():raise ValueError('duplicate power hour')
 csv_write(f,'power_hourly.csv');write_json(ROOT/'reports/power_collection_failures.json',errors);return len(f)
def collect_weather(client,start,end,stations=(108,133,143,156,159,105)):
 def one(pair):
  a,b=pair;payload,m=client.fetch('weather_asos','https://apihub.kma.go.kr/api/typ01/url/kma_sfctm3.php',dict(tm1=a.strftime('%Y%m%d')+'0000',tm2=b.strftime('%Y%m%d')+'2300',stn=':'.join(map(str,stations)),help=0),key_name='KMA_APIHUB_AUTH_KEY')
  f=parse_weather(payload,stations);f['first_received_at']=m['first_received_at'];print('ASOS',a.strftime('%Y-%m'),len(f),flush=True);return f
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:frames=list(pool.map(one,month_ranges(start,end)))
 f=pd.concat(frames).sort_values(['timestamp','station_id'])
 if f.duplicated(['timestamp','station_id']).any():raise ValueError('duplicate station hour')
 csv_write(f,'weather_stations.csv');agg=f.groupby('timestamp')[['temperature_c','wind_ms','solar_radiation_mj_m2']].mean();agg['station_count']=f.groupby('timestamp').station_id.nunique();csv_write(agg.reset_index(),'weather_hourly.csv');return len(f)
def collect_fuel(client,start,end):
 payload,m=client.fetch('fuel_lng','https://epsis.kpx.or.kr/epsisnew/selectEkmaFucUpf.ajax',dict(beginDate=start.strftime('%Y%m'),endDate=end.strftime('%Y%m'),selYear='N'),post=True);text=payload.decode();rows=[]
 for block,period in re.findall(r'(c1\s*=.*?)gridData.push\(\{"Period":"(\d{4}/\d{2})"',text,re.S):
  values=dict(re.findall(r'(c\d+)\s*=\s*textFormmat\("([^"]*)",count\)',block))
  rows.append(dict(month=period.replace('/','-'),lng_fuel_cost_krw_kwh=float(values['c15']),publicly_released_at=None,release_evidence=None,first_received_at=m['first_received_at'],release_status='historical_publication_date_unknown',source=m['source']))
 f=pd.DataFrame(rows).sort_values('month');csv_write(f,'fuel_monthly.csv');return len(f)
def get_csv(client,dataset,uid):
 payload,_=client.fetch('portal_download_metadata','https://www.data.go.kr/tcs/dss/selectFileDataDownload.do',dict(publicDataDetailPk=uid,publicDataPk=dataset,atchFileId='',fileDetailSn='1',publicDataTyCode='PR0051'),post=True);o=json.loads(payload)
 if not o.get('status'):raise FetchError('portal file download not available')
 payload,m=client.fetch('renewable_files','https://www.data.go.kr/cmm/cmm/fileDownload.do',dict(atchFileId=o['atchFileId'],fileDetailSn=o['fileDetailSn'],insertDataPrcus='N'))
 for enc in ('utf-8-sig','cp949'):
  try:return pd.read_csv(BytesIO(payload),encoding=enc),m
  except UnicodeDecodeError:pass
 raise ValueError('unrecognized CSV encoding')
def collect_renewable(client,start,end):
 dataset='15065269';page,_=client.fetch('renewable_catalog','https://www.data.go.kr/data/15065269/fileData.do');text=page.decode('utf-8');uid=re.search(r"fn_fileDataDown\('15065269',\s*'([^']+)'",text).group(1)
 hist,_=client.fetch('renewable_catalog_history','https://www.data.go.kr/tcs/dss/selectHistAndCsvData.do',dict(publicDataPk=dataset,publicDataDetailPk=uid),post=True)
 h=hist.decode('utf-8');ids=[uid]+re.findall(r'data-public-pk="([^"]+)"',h);ids=list(dict.fromkeys(ids));frames=[];catalog=[]
 # History contains descriptions/dates. Preserve source CSVs even when parsing fails.
 for i,u in enumerate(ids[:10]):
  raw,m=get_csv(client,dataset,u);catalog.append(dict(id=u,columns=list(raw.columns),rows=len(raw)))
  print('RENEWABLE CSV',u,len(raw),list(raw.columns),flush=True)
  csv_write(raw,'renewable_source_'+str(i)+'.csv')
  # Known public schema: 거래일자/지역/발전원/거래시간/발전량. Detect exact column roles, fail visibly otherwise.
  datecol=next((c for c in raw if any(k in c for k in ['거래일','일자','날짜'])),None);hourcol=next((c for c in raw if any(k in c for k in ['거래시간','시간'])),None);region=next((c for c in raw if any(k in c for k in ['지역','시도'])),None);kind=next((c for c in raw if any(k in c for k in ['발전원','연료','구분'])),None);value=next((c for c in raw if '전력거래량' in c or '발전량' in c),None)
  if not all([datecol,hourcol,region]):continue
  r=raw.copy();r['timestamp']=pd.to_datetime(r[datecol].astype(str).str.replace('-',''),errors='coerce')+pd.to_timedelta(pd.to_numeric(r[hourcol],errors='coerce')-1,unit='h');r=r[r['timestamp'].between(start,end+pd.Timedelta(hours=23)) & ~r[region].astype(str).str.contains('제주')]
  if r.empty:continue
  if kind and value:
   r[value]=pd.to_numeric(r[value],errors='coerce');r['kind']=r[kind].astype(str).map(lambda x:'solar_mwh' if '태양' in x else 'wind_mwh' if '풍력' in x else None);r=r[r.kind.notna()];g=r.groupby(['timestamp','kind'])[value].sum(min_count=1).unstack('kind').reset_index()
  else:
   sol=next((c for c in r if '태양' in c),None);wind=next((c for c in r if '풍력' in c),None)
   if not sol or not wind:continue
   r=r.rename(columns={sol:'solar_mwh',wind:'wind_mwh'});r[['solar_mwh','wind_mwh']]=r[['solar_mwh','wind_mwh']].apply(pd.to_numeric,errors='coerce');g=r.groupby('timestamp')[['solar_mwh','wind_mwh']].sum(min_count=1).reset_index()
  g.timestamp=g.timestamp.dt.tz_localize('Asia/Seoul');g['first_received_at']=m['first_received_at'];frames.append(g)
 write_json(ROOT/'reports/renewable_file_inventory.json',catalog)
 if not frames:raise ValueError('renewable files received, schema requires explicit parser')
 f=pd.concat(frames).sort_values('timestamp').drop_duplicates('timestamp',keep='first');csv_write(f,'renewable_hourly.csv');return len(f)
def collect_holidays(client,start,end):
 rows=[];statuses=[]
 import holidays
 for year in range(start.year,end.year+2):
  try:
   p,m=client.fetch('holidays','https://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo',dict(solYear=year,numOfRows=100,pageNo=1,_type='json'),key_name='KPX_SERVICE_KEY');items,_=items_from(p)
   for r in items:
    if r.get('isHoliday')=='Y':rows.append(dict(date=pd.to_datetime(str(r['locdate']),format='%Y%m%d').strftime('%Y-%m-%d'),name=r['dateName'],source='KASI_API',official_api_verified=True))
   statuses.append(dict(year=year,source='KASI_API'))
  except FetchError as e:
   # Not silently certify alternative calendar as an authenticated API response.
   for date,name in holidays.KR(years=year,language='ko').items():rows.append(dict(date=str(date),name=name,source='python-holidays KR fallback',official_api_verified=False))
   statuses.append(dict(year=year,source='python-holidays fallback',api_failure=str(e)))
 f=pd.DataFrame(rows).sort_values('date');csv_write(f,'holidays.csv');write_json(ROOT/'reports/holiday_sources.json',statuses);return len(f)
def run(start='2023-01-01',end='2026-11-13',keys=None,only=None):
 client=Client(keys);a=pd.Timestamp(start);b=pd.Timestamp(end);status=[]
 previous=ROOT/'reports/collection_status.json'
 if previous.exists():status=json.loads(previous.read_text()).get('datasets',[])
 actions={'smp':collect_smp,'power':collect_power,'weather':collect_weather,'fuel':collect_fuel,'renewable':collect_renewable,'holidays':collect_holidays}
 for name,action in actions.items():
  if only and name not in only:continue
  try:rows=action(client,a,b);s=dict(dataset=name,status='collected',rows=rows)
  except Exception as e:s=dict(dataset=name,status='failed',reason=str(e) if isinstance(e,(FetchError,ValueError)) else type(e).__name__)
  print(json.dumps(s,ensure_ascii=False),flush=True);status=[old for old in status if old.get('dataset')!=name]+[s];write_json(ROOT/'reports/collection_status.json',dict(at=now(),start=start,end=end,datasets=status))
 return status
