# 발전량 보완 후 LSTM·SARIMAX 재실행

**실제 재학습·평가 완료. 데이터 보완 후의 후속 실험이며, 최초의 독립 Final Test와 구분합니다.**

- 이전 공통 버전: `v3_a90141b81ecd_lag72`
- 새 공통 버전: `v4_a90141b81ecd_generation_911281bf_lag72`
- 변경: 2023·2025년 발전량을 검증한 연간 CSV로 교체. 2024년은 API와 남은 결측 유지.
- 유지: 나머지11개 입력 그룹, 목표SMP, 평가 날짜, 기준 예측,72시간 지연,Train/Validation/Test 분할,각모델 후보군과 선택 기준.
- 원본·기존 공통v3·기존 모델 및 성능표는 보존했습니다.

## 최종 하반기 비교

|모델|보완 전 MAE|보완 후 MAE|오차 감소율|보완 후 RMSE|보완 후 R²|전주 기준 MAE|
|---|---:|---:|---:|---:|---:|---:|
|LSTM|17.6751|22.1030|-25.05%|26.6381|-0.3337|11.4334|
|SARIMAX|13.9553|14.2391|-2.03%|18.3518|0.3670|11.4334|

MAE·RMSE단위: 원/kWh. 감소율이 음수면 오차가 증가한 것입니다. 데이터 보완만으로 성능 개선이 보장되는 것은 아닙니다.

## Validation과 예측일별 성능

|모델|구간|예측일|보완 전 MAE|보완 후 MAE|R²|
|---|---|---|---:|---:|---:|
|LSTM|validation|all|12.8817|11.5736|0.4231|
|LSTM|validation|D+1|12.5840|11.4163|0.4347|
|LSTM|validation|D+2|12.8693|11.5832|0.4263|
|LSTM|validation|D+3|13.1919|11.7214|0.4079|
|LSTM|test|all|17.6751|22.1030|-0.3337|
|LSTM|test|D+1|17.4084|21.9350|-0.3107|
|LSTM|test|D+2|17.6797|22.0745|-0.3328|
|LSTM|test|D+3|17.9372|22.2995|-0.3580|
|SARIMAX|validation|all|12.9804|12.4756|0.3153|
|SARIMAX|validation|D+1|12.7373|12.3644|0.3324|
|SARIMAX|validation|D+2|12.9606|12.4460|0.3163|
|SARIMAX|validation|D+3|13.2434|12.6165|0.2967|
|SARIMAX|test|all|13.9553|14.2391|0.3670|
|SARIMAX|test|D+1|13.4911|13.8304|0.3998|
|SARIMAX|test|D+2|13.8905|14.2164|0.3700|
|SARIMAX|test|D+3|14.4842|14.6704|0.3310|

## 조건과 해석

발전량 외 다른 변수는 데이터 값까지 이전 버전과 같음을 확인했습니다. 두 모델 모두 평가25992행(Validation12888행·하반기13104행)의 키·정답·기준예측이 일치합니다. 학습 및 대체 통계·표준화는Train으로만 적합하고,Validation으로 후보·LSTM epoch를 선택했습니다. 하반기 결과를 보고 추가 후보를 만들거나 재튜닝하지 않았습니다.

다만 이전 하반기 성능을 확인한 뒤 발전량 입력을 개선한 실험이므로, 이 하반기를 처음 보는 독립적인 최종 검증이라고 주장하지 않습니다. 이후 추가 개선을 계속하면 별도 미사용 기간이나 시계열 교차검증이 필요합니다.

동월 LNG 제공 조건부 입력,실측72시간 지연은 공개시각 검증이 아닌 가정,서울 단일 관측소,시장/육지 범위 차이,2024년 발전량 결측 및일부수요·기상 결측 등의 한계는 유지됩니다. 2023년 연간자료와API의정산버전 차이도 남아 있습니다.

SARIMAX는 기존과 같은 외생계수 최소노름OLS 고정 후ARIMA계수 조건부최대우도 방식입니다. 공동MLE로 바꾸지 않았습니다. LSTM은 기존 직접72시간 출력 구조를 유지했습니다.

## 보완 후 원본 발전량 결측

{
  "generation_lng": {
    "2023": 0.0,
    "2024": 0.00273224043715847,
    "2025": 0.0
  },
  "generation_coal": {
    "2023": 0.0,
    "2024": 0.08743169398907104,
    "2025": 0.0
  },
  "generation_nuclear": {
    "2023": 0.0,
    "2024": 0.08743169398907104,
    "2025": 0.0
  }
}

## 재현

```sh
PYTHONPATH=1120gradpj/src 1120gradpj/.venv/bin/python -m smp_forecast.common_v4
1120gradpj/.venv/bin/python 1120gradpj/models/lstm/train.py --dataset-version v4
1120gradpj/.venv/bin/python 1120gradpj/models/sarimax/train.py --dataset-version v4
1120gradpj/.venv/bin/python 1120gradpj/models/sarimax/report_v3.py --dataset-version v4
1120gradpj/.venv/bin/python 1120gradpj/scripts/compare_generation_update_v4.py
```

