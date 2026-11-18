"""Verified TLS, secret-free receipts and immutable source bodies. No request URL logging."""
import os,json,hashlib,ssl,time,urllib.request,urllib.parse,urllib.error
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import certifi
ROOT=Path(__file__).resolve().parents[2]
KST=ZoneInfo('Asia/Seoul')
def now():return datetime.now(KST).isoformat()
def write_json(path,obj):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8');tmp.replace(path)
class FetchError(RuntimeError):pass
class Client:
 def __init__(self,keys=None):
  self.keys={k:v for k,v in (keys or {}).items() if v};self.context=ssl.create_default_context(cafile=certifi.where())
 def fetch(self,name,url,params=None,key_name=None,post=False,refresh=False):
  params=dict(params or {});safe={k:v for k,v in params.items() if k.lower() not in ('servicekey','authkey','api_key','apikey')}
  identity=hashlib.sha256(json.dumps([url,safe],sort_keys=True).encode()).hexdigest()[:16];folder=ROOT/'data/raw'/name;folder.mkdir(parents=True,exist_ok=True);marker=folder/(identity+'.json')
  if marker.exists() and not refresh:
   m=json.loads(marker.read_text());payload=(folder/m['raw']).read_bytes()
   if hashlib.sha256(payload).hexdigest()!=m['sha256']:raise FetchError(name+': cache hash mismatch')
   return payload,m
  if key_name:
   credential=self.keys.get(key_name) or os.environ.get(key_name)
   if not credential:raise FetchError(name+': missing '+key_name)
   auth_param='authKey' if key_name=='KMA_APIHUB_AUTH_KEY' else 'api_key' if key_name=='FRED_API_KEY' else 'serviceKey'
   params[auth_param]=urllib.parse.unquote(credential)
  q=urllib.parse.urlencode(params);req=urllib.request.Request(url if post else url+('?' if '?' not in url else '&')+q,data=q.encode() if post else None,headers={'User-Agent':'1120gradpj educational research','Content-Type':'application/x-www-form-urlencoded'})
  for attempt in range(3):
   try:
    with urllib.request.urlopen(req,context=self.context,timeout=60) as r:payload=r.read();status=r.status
    if any(v.encode() in payload for v in list(self.keys.values())+[os.environ.get(k,'') for k in ('KPX_SERVICE_KEY','KMA_APIHUB_AUTH_KEY','FRED_API_KEY')] if v):raise FetchError(name+': credential echo suppressed')
    digest=hashlib.sha256(payload).hexdigest();raw=digest+'.raw';(folder/raw).write_bytes(payload)
    m=dict(source=url,params=safe,http_status=status,first_received_at=now(),sha256=digest,raw=raw,bytes=len(payload),authenticated=bool(key_name));write_json(marker,m);return payload,m
   except urllib.error.HTTPError as e:
    # Never interpolate exceptions: HTTPError includes authenticated URL.
    if e.code in (401,403,404,429) or attempt==2:raise FetchError(name+': HTTP '+str(e.code)) from None
   except urllib.error.URLError as e:
    if attempt==2:raise FetchError(name+': transport '+type(e.reason).__name__) from None
   if attempt<2:time.sleep(1+attempt)
  raise FetchError(name+': retrieval failed')
def items_from(payload):
 import xml.etree.ElementTree as ET
 text=payload.decode('utf-8-sig')
 try:
  o=json.loads(text);res=o.get('response',o);h=res.get('header',{});code=str(h.get('resultCode','00'))
  if code not in ('00','0'):raise FetchError('service resultCode='+code)
  body=res.get('body',{});items=body.get('items',{});items=items.get('item',[]) if isinstance(items,dict) else items
  if not items:items=[]
  if isinstance(items,dict):items=[items]
  return items,int(body.get('totalCount',len(items)))
 except json.JSONDecodeError:
  try:root=ET.fromstring(text)
  except ET.ParseError:raise FetchError('unexpected non-JSON/XML response') from None
  code=root.findtext('.//resultCode')
  if code not in ('00','0',None):raise FetchError('service resultCode='+str(code))
  if root.find('.//returnAuthMsg') is not None:raise FetchError('service authentication/approval rejected')
  items=[{e.tag:e.text for e in item} for item in root.findall('.//item')];return items,int(root.findtext('.//totalCount') or len(items))
