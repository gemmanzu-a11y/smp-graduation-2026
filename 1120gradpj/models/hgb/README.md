# hgb

특성을 히스토그램 구간으로 나눈 뒤 결정트리를 순차적으로 더해 앞선 오차를 줄입니다. 무작위 내부 validation 분할은 끄고 공통 시계열 분할만 사용합니다.

프로젝트 루트에서 `.venv/bin/python models/hgb/train.py`로 실행합니다. 공통 설정은 `configs/experiment.json`, 입력은 `data/processed/training_dataset.npz`입니다. 공통 입력·분할·평가를 사용하며 이 폴더의 `algorithm.py`가 추정기를 정의합니다. 결과는 `artifacts/`에 저장합니다.
