"""SARIMAX v3 conditional estimation and fixed-cutoff state safety."""
import importlib.util,sys,unittest
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('sarimax_algorithm_v3',ROOT/'models/sarimax/algorithm_v3.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class ConditionalSARIMAXTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng=np.random.default_rng(42);cls.x=rng.normal(size=(400,3));cls.x[:,2]=0
        cls.y=100+5*cls.x[:,0]+rng.normal(size=400)
        cls.model=mod.Estimator((1,0,0),(0,0,0,0),100).fit(cls.y,cls.x)
    def test_all_columns_preserved_constant_scale_one(self):
        self.assertEqual(len(self.model.beta),3);self.assertEqual(self.model.scale[2],1)
        self.assertEqual(self.model.rank,2);np.testing.assert_allclose(self.model.mean,self.x.mean(0))
    def test_fixed_cutoff_bridge_and_future_actual_invariance(self):
        origin=pd.Timestamp('2025-07-01 23:00',tz='Asia/Seoul');cutoff=origin-pd.Timedelta(hours=72)
        self.model.reset(self.y,self.x,cutoff-pd.Timedelta(hours=1))
        future=np.zeros((145,3));pred,ci,bridge=self.model.predict(future,origin,cutoff)
        self.assertEqual(bridge,73);self.assertEqual(len(pred),72);self.assertEqual(ci.shape,(72,2))
        self.assertTrue(np.isfinite(pred).all())
        with self.assertRaisesRegex(ValueError,'Incorrect fixed origin cutoff'):self.model.predict(future,origin,origin)
        with self.assertRaisesRegex(ValueError,'Unreleased interval'):
            self.model.update([100],np.zeros((1,3)),[cutoff],cutoff)
    def test_save_load_identical_fixed_parameters(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'model.npz';self.model.save(path);restored=mod.Estimator.load(path)
            np.testing.assert_array_equal(restored.params,self.model.params)
            np.testing.assert_array_equal(restored.scale,self.model.scale)

if __name__=='__main__':unittest.main()
