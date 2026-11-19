# XGBOOST 72시간 업그레이드

발전량 보완 전 공통 v3를 읽기 전용으로 재사용했습니다. 기존 모델과 완료된 LSTM·SARIMAX 업그레이드는 변경하지 않았습니다.

최종 채택은 E3이며, **재학습 모델 0.7 + 주간 기준선 0.3**입니다. 편향 보정은 검증에서 채택되지 않아 적용하지 않았습니다.

하반기 재평가: MAE **14.4095원/kWh**, RMSE 18.3090, R² 0.3699.

[최종 보고서](reports/final_upgrade_report.md)에서 단계별 결과와 연구 한계를 확인하세요. 전체 예측은 outputs/predictions/*.csv.gz, 새 모델은 models/에 있습니다. 고정된 트리 수는 231개입니다.

재현에는 기존 공통 v3 자료와 원본 모델이 있는 로컬 프로젝트 및 같은 브랜치의 LSTM 공통 선택 스크립트가 필요합니다. 기존 출력은 덮어쓰지 않습니다.

```sh
python scripts/run_upgrade.py --source-project /path/to/1120gradpj
python scripts/evaluate_upgrade.py --model xgboost --source-project /path/to/1120gradpj
```

Git 브랜치: codex/xgboost-lightgbm-72h-upgrade-20261119.

기존 결과를 보존하며 재현하려면 빈 새 출력 위치를 지정하세요.

```sh
python scripts/run_upgrade.py --source-project /path/to/1120gradpj --output-dir /tmp/new-xgboost-run
python scripts/evaluate_upgrade.py --model xgboost --source-project /path/to/1120gradpj --upgrade-dir /tmp/new-xgboost-run
```
