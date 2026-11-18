"""Train xgboost on the frozen, pre-generation-supplement v3 matrix."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from smp_forecast.tree_models_v3 import run
if __name__=='__main__':run('xgboost')
