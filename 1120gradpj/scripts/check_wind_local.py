"""Read-only audit of the local source wind rows and mainland aggregation; no API calls."""
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from smp_forecast.http import write_json,now


def main():
    records=[];direct=[]
    for number in range(7):
        path=ROOT/f'data/processed/renewable_source_{number}.csv'
        raw=pd.read_csv(path);raw.columns=raw.columns.str.strip()
        datecol=next(c for c in raw if '거래일' in c)
        region=next(c for c in raw if '지역' in c)
        raw['date']=pd.to_datetime(raw[datecol],errors='raise')
        raw=raw[raw.date.dt.year.between(2023,2025)].copy()
        if '연료원' in raw:
            raw=raw[raw['연료원'].eq('풍력')].copy();value=next(c for c in raw if '량(' in c)
        else:value=next(c for c in raw if '풍력' in c)
        raw['wind_value']=pd.to_numeric(raw[value],errors='coerce')
        raw['timestamp']=raw.date.dt.tz_localize('Asia/Seoul')+pd.to_timedelta(pd.to_numeric(raw['거래시간'])-1,unit='h')
        groups=[]
        for name,group in raw.groupby(region):
            valid=group.wind_value.dropna()
            groups.append(dict(region=name,rows=len(group),numeric_values=len(valid),blank_values=int(group.wind_value.isna().sum()),
                               nonzero_values=int((valid!=0).sum()),minimum=float(valid.min()) if len(valid) else None,maximum=float(valid.max()) if len(valid) else None))
        land=raw[raw[region].eq('육지')]
        if len(land):direct.append(land[['timestamp','wind_value']])
        records.append(dict(file=str(path.relative_to(ROOT)),start=raw.date.min().strftime('%Y-%m-%d'),end=raw.date.max().strftime('%Y-%m-%d'),
                            source_value_column=value,regions=groups,explicit_mainland_rows=len(land),sample=land[['timestamp','wind_value']].head(2).astype(str).to_dict('records')))
    explicit=pd.concat(direct,ignore_index=True)
    hourly=pd.read_csv(ROOT/'data/processed/renewable_hourly.csv');hourly['timestamp']=pd.to_datetime(hourly.timestamp,utc=True).dt.tz_convert('Asia/Seoul')
    comparison=explicit.merge(hourly[['timestamp','wind_mwh']],on='timestamp',validate='one_to_one')
    assert np.allclose(comparison.wind_value,comparison.wind_mwh,rtol=0,atol=1e-9)
    report=dict(at=now(),source_page='https://www.data.go.kr/data/15065269/fileData.do',
                conclusion='풍력 육지 원본 존재. 2023-12 이후 육지/제주 구분; 그 이전은 시도별 제주 제외 집계.',
                unit='MWh',explicit_mainland_compared_hours=len(comparison),max_difference=float(abs(comparison.wind_value-comparison.wind_mwh).max()),
                records=records,model_training_performed=False,network_api_calls=0,
                limitation='2023년 일부 시도별 빈칸은 구조적 비해당/관측 누락 구분 필요. 합계 값 존재를 지역 전체 품질 완비로 해석하지 않음.')
    write_json(ROOT/'reports/wind_local_verification.json',report)
    lines=['# 6번 풍력 로컬 수집본 확인','','결론: **제주만 있는 자료가 아닙니다. 육지 풍력 원본이 있습니다.**','',
        '| 기간 | 원본 형식 | 로컬 파일 |','|---|---|---|',
        '| 2023-01~11 | 시도별 풍력 열, 제주 제외 합계 | renewable_source_3~6.csv |',
        '| 2023-12 | 연료원=풍력, 지역=육지/제주 | renewable_source_2.csv |',
        '| 2024 전체 | 연료원=풍력, 지역=육지/제주 | renewable_source_1.csv |',
        '| 2025 전체 | 연료원=풍력, 지역=육지/제주도 | renewable_source_0.csv |','',
        '위 파일들은 `1120gradpj/data/processed/`에 있습니다. 최종 집계본은 같은 경로의 `renewable_hourly.csv`이며 풍력 열 이름은 `wind_mwh`입니다. 단위는 MWh입니다.','',
        f'2023-12~2025-12 육지 원본 {len(comparison):,}시간과 기존 집계본을 전부 대조: 최대 차이 {report["max_difference"]}.','',
        '2023~2025 시간별 풍력 합계 26,304개는 존재합니다. 다만 2023-01~11 일부 시도 원본 빈칸은 별도 품질 확인 대상이며, 모든 지역 무결측을 확인한 것은 아닙니다.','',
        '공식 상세 설명은 2023년 12월 이후 풍력을 육지/제주로 제공한다고 명시합니다. 일부 지역의 발전기 수가 적어 사업자 영업정보 보호를 위해 지역 구분을 묶었습니다. 태양광은 시도별이므로 태양광의 시도명으로 풍력을 필터링하면 육지 행을 놓칠 수 있습니다.','',
        '확인 예: 2024/2025 파일에서 `연료원 == 풍력`과 `지역 == 육지`를 함께 선택합니다. 제주/제주도 표기는 모두 제주로 분류합니다. 기존 코드는 제주가 포함된 지역명을 제외하고 집계했습니다.','',
        report['limitation'],'',
        '이는 전력시장 참여 발전기 전력거래량이며 PPA·자가용·BTM을 포함한 전체 풍력 발전량이라고 표시하지 않습니다.','',
        '공식 출처: https://www.data.go.kr/data/15065269/fileData.do','',
        '이번 작업은 로컬 원본·집계 확인입니다. 새 API 호출·모델 학습은 실행하지 않았습니다.']
    (ROOT/'reports/WIND_LOCAL_VERIFICATION.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(dict(explicit_mainland_compared_hours=len(comparison),max_difference=report['max_difference'],samples=records[0]['sample']),ensure_ascii=False))

if __name__=='__main__':main()
