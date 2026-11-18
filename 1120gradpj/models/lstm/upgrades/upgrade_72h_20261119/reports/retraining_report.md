# Train+Validation 재학습

{
  "params": {
    "lookback": 48,
    "hidden_size": 32,
    "layers": 1,
    "dropout": 0.0,
    "learning_rate": 0.001,
    "batch_size": 32,
    "epochs": 100,
    "patience": 10
  },
  "best_epoch": 22,
  "validation_mae": 12.881725311279297
}

계수/가중치는2023~2025년상반기표본으로적합했습니다. 대체통계는원래Train기준을유지하며표준화는재학습표본만사용했습니다. E2~E4Validation은학습내오차로구분했습니다.
