"""여러 트리에서 특성과 분할 임계값을 무작위로 선택하고 예측을 평균합니다. Random Forest와 달리 기본적으로 부트스트랩을 사용하지 않습니다."""
from sklearn.ensemble import ExtraTreesRegressor

def create(params, seed=42, jobs=4):
    return ExtraTreesRegressor(random_state=seed, n_jobs=jobs, **params)
