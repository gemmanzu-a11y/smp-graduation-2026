"""Check the current common contract, not the obsolete release-date-only gate."""
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
raise SystemExit(subprocess.run([sys.executable,str(ROOT/'models/sarimax/train.py'),'--audit-only'],cwd=ROOT).returncode)
