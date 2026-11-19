# Train+Validation 재학습

원래 선택된 설정을 유지하고 n_estimators만 검증으로 확정된 best_rounds=187로 고정했습니다. 추가 표준화는 없으며 공통 결측 대체값은 기존 Train 기준을 유지합니다. 최종 적합에는 eval_set과 early stopping을 사용하지 않았습니다. E2~E4의 Validation 값은 학습내 오차입니다.

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
  "validation_mae": 10.428670578738119
}
