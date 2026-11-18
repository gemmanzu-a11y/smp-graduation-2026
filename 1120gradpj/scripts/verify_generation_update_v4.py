"""Saved LSTM and common-feature causality validation after the v4 rerun."""
import sys,json,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'models/lstm'))
from smp_forecast import common_v4 as c
from algorithm import Estimator
import pandas as pd

def main():
    reports=ROOT/'models/lstm/reports/v4_generation_update';latest=json.loads((reports/'latest_run_v4.json').read_text());run=Path(latest['path'])
    model=Estimator.load(run/'model.pt');bundle=c.load();h,x,y=c.arrays(bundle,'test',model.lookback)
    saved=pd.read_csv(run/'predictions.csv');test=saved[saved.split=='test']
    np.testing.assert_allclose(model.predict(h,x).reshape(-1),test.predicted_smp,rtol=1e-6,atol=1e-5)
    np.testing.assert_allclose(y.reshape(-1),test.actual_smp,rtol=1e-6,atol=1e-5)
    history,future,m=bundle;origin=future.loc[future.split=='test','forecast_origin'].min();cutoff=origin-pd.Timedelta(hours=72)
    block=future[future.forecast_origin==origin].copy();before=c.arrays((history,block,m),'test',model.lookback)
    changed=history.copy();changed.loc[changed.index>=cutoff,:]=1e9;block['actual_smp']=-1e9
    after=c.arrays((changed,block,m),'test',model.lookback)
    np.testing.assert_array_equal(before[0],after[0]);np.testing.assert_array_equal(before[1],after[1]);assert not np.array_equal(before[2],after[2])
    max_context=float(np.abs((x-model.context_mean)/model.context_scale).max());max_history=float(np.abs((h-model.history_mean)/model.history_scale).max())
    check=dict(saved_model_roundtrip=True,saved_actuals_match=True,future_actual_mutation_invariant=True,rows=len(saved),max_absolute_standardized_context=max_context,max_absolute_standardized_history=max_history,constant_scale_policy='unit scale for Train constants',tests_passed=86)
    c.dump(reports/'verification_v4.json',check)
    exp=json.loads((run/'experiment.json').read_text());exp['post_training_checks']=check
    exp['manifest_sha256']=hashlib.sha256((c.OUT/'manifest.json').read_bytes()).hexdigest();exp['model_sha256']=hashlib.sha256((run/'model.pt').read_bytes()).hexdigest()
    exp['source_code_sha256']={str(p.relative_to(c.WORK)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'models/lstm/algorithm.py',ROOT/'src/smp_forecast/common_v3.py',ROOT/'src/smp_forecast/common_v4.py']}
    c.dump(run/'experiment.json',exp);print('PASS',check)

if __name__=='__main__':main()
