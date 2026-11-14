# random_forest

부트스트랩 표본과 무작위 특성 부분집합으로 다수의 회귀트리를 학습하고 예측을 평균합니다.

프로젝트 루트에서 `.venv/bin/python models/random_forest/train.py`로 실행합니다. 공통 설정은 `configs/experiment.json`, 입력은 `data/processed/training_dataset.npz`입니다. 공통 입력·분할·평가를 사용하며 이 폴더의 `algorithm.py`가 추정기를 정의합니다. 결과는 `artifacts/`에 저장합니다.
