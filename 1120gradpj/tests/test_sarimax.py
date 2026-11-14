"""Technical checks with synthetic series only: not an SMP performance experiment."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parents[1]/'models/sarimax'
def load(name):
    spec=importlib.util.spec_from_file_location('sarimax_'+name,HERE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
algorithm, fuel, contract=load('algorithm'), load('fuel'), load('contract')

class SARIMAXTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng=np.random.default_rng(42)
        cls.index=pd.date_range('2024-01-01',periods=24*14,freq='h',tz='Asia/Seoul')
        cls.x=pd.DataFrame({'weather':rng.normal(size=len(cls.index))},index=cls.index)
        cls.y=pd.Series(100+4*cls.x.weather+8*np.sin(np.arange(len(cls.index))*2*np.pi/24)+rng.normal(size=len(cls.index)),index=cls.index)
        cls.model=algorithm.Estimator(order=(1,0,0),seasonal_order=(1,0,0,24),maxiter=200).fit(cls.y,cls.x)
        cls.origin=cls.index[-1]
        cls.future=pd.DataFrame({'weather':np.zeros(72)},index=pd.date_range(cls.origin+pd.Timedelta(hours=1),periods=72,freq='h'))

    def clone(self):
        import copy
        return copy.deepcopy(self.model)

    def test_exact_72h(self):
        f=self.model.predict72(self.future,self.origin)
        self.assertEqual(len(f),72);self.assertTrue(np.isfinite(f.to_numpy()).all())
        self.assertEqual(f.index[0],self.origin+pd.Timedelta(hours=1))

    def test_saved_model_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            self.model.save(d);restored=algorithm.Estimator.load(d)
            np.testing.assert_allclose(restored.predict72(self.future,self.origin),self.model.predict72(self.future,self.origin))

    def test_future_actual_rejected(self):
        idx=self.future.index[:24]
        with self.assertRaisesRegex(ValueError,'Future actuals'):
            self.clone().update(pd.Series(np.ones(24),index=idx),self.future.iloc[:24],self.origin)

    def test_state_update_does_not_refit(self):
        model=self.clone();before=np.asarray(model.result.params).copy()
        idx=self.future.index[:24]
        model.update(pd.Series(np.ones(24)*100,index=idx),self.future.iloc[:24],idx[-1])
        np.testing.assert_allclose(model.result.params,before)
        np.testing.assert_allclose(model.mean,self.model.mean)
        self.assertEqual(model.last_timestamp,idx[-1])

    def test_wrong_forecast_window_rejected(self):
        with self.assertRaises(ValueError):self.model.predict72(self.future.iloc[1:],self.origin)

    def test_nan_cannot_be_imputed_silently(self):
        bad=self.future.copy();bad.iloc[0,0]=np.nan
        with self.assertRaises(ValueError):self.model.predict72(bad,self.origin)

    def test_unknown_feature_rejected(self):
        with self.assertRaises(ValueError):self.model.predict72(self.future.rename(columns={'weather':'other'}),self.origin)

    def test_month_boundary_and_demo_fuel(self):
        m=pd.DataFrame({'month':['2024-01','2024-02','2026-10'],'domestic_lng_cost_krw_kwh':[100.,200.,150.]})
        targets=pd.date_range('2024-01-31 23:00',periods=3,freq='h',tz='Asia/Seoul')
        origin=pd.Timestamp('2024-01-30 23:00',tz='Asia/Seoul')
        np.testing.assert_array_equal(fuel.fuel_for_targets(m,targets,origin),[100,200,200])
        targets=pd.date_range('2026-11-20',periods=72,freq='h',tz='Asia/Seoul')
        demo=fuel.fuel_for_targets(m,targets,pd.Timestamp('2026-11-19 23:00',tz='Asia/Seoul'),'november_demo')
        self.assertTrue((demo==150).all())

    def test_missing_shared_data_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            issues,bundle=contract.inspect_bundle(d,{})
            self.assertTrue(issues);self.assertIsNone(bundle)

    def test_split_boundary_purge(self):
        dates=contract.origins('2025-07-01','2025-12-31')
        self.assertEqual(len(dates),182)
        self.assertEqual(dates[0],pd.Timestamp('2025-06-30 23:00',tz='Asia/Seoul'))
        self.assertEqual(dates[-1]+pd.Timedelta(hours=72),pd.Timestamp('2025-12-31 23:00',tz='Asia/Seoul'))

    def test_naive_timestamps_rejected(self):
        with self.assertRaises(ValueError):contract.parse_time(pd.Series(['2025-01-01 00:00:00']))

if __name__=='__main__':unittest.main()
