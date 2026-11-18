# 4개 모델 — 발전량 보완 전 공통 v3 비교

데이터·평가 날짜·정답·기준예측이 같은4개 모델의 실제 실행 결과입니다. 현재 선택된 LSTM·SARIMAX v3와 새 LightGBM·XGBoost를 비교합니다. 기존 LSTM·SARIMAX 모델 및 결과는 변경하지 않았습니다.

|모델|구간|MAE 원/kWh|RMSE 원/kWh|R²|전주 기준 MAE|
|---|---|---:|---:|---:|---:|
|LSTM|test|17.6751|21.8759|0.1005|11.4334|
|LSTM|validation|12.8817|17.1546|0.3177|12.2211|
|SARIMAX|test|13.9553|18.0230|0.3895|11.4334|
|SARIMAX|validation|12.9804|17.8097|0.2646|12.2211|
|LIGHTGBM|test|19.4655|23.3385|-0.0238|11.4334|
|LIGHTGBM|validation|10.4287|14.4337|0.5170|12.2211|
|XGBOOST|test|19.6752|23.6281|-0.0494|11.4334|
|XGBOOST|validation|10.3212|14.4966|0.5128|12.2211|

각 모델의 평가행은25,992개(Validation12,888·하반기13,104)로 모두 일치합니다. 후보·조기종료 선택은Validation으로만 수행했습니다. 이번 비교로 하반기 성능을 보고 새 후보를 추가하지 않았습니다.

동월LNG조건부 입력·실측72시간공개지연가정·2025년발전량99.726%결측대체 등 공통한계가 유지됩니다. 이 하반기 기간은 이전 모델 결과를 이미 확인한 기간이므로 후속모델 비교로 구분합니다.

- [LightGBM 보고서](../../models/lightgbm/reports/v3_common/final_evaluation_report.md)
- [XGBoost 보고서](../../models/xgboost/reports/v3_common/final_evaluation_report.md)
