from pathlib import Path
import hashlib,json,os,sys,unittest
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];MODELS=ROOT.parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from run_experiment import gate

class SavedDesignTest(unittest.TestCase):
    def test_selection_uses_tuning_rank_only(self):
        records=json.loads((ROOT/'outputs/metrics/tuning_candidates.json').read_text());protocol=json.loads((ROOT/'config/protocol_before_training.json').read_text());selected=json.loads((ROOT/'config/selection_before_confirmation.json').read_text())
        self.assertEqual([r['params'] for r in records],protocol['candidates'])
        best=min(records,key=lambda r:(r['blending']['mae'],r['blending']['alpha']))
        self.assertEqual(best['params'],selected['params']);self.assertEqual(best['best_epoch'],selected['best_epoch'])
    def test_confirmation_gate_recomputed(self):
        candidate=pd.read_csv(ROOT/'outputs/predictions/confirmation_candidate.csv.gz');candidate.target_timestamp=pd.to_datetime(candidate.target_timestamp)
        reference=pd.read_csv(ROOT.parent/'upgrade_72h_20261119/outputs/predictions/rolling_oof.csv.gz');reference.target_timestamp=pd.to_datetime(reference.target_timestamp);reference=reference[reference.fold==3]
        decision=gate(candidate,reference);policy=json.loads((ROOT/'config/final_policy_before_test.json').read_text())
        self.assertEqual(decision['accepted'],policy['confirmation']['accepted']);self.assertFalse(policy['test_used_for_choice'])
        self.assertAlmostEqual(decision['candidate_mae'],policy['confirmation']['candidate_mae'],places=8)
    def test_all_test_rows_identical_and_no_failed_candidate_adoption(self):
        f=pd.read_csv(ROOT/'outputs/predictions/test_predictions.csv.gz');scores=pd.read_csv(ROOT/'outputs/metrics/test_metrics.csv');reference=None
        for name,z in f.groupby('experiment_id'):
            keys=z[['forecast_origin','target_timestamp','horizon','actual_smp']].reset_index(drop=True)
            self.assertEqual(len(keys),13104);self.assertFalse(keys.duplicated(['forecast_origin','target_timestamp']).any())
            if reference is None:reference=keys
            else:pd.testing.assert_frame_equal(reference,keys)
            score=scores[scores.experiment_id==name].mae.iloc[0];self.assertAlmostEqual(float(np.abs(z.predicted_smp-z.actual_smp).mean()),score,places=8)
        policy=json.loads((ROOT/'config/final_policy_before_test.json').read_text())
        if not policy['confirmation']['accepted']:
            self.assertEqual(policy['adopt'],'previous_lstm_upgrade')
            np.testing.assert_array_equal(f[f.experiment_id=='adopted_lstm'].predicted_smp.to_numpy(),f[f.experiment_id=='previous_lstm'].predicted_smp.to_numpy())
    def test_originals_protected(self):
        source=os.environ.get('SMP_LEGIT_SOURCE_PROJECT')
        if not source:self.skipTest('Set SMP_LEGIT_SOURCE_PROJECT for readonly source audit')
        hashes=json.loads((ROOT/'config/protected_hashes.json').read_text())
        for name,digest in hashes.items():
            p=MODELS/name.removeprefix('prior_upgrade/') if name.startswith('prior_upgrade/') else Path(source).resolve().parent/name
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),digest)

if __name__=='__main__':unittest.main()
