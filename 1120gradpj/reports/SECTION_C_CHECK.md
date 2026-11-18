# C 연료 데이터 수집·검증 결과

확인일: 2026-11-18 KST. 모델 학습은 수행하지 않았습니다.

## 결과

| 입력 | 원자료·주기 | 적용 | 결과 |
|---|---|---|---|
| 국내 LNG | 지정 엑셀 연료비단가/LNG/원/kWh, 월별 46개월 | 과거 대상월 값, 11월 시연은 2026년 10월 값 | 과거 필요 36개월·26,304시간 결측 0 |
| DCOILWTICO | Daily, Dollars per Barrel | 발행일 D−2의 과거 빈티지 최신 유효값 | 1,096개 발행일 결측 0, 최대 경과 33일 |
| DCOILBRENTEU | Daily, Dollars per Barrel | 발행일 D−2의 과거 빈티지 최신 유효값 | 1,096개 발행일 결측 0, 최대 경과 15일 |
| PNGASJPUSDM | Monthly, U.S. Dollars per Million Metric British Thermal Unit | 발행일 D−2의 과거 빈티지 최신 유효값 | 1,096개 발행일 결측 0, 최대 경과 210일 |
| PCOALAUUSDM | Monthly, U.S. Dollars per Metric Ton | 발행일 D−2의 과거 빈티지 최신 유효값 | 1,096개 발행일 결측 0, 최대 경과 210일 |

## 국내 LNG 원본

파일: HOME_전력거래_연료비용.xlsx
Sheet1, P열(16번째 열), 헤더 1~3행, 값 4~49행. 원본 기간 2023-01~2026-10.
원본 SHA-256: 295d800831325f19e6a47b0ef2b406494e56da48bbb73e92b949de9736d6bc98

연료단가·열량단가가 아니라 연료비단가의 LNG 원/kWh만 추출했습니다. 원본은 수정하지 않았습니다. KPX 열량단가 API와 국내 연료 2개월 지연 가정은 사용하지 않았습니다. 과거 평가는 대상월 값이므로 월 경계를 넘는 72시간 블록에서는 LNG 값이 바뀔 수 있습니다. 이 점은 당시 공개 여부를 증명한 운영 평가가 아니라 동월 LNG 제공 조건부 실험입니다.

2026년 11월 시연용 국내 값: 2026년 10월 164.906245원/kWh, 72시간 전체 고정.

## 국제가격 과거 시점 재구성

FRED API의 output_type=1로 관측 기준일과 realtime_start/realtime_end 구간을 받았습니다. 각 발행일 D에 대해 D−2일이 해당 구간 안에 있고 관측 기준일이 D−2일 이후가 아닌 유효 숫자만 선택합니다. 그중 가장 최근 관측 기준일을 택합니다. 일별 휴일·결측과 월별 발표 지연이 있어도 미래값을 가져오지 않습니다. 모든 원래 단위를 유지하며 원화·원/kWh로 임의 환산하지 않습니다.

4개 시리즈 × 3개 과거 기준일의 직접 조회 12건과 구간 재구성 값을 대조해 모두 일치했습니다. 사용한 기준일은 2022-12-29, 2024-07-01, 2025-12-28입니다.

D−2일은 날짜 단위의 보수적 규칙이며 실제 한국시간 23시의 공개시각을 복원한 것은 아닙니다. API가 반환하는 realtime_start는 조회 범위 시작에서 잘린 구간일 수 있으므로 최초 공개일이라고 부르지 않습니다.

## 오래된 관측 기준일 주의

국제 LNG·석탄은 2025년 말 과거 조회에서 2025년 6월 기준값이 최신 유효값으로 선택되는 구간이 있습니다. 최대 age_days는 210일입니다. WTI도 최대 33일, Brent는 최대 15일입니다. 이는 당시 FRED 기록에서 선택 가능한 최신값 기준이며 시장가격이 그 기간 동안 변하지 않았다는 뜻이 아닙니다. 현재 수정본이나 임의의 더 최근 월 값으로 바꾸지 않았습니다. 사용 관측일·빈티지 구간·경과일을 전부 열로 보존했습니다.

## 파일

모든 데이터는 data/processed/section_c/ 아래에 저장합니다.

| 파일 | 내용 |
|---|---|
| domestic_lng_monthly.csv | 원본 월별 LNG 46개월 |
| domestic_lng_hourly_2023_2025.csv | 대상월 LNG 26,304시간 |
| *_vintage_intervals.csv | FRED 원본 관측·빈티지 구간 |
| international_fuel_by_origin_2023_2025.csv | 발행일별 국제가격 1,096행과 사용 근거 |
| fuel_forecast_inputs_2023_2025.csv | 완전한 72시간 블록 1,090개, 78,480행 |
| november_demo_fuel_preview.csv | 현재 날짜를 참조한 11월 입력 예시 72행, 모델 예측 아님 |
| fred_metadata.json | 시리즈 원래 주기·단위·공식 출처 |
| fred_asof_validation.json | 직접 과거 기준일 대조 12건 |

미래 입력 CSV는 목표 블록 전체가 한 분할에 들어오는 경우만 포함합니다. 2023~2024 학습 729개, 2025 상반기 검증 179개, 하반기 평가 182개입니다. 초기 다른 변수의 이력 요구에 따라 공통 평가 발행일과 교집합을 정할 수 있지만, 이 파일 자체에서 임의로 과거 시점을 누락하지 않았습니다.

## 현재 입력 미리보기

오늘 참조 발행일의 국제가격은 D−2일 기준입니다. 실제 모델을 발행한 결과가 아닙니다.

| 국제가격 | 관측 기준일 | 값 | 단위 |
|---|---|---:|---|
| DCOILWTICO | 2026-11-11 | 89.62 | Dollars per Barrel |
| DCOILBRENTEU | 2026-11-11 | 92.14 | Dollars per Barrel |
| PNGASJPUSDM | 2026-09-01 | 26.637 | U.S. Dollars per Million Metric British Thermal Unit |
| PCOALAUUSDM | 2026-09-01 | 153.84 | U.S. Dollars per Metric Ton |

## 실행

`.venv/bin/python scripts/collect_section_c.py`

FRED_API_KEY 환경변수가 필요합니다. 인증키는 코드·로그·원본 영수증에 저장하지 않습니다. 공통 HTTP 수집기에 FRED api_key 파라미터 지원 및 응답 키 반사 저장 차단 검사를 추가했습니다.

C 연료 값은 합의한 가정하에 준비됐지만, A 실적 정의 선택·B 과거 예측 및 자료 품질·D 기상 전체 점검은 별도입니다. 모델 학습 차단은 유지합니다.

공식 문서:
- https://fred.stlouisfed.org/docs/api/fred/series_observations.html
- https://fred.stlouisfed.org/series/PNGASJPUSDM
- https://fred.stlouisfed.org/series/PCOALAUUSDM

## 테스트 결과

전체 47개 통과. C 전용 9개는 과거 수정본 선택·발표 전 값 차단·72시간·기간 경계·국내 LNG 대상월·시연 10월 매핑을 검사했습니다. 공통 HTTP 2개는 인증 파라미터 분리와 인증키 반사 응답 저장 차단을 검사했습니다.
