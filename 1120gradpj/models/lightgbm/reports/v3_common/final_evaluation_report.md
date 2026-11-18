# LIGHTGBM — 발전량 보완 전 공통 v3

실제 학습·Validation 설정 선택·하반기 평가를 완료했습니다.

- 데이터: `v3_a90141b81ecd_lag72`
- 결과: `1120gradpj/models/lightgbm/outputs/v3_a90141b81ecd_lag72/20261119T025702`
- 공통 입력83개를 그대로 사용했습니다. 목표SMP·정답·기준예측은 입력 열에 포함하지 않습니다.
- 입력 그룹12개를 유지하며 기존Train 대체값·결측 표시를 그대로 읽습니다. 자체 수집·재집계·v4발전량 대체는 하지 않았습니다.
- 한 모델이 각 대상시간을 직접 회귀합니다. 하루72개 행을 예측하며 미래SMP를 재귀 입력하거나 teacher forcing하지 않습니다.
- 후보3개, seed42,CPU2threads. Train 학습,Validation MAE로40회 patience 조기 종료·후보 선택. 하반기는 선택 후 평가하며 재튜닝·Train+Validation 재학습을 하지 않았습니다.

- 선택: {'n_estimators': 1200, 'learning_rate': 0.03, 'num_leaves': 15, 'max_depth': 5, 'min_child_samples': 100, 'subsample': 0.85, 'subsample_freq': 1, 'colsample_bytree': 0.85, 'reg_lambda': 10, 'reg_alpha': 0.1}; 최적 boosting rounds=187
- 소요 시간: 18.1초

## 성능

|구간|MAE 원/kWh|RMSE 원/kWh|R²|전주 기준 MAE|
|---|---:|---:|---:|---:|
|test|19.4655|23.3385|-0.0238|11.4334|
|validation|10.4287|14.4337|0.5170|12.2211|

## 예측일별

|구간|예측일|MAE|RMSE|
|---|---:|---:|---:|
|test|D+1|19.3420|23.1915|
|test|D+2|19.4542|23.3326|
|test|D+3|19.6005|23.4904|
|validation|D+1|10.4269|14.5444|
|validation|D+2|10.4027|14.3572|
|validation|D+3|10.4564|14.3988|

## 한계

동월 LNG 단가 제공 조건부 과거 실험입니다. 실측 공개시각을 검증한 것이 아니라72시간 지연을 가정했고 과거SMP에도 같은 보수적 지연을 적용했습니다. 2025년 발전량 원본은1일뿐이므로99.726% 결측을 대체한 조건입니다. 나중에 검증한2023/2025년 연간 발전량을 이번 입력에 반영하지 않았습니다. 원자료 시장/육지 범위 차이와서울108단일관측소 등의 한계도 그대로입니다.

기존 모델의 하반기 결과를 이미 확인한 뒤 추가하는 모델 비교입니다. 미사용 자료에 대한 새 독립 시험으로 주장하지 않습니다. 중요도는 트리의 분할 기여를 나타내며 인과적 경제 효과가 아닙니다.

## 구현 및 공식 문서

XGBoost는 XGBRegressor의 hist 트리·규제·행/열 샘플링을 사용합니다. LightGBM은 LGBMRegressor의 leaf 수·최소 leaf 표본·규제로 복잡도를 제한합니다. 알고리즘 자체 구현을 새로 복제하지 않고 공식 라이브러리를 사용했습니다. [XGBoost 문서](https://xgboost.readthedocs.io/en/stable/python/python_api.html) / [LightGBM 문서](https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.LGBMRegressor.html).

## 재현

```sh
1120gradpj/.venv/bin/python 1120gradpj/models/lightgbm/train.py
1120gradpj/.venv/bin/python 1120gradpj/scripts/report_tree_models_v3.py
```

후보별 설정·경고·Validation MAE는 candidate_results.json, 라이브러리·코드해시·원본해시는 experiment.json을 확인하세요. 저장 모델의 Validation/Test 예측 재현과 평가키 일치·미래정답변경 불변을 검사했습니다. 전체25,992개 예측과 월별·발행일별·예측거리별 지표, PNG/확대HTML은 로컬결과에 저장했습니다.

```json
[
  {
    "params": {
      "n_estimators": 1200,
      "learning_rate": 0.03,
      "num_leaves": 15,
      "max_depth": 5,
      "min_child_samples": 100,
      "subsample": 0.85,
      "subsample_freq": 1,
      "colsample_bytree": 0.85,
      "reg_lambda": 10,
      "reg_alpha": 0.1
    },
    "best_rounds": 187,
    "validation_mae": 10.428670578738119,
    "warnings": [
      "X does not have valid feature names, but LGBMRegressor was fitted with feature names"
    ]
  },
  {
    "params": {
      "n_estimators": 1200,
      "learning_rate": 0.03,
      "num_leaves": 31,
      "max_depth": 6,
      "min_child_samples": 150,
      "subsample": 0.85,
      "subsample_freq": 1,
      "colsample_bytree": 0.85,
      "reg_lambda": 20,
      "reg_alpha": 0.1
    },
    "best_rounds": 128,
    "validation_mae": 10.452328702100806,
    "warnings": [
      "X does not have valid feature names, but LGBMRegressor was fitted with feature names"
    ]
  },
  {
    "params": {
      "n_estimators": 1000,
      "learning_rate": 0.05,
      "num_leaves": 15,
      "max_depth": 5,
      "min_child_samples": 200,
      "subsample": 0.8,
      "subsample_freq": 1,
      "colsample_bytree": 0.8,
      "reg_lambda": 30,
      "reg_alpha": 1
    },
    "best_rounds": 101,
    "validation_mae": 10.56017538771342,
    "warnings": [
      "X does not have valid feature names, but LGBMRegressor was fitted with feature names"
    ]
  }
]
```

NumPy 행렬을 사용할 때 sklearn이 자동 생성된 feature names에 관한 경고를 출력했습니다. 공통83개 열 순서·개수와 저장 모델 예측 일치를 확인했으며, 이를 열 누락이나 성능 개선의 증거로 해석하지 않습니다.
