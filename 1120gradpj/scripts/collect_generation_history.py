"""Resumable daily 2023–2025 generation collection. Stop network requests on quota exhaustion."""
from pathlib import Path
import argparse
import concurrent.futures
import hashlib
import json
import sys
import threading
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from smp_forecast.http import Client,FetchError,items_from,write_json,now
URL='https://apis.data.go.kr/B552115/PvAmountByPwrGen/getPvAmountByPwrGen'
OUT=ROOT/'data/processed/section_b/generation_history'
REPORT=ROOT/'reports/generation_history_2023_2025.json'
STOP=threading.Event()
FUELS=['LNG','무연탄','수력','신재생·기타','양수','원자력','유연탄','유전']


def validate(rows,date):
    frame=pd.DataFrame(rows)
    if frame.empty:return frame
    required=['tradeYmd','tradeNo','fuelTpCd','amgo']
    if not set(required).issubset(frame):raise ValueError('Required field absent')
    if not frame.tradeYmd.astype(str).eq(date).all():raise ValueError('Returned date differs from requested date')
    hours=pd.to_numeric(frame.tradeNo,errors='raise')
    if not (hours.between(1,24)&hours.eq(hours.astype(int))).all():raise ValueError('Unexpected tradeNo')
    frame['amgo']=pd.to_numeric(frame.amgo,errors='raise')
    if not np.isfinite(frame.amgo).all():raise ValueError('NaN/inf amgo')
    if frame.duplicated(['tradeYmd','tradeNo','fuelTpCd']).any():raise ValueError('Duplicate day/hour/fuel key')
    frame['timestamp']=pd.to_datetime(frame.tradeYmd.astype(str),format='%Y%m%d').dt.tz_localize('Asia/Seoul')+pd.to_timedelta(hours-1,unit='h')
    return frame


def required_complete(frame):
    return all(frame.loc[frame.fuelTpCd.eq(fuel),'tradeNo'].astype(int).nunique()==24 for fuel in ['LNG','원자력','유연탄','무연탄'])


def fetch(date):
    # Validated daily checkpoints are immutable unless explicitly refreshed in a separate run.
    output=OUT/'daily'/f'{date}.csv'
    if output.exists():
        try:
            frame=validate(pd.read_csv(output,dtype={'tradeYmd':str,'tradeNo':str}).to_dict('records'),date)
            if len(frame):return dict(date=date,status='cached' if required_complete(frame) else 'partial_cached',rows=len(frame))
        except (ValueError,KeyError):pass
    if STOP.is_set():return dict(date=date,status='not_attempted_quota')
    try:
        client=Client();all_rows=[];receipts=[];page=1
        while True:
            if STOP.is_set():return dict(date=date,status='not_attempted_quota')
            payload,receipt=client.fetch('section_b_generation',URL,dict(tradeYmd=date,numOfRows=1000,pageNo=page,dataType='json'),'KPX_SERVICE_KEY')
            # Some gateways return quota errors in an HTTP 200 XML body.
            if b'LIMITED_NUMBER_OF_SERVICE_REQUESTS' in payload or b'<returnReasonCode>22</returnReasonCode>' in payload:
                STOP.set();return dict(date=date,status='quota',reason='daily request limit, gateway reason 22')
            rows,total=items_from(payload);all_rows.extend(rows);receipts.append(receipt)
            if len(all_rows)>=total:break
            if not rows:raise ValueError('Incomplete pagination')
            page+=1
        frame=validate(all_rows,date)
        if frame.empty:return dict(date=date,status='normal_empty',rows=0)
        frame.to_csv(output,index=False)
        write_json(OUT/'receipts'/f'{date}.json',dict(date=date,receipts=receipts))
        return dict(date=date,status='received' if required_complete(frame) else 'partial_received',rows=len(frame),fuels=sorted(frame.fuelTpCd.unique()))
    except FetchError as exc:
        if '429' in str(exc) or 'resultCode=22' in str(exc):STOP.set();return dict(date=date,status='quota',reason=str(exc))
        return dict(date=date,status='failed',reason=str(exc))
    except (ValueError,KeyError,TypeError) as exc:
        return dict(date=date,status='invalid',reason=str(exc))


def summarize(results):
    expected=pd.date_range('2023-01-01','2025-12-31 23:00',freq='h',tz='Asia/Seoul')
    frames=[pd.read_csv(path,dtype={'tradeYmd':str,'tradeNo':str}) for path in sorted((OUT/'daily').glob('*.csv'))]
    if frames:
        data=pd.concat(frames,ignore_index=True);data['timestamp']=pd.to_datetime(data.timestamp,utc=True).dt.tz_convert('Asia/Seoul')
        data.to_csv(OUT/'generation_all_fuels_2023_2025.csv',index=False)
        if data.duplicated(['timestamp','fuelTpCd']).any():raise ValueError('Duplicate combined generation keys')
        wide=data.pivot(index='timestamp',columns='fuelTpCd',values='amgo').reindex(index=expected,columns=FUELS)
    else:wide=pd.DataFrame(index=expected,columns=FUELS,dtype=float)
    wide.to_csv(OUT/'generation_wide_2023_2025.csv',index_label='timestamp')
    selected=pd.DataFrame({'lng_amgo':wide.LNG,'bituminous_coal_amgo':wide['유연탄'],
                          'anthracite_coal_amgo':wide['무연탄'],'coal_amgo':wide[['유연탄','무연탄']].sum(axis=1,min_count=2),
                          'nuclear_amgo':wide['원자력']})
    selected.to_csv(OUT/'generation_model_candidates_2023_2025.csv',index_label='timestamp')
    missing=wide.isna().stack();missing=missing[missing].reset_index();missing.columns=['timestamp','fuelTpCd','missing']
    missing.to_csv(OUT/'missing_hour_fuel_keys.csv',index=False)
    counts={fuel:dict(valid_hours=int(wide[fuel].notna().sum()),missing_hours=int(wide[fuel].isna().sum())) for fuel in FUELS}
    complete=not wide.isna().any().any()
    summary=dict(at=now(),source=URL,source_page='https://www.data.go.kr/data/15106744/openapi.do',
        expected_days=1096,expected_hours=26304,expected_fuel_hour_rows=210432,
        collected_days=len(frames),row_coverage_complete=complete,ready_for_model=False,
        status='COLLECTED_UNIT_SCOPE_PENDING' if complete else 'INCOMPLETE',
        counts=counts,quota_reached=STOP.is_set(),results=results,
        unit='unconfirmed: raw amgo preserved; no MW/MWh conversion',
        scope='전력거래 정산데이터; 육지/제주 및 시장 포함 범위의 명확한 근거 추가 확인 필요',
        coal_mapping='유연탄+무연탄, both values required; provisional until unit/scope confirmed',
        time_mapping='tradeYmd + (tradeNo-1) hours, tradeNo 1..24; source interval numbering retained',
        model_training_performed=False,credentials_saved=False,
        source_revisions='정산자료는 수정정산으로 바뀔 수 있음; 조회 시점 원본/해시 보존')
    write_json(REPORT,summary)
    return summary


