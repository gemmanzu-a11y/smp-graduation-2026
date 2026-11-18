from pathlib import Path
import hashlib,json,os,unittest
import numpy as np
import pandas as pd
MODELS=Path(__file__).resolve().parents[4]

class SavedUpgradeTest(unittest.TestCase):
    def test_same_target_keys_and_metrics_from_saved_predictions(self):
        reference=None
        for name in ['lstm','sarimax']:
            root=MODELS/name/'upgrades/upgrade_72h_20261119'
            frame=pd.read_csv(root/'outputs/predictions/final_test_predictions.csv.gz')
            metrics=pd.read_csv(root/'outputs/metrics/experiment_comparison.csv')
            for exp,z in frame.groupby('experiment_id'):
                keys=z[['forecast_origin','target_timestamp','horizon']].reset_index(drop=True)
                self.assertEqual(len(z),13104);self.assertFalse(keys.duplicated().any())
                if reference is None:reference=keys
                else:pd.testing.assert_frame_equal(reference,keys)
                expected=metrics[(metrics.split=='test')&(metrics.experiment_id==exp)].mae.iloc[0]
                self.assertAlmostEqual(float(np.abs(z.predicted_smp-z.actual_smp).mean()),expected,places=8)
    def test_recorded_policy_matches_final_predictions(self):
        for name in ['lstm','sarimax']:
            root=MODELS/name/'upgrades/upgrade_72h_20261119';artifact=json.loads((root/'config/final_artifact.json').read_text())
            self.assertFalse(json.loads((root/'config/selection_before_test.json').read_text())['test_metric_used'])
            f=pd.read_csv(root/'outputs/predictions/final_test_predictions.csv.gz')
            rule=json.loads((root/'config/selection_before_test.json').read_text())['blending']
            e2=f[f.experiment_id=='E2'];e3=f[f.experiment_id=='E3']
            expected=rule['alpha']*e2.predicted_smp.to_numpy()+(1-rule['alpha'])*e3.baseline_prediction.to_numpy()
            np.testing.assert_allclose(e3.predicted_smp,expected,rtol=1e-10,atol=1e-8)
            a=f[f.experiment_id=='E3'].predicted_smp.to_numpy();b=f[f.experiment_id=='E4'].predicted_smp.to_numpy()
            self.assertEqual(json.loads((root/'config/selection_before_test.json').read_text())['correction']['mode'],'none')
            np.testing.assert_array_equal(a,b)
    def test_original_sources_and_other_models_unchanged(self):
        source=os.environ.get('SMP_UPGRADE_SOURCE_PROJECT')
        if not source:self.skipTest('Set SMP_UPGRADE_SOURCE_PROJECT to audit local readonly inputs')
        parent=Path(source).resolve().parent
        for name in ['lstm','sarimax']:
            root=MODELS/name/'upgrades/upgrade_72h_20261119';hashes=json.loads((root/'config/protected_source_hashes.json').read_text())
            for path,digest in hashes.items():self.assertEqual(hashlib.sha256((parent/path).read_bytes()).hexdigest(),digest)
    def test_refit_validation_is_explicitly_in_sample(self):
        for name in ['lstm','sarimax']:
            root=MODELS/name/'upgrades/upgrade_72h_20261119';f=pd.read_csv(root/'outputs/metrics/experiment_comparison.csv')
            rows=f[(f.split=='validation')&f.experiment_id.isin(['E2','E3','E4'])]
            self.assertTrue(rows.evaluation_role.str.contains('in-sample').all())

if __name__=='__main__':unittest.main()
