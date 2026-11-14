"""부트스트랩 표본과 무작위 특성 부분집합으로 다수의 회귀트리를 학습하고 예측을 평균합니다."""
from sklearn.ensemble import RandomForestRegressor

def create(params, seed=42, jobs=4):
    return RandomForestRegressor(random_state=seed, n_jobs=jobs, **params)
