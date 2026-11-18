"""Read-only validation of annual 2025 generation against the pinned API source.

Writes audit reports only; does not patch the shared dataset or fit any model.
"""
from pathlib import Path
import hashlib,json,sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT.parent
sys.path.insert(0,str(ROOT/'src'))
from smp_forecast import common_v3 as common


def main():
    folder=common.SOURCE/'05_generation_by_fuel_amgo'
    annual=next((folder/'user_provided_annual_csvs').glob('*20251231.csv'))
    api=folder/'api_generation_partial_2023_2025_merged_20261119.csv'
    raw_hash=hashlib.sha256(annual.read_bytes()).hexdigest()
    data=pd.read_csv(annual,encoding='cp949');data.columns=data.columns.str.strip()
    required=['거래일자','거래시간','연료원별','설비용량(MW)','전력거래량(MWh)']
    assert list(data)==required,'Unexpected source schema'
    data['date']=pd.to_datetime(data['거래일자'],format='%Y-%m-%d',errors='raise')
    data['hour']=pd.to_numeric(data['거래시간'],errors='raise')
    assert data.hour.between(1,24).all() and (data.hour%1==0).all()
    data['timestamp']=data.date.dt.tz_localize(common.TZ)+pd.to_timedelta(data.hour-1,unit='h')
    assert data.date.dt.year.eq(2025).all()
    assert not data.duplicated(['timestamp','연료원별']).any()
    fuels=['LNG','유연탄','무연탄','원자력']
    selected=data[data['연료원별'].isin(fuels)].copy()
    selected['value']=pd.to_numeric(selected['전력거래량(MWh)'],errors='raise')
    selected['capacity_mw']=pd.to_numeric(selected['설비용량(MW)'],errors='raise')
    assert np.isfinite(selected[['value','capacity_mw']]).all().all()
    assert selected.value.ge(0).all()
    expected=pd.date_range('2025-01-01','2025-12-31 23:00',freq='h',tz=common.TZ)
    coverage=[]
    for fuel in fuels:
        rows=selected[selected['연료원별']==fuel].sort_values('timestamp')
        assert pd.DatetimeIndex(rows.timestamp).equals(expected),fuel+' missing/extra hour'
        coverage.append(dict(fuel=fuel,expected_hours=len(expected),valid_hours=len(rows),missing_hours=int(rows.value.isna().sum()),duplicates=0,negative_values=int(rows.value.lt(0).sum()),observed_zeros=int(rows.value.eq(0).sum()),minimum_mwh=float(rows.value.min()),maximum_mwh=float(rows.value.max()),annual_energy_gwh=float(rows.value.sum()/1000),capacity_exceedances=int((rows.value>rows.capacity_mw+.001).sum())))
    a=pd.read_csv(api);a=a[a.tradeYmd.astype(str).str.startswith('2025')&a.fuelTpCd.isin(fuels)].copy()
    a['timestamp']=pd.to_datetime(a.tradeYmd.astype(str),format='%Y%m%d').dt.tz_localize(common.TZ)+pd.to_timedelta(pd.to_numeric(a.tradeNo)-1,unit='h')
    a['value_api']=pd.to_numeric(a.amgo)
    pairs=selected.merge(a[['timestamp','fuelTpCd','value_api']],left_on=['timestamp','연료원별'],right_on=['timestamp','fuelTpCd'],validate='one_to_one')
    assert len(pairs)==len(a)==96,'Unexpected overlap coverage'
    pairs['absolute_difference_mwh']=np.abs(pairs.value-pairs.value_api)
    tolerance=.0005001
    assert pairs.absolute_difference_mwh.le(tolerance).all(),'Overlap differs beyond API 0.001 MWh display precision'
    comparison=[]
    for fuel in fuels:
        p=pairs[pairs.fuelTpCd==fuel]
        comparison.append(dict(fuel=fuel,pairs=len(p),mean_absolute_difference_mwh=float(p.absolute_difference_mwh.mean()),max_absolute_difference_mwh=float(p.absolute_difference_mwh.max()),outside_tolerance=int(p.absolute_difference_mwh.gt(tolerance).sum())))
    offsets=[]
    for offset in [-1,0,1]:
        shifted=a.copy();shifted.timestamp=shifted.timestamp+pd.Timedelta(hours=offset)
        p=selected.merge(shifted[['timestamp','fuelTpCd','value_api']],left_on=['timestamp','연료원별'],right_on=['timestamp','fuelTpCd'])
        offsets.append(dict(api_timestamp_offset_hours=offset,pairs=len(p),mae_mwh=float(np.abs(p.value-p.value_api).mean())))
    wide=selected.pivot(index='timestamp',columns='연료원별',values='value').reindex(expected)
    wide['coal']=wide[['유연탄','무연탄']].sum(axis=1,min_count=2)
    # Independently reconcile the existing, already-shared normalized CSV.
    shared=WORK/'shared_datasets/kpx_generation/annual_generation_2025.csv'
    existing=pd.read_csv(shared);existing.index=common.times(existing.timestamp)
    mapping={'LNG':'lng_generation_mwh','유연탄':'bituminous_coal_generation_mwh','무연탄':'anthracite_coal_generation_mwh','원자력':'nuclear_generation_mwh','coal':'coal_generation_mwh'}
    shared_diff={fuel:float(np.abs(wide[fuel]-existing.reindex(expected)[column]).max()) for fuel,column in mapping.items()}
    assert max(shared_diff.values())<1e-8
    monthly=wide.resample('MS').agg(['count','sum'])
    assert monthly.xs('count',axis=1,level=1).eq(monthly.index.days_in_month*24,axis=0).all().all()
    assert hashlib.sha256(annual.read_bytes()).hexdigest()==raw_hash,'Original was modified'
    report=dict(status='SUITABLE_AS_VERSIONED_RETROSPECTIVE_SUPPLEMENT',source_commit=common.SHA,annual_source=str(annual.relative_to(WORK)),annual_sha256=raw_hash,api_sha256=hashlib.sha256(api.read_bytes()).hexdigest(),annual_rows=len(data),annual_all_fuel_types=int(data['연료원별'].nunique()),selected_fuel_rows=len(selected),coverage=coverage,api_overlap_dates=sorted(a.tradeYmd.unique().tolist()),api_comparison=comparison,hour_offset_comparison=offsets,shared_normalized_max_differences=shared_diff,missing_before_per_fuel=8736,candidate_missing_per_fuel=0,coal_definition='유연탄 + 무연탄; no IGCC/biomass/oil',unit='MWh; net sent-out market-traded energy, NOT installed capacity MW',geography='No region field; cannot claim mainland-only or subtract Jeju',api_full_year_identity_verified=False,publication_vintage_verified=False,raw_modified=False,common_dataset_modified=False,models_retrained=False,limitations=['Only 2025-01-01 overlaps the API; rest of year is internally validated, not independently API-matched','Both official sources can change after settlement revisions; do not claim identical historical vintages','Annual source publication and revision timestamps are not historically reconstructed; 72h availability remains an assumption','2024 source and its gaps are unaffected'],official_sources=['https://www.data.go.kr/data/15127395/fileData.do','https://www.data.go.kr/data/15106744/openapi.do'])
    out=ROOT/'reports/annual_generation_2025_validation';out.mkdir(parents=True,exist_ok=True)
    (out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    # JSON records are audit intermediates, not replacement source spreadsheets.
    (out/'overlap_values.json').write_text(pairs[['timestamp','연료원별','value','value_api','absolute_difference_mwh']].to_json(orient='records',force_ascii=False,date_format='iso',indent=2)+'\n')
    lines=['# 2025년 연간 발전량 CSV 보완 적합성 검증','','**결론: 새 데이터 버전의 과거 분석용 보완 자료로 사용 가능.** 전체 연도 API 동일성과 당시 공표시각까지 검증한 것은 아닙니다. 기존 공통 데이터·모델·원본은 변경하지 않았습니다.','',f'원본: `{annual.relative_to(WORK)}`',f'SHA256: `{raw_hash}`','','## 원자료 정의','','[KPX 공식 파일 설명](https://www.data.go.kr/data/15127395/fileData.do)에 따르면 전력시장에서 거래하는 발전기의 송전단 전력거래량(발전량)이며 소내용 및 주변압기 손실을 제외합니다. 설비용량 MW가 아니라 `전력거래량(MWh)`를 사용합니다. 전국 모든 발전소의 총발전량, 공급가능용량, 입찰량과 구분합니다. 지역 필드가 없어 육지 단독 자료로 명명할 수 없습니다. 공식 API 설명 역시 전력거래 정산자료라고 명시하며 수정정산에 따라 변동할 수 있습니다.','','## 시간별 완전성','','|발전원|예상 시간|실제 시간|결측|중복|음수|','|---|---:|---:|---:|---:|---:|']
    for r in coverage:lines.append(f'|{r["fuel"]}|{r["expected_hours"]:,}|{r["valid_hours"]:,}|{r["missing_hours"]}|{r["duplicates"]}|{r["negative_values"]}|')
    lines+=['',f'연간 원본 전체는 {len(data):,}행·26개 연료원이며, 필수4종은35,040행입니다. 2025-01-01 00시~12-31 23시의 모든시간이 있습니다. 거래시간1~24를00~23시 시작 슬롯으로 변환했습니다. 석탄은 유연탄+무연탄 합계로 구성하며 둘 다 유효한 시간만 합칩니다. 12개 월의 일수×24시간도 각각 일치했습니다. 관측된 실제0은 그대로 유지합니다.','','## API 값 대조','','겹치는 구간은2025-01-01 하루뿐입니다. 4종×24시간=96쌍을 비교했습니다. API 0.001MWh 표시 정밀도에 대한 반올림 허용차0.0005001MWh를 사용했습니다.','','|발전원|비교 쌍|최대 절대차 MWh|허용차 초과|','|---|---:|---:|---:|']
    for r in comparison:lines.append(f'|{r["fuel"]}|{r["pairs"]}|{r["max_absolute_difference_mwh"]:.9f}|{r["outside_tolerance"]}|')
    lines+=['','시각을±1시간 옮긴 대조도 수행했습니다. 아래의0시간 정렬이 API와 일치합니다.','',json.dumps(offsets,ensure_ascii=False,indent=2),'','기존 공유 정규화본 `shared_datasets/kpx_generation/annual_generation_2025.csv`도 원본에서 독립적으로 추출한4종 및 석탄 합계와 최대오차1e-8MWh 미만으로 일치했습니다. 기존 정규화본을 그대로 새 버전에 연결할 수 있습니다.','','## 보완 효과 및 적용 방법','','- 2025년 변수별 확보24시간 →8,760시간, 미확보8,736시간 →0시간입니다. LNG·원자력·석탄 모두 해당합니다.','- 2025년은 연간 CSV를 단일 출처로 채택하는 것이 적절합니다. API와 날짜별로 뒤섞거나 두 파일의 행을 중복 합산하지 않습니다.','- 새 공통 데이터 버전에서 원본 출처·해시·시장 범위·단위를 기록하고 실측72시간 지연을 그대로 적용합니다.','- 달력상2024년 말 또는2026년 초에 걸친 데이터는 별도 연도 원본이 필요합니다. 이 검증으로2024년 누락이 해결되는 것은 아닙니다.','- 모델 재학습 전 이력창과 모든 평가 발행일의 입력을 다시 생성해야 합니다. 기존 LSTM/SARIMAX 성능표는 보완 전 실험으로 보존합니다.','','## 남은 한계','','1. 96쌍의 일치는 강한 호환 근거지만 나머지364일의 API 일치를 증명하지 않습니다.','2. [공식 파일](https://www.data.go.kr/data/15127395/fileData.do)과 [API](https://www.data.go.kr/data/15106744/openapi.do)는 수정정산으로 값이 바뀔 수 있습니다. 완전히 같은 발표본이라고 주장하지 않습니다.','3. 현재 연간 파일을 확보했다는 사실은2025년 각 예측일에 해당 값이72시간 안에 공개됐다는 증거가 아닙니다. 과거 발표본을 복원한 자료가 아니므로 기존 지연 가정을 계속 명시해야 합니다.','4. 용량 대비 에너지 범위 점검은 내부 타당성 확인이며 자료 범위 동등성을 보증하지 않습니다. 연료별 용량 초과 건수 등은 validation.json에 기록했습니다.','5. 성능 개선은 아직 평가하지 않았습니다. 2025년 하반기를 본 뒤 구성한 후속 실험이므로 재평가 시 최초의 독립 Final Test와 구분합니다.','']
    (out/'README.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
