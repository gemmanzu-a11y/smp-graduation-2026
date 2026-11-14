# extra_trees

여러 트리에서 특성과 분할 임계값을 무작위로 선택하고 예측을 평균합니다. Random Forest와 달리 기본적으로 부트스트랩을 사용하지 않습니다.

프로젝트 루트에서 `.venv/bin/python models/extra_trees/train.py`로 실행합니다. 공통 설정은 `configs/experiment.json`, 입력은 `data/processed/training_dataset.npz`입니다. 공통 입력·분할·평가를 사용하며 이 폴더의 `algorithm.py`가 추정기를 정의합니다. 결과는 `artifacts/`에 저장합니다.
