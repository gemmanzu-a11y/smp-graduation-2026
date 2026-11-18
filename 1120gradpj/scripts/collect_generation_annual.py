"""Collect published annual settlement files and audit the required fuel-hour grid.
Keep annual-file values separate from API values, especially where precision differs.
"""
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from smp_forecast.http import Client,items_from,write_json,now
from smp_forecast.collect import get_csv
OUT=ROOT/'data/processed/section_b/generation_annual'
FILES={2023:('uddi:c3c4a685-8ecd-4854-9781-9724e83a7f9b',2),
       2024:('uddi:54f28932-fcc4-4315-a44c-f480e808a84e',1),
       2025:('uddi:af29850e-c2aa-4341-9b8b-ce6da5252913',0)}
REQUIRED=['LNG','유연탄','무연탄','원자력']


def normalize(source,year):
    frame=source.copy();frame.columns=frame.columns.str.strip()
    fuel=next(c for c in ['연료원별','원료원','연료원'] if c in frame)
    hour=next(c for c in ['거래시간','시간'] if c in frame)
    dates=pd.to_datetime(frame['거래일자'],errors='raise')
    hours=pd.to_numeric(frame[hour],errors='raise')
    if not dates.dt.year.eq(year).all():raise ValueError('Wrong annual source year')
    if not (hours.between(1,24)&hours.eq(hours.astype(int))).all():raise ValueError('Invalid hour')
    result=pd.DataFrame(dict(timestamp=dates.dt.tz_localize('Asia/Seoul')+pd.to_timedelta(hours-1,unit='h'),
        source_date=dates.dt.strftime('%Y-%m-%d'),source_hour=hours.astype(int),fuel=frame[fuel].str.strip(),
        generation_mwh=pd.to_numeric(frame['전력거래량(MWh)'],errors='raise')))
    if not np.isfinite(result.generation_mwh).all():raise ValueError('Nonfinite annual generation')
    if result.duplicated(['timestamp','fuel']).any():raise ValueError('Duplicate annual fuel-hour key')
    return result


