# lightgbm

히스토그램 기반 트리를 leaf-wise로 확장하는 그래디언트 부스팅입니다. num_leaves, 최소 leaf 표본 수와 L2 규제로 과적합을 제한합니다.

프로젝트 루트에서 `.venv/bin/python models/lightgbm/train.py`로 실행합니다. 공통 설정은 `configs/experiment.json`, 입력은 `data/processed/training_dataset.npz`입니다. 공통 입력·분할·평가를 사용하며 이 폴더의 `algorithm.py`가 추정기를 정의합니다. 결과는 `artifacts/`에 저장합니다.
