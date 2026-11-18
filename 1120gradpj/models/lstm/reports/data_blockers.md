# LSTM 데이터 사전 검사

상태: BLOCKED

실제 SMP 학습·튜닝·평가 미실행.

| 항목 | 원인 | 조치 |
|---|---|---|
| manifest.json | 공통 버전 파일 없음 | 공통 데이터 정의·근거·정규화 보완 후 재검사 |
| hourly.csv | 공통 버전 파일 없음 | 공통 데이터 정의·근거·정규화 보완 후 재검사 |
| forecast_inputs.csv | 공통 버전 파일 없음 | 공통 데이터 정의·근거·정규화 보완 후 재검사 |
| evaluation_origins.csv | 공통 버전 파일 없음 | 공통 데이터 정의·근거·정규화 보완 후 재검사 |
| evaluation_targets.csv | 공통 버전 파일 없음 | 공통 데이터 정의·근거·정규화 보완 후 재검사 |
| feature_manifest.csv | 공통 버전 파일 없음 | 공통 데이터 정의·근거·정규화 보완 후 재검사 |
| demand_actual_definition | 확정된 공통 manifest 없음 | 팀 공통 선택·규칙과 근거를 manifest에 기록 |
| midrange_72h_mapping | 확정된 공통 manifest 없음 | 팀 공통 선택·규칙과 근거를 manifest에 기록 |
| demand_forecast_72h_mapping | 확정된 공통 manifest 없음 | 팀 공통 선택·규칙과 근거를 manifest에 기록 |
| baseline_origin_day | 확정된 공통 manifest 없음 | 팀 공통 선택·규칙과 근거를 manifest에 기록 |

## 수집 현황 참고

- demand_actual: EPSIS 결측 1,095시간; 공식 전국 수요 후보와 공통 선택 미확정
- demand_forecast: 2023~2025 공식 연간 자료 확보; D+2/3 사용 규칙 필요
- holidays: 공식 API 자료 확보; 공통 버전 연결 필요
- calendar: 날짜에서 생성; 공통 인코딩 연결 필요
- generation: 표본 API 성공; 전체 기간·단위·범위 검증 필요
- renewables: 2023~2025 수집본 존재; 태양광 1시간 결측·버전 차이 검토 필요
- reserve: 1,095시간 결측 및 공급능력·수요·예비력 관계 검토 필요
- domestic_lng: 지정 HOME 파일과 section_c 정규화본 존재; 동월 값 조건부 정책
- oil: FRED 과거 기록 수집본 존재; D−2·72시간 고정값 사용
- international_fuel: 과거 기록 수집본 존재; 오래된 관측값 경과일 보존
- weather_actual: ASOS 이력 존재; 일사량 결측/야간 구분 및 지역 정의 필요
- midrange_forecast: 공유 CSV 확보; 일 최저·최고기온 및 날씨·강수확률의 72시간 연결 미확정

제외한 동서발전·단기예보·열량단가의 미확보는 차단 사유가 아닙니다.
