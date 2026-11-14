"""표준화된 이력·달력 특성의 선형 결합을 최소제곱법으로 적합합니다. 일반 선형회귀이며 Ridge/Lasso로 바꾸지 않았습니다."""
from sklearn.linear_model import LinearRegression

def create(params, seed=42, jobs=4):
    return LinearRegression(n_jobs=jobs, **params)