def main():
    OUT.mkdir(parents=True,exist_ok=True);client=Client();frames=[];receipts=[]
    for year,(uid,index) in FILES.items():
        source,receipt=get_csv(client,'15127395',uid)
        source.to_csv(OUT/f'source_{index}.csv',index=False)
        frame=normalize(source,year);frames.append(frame)
        receipts.append(dict(year=year,file_id=uid,source_dataset='15127395',rows=len(frame),
            raw_sha256=receipt['sha256'],raw_receipt=receipt,
            fuels=sorted(frame.fuel.unique()),unit='MWh',scope='전력시장 참여 발전기 송전단 전력거래량; 지역 구분 열 없음'))
    data=pd.concat(frames,ignore_index=True)
    data.to_csv(OUT/'all_original_fuels_normalized.csv',index=False)
    index=pd.date_range('2023-01-01','2025-12-31 23:00',freq='h',tz='Asia/Seoul')
    wide=data.pivot(index='timestamp',columns='fuel',values='generation_mwh').reindex(index=index,columns=REQUIRED)
    selected=wide.rename(columns={'LNG':'lng_generation_mwh','유연탄':'bituminous_coal_generation_mwh',
        '무연탄':'anthracite_coal_generation_mwh','원자력':'nuclear_generation_mwh'})
    selected['coal_generation_mwh']=wide[['유연탄','무연탄']].sum(axis=1,min_count=2)
    selected.to_csv(OUT/'generation_selected_2023_2025.csv',index_label='timestamp')
    missing=[]
    for fuel in REQUIRED:
        missing.extend(dict(timestamp=timestamp,fuel=fuel) for timestamp in wide.index[wide[fuel].isna()])
    pd.DataFrame(missing,columns=['timestamp','fuel']).to_csv(OUT/'missing_required_fuel_hours.csv',index=False)
    # Compare every cached API day; never consume more of an exhausted API allowance.
    api=[]
    for path in (ROOT/'data/raw/section_b_generation').glob('*.json'):
        record=json.loads(path.read_text());date=str(record.get('params',{}).get('tradeYmd',''))
        if not '20230101'<=date<='20251231':continue
        try:rows,total=items_from((path.parent/record['raw']).read_bytes())
        except RuntimeError:continue
        if len(rows)!=total:continue
        for row in rows:
            if row['fuelTpCd'] not in REQUIRED:continue
            api.append(dict(timestamp=pd.Timestamp(str(row['tradeYmd']),tz='Asia/Seoul')+pd.Timedelta(hours=int(row['tradeNo'])-1),
                fuel=row['fuelTpCd'],api_amgo=float(row['amgo'])))
    api=pd.DataFrame(api).drop_duplicates(['timestamp','fuel']) if api else pd.DataFrame(columns=['timestamp','fuel','api_amgo'])
    compare=data[data.fuel.isin(REQUIRED)].merge(api,on=['timestamp','fuel'],how='inner',validate='one_to_one')
    compare['difference']=compare.generation_mwh-compare.api_amgo
    compare.to_csv(OUT/'annual_vs_cached_api.csv',index=False)
    by_year=[]
    for year in FILES:
        f=selected[selected.index.year==year]
        by_year.append(dict(year=year,expected_hours=len(f),missing_by_column={c:int(f[c].isna().sum()) for c in f},
                            complete=bool(f.notna().all().all())))
    comparison={}
    for year,group in compare.groupby(compare.timestamp.dt.year):
        comparison[str(year)]=dict(compared_rows=len(group),max_absolute_difference=float(abs(group.difference).max()),
                                  mean_absolute_difference=float(abs(group.difference).mean()))
    report=dict(at=now(),status='INCOMPLETE_2024_REQUIRED_FUELS_ABSENT',row_coverage_complete=bool(selected.notna().all().all()),
        expected_hours=26304,by_year=by_year,receipts=receipts,api_comparison=comparison,
        api_values_merged_into_annual=False,unit='MWh',
        scope='전력시장 정산 기준 송전단 전력거래량. 발전기 입찰량·설비용량·전국 총발전량과 구분. 육지/제주 분리 미확정.',
        blocker='2024년 공식 연간 첨부파일은 신재생 계열만 포함: LNG·유연탄·무연탄·원자력 4개 모두 없음. 일별 API는 오늘 한도 도달.',
        resolution='공식 2024년 전체 연료원 파일 정정/제공 요청 또는 API 일일 트래픽 증설 후 2024년 전체 수집. 키 변경으로 한도 우회하지 않음.',
        precision_note='2023년 공식 파일은 정수 MWh로 표시되어 API 소수값과 차이가 날 수 있음. 서로 다른 정밀도를 시간별로 섞지 않음.',
        model_training_performed=False)
    write_json(ROOT/'reports/generation_annual_collection.json',report)
    lines=['# 5번 발전원별 발전량: 전체 기간 수집 결과','','상태: **2024년 핵심 발전원 미확보로 미완료**','',
           '| 연도 | 필요 시간 | LNG 결측 | 석탄(유연탄+무연탄) 결측 | 원자력 결측 |','|---|---:|---:|---:|---:|']
    for record in by_year:
        missing=record['missing_by_column'];lines.append(f"| {record['year']} | {record['expected_hours']} | {missing['lng_generation_mwh']} | {missing['coal_generation_mwh']} | {missing['nuclear_generation_mwh']} |")
    lines+=['','## 실제로 확인한 원인','',report['blocker'],'',
        '2024년 상세항목 이름은 연료원별 시간대별 설비용량 및 전력거래량이지만 실제 첨부파일명은 `신재생 연료원별 설비용량 및 전력거래량_2024.csv`입니다. 실제 파일 110,544행의 연료원 목록을 검사해 핵심 발전원 부재를 확인했습니다. 이를 값 0으로 처리하지 않았습니다.','',
        '2023년과 2025년 LNG·유연탄·무연탄·원자력은 연간 전체 시간 확보했습니다. 단위는 원본 열의 MWh입니다. 설비용량 MW 열을 발전량으로 사용하지 않았습니다. 원본 세부 연료원은 모두 별도 보존했습니다.','',
        report['precision_note'],'API 대조 수치: `generation_annual_collection.json` 및 `annual_vs_cached_api.csv`.','',
        '## 해결 경로','',report['resolution'],'',
        '- 공식 연간 파일: https://www.data.go.kr/data/15127395/fileData.do',
        '- 일별 API: https://www.data.go.kr/data/15106744/openapi.do',
        '- 공식 문의처: 한국전력거래소 전사AX총괄팀 061-330-8718 (공식 상세 페이지 기준)',
        '- 필요한 자료: 2024-01-01~2024-12-31, 01~24시, LNG·유연탄·무연탄·원자력 전력거래량(MWh), 원본 지역 범위 명시.',
        '- API 재개: KPX_SERVICE_KEY 환경변수 설정 후 `.venv/bin/python scripts/collect_generation_history.py`. 저장된 일자는 재사용합니다.','',
        '## 파일','',
        '- data/processed/section_b/generation_annual/generation_selected_2023_2025.csv: 공통 시간축 후보, 2024년은 NaN 유지',
        '- source_0/1/2.csv: 각각 2025/2024/2023 공식 원본 CSV 파싱본',
        '- all_original_fuels_normalized.csv: 원래 세부 연료원 전체 보존',
        '- missing_required_fuel_hours.csv: 부족한 시간·연료원 목록','',
        '실제 모델 학습은 실행하지 않았습니다. 2024년을 빼거나 복사·보간하여 완비로 표시하지 않았습니다.']
    (ROOT/'reports/GENERATION_COLLECTION_STATUS.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(dict(by_year=by_year,api_comparison=comparison,status=report['status']),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
