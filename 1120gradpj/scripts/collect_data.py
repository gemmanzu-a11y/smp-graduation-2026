import sys,argparse,json,os,getpass
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from smp_forecast.collect import run
p=argparse.ArgumentParser();p.add_argument('--start',default='2023-01-01');p.add_argument('--end',default=(datetime.now(ZoneInfo('Asia/Seoul')).date()-timedelta(days=1)).isoformat());p.add_argument('--only',nargs='+');p.add_argument('--keys-stdin',action='store_true');p.add_argument('--prompt-keys',action='store_true');a=p.parse_args();keys=json.loads(sys.stdin.readline()) if a.keys_stdin else {}
if a.prompt_keys:
 for key in ['KPX_SERVICE_KEY','KMA_APIHUB_AUTH_KEY']:
  if not os.environ.get(key):keys[key]=getpass.getpass(key+' (화면·파일에 저장하지 않음): ')
run(a.start,a.end,keys,a.only)
