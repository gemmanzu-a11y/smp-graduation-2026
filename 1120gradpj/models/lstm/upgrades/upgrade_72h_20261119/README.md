# LSTM 72시간 업그레이드

발전량 보완 전 공통 v3를 읽기 전용으로 재사용했습니다. 기존 모델과 다른 모델의 결과는 변경하지 않았습니다.

최종 채택은 E3이며, **재학습 모델 0.5 + 주간 기준선 0.5**입니다. 편향 보정은 검증에서 채택되지 않아 적용하지 않았습니다.

하반기 재평가: MAE **11.2630원/kWh**, RMSE 15.4813, R² 0.5495.

[최종 보고서](reports/final_upgrade_report.md)에서 단계별 결과, 연구 조건과 평가 한계를 확인하세요. 전체 예측은 outputs/predictions의 csv.gz, 새 모델은 models에 있습니다.

재현에는 기존 공통 v3 데이터와 원본 모델이 있는 로컬 프로젝트가 필요합니다. 저장소 clone만으로 원본을 새로 수집하지 않습니다.

```sh
python scripts/run_upgrade.py --source-project /path/to/1120gradpj
python scripts/evaluate_upgrade.py --model lstm --source-project /path/to/1120gradpj
```

기존 출력은 덮어쓰지 않습니다. 재실행은 새 업그레이드 출력 위치에서 진행하세요. SARIMAX는 LSTM 업그레이드의 공통 프로토콜을 재사용합니다.

실험 코드·최초 결과 커밋: `91456ee`. 브랜치: `codex/lstm-sarimax-72h-upgrade-20261119`.
