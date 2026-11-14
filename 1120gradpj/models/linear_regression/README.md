# linear_regression

표준화된 이력·달력 특성의 선형 결합을 최소제곱법으로 적합합니다. 일반 선형회귀이며 Ridge/Lasso로 바꾸지 않았습니다.

프로젝트 루트에서 `.venv/bin/python models/linear_regression/train.py`로 실행합니다. 공통 설정은 `configs/experiment.json`, 입력은 `data/processed/training_dataset.npz`입니다. 공통 입력·분할·평가를 사용하며 이 폴더의 `algorithm.py`가 추정기를 정의합니다. 결과는 `artifacts/`에 저장합니다.
