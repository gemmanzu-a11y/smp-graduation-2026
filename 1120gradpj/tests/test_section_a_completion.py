"""Regression checks on collected section-A files; skip if data is not shared locally."""
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/processed/section_a'

@unittest.skipUnless((OUT/'section_a_hourly_2023_2025.csv').exists(), 'Local collected data not present')
class SectionACompletionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forecast=pd.read_csv(OUT/'demand_forecast_mainland_2023_2025.csv')
        cls.forecast.timestamp=pd.to_datetime(cls.forecast.timestamp,utc=True).dt.tz_convert('Asia/Seoul')
        cls.expected=pd.date_range('2023-01-01','2025-12-31 23:00',freq='h',tz='Asia/Seoul')

    def test_full_forecast_time_axis(self):
        self.assertTrue(pd.DatetimeIndex(self.forecast.timestamp).equals(self.expected))
        self.assertTrue(self.forecast.groupby('target_date').size().eq(24).all())
        self.assertTrue(self.forecast.geography.eq('mainland').all())

    def test_forecast_matches_all_api_overlap(self):
        old=pd.read_csv(OUT/'demand_forecast_mainland_api_partial_20261118.csv')
        old.timestamp=pd.to_datetime(old.timestamp,utc=True).dt.tz_convert('Asia/Seoul')
        pair=self.forecast.merge(old,on='timestamp',suffixes=('_annual','_api'),validate='one_to_one')
        self.assertEqual(len(pair),len(old))
        np.testing.assert_allclose(pair.demand_forecast_mw_annual,pair.demand_forecast_mw_api,rtol=0,atol=0)

    def test_interval_end_to_start_mapping(self):
        np.testing.assert_array_equal(self.forecast.timestamp.dt.hour,self.forecast.source_hour-1)
        self.assertTrue(np.isfinite(self.forecast.demand_forecast_mw).all())

    def test_leap_day(self):
        self.assertEqual(self.forecast.timestamp.dt.strftime('%Y-%m-%d').eq('2024-02-29').sum(),24)

    def test_old_valid_actuals_preserved(self):
        old=pd.read_csv(ROOT/'data/processed/power_hourly.csv');old.timestamp=pd.to_datetime(old.timestamp,utc=True)
        old=old.set_index('timestamp').reindex(self.expected)
        new=pd.read_csv(OUT/'demand_actual_2023_2025_repaired.csv');new.timestamp=pd.to_datetime(new.timestamp,utc=True)
        new=new.set_index('timestamp').reindex(self.expected)
        known=old.demand_mw.notna()
        np.testing.assert_allclose(old.loc[known,'demand_mw'],new.loc[known,'demand_mw'],rtol=0,atol=0)

    def test_unresolved_gaps_not_filled_with_other_indicator(self):
        missing=pd.read_csv(OUT/'actual_unresolved_hours.csv')
        repaired=pd.read_csv(OUT/'demand_actual_2023_2025_repaired.csv')
        self.assertEqual(len(missing),repaired.demand_mw.isna().sum())
        self.assertTrue((missing.valid_5min_samples+missing.missing_5min_samples).eq(12).all())

    def test_separate_national_candidate_complete(self):
        candidate=pd.read_csv(OUT/'national_generation_demand_candidate_2023_2025.csv')
        t=pd.to_datetime(candidate.timestamp,utc=True).dt.tz_convert('Asia/Seoul')
        self.assertTrue(pd.DatetimeIndex(t).equals(self.expected))
        self.assertTrue(candidate.unit.eq('MWh').all())
        self.assertTrue(candidate.geography.eq('mainland and Jeju').all())
        self.assertTrue(np.isfinite(candidate.national_generation_demand_mwh).all())

    def test_combined_preserves_distinct_definitions(self):
        combined=pd.read_csv(OUT/'section_a_hourly_2023_2025.csv')
        self.assertEqual(len(combined),26304)
        self.assertIn('epsis_current_load_hourly_mean_mw',combined)
        self.assertIn('national_generation_demand_mwh',combined)
        self.assertFalse(combined.demand_forecast_mw.isna().any())
        self.assertTrue(combined.is_holiday.isin([0,1]).all())

if __name__=='__main__':unittest.main()
