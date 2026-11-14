"""손실의 그래디언트와 헤시안을 활용해 규제된 회귀트리를 순차적으로 추가합니다. CPU hist 방식과 열/행 샘플링을 사용합니다."""
from xgboost import XGBRegressor

def create(params, seed=42, jobs=4):
    return XGBRegressor(random_state=seed, n_jobs=jobs, objective="reg:squarederror", **params)
