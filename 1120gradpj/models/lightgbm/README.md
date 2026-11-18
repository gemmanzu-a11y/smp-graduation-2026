# lightgbm

## 현재 실행: 발전량 보완 전 공통 v3

`train.py`는 LSTM·SARIMAX와 같은 공통v3 입력83개를 사용합니다. 결과는 `reports/v3_common/final_evaluation_report.md`, 현재 실행 위치는 `CURRENT_RUN.json`입니다. 기존 실행기는 `train_legacy.py`로 보존했습니다.

```sh
1120gradpj/.venv/bin/python 1120gradpj/models/lightgbm/train.py
1120gradpj/.venv/bin/python 1120gradpj/scripts/report_tree_models_v3.py
```

아래 기존 설명·과거 산출물은 이전 실험 기록이며 현재 공통v3 결과와 구분합니다.

히스토그램 기반 트리를 leaf-wise로 확장하는 그래디언트 부스팅입니다. num_leaves, 최소 leaf 표본 수와 L2 규제로 과적합을 제한합니다.

프로젝트 루트에서 `.venv/bin/python models/lightgbm/train.py`로 실행합니다. 공통 설정은 `configs/experiment.json`, 입력은 `data/processed/training_dataset.npz`입니다. 공통 입력·분할·평가를 사용하며 이 폴더의 `algorithm.py`가 추정기를 정의합니다. 결과는 `artifacts/`에 저장합니다.
