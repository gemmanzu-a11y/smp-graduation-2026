"""Scan project text for actual runtime credentials without printing any secret."""
import os,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];secrets=[os.environ.get(k) for k in ('KPX_SERVICE_KEY','KMA_APIHUB_AUTH_KEY')];secrets=[s.encode() for s in secrets if s]
if not secrets:raise SystemExit('Set credentials in process environment to run exact secret scan; no credential values are printed.')
violations=[]
for path in root.rglob('*'):
 if not path.is_file() or '.venv' in path.parts or '__pycache__' in path.parts:continue
 if any(s in path.read_bytes() for s in secrets):violations.append(str(path.relative_to(root)))
print('Exact-key scan:', 'PASS' if not violations else 'FAIL', 'matched file count:',len(violations))
if violations:print('\n'.join(violations));raise SystemExit(1)
