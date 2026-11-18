# SARIMAX 72시간 최종 평가 — 공통 v4

실제 statsmodels SARIMAX 학습·Validation 선택·Final Test 평가를 수행했습니다.

- 데이터: `v4_a90141b81ecd_generation_911281bf_lag72` / 팀 원본 커밋 `a90141b81ecd841c524eb75a72f4bcc4f39989f5`
- 결과: `1120gradpj/models/sarimax/outputs/v4_a90141b81ecd_generation_911281bf_lag72/20261119T024504`
- 모델: order=[2, 0, 0], seasonal_order=[1, 0, 0, 24]
- 학습·평가 소요: 49.5초
- 외생변수 83열 유지, Train 행렬 rank=69. Train 시간별 표본 17,280개.
- **전체 외생계수 최소노름 OLS → 계수 고정 → ARIMA/계절/분산 조건부 최대우도**의 2단계 추정입니다. 모든 계수를 공동 MLE로 최적화한 결과는 아닙니다. 상수·중복 열을 임의 삭제하거나 외생변수 없는 SARIMA로 축소하지 않았습니다.

## 전체 성능

|구간|행 수|MAE 원/kWh|RMSE 원/kWh|R²|전주 패턴 MAE|전주 대비 개선율|
|---|---:|---:|---:|---:|---:|---:|
|test|13104|14.2391|18.3518|0.3670|11.4334|-24.54%|
|validation|12888|12.4756|17.1847|0.3153|12.2211|-2.08%|

## 예측일별 성능

|구간|예측일|MAE|RMSE|
|---|---:|---:|---:|
|test|D+1|13.8304|17.8813|
|test|D+2|14.2164|18.3077|
|test|D+3|14.6704|18.8534|
|validation|D+1|12.3644|17.1064|
|validation|D+2|12.4460|17.1080|
|validation|D+3|12.6165|17.3386|

## 동일 평가 대상 LSTM 비교

|구간|SARIMAX MAE|LSTM MAE|
|---|---:|---:|
|validation|12.4756|11.5736|
|test|14.2391|22.1030|

## 시간 기준 및 검증

- 매일 23시 발행, 다음 3일 00~23시 총72시간입니다. 실측 마감은 발행시각−72시간으로 고정합니다.
- 마지막 상태는 실측 마감에 종료된 SMP까지만 필터링합니다. 이후 공백73시간과 목표72시간을 함께145시간 예측하고 뒤72시간을 저장합니다. 중간 미래 SMP를 주입하지 않습니다.
- 후보마다 계수는 Train만으로 적합합니다. Validation은 설정 선택, Final Test는 선택 후 평가에만 사용합니다. Train+Validation 재학습 및 매일 계수 재추정은 하지 않습니다.
- 상태 갱신은 계수 재학습과 다릅니다. 이미 이용 가능한 과거 SMP만 새로 필터링합니다.
- Train 마지막 상태를 평가에 그대로 연결하지 않고, 첫 평가의 마감까지의 과거만 다시 필터링합니다.
- 학습용 중복 목표시간은 최신 발행 입력 한 행을 채택합니다. 평가에서는 겹치는 모든 72시간 블록을 보존합니다.
- 공통 evaluation_origins/targets를 그대로 사용했습니다. Validation179개·Final Test182개 발행일, 각72행입니다.

## 데이터 및 해석 한계

실제 수요, 발전량, 예비력 및 기상 관측자료의 개별 공표시각을 모두 확인할 수 없어, 본 연구에서는 예측 기준시각보다 72시간 이전의 실측 자료만 활용하는 보수적 지연 규칙을 가정하였다. 이 규칙은 각 자료의 실제 공개시각을 검증한 결과가 아니다.

