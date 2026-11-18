# LSTM — 공통 v3 72시간 육지 SMP 연구

최신 실행기는 `train.py`, 이전 엄격 차단 v2 실행기는 `train_v2.py`로 보존했습니다. 공통 전처리기는 `src/smp_forecast/common_v3.py`에 한 번만 구현했습니다. 모델별 수집기를 만들지 않았습니다.

```sh
# 최초 실행: 팀 지정 브랜치의 고정 커밋 원본 104개 다운로드
1120gradpj/.venv/bin/python 1120gradpj/scripts/fetch_team_training_snapshot.py
# 기존 EPSIS 수요·SMP 및 shared_datasets/kma_midrange 원본도 필요
PYTHONPATH=1120gradpj/src 1120gradpj/.venv/bin/python -m smp_forecast.common_v3
1120gradpj/.venv/bin/python 1120gradpj/scripts/audit_common_v3.py
1120gradpj/.venv/bin/python 1120gradpj/models/lstm/train.py --audit-only
1120gradpj/.venv/bin/python 1120gradpj/models/lstm/train.py
```

필요 패키지는 `1120gradpj/requirements.txt`에 있습니다. 이미 수집된 원본만 사용하므로 이번 학습에는 API 키가 필요하지 않습니다. 기존 EPSIS 원본은 새로 수집하거나 전국 수요로 대체하지 않습니다.

- 과거 48/168시간을 인코딩하고 미래 달력·조건부 연료·발표 완료 중기예보를 결합해 72시간을 직접 출력합니다.
- 모든 실측 및 과거 SMP는 origin−72시간에 종료된 구간까지만 사용합니다.
- Validation MAE로 후보 3개와 epoch를 선택하며 Final Test로 설정을 바꾸지 않습니다.
- 결과는 `outputs/<dataset_version>/<run>/`, 최신 위치는 `reports/latest_run_v3.json`입니다.
- 데이터 검사: `reports/data_collection_report_v3.md`, 성능: `reports/final_evaluation_report_v3.md`.
- 기존 v2 보고서가 BLOCKED라고 표시하는 것은 과거 실행 상태입니다. 현재 v3 상태와 구분합니다.

동월 LNG를 제공한 조건부 사후 실험이며, 실측 공개시각이 검증된 운영 실험이 아닙니다. 발전량의 큰 결측도 대체값·표시 변수를 넣은 채 유지합니다. 정확한 결측률과 성능의 한계는 보고서를 확인하세요.
