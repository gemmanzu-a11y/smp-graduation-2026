"""Check B's collected samples and preserve missing values/source definitions."""
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/processed/section_b'

@unittest.skipUnless((OUT/'generation_20230101.csv').exists(),'Local B audit files absent')
class SectionBAuditTest(unittest.TestCase):
    def test_generation_fuel_hour_keys(self):
        for date in ['20230101','20240101','20250101','20260901']:
            f=pd.read_csv(OUT/f'generation_{date}.csv')
            self.assertEqual(len(f),192)
            self.assertFalse(f.duplicated(['tradeYmd','tradeNo','fuelTpCd']).any())
            self.assertTrue(f.groupby('fuelTpCd').size().eq(24).all())
            self.assertTrue({'LNG','유연탄','무연탄','원자력'}.issubset(f.fuelTpCd))
            self.assertTrue(np.isfinite(f.amgo).all())

    def test_mainland_solar_uses_market_field(self):
        for date in ['20250102','20250702','20261118']:
            f=pd.read_csv(OUT/f'solar_forecast_{date}.csv',dtype={'hh':str,'baseDate':str,'baseTime':str,'predDate':str})
            mainland=f[~f.city.str.contains('제주')]
            expected=mainland.groupby(['baseDate','baseTime','predDate','hh'],as_index=False).solgenKpx.sum()
            actual=pd.read_csv(OUT/f'solar_forecast_mainland_{date}.csv',dtype={'hh':str,'baseDate':str,'baseTime':str,'predDate':str})
            np.testing.assert_allclose(expected.solgenKpx,actual.solgenKpx)
            self.assertEqual(len(actual),14)
            self.assertEqual(set(f.hh.astype(int)),set(range(6,20)))

    def test_original_renewable_gaps_preserved(self):
        original=pd.read_csv(ROOT/'data/processed/renewable_hourly.csv');original.timestamp=pd.to_datetime(original.timestamp,utc=True)
        checked=pd.read_csv(OUT/'renewable_mainland_2023_2025.csv');checked.timestamp=pd.to_datetime(checked.timestamp,utc=True)
        pair=checked.merge(original,on='timestamp',suffixes=('_audit','_original'),validate='one_to_one')
        for c in ['solar_mwh','wind_mwh']:
            np.testing.assert_allclose(pair[c+'_audit'],pair[c+'_original'],equal_nan=True)
        self.assertEqual(checked.solar_mwh.isna().sum(),1)
        self.assertEqual(checked.wind_mwh.isna().sum(),0)

    def test_reserve_reported_values_not_derived_overwrite(self):
        source=pd.read_csv(ROOT/'data/processed/section_a/demand_actual_2023_2025_repaired.csv')
        checked=pd.read_csv(OUT/'supply_reserve_2023_2025.csv')
        self.assertEqual(checked.timestamp.tolist(),source.timestamp.tolist())
        for c in ['reserve_mw','reserve_rate_pct']:
            np.testing.assert_allclose(checked[c],source[c],equal_nan=True)
        self.assertEqual(checked.reserve_mw.isna().sum(),1095)

if __name__=='__main__':unittest.main()
