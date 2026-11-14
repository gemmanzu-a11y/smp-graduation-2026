"""Only the four team models; every run requires the full shared data contract."""
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
MODELS=['sarimax','lstm','xgboost','lightgbm']

def main():
    names=sys.argv[1:] or MODELS
    if any(n not in MODELS for n in names):raise SystemExit('Allowed models: '+', '.join(MODELS))
    gate=subprocess.run([sys.executable,str(ROOT/'models/sarimax/train.py'),'--audit-only'],cwd=ROOT)
    if gate.returncode:raise SystemExit(gate.returncode)
    # The retained ML/DL runners are previous partial-input experiments, not the new contract.
    if any(n!='sarimax' for n in names):
        raise SystemExit('공통 데이터 게이트는 통과했지만 LSTM/XGBoost/LightGBM의 새 공통 입력 연결은 별도 작업입니다. 기존 부분 입력 결과로 대체하지 않습니다. SARIMAX만 실행하려면 run_all.py sarimax')
    raise SystemExit(subprocess.run([sys.executable,str(ROOT/'models/sarimax/train.py')],cwd=ROOT,env={**os.environ,'OMP_NUM_THREADS':'4'}).returncode)

if __name__=='__main__':main()
