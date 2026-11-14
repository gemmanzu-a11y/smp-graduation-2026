"""특성을 히스토그램 구간으로 나눈 뒤 결정트리를 순차적으로 더해 앞선 오차를 줄입니다. 무작위 내부 validation 분할은 끄고 공통 시계열 분할만 사용합니다."""
from sklearn.ensemble import HistGradientBoostingRegressor

def create(params, seed=42, jobs=4):
    return HistGradientBoostingRegressor(random_state=seed, early_stopping=False, **params)