- **동월 LNG 단가 제공 조건부 과거 예측 실험**입니다. 실제 운영에서 당시 이용 가능한 단가임이 검증된 것은 아닙니다.
- 발전량은 2023/2025년 연간 CSV로 보완했고 해당 연도 결측은 없습니다. 2024년 LNG24시간·석탄/원자력768시간 결측은 공통 대체 규칙을 유지했습니다. 나머지 입력은 이전 버전과 같습니다.
- EPSIS 수요의 원자료 범위를 유지하며 전국 자료를 육지라고 이름 바꾸지 않았습니다. 발전량·예비력의 시장/지역 범위와 육지 SMP의 범위 차이도 남아 있습니다.
- 중기예보는 실제 발표시각과 대상 날짜로 연결합니다. 과거 발행본을 당일 발표 단기예보로 표현하지 않습니다.
- SMP도 추가로72시간 지연했습니다. 23시에는 일부 대상일 SMP가 공식 공표되었을 수 있으며, 이 연구의 운영상 효용은 별도 검토해야 합니다.
- Train 전체로 계수를 추정하는 오프라인 분할 평가입니다. 실제 공개 지연을 고려할 때 연말 Train 정답이 첫 Validation 발행일 전에 모두 확보되었는지 증명하는 운영 실험이 아닙니다.
- rank 결손으로 개별 외생계수의 유일한 경제적 효과를 주장할 수 없습니다. OLS와 ARIMA의 2단계 추정은 공동추정보다 비효율적일 수 있습니다.
- 예측구간은 모형·고정 beta 조건부 구간입니다. 외생예보/대체값/연료/계수 추정의 모든 불확실성을 포함하는 보정 확률구간이 아닙니다.
- 최종 테스트는7~12월로 사계절 전체 검증이 아니며 겹치는 목표시간의 오차는 독립 표본이 아닙니다.

## 후보별 수렴·경고

```json
[
  {
    "params": {
      "order": [
        1,
        0,
        0
      ],
      "seasonal_order": [
        1,
        0,
        0,
        24
      ]
    },
    "validation_mae": 12.476323504862673,
    "rank": 69,
    "constant_features": [
      "smp_missing_last",
      "demand_forecast_history_missing_last",
      "solar_actual_missing_last",
      "wind_actual_missing_last",
      "irradiance_mj_m2_missing_last",
      "mid_tmin_missing",
      "mid_tmax_missing",
      "mid_rain_missing",
      "mid_weather_missing",
      "mid_weather_unknown"
    ],
    "converged": true,
    "warnings": [],
    "seconds": 9.20058424997842,
    "status": "ok"
  },
  {
    "params": {
      "order": [
        1,
        0,
        1
      ],
      "seasonal_order": [
        1,
        0,
        0,
        24
      ]
    },
    "validation_mae": 12.475718434792224,
    "rank": 69,
    "constant_features": [
      "smp_missing_last",
      "demand_forecast_history_missing_last",
      "solar_actual_missing_last",
      "wind_actual_missing_last",
      "irradiance_mj_m2_missing_last",
      "mid_tmin_missing",
      "mid_tmax_missing",
      "mid_rain_missing",
      "mid_weather_missing",
      "mid_weather_unknown"
    ],
    "converged": true,
    "warnings": [],
    "seconds": 12.336558375012828,
    "status": "ok"
  },
  {
    "params": {
      "order": [
        2,
        0,
        0
      ],
      "seasonal_order": [
        1,
        0,
        0,
        24
      ]
    },
    "validation_mae": 12.475618785211,
    "rank": 69,
    "constant_features": [
      "smp_missing_last",
      "demand_forecast_history_missing_last",
      "solar_actual_missing_last",
      "wind_actual_missing_last",
      "irradiance_mj_m2_missing_last",
      "mid_tmin_missing",
      "mid_tmax_missing",
      "mid_rain_missing",
      "mid_weather_missing",
      "mid_weather_unknown"
    ],
    "converged": true,
    "warnings": [],
    "seconds": 13.732830499997362,
    "status": "ok"
  }
]
```

## 산출물·재현

전체 예측 CSV, 발행일·월·예측거리별 지표, 선택일 PNG/HTML과6개월 비교는 위 결과 폴더에 있습니다. 원본과 LSTM 결과는 보존했습니다. 인증키가 필요 없는 기존 공통 데이터 재사용입니다.

```sh
1120gradpj/.venv/bin/python 1120gradpj/models/sarimax/train.py --dataset-version v4
1120gradpj/.venv/bin/python 1120gradpj/models/sarimax/report_v3.py --dataset-version v4
```


이번 결과는 기존 2025년 하반기 평가를 확인한 뒤 발전량을 보완한 후속 실험입니다. 최초의 독립 Final Test와 구분합니다.
