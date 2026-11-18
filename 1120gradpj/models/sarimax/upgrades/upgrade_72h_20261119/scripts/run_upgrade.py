from pathlib import Path
import sys
HERE=Path(__file__).resolve()
sys.path.insert(0,str(HERE.parents[4]/'lstm/upgrades/upgrade_72h_20261119/scripts'))
from protocol import run
if __name__=='__main__':run('sarimax',HERE.parents[1])
