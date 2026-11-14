"""Manual daily job entry point. Scheduler registration is deliberately separate."""
import sys,subprocess
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
root=Path(__file__).resolve().parents[1]
current=datetime.now(ZoneInfo('Asia/Seoul'))
if current.hour<23:raise SystemExit('23시 기준 일일 실행은 KST 23시 이후에 실행하세요. 과거 시점 추론은 predict.py --origin을 사용합니다.')
raise SystemExit('새 공통 입력 연결·학습 완료 전에는 기존 부분 입력 모델의 일일 실행을 중단합니다.')
# Keep credentials in environment; no command-line secrets. Cached history is preserved.
subprocess.run([sys.executable,str(root/'scripts/collect_data.py'),'--end',current.date().isoformat()],check=True,cwd=root)
subprocess.run([sys.executable,str(root/'scripts/build_dataset.py')],check=True,cwd=root)
for name in ['lstm','lightgbm','xgboost']:
 subprocess.run([sys.executable,str(root/'scripts/predict.py'),'--model',name],check=True,cwd=root)