def main():
    (OUT/'daily').mkdir(parents=True,exist_ok=True);(OUT/'receipts').mkdir(exist_ok=True)
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--start',default='2024-01-01');parser.add_argument('--end',default='2024-12-31');parser.add_argument('--plan-only',action='store_true');args=parser.parse_args()
    if args.start<'2023-01-01' or args.end>'2025-12-31' or args.start>args.end:raise ValueError('Use a range inside 2023–2025')
    dates=pd.date_range(args.start,args.end,freq='D').strftime('%Y%m%d').tolist();results=[]
    # Import existing raw receipts before planning; this consumes no network/API allowance.
    for marker in (ROOT/'data/raw/section_b_generation').glob('*.json'):
        record=json.loads(marker.read_text());date=str(record.get('params',{}).get('tradeYmd',''))
        if date not in dates or record.get('params',{}).get('pageNo')!=1:continue
        output=OUT/'daily'/f'{date}.csv'
        if output.exists():continue
        try:
            rows,total=items_from((marker.parent/record['raw']).read_bytes())
            if len(rows)!=total:continue
            frame=validate(rows,date)
            if len(frame)!=192 or set(frame.fuelTpCd)!=set(FUELS):continue
            frame.to_csv(output,index=False)
            write_json(OUT/'receipts'/f'{date}.json',dict(date=date,receipts=[record],imported_existing_cache=True))
        except (RuntimeError,ValueError,KeyError):continue
    complete=[];partial=[]
    for date in dates:
        checkpoint=OUT/'daily'/f'{date}.csv'
        if not checkpoint.exists():continue
        frame=pd.read_csv(checkpoint,dtype={'tradeYmd':str,'tradeNo':str})
        (complete if required_complete(frame) else partial).append(date)
    missing=[date for date in dates if date not in complete]
    pd.DataFrame({'tradeYmd':missing}).to_csv(OUT/'pending_dates.csv',index=False)
    write_json(OUT/'collection_plan.json',dict(start=args.start,end=args.end,total_days=len(dates),
        cached_days=len(complete),partial_days=len(partial),not_received_days=len(missing)-len(partial),pending_days=len(missing),estimated_minimum_requests=len(missing)-len(partial),
        no_new_api_calls=args.plan_only,reset_timestamp_verified=False))
    if args.plan_only:
        print(f'PLAN: {len(dates)} days, {len(complete)} required-complete, {len(partial)} partial, {len(missing)} need completion; no network calls')
        return
    # Only four requests may be in flight. Do not enqueue the whole range after a quota signal.
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for index in range(0,len(dates),4):
            results.extend(pool.map(fetch,dates[index:index+4]))
            if len(results)%40==0 or STOP.is_set():
                received=sum(row['status'] in ['received','cached'] for row in results)
                print(f'Checked {len(results)}/{len(dates)} days; saved {received}; quota={STOP.is_set()}',flush=True)
            if STOP.is_set():
                results.extend(dict(date=date,status='not_attempted_quota') for date in dates[index+4:]);break
    report=summarize(results)
    lines=['# 발전원별 발전량 2023~2025 전체 수집','','상태: '+report['status'],'',
           '수집 일수: '+str(report['collected_days'])+'/1096. 학습 실행 없음.','',
           '| 발전원 | 유효 시간 | 결측 시간 |','|---|---:|---:|']
    lines+=['| '+fuel+' | '+str(row['valid_hours'])+' | '+str(row['missing_hours'])+' |' for fuel,row in report['counts'].items()]
    lines+=['','API 원문 필드 amgo의 값과 원자료를 보존했습니다. 단위·지역의 공식 근거가 확정되기 전에는 모델 READY로 표시하지 않습니다.',
            '석탄 후보는 유연탄+무연탄이며 한쪽 결측이면 합계도 결측입니다. 빈값을 0으로 채우지 않았습니다.',
            '호출 한도에 도달하면 네트워크 수집을 중단합니다. 재실행 시 일별 체크포인트를 재사용합니다.',
            '공식 출처: https://www.data.go.kr/data/15106744/openapi.do',
            '데이터: data/processed/section_b/generation_history/']
    (ROOT/'reports/GENERATION_HISTORY_2023_2025.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:report[k] for k in ['status','collected_days','row_coverage_complete','quota_reached','counts']},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
