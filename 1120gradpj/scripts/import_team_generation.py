"""Import a pinned, already-downloaded teammate CSV without overwriting conflicting source versions."""
from pathlib import Path
import json
import sys
import hashlib
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from smp_forecast.http import write_json,now
from collect_generation_history import validate,required_complete
BLOB='42b48265194b5afa24a932345f77e876a279999c'
NAME='api_generation_partial_2023_2025_merged_20261119.csv'
SOURCE=ROOT/'data/raw/team_generation'/BLOB/NAME
OUT=ROOT/'data/processed/section_b/generation_team_import_20261119'
DAILY=ROOT/'data/processed/section_b/generation_history/daily'


def main():
    payload=SOURCE.read_bytes()
    if hashlib.sha1(b'blob '+str(len(payload)).encode()+b'\0'+payload).hexdigest()!=BLOB:raise ValueError('Pinned file hash mismatch')
    frame=pd.read_csv(SOURCE,dtype={'tradeYmd':str,'tradeNo':str})
    key=['tradeYmd','tradeNo','fuelTpCd']
    if frame.duplicated(key).any():raise ValueError('Duplicate teammate fuel-hour keys')
    if not np.isfinite(pd.to_numeric(frame.amgo,errors='raise')).all():raise ValueError('Nonfinite teammate generation')
    pieces=[]
    for date,rows in frame.groupby('tradeYmd'):
        parsed=validate(rows.to_dict('records'),str(date))
        original_time=pd.to_datetime(rows.timestamp,utc=True).dt.tz_convert('Asia/Seoul').reset_index(drop=True)
        if not original_time.equals(parsed.timestamp.reset_index(drop=True)):raise ValueError('Source timestamp differs from day/hour')
        pieces.append(parsed)
    normalized=pd.concat(pieces,ignore_index=True)
    local=pd.concat([pd.read_csv(path,dtype={'tradeYmd':str,'tradeNo':str}) for path in DAILY.glob('*.csv')],ignore_index=True)
    local.tradeNo=local.tradeNo.astype(int);normalized.tradeNo=normalized.tradeNo.astype(int)
    overlap=normalized.merge(local[key+['amgo']],on=key,validate='one_to_one',suffixes=('_team','_local'))
    differences=(overlap.amgo_team-overlap.amgo_local).abs()
    OUT.mkdir(parents=True,exist_ok=True)
    conflicts=overlap[differences>1e-9]
    conflicts.to_csv(OUT/'conflicting_values.csv',index=False)
    if len(conflicts):raise ValueError('Conflicting values retained separately; integration stopped')
    imported=[];retained=[]
    for date,rows in normalized.groupby('tradeYmd'):
        dest=DAILY/f'{date}.csv'
        if dest.exists():retained.append(str(date));continue
        rows.to_csv(dest,index=False);imported.append(str(date))
        write_json(DAILY.parent/'receipts'/f'{date}.json',dict(date=str(date),source='teammate GitHub CSV',
            git_blob_sha=BLOB,source_sha256=hashlib.sha256(payload).hexdigest(),source_file=NAME,network_api_calls=0))
    records=[];missing=[]
    for year in [2023,2024,2025]:
        data=normalized[normalized.tradeYmd.str.startswith(str(year))]
        expected=pd.date_range(f'{year}-01-01',f'{year}-12-31 23:00',freq='h',tz='Asia/Seoul')
        wide=data.pivot(index='timestamp',columns='fuelTpCd',values='amgo').reindex(index=expected,columns=['LNG','유연탄','무연탄','원자력'])
        wide['coal_amgo']=wide[['유연탄','무연탄']].sum(axis=1,min_count=2)
        wide.to_csv(OUT/f'team_generation_{year}_wide.csv',index_label='timestamp')
        detail={fuel:dict(valid_hours=int(wide[fuel].notna().sum()),missing_hours=int(wide[fuel].isna().sum())) for fuel in wide}
        records.append(dict(year=year,expected_hours=len(expected),received_days=data.tradeYmd.nunique(),coverage=detail))
        for fuel in ['LNG','유연탄','무연탄','원자력']:
            missing.extend(dict(timestamp=timestamp,fuel=fuel) for timestamp in wide.index[wide[fuel].isna()])
    pd.DataFrame(missing).to_csv(OUT/'missing_required_fuel_hours.csv',index=False)
    report=dict(at=now(),source_url='https://github.com/parksiwon22/gradproject/blob/codex/smp-72h-data/SMP_72H_INPUT_DATA/05_generation_by_fuel_amgo/'+NAME,
        git_blob_sha=BLOB,sha256=hashlib.sha256(payload).hexdigest(),source_rows=len(frame),duplicate_keys=0,
        overlap_rows=len(overlap),max_overlap_difference=float(differences.max()),conflicting_rows=0,
        imported_new_days=imported,retained_existing_days=len(retained),years=records,
        unit='raw API amgo; independent unit evidence pending',region='source has no mainland/Jeju region field',
        status='IMPORTED_2024_STILL_INCOMPLETE',model_training_performed=False,network_api_calls=0)
    write_json(ROOT/'reports/team_generation_import_20261119.json',report)
    lines=['# 团队 발전량 CSV 가져오기','','실제 파일 다운로드·해시 검증·로컬 반영 완료. **2024년 필수 발전원 완비는 아님.**','',
        f'원본 {len(frame):,}행, Git blob {BLOB}. 중복 키 0개. 기존 {len(overlap):,}행 대조, 최대차 {float(differences.max())}. 새 날짜 {len(imported)}개를 추가하고 기존 원본은 보존했습니다.','',
        '| 연도 | API 응답 날짜 | LNG 유효시간 | 원자력 유효시간 | 유연탄 유효시간 | 무연탄 유효시간 |','|---|---:|---:|---:|---:|---:|']
    for r in records:
        c=r['coverage'];lines.append(f"| {r['year']} | {r['received_days']} | {c['LNG']['valid_hours']} | {c['원자력']['valid_hours']} | {c['유연탄']['valid_hours']} | {c['무연탄']['valid_hours']} |")
    lines+=['','2024년 필요 시간은 8,784시간입니다. 2월 29일 24시간이 전 발전원에서 없고, 8월 1~31일 원자력·무연탄 744시간이 추가로 없습니다. API 호출을 모두 시도한 것과 필요한 값이 모두 제공된 것은 구분합니다. 누락을 0으로 채우지 않았습니다.','',
        '2023년 API 파일은 96일, 2025년은 1일만 포함합니다. 별도 확보한 2023/2025년 연간 CSV와 구분하며 서로 다른 버전을 임의로 합치지 않습니다.','',
        '원본: data/raw/team_generation/'+BLOB+'/'+NAME,
        '정규화·결측 목록: data/processed/section_b/generation_team_import_20261119/',
        '일별 가져오기: data/processed/section_b/generation_history/daily/','',
        '외부 발전량 API 호출이나 모델 학습은 실행하지 않았습니다.']
    (ROOT/'reports/TEAM_GENERATION_IMPORT_20261119.md').write_text('\n'.join(lines).replace('团队','팀원')+'\n')
    print(json.dumps({key:report[key] for key in ['source_rows','overlap_rows','max_overlap_difference','conflicting_rows','status']},ensure_ascii=False));print('New days imported',len(imported))

if __name__=='__main__':main()
