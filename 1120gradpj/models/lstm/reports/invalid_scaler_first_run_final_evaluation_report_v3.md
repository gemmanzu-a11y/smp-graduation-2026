# 무효 실행 — 상수 특성 표준화 오류

이 결과는 최종 성능으로 사용하지 않습니다. numerical_correction_v3.md와 수정 후 final_evaluation_report_v3.md를 확인하세요.

# LSTM 72시간 최종 평가 — 공통 v3

실제 PyTorch 학습·Validation 선택·Final Test 평가를 실행했습니다.

- 데이터 버전: `v3_a90141b81ecd_lag72`
- 입력 커밋: `a90141b81ecd841c524eb75a72f4bcc4f39989f5`
- 결과 경로: `1120gradpj/models/lstm/outputs/v3_a90141b81ecd_lag72/20261119T012006`
- 학습 시간: 75.7초
- 선택 모델: {'lookback': 48, 'hidden_size': 32, 'layers': 1, 'dropout': 0.0, 'learning_rate': 0.001, 'batch_size': 32, 'epochs': 100, 'patience': 10}; best epoch=22
- 입력: 과거 48시간 × 29변수, 미래 72시간 × 83변수
- Train으로만 표준화·대체 통계를 적합. Validation MAE로 설정·epoch 선택. Train+Validation 재학습 없음. Test 재튜닝 없음.
- 직접 72시간 출력. 미래 SMP teacher forcing 없음.

## 전체 성능

|구간|MAE 원/kWh|RMSE 원/kWh|R²|최근 일별 패턴 MAE|전주 패턴 MAE|전주 대비 개선율|
|---|---:|---:|---:|---:|---:|---:|
|test|6036.9467|114841.4041|-24789244.4149|13.0875|11.4334|-52701.05%|
|validation|12.8817|17.1546|0.3177|14.3473|12.2211|-5.41%|

## 예측일별 성능

|구간|예측일|MAE|RMSE|
|---|---:|---:|---:|
|test|D+1|6036.6896|114841.6392|
|test|D+2|6036.9481|114841.3324|
|test|D+3|6037.2025|114841.2408|
|validation|D+1|12.5840|16.9989|
|validation|D+2|12.8693|17.0881|
|validation|D+3|13.1919|17.3746|

## 해석 및 한계

실제 수요, 발전량, 예비력 및 기상 관측자료의 개별 공표시각을 모두 확인할 수 없어, 본 연구에서는 예측 기준시각보다 72시간 이전의 실측 자료만 활용하는 보수적 지연 규칙을 가정하였다. 이 규칙은 각 자료의 실제 공개시각을 검증한 결과가 아니다.

- **동월 LNG 단가 제공 조건부 과거 예측 실험**입니다. 당시 공개 여부가 확인된 운영 예측 성능으로 해석할 수 없습니다.
- SMP도 공표 이력 미확인으로 72시간 지연했습니다. 기준 예측에도 동일한 제한을 적용했습니다. 23시에는 대상일 일부 공식 SMP가 이미 공개되어 있을 가능성이 있어 운영적 효용은 별도 검토해야 합니다.
- 발전량 2025년 원본은 1일뿐입니다. 장기 결측을 Train 계절·시간대 대표값으로 대체하므로 실제 공급 변동을 대부분 반영하지 못합니다. 결측 자체를 수집 완료로 표시하지 않습니다.
- 중기예보는 대상 날짜가 일치하고 발행시각이 origin 이전인 최신 자료를 사용합니다. D+1/2에는 이전 발행본이 연결될 수 있으며, 이를 당일 발표 단기예보로 해석하지 않습니다. 시간별 기온·풍속·일사 예보를 생성하지 않았습니다.
- EPSIS 수요 원본을 사용했습니다. 전국/육지 범위는 원자료 정의를 따르며, 제주 차감이나 육지 명칭 변경을 하지 않았습니다. 공급·발전량도 원본 시장 범위가 SMP 육지 범위와 완전히 동일하다고 보장하지 않습니다.
- ASOS는 서울108 단일 지점입니다. 전국 대표 기상으로 간주하지 않습니다. 야간 플래그는 근사 태양고도이며 관측 정상 여부의 증거가 아닙니다. 결측 일사량을 0으로 바꾸지 않았습니다.
- Final Test는 7~12월로 사계절 전체 검증이 아닙니다. 인접 72시간 블록의 목표 시간이 겹치므로 행별 오차는 독립 표본이 아닙니다.

## 결측과 커버리지

{
  "raw_missing": {
    "demand_actual": 1095,
    "smp": 0,
    "demand_forecast_history": 0,
    "generation_lng": 15216,
    "generation_nuclear": 15960,
    "generation_coal": 15960,
    "solar_actual": 1,
    "solar_actual_regional_missing": 0,
    "wind_actual": 0,
    "wind_actual_regional_missing": 0,
    "reserve_mw": 703,
    "reserve_pct": 703,
    "temperature_c": 42,
    "wind_ms": 69,
    "irradiance_mj_m2": 11956,
    "irradiance_night": 0
  },
  "raw_rows": 26304,
  "split_origins": {
    "test": 182,
    "train": 718,
    "validation": 179
  },
  "excluded_origins": 11,
  "forecast_missing": {
    "mid_tmin": 0.0,
    "mid_tmax": 0.0,
    "mid_rain": 0.0
  },
  "checks": {
    "fixed_origin_cutoff": true,
    "issued_before_origin": true,
    "finite_model_arrays": true,
    "target_split_blocks": true
  },
  "generation_missing_by_year": {
    "generation_lng": {
      "2023": 0.736986301369863,
      "2024": 0.00273224043715847,
      "2025": 0.9972602739726028
    },
    "generation_nuclear": {
      "2023": 0.736986301369863,
      "2024": 0.08743169398907104,
      "2025": 0.9972602739726028
    },
    "generation_coal": {
      "2023": 0.736986301369863,
      "2024": 0.08743169398907104,
      "2025": 0.9972602739726028
    }
  }
}

## 재현

```sh
PYTHONPATH=1120gradpj/src 1120gradpj/.venv/bin/python -m smp_forecast.common_v3
1120gradpj/.venv/bin/python 1120gradpj/models/lstm/train.py
```

결과 CSV는 모든 평가 발행일의 72시간 값을 보존합니다. 월별·발행일별·horizon별 지표와 선택일 PNG/HTML은 위 결과 경로에 저장되어 있습니다.
