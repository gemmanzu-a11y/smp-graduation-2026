"""히스토그램 기반 트리를 leaf-wise로 확장하는 그래디언트 부스팅입니다. num_leaves, 최소 leaf 표본 수와 L2 규제로 과적합을 제한합니다."""
from lightgbm import LGBMRegressor

def create(params, seed=42, jobs=4):
    return LGBMRegressor(random_state=seed, n_jobs=jobs, deterministic=True, force_col_wise=True, **params)
