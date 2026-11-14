"""Run each requested algorithm as an isolated process, continuing only after recording failures."""
import sys,subprocess,json,os,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from smp_forecast.http import write_json,now
models=sys.argv[1:] or ['linear_regression','hgb','lightgbm','extra_trees','random_forest','xgboost','lstm'];status=[]
for name in models:
 if name not in ['linear_regression','hgb','lightgbm','extra_trees','random_forest','xgboost','lstm']:raise SystemExit('Unknown model '+name)
 env={**os.environ,'OMP_NUM_THREADS':'4','OPENBLAS_NUM_THREADS':'4','MPLCONFIGDIR':str(ROOT/'data/matplotlib')};print('START',name,flush=True);p=subprocess.run([sys.executable,str(ROOT/'models'/name/'train.py')],cwd=ROOT,env=env);status.append(dict(model=name,exit_code=p.returncode,finished_at=now()));write_json(ROOT/'reports/run_status.json',status)
subprocess.run([sys.executable,str(ROOT/'scripts/summarize.py')],cwd=ROOT)
raise SystemExit(1 if any(r['exit_code'] for r in status) else 0)
