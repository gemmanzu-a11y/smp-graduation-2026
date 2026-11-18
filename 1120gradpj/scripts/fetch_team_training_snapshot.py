"""Pin and verify the user-designated shared-input branch; download data only, never run remote code."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import hashlib,json,time
import requests,certifi
ROOT=Path(__file__).resolve().parents[1]
COMMIT='a90141b81ecd841c524eb75a72f4bcc4f39989f5'

def main():
 folder=ROOT/'data/raw/team_training_snapshot'/COMMIT
 folder.mkdir(parents=True,exist_ok=True)
 treefile=folder/'source_tree.json'
 if treefile.exists():tree=json.loads(treefile.read_text())
 else:
  response=requests.get('https://api.github.com/repos/parksiwon22/gradproject/git/trees/'+COMMIT,params={'recursive':'1'},timeout=60,verify=certifi.where())
  response.raise_for_status();tree=response.json()
  if tree.get('truncated'):raise ValueError('Truncated Git tree')
  treefile.write_text(json.dumps(tree,ensure_ascii=False,indent=2)+'\n')
 entries=[row for row in tree['tree'] if row['type']=='blob' and row['path'].startswith('SMP_72H_INPUT_DATA/')]
 if len(entries)!=104:raise ValueError('Pinned snapshot inventory mismatch')
 def one(row):
  path=folder/row['path'];path.parent.mkdir(parents=True,exist_ok=True)
  if path.exists():body=path.read_bytes()
  else:
   for attempt in range(3):
    try:
     response=requests.get('https://raw.githubusercontent.com/parksiwon22/gradproject/'+COMMIT+'/'+row['path'],timeout=60,verify=certifi.where());response.raise_for_status();body=response.content;break
    except requests.RequestException:
     if attempt==2:raise
     time.sleep(1)
  digest=hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()
  if digest!=row['sha']:raise ValueError('Git blob mismatch: '+row['path'])
  path.write_bytes(body)
  return dict(path=row['path'],git_blob_sha=digest,sha256=hashlib.sha256(body).hexdigest(),bytes=len(body))
 records=[]
 with ThreadPoolExecutor(max_workers=4) as pool:
  for future in as_completed([pool.submit(one,row) for row in entries]):
   records.append(future.result())
   if len(records)%20==0:print('Verified downloads',len(records),'/',len(entries),flush=True)
 (folder/'snapshot_manifest.json').write_text(json.dumps(dict(repository='parksiwon22/gradproject',branch='codex/smp-72h-data',commit=COMMIT,files=sorted(records,key=lambda x:x['path'])),ensure_ascii=False,indent=2)+'\n')
 print('SNAPSHOT READY',folder,'files',len(records),flush=True)
if __name__=='__main__':main()
