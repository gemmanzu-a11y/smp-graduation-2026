from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'lstm/upgrades/upgrade_72h_20261119/scripts'))
from evaluate_upgrade import main
if __name__=='__main__':main()
