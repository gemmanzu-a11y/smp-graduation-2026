"""Verify the saved real model, exact common evaluation keys and causal state."""
import json,sys
from pathlib import Path
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
from train import contract,prepare,evaluate
from algorithm_v3 import Estimator


def main():
    latest=json.loads((HERE/'reports/latest_run_v3.json').read_text());run=Path(latest['path'])
    bundle=contract.load();hourly,features,_=prepare(bundle)
    saved=pd.read_csv(run/'predictions.csv');keys=['split','forecast_origin','target_timestamp','horizon']
    for c in ['forecast_origin','target_timestamp','observed_cutoff']:saved[c]=contract.times(saved[c])
    assert len(saved)==25992;assert not saved.duplicated(keys).any();assert saved.bridge_hours.eq(73).all()
    assert (saved.observed_cutoff==saved.forecast_origin-pd.Timedelta(hours=72)).all()
    assert np.isfinite(saved[['predicted_smp','lower_95','upper_95']].to_numpy()).all()
    expected=pd.read_csv(contract.OUT/'evaluation_targets.csv');expected=expected[expected.split.isin(['validation','test'])]
    for c in ['forecast_origin','target_timestamp']:expected[c]=contract.times(expected[c])
    a=saved[keys].sort_values(keys).reset_index(drop=True);b=expected[keys].sort_values(keys).reset_index(drop=True)
    pd.testing.assert_frame_equal(a,b)
    lstm=Path(json.loads((HERE.parent/'lstm/reports/latest_run_v3.json').read_text())['path'])
    lf=pd.read_csv(lstm/'predictions.csv')
    for c in ['forecast_origin','target_timestamp']:lf[c]=contract.times(lf[c])
    pd.testing.assert_frame_equal(a,lf[keys].sort_values(keys).reset_index(drop=True))
    first=bundle[1].loc[bundle[1].split=='test','forecast_origin'].min()
    block=bundle[1][bundle[1].forecast_origin==first].copy();small=(bundle[0],block,bundle[2])
    model=Estimator.load(run/'model.npz');original=evaluate(model,small,hourly,features,'test')
    reference=saved[(saved.split=='test')&(saved.forecast_origin==first)]
    np.testing.assert_allclose(original.predicted_smp,reference.predicted_smp,rtol=1e-10,atol=1e-8)
    cutoff=first-pd.Timedelta(hours=72);changed=hourly.copy();changed.loc[changed.index>=cutoff,'actual_smp']=999999999
    block['actual_smp']=-999999999
    again=evaluate(Estimator.load(run/'model.npz'),(bundle[0],block,bundle[2]),changed,features,'test')
    np.testing.assert_array_equal(original.predicted_smp.to_numpy(),again.predicted_smp.to_numpy())
    assert not np.array_equal(original.actual_smp.to_numpy(),again.actual_smp.to_numpy())
    checks=dict(saved_model_reproduces_predictions=True,all_25992_keys_match_common_targets=True,all_evaluation_keys_match_lstm=True,future_actual_mutation_invariant=True,all_bridges_73_hours=True,all_predictions_finite=True)
    contract.dump(HERE/'reports/verification_v3.json',checks)
    print('PASS',checks)

if __name__=='__main__':main()
