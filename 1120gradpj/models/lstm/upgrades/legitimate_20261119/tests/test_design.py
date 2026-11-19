from pathlib import Path
import sys,tempfile,unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from estimator import Estimator
from run_experiment import gate,candidates

class DesignTest(unittest.TestCase):
    def test_predeclared_small_grid(self):
        grid=candidates();self.assertEqual(len(grid),6);self.assertEqual(len({c['id'] for c in grid}),6)
    def test_confirmation_gate_rejects_bad_month_and_test_period(self):
        dates=pd.to_datetime(['2025-05-01','2025-06-01']).tz_localize('Asia/Seoul');ref=pd.DataFrame(dict(target_timestamp=dates,actual_smp=100.,predicted_smp=[110.,110.]))
        candidate=ref.copy();candidate.predicted_smp=[100.,111.];self.assertFalse(gate(candidate,ref)['accepted'])
        candidate.predicted_smp=[105.,105.];self.assertTrue(gate(candidate,ref)['accepted'])
        candidate.target_timestamp=candidate.target_timestamp+pd.Timedelta(days=62)
        with self.assertRaises(ValueError):gate(candidate,ref)
    def test_residual_target_train_scalers_and_serialization(self):
        rng=np.random.default_rng(42);h=rng.normal(size=(8,4,3)).astype('float32');x=rng.normal(size=(8,72,2)).astype('float32');h[:,:,2]=1.;b=np.full((8,72),100.);y=b+x[:,:,0]
        params=dict(id='synthetic',target='weekly_residual',loss='huber',hidden=4,lr=.001,lookback=4,max_epochs=2,patience=1)
        m=Estimator(params).fit(h,x,y,b,epochs=2)
        np.testing.assert_allclose(m.hm,h.mean((0,1)));self.assertEqual(m.hs[2],1.)
        self.assertAlmostEqual(m.ym,float((y-b).mean()));self.assertEqual(m.predict(h,x,b).shape,(8,72))
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.pt';m.save(p);loaded=Estimator.load(p);np.testing.assert_allclose(m.predict(h,x,b),loaded.predict(h,x,b),rtol=1e-6,atol=1e-5)
    def test_predict_does_not_accept_future_labels(self):
        import inspect
        self.assertEqual(list(inspect.signature(Estimator.predict).parameters),['self','h','x','baseline'])

if __name__=='__main__':unittest.main()
