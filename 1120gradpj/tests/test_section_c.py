"""As-of selection tests and regression checks on actually collected fuel inputs."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/processed/section_c'
spec=importlib.util.spec_from_file_location('collect_c',ROOT/'scripts/collect_section_c.py')
collector=importlib.util.module_from_spec(spec);spec.loader.exec_module(collector)

class VintageSelectionTest(unittest.TestCase):
    def history(self):
        return pd.DataFrame([
            dict(date='2025-01-01',realtime_start='2025-01-02',realtime_end='2025-01-05',value='10'),
            dict(date='2025-01-01',realtime_start='2025-01-06',realtime_end='2025-01-20',value='20'),
            dict(date='2025-01-10',realtime_start='2025-01-12',realtime_end='2025-01-20',value='30'),
            dict(date='2025-02-01',realtime_start='2025-01-02',realtime_end='2025-01-20',value='99')])

    def test_cannot_use_later_revision(self):
        self.assertEqual(collector.select_asof(self.history(),'2025-01-05')['value'],10)
        self.assertEqual(collector.select_asof(self.history(),'2025-01-06')['value'],20)

    def test_new_period_not_used_before_its_release(self):
        self.assertEqual(collector.select_asof(self.history(),'2025-01-11')['observation_date'],'2025-01-01')
        self.assertEqual(collector.select_asof(self.history(),'2025-01-12')['observation_date'],'2025-01-10')

    def test_missing_cannot_use_future(self):
        with self.assertRaises(ValueError):collector.select_asof(self.history(),'2025-01-01')

    def test_conflicting_intervals_rejected(self):
        h=self.history();h=pd.concat([h,pd.DataFrame([dict(date='2025-01-01',realtime_start='2025-01-03',realtime_end='2025-01-05',value='500')])])
        with self.assertRaises(ValueError):collector.select_asof(h,'2025-01-04')

@unittest.skipUnless((OUT/'fuel_forecast_inputs_2023_2025.csv').exists(),'Collected C data absent')
class SectionCDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f=pd.read_csv(OUT/'fuel_forecast_inputs_2023_2025.csv')
        cls.origin=pd.to_datetime(cls.f.forecast_origin,utc=True).dt.tz_convert('Asia/Seoul')
        cls.target=pd.to_datetime(cls.f.target_timestamp,utc=True).dt.tz_convert('Asia/Seoul')

    def test_complete_72h_blocks(self):
        self.assertEqual(len(self.f),78480)
        self.assertTrue(self.f.groupby('forecast_origin').size().eq(72).all())
        self.assertTrue(self.f.groupby(['forecast_origin','forecast_day']).size().eq(24).all())
        self.assertFalse(self.f.duplicated(['forecast_origin','target_timestamp']).any())
        feature_cols=['domestic_lng_cost_krw_kwh']+[x[0] for x in collector.SERIES.values()]
        self.assertTrue(np.isfinite(self.f[feature_cols].to_numpy()).all())

    def test_dminus2_and_vintage_bounds(self):
        expected=(self.origin.dt.normalize()-pd.Timedelta(days=2)).dt.strftime('%Y-%m-%d')
        self.assertTrue(self.f.fred_asof_date.eq(expected).all())
        for feature,_ in collector.SERIES.values():
            self.assertTrue((self.f[feature+'_vintage_start']<=self.f.fred_asof_date).all())
            self.assertTrue((self.f[feature+'_vintage_end']>=self.f.fred_asof_date).all())
            self.assertTrue((self.f[feature+'_observation_date']<=self.f.fred_asof_date).all())
            self.assertTrue(self.f.groupby('forecast_origin')[feature].nunique().eq(1).all())

    def test_domestic_target_month_exception(self):
        self.assertTrue(self.f.domestic_lng_reference_month.eq(self.target.dt.strftime('%Y-%m')).all())
        monthly=pd.read_csv(OUT/'domestic_lng_monthly.csv').set_index('month').domestic_lng_cost_krw_kwh
        np.testing.assert_allclose(self.f.domestic_lng_cost_krw_kwh,monthly.reindex(self.f.domestic_lng_reference_month))
        # This must genuinely exercise at least one origin that crosses a month boundary.
        self.assertTrue(self.f.groupby('forecast_origin').domestic_lng_reference_month.nunique().gt(1).any())

    def test_demo_uses_october(self):
        demo=pd.read_csv(OUT/'november_demo_fuel_preview.csv')
        monthly=pd.read_csv(OUT/'domestic_lng_monthly.csv').set_index('month')
        self.assertEqual(len(demo),72)
        self.assertTrue(demo.domestic_lng_reference_month.eq('2026-10').all())
        np.testing.assert_allclose(demo.domestic_lng_cost_krw_kwh,monthly.loc['2026-10','domestic_lng_cost_krw_kwh'])

    def test_target_split_boundaries(self):
        dates=self.target.dt.strftime('%Y-%m-%d')
        for split,lo,hi in [('train','2023-01-01','2024-12-31'),('validation','2025-01-01','2025-06-30'),('test','2025-07-01','2025-12-31')]:
            self.assertTrue(dates[self.f.split==split].between(lo,hi).all())
        self.assertTrue(self.f.groupby('forecast_origin').split.nunique().eq(1).all())

if __name__=='__main__':unittest.main()
