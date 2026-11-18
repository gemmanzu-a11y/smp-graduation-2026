# 공통 v3 원자료 선택·검사 보고서

팀 저장소 `parksiwon22/gradproject`, `codex/smp-72h-data` 브랜치를 커밋 `a90141b81ecd841c524eb75a72f4bcc4f39989f5`에 고정했습니다. `SMP_72H_INPUT_DATA` 아래 104개 실제 파일을 내려받고 Git blob SHA 및 SHA256을 검사했습니다. 원본을 수정하거나 API를 재호출하지 않았습니다. 전체 목록·해시는 로컬 `1120gradpj/data/raw/team_training_snapshot/<commit>/snapshot_manifest.json`에 있습니다.

|그룹|채택 자료|처리·제약|
|---|---|---|
|1 수요 실적|기존 공식 EPSIS 수집본 `1120gradpj/data/processed/power_hourly.csv`|팀 01 CSV는 전국 수요 후보이므로 사용하지 않음. 12개 5분 표본이 모인 시간만 평균. 1,095시간 NaN. 원본 범위를 육지라고 바꾸지 않음.|
|2 수요예측|`02_day_ahead_demand_mlfd/mainland_demand_forecast_2023_2025.csv`|26,304시간. 미래 대상일 예측으로 직접 연결하지 않고 72시간 지연 과거 이력으로 사용.|
|3 공휴일|`03_kasi_holidays/03_kasi_holidays.csv`|isHoliday=Y 공식 날짜, 주말과 별도 변수.|
|4 달력|Asia/Seoul 대상시각에서 재생성|시간 0~23, 월 1~12 기준 sin/cos. 원 CSV의 hour_ending을 시작 시각으로 잘못 해석하지 않음.|
|5 발전량|`05_generation_by_fuel_amgo/api_generation_partial_2023_2025_merged_20261119.csv`|86,472행. LNG·원자력·석탄(유연탄+무연탄, 둘 다 있어야 합계)으로 구성. 연간 설비용량 CSV를 보충 자료로 섞지 않음.|
|6 재생에너지|`06_regional_solar_wind_actuals/team_shared_originals/renewable_source_0~6.csv`|2023~2025, 제주 제외. 지역 빈칸을 0으로 변경하지 않고 최소 1개 유효값이 있는 합계와 지역 누락 플래그를 함께 사용. 태양광 전체 1시간 누락. 원본의 전력거래량/발전량·시장 범위 차이 유지.|
|7 예비력|`07_supply_reserve/07_supply_reserve_mw_pct.csv`|314,563개 5분 행. 시간당 12개 고유 시각일 때만 평균. MW와 % 별도. 재검사 결과 각각 703시간 NaN; 이전 1,095시간 보고는 다른 수집본에 해당.|
|8 국내 LNG|`08_domestic_lng_fuel_cost/08_domestic_lng_fuel_cost.csv`|연료비단가 원/kWh. 대상 월 값 연결, 월 경계에도 대상시간별 월 적용. 동월 단가 제공 조건부 실험.|
|9 원유|09 폴더의 재구성 CSV 및 `fred_vintage_source` 원본 JSON|WTI·Brent의 origin 날짜 D−2 시점 vintage를 다시 선택. 팀 재구성본과 1,079개 발행일에서 차이 0. .pre_rebuild 파일 미사용.|
|10 국제 LNG·석탄|10 폴더의 `fred_vintage_source` 원본 JSON|PNGASJPUSDM USD/MMBtu, PCOALAUUSDM USD/metric ton. 월간 값. D−2 최신 이용 가능 값. 1,079개 발행일 팀 재구성본과 차이 0. 국내 구매가격과 구분.|
|11 관측|`11_kma_asos_actuals/11_kma_asos_actuals.csv`|서울108. 기온 42, 풍속 69, 일사 11,956시간 결측. SI는 직전 시간 누적량이므로 관측시각을 구간 종료로 취급해 시작 라벨 −1시간. TA/WS는 해당 종료시각 관측. 일사 음수는 결측; 실제 0은 보존.|
|12 중기예보|`12_kma_midrange_forecast/12_kma_midrange_temperature_seoul.csv` + `shared_datasets/kma_midrange/forecast_YYYY-MM.csv`|기온·서울인천경기 날씨/강수확률. 대상 날짜가 같고 origin 이전에 발표된 최신 행. AM/PM별, DAY는 전일 값으로만 사용. 이전 발표본이 D+1/2에 연결될 수 있음. 미래 실측 사용·시간별 기상예보 생성 없음.|
|목표 및 과거 SMP|공식 EPSIS 수집본 `1120gradpj/data/processed/smp_hourly.csv`|2023~2025 목표 결측 없음. 공개 이력 불확실성으로 과거 입력 SMP도 추가로 72시간 지연.|

## 단위·시간과 근거

- AMGO는 조정 계량발전량(Adjusted Metered Generation Output)입니다. [KPX 공식 전력시장운영규칙](https://new.kpx.or.kr/boardDownload.es?bid=0031&list_no=70403&seq=1)의 AMGO 정의와 [원저 논문의 기호표·자료 설명](https://www.ksesjournal.co.kr/articles/xml/QNM9/)(DOI 10.7836/kses.2019.39.6.113)의 AMGO(MWh)를 함께 근거로 사용했습니다. API 항목 설명 자체에는 단위가 명시되지 않았다는 한계도 보존합니다. 2025-01-01 핵심 발전원 96행은 공식 연간 MWh CSV와 최대 0.0005 차이였습니다. 2023 자료는 수정·정밀도 차이가 있어 연간 CSV와 병합하지 않았습니다.
- 거래시간 1~24는 해당 날짜 00~23시 시작 라벨로 변환합니다. 원본 시간별 발전량은 한 시간 구간의 에너지입니다. 수요는 원본 EPSIS MW, 예비력 MW, 일사 MJ/m²를 그대로 유지합니다.
- 실측 72시간 마감은 모든 horizon에 대해 `forecast_origin - 72h` 하나입니다. 실제 사용할 마지막 시간 구간은 마감시각에 종료됩니다. ASOS 시간 라벨 조정 후에도 같은 규칙을 적용합니다.
- 야간 플래그는 서울 좌표에서 근사 태양고도로 계산합니다. [NOAA 계산식](https://gml.noaa.gov/grad/solcalc/solareqns.PDF)을 이용하며 관측이 정상적으로 0이라는 증거로 사용하지 않습니다. 야간 결측도 원본 NaN 및 결측 표시를 유지합니다.
- 수요·예비력·발전량의 전국/시장 범위와 육지 SMP의 지리적 범위 차이는 남아 있습니다. 임의로 제주를 차감하거나 자료 이름을 육지로 바꾸지 않았습니다.

## 결측 및 버전

학습용 실측은 과거값 24시간까지 전방 유지 → Train 계절/시간대 중앙값 → Train 전체 중앙값으로 대체합니다. Train은 2023~2024년이며 Validation/Test로 통계를 다시 맞추지 않습니다. 원본 NaN과 모델 입력을 별도 CSV로 보존합니다. 원자료 결측과 태양광 지역별 일부 누락, 야간 일사량을 별도 표시합니다. 원본에 사유 코드가 없으면 원자료 결측의 원인을 기기 장애 등으로 단정하지 않습니다.

발전량 핵심 그룹의 2025년 결측률은 **99.726%**입니다. 2023년에도 73.699%가 결측입니다. 최종 평가는 이 불완전한 발전량 입력을 대체한 조건의 성능입니다. 실제로 완전 수집한 발전량을 이용한 성능으로 표현하면 안 됩니다. 2024-02-29는 전체 누락, 2024년 8월 원자력·무연탄 누락도 그대로 유지합니다.

공통 평가 발행일: Train 718일, Validation 179일, Final Test 182일. Train 시작의 11개 발행일은 168시간 이력과 72시간 지연에 필요한 이전 원본이 없어 제외했습니다. 각 경계를 넘는 72시간 블록은 제외하며, 공통 evaluation_origins/targets에 고정했습니다. Validation 12,888행, Final Test 13,104행입니다.

공통 데이터 버전은 `v3_a90141b81ecd_lag72`입니다. 실제 선택 파일의 SHA256, 시차·대체 규칙, 입력 열 목록은 공통 버전의 manifest/feature_manifest에 저장했습니다. 입력·훈련 바이너리·전체 예측 CSV는 로컬에 보존하고 공개 Git에는 올리지 않도록 설정했습니다. 코드와 지표·보고서는 공유 가능합니다.
