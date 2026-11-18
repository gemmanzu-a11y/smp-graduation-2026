"""Check source schema normalization, completeness, and preserving missing required fuels."""
import importlib.util
from pathlib import Path
import unittest
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('generation_annual_collector',ROOT/'scripts/collect_generation_annual.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class GenerationNormalizationTest(unittest.TestCase):
    def frame(self):return pd.DataFrame({'거래일자':['2024-01-01'],'시간':[24],'원료원':['LNG'],' 설비용량(MW) ':[100],' 전력거래량(MWh) ':[25]})
    def test_source_hours_and_whitespace(self):
        result=module.normalize(self.frame(),2024)
        self.assertEqual(result.timestamp.iloc[0],pd.Timestamp('2024-01-01 23:00',tz='Asia/Seoul'))
        self.assertEqual(result.generation_mwh.iloc[0],25)
    def test_wrong_year_rejected(self):
        with self.assertRaisesRegex(ValueError,'year'):module.normalize(self.frame(),2023)
    def test_duplicate_key_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):module.normalize(pd.concat([self.frame(),self.frame()]),2024)
    def test_invalid_hours_rejected(self):
        frame=self.frame();frame['시간']=0
        with self.assertRaisesRegex(ValueError,'hour'):module.normalize(frame,2024)
    def test_nan_not_zeroed(self):
        frame=self.frame();frame[' 전력거래량(MWh) ']=float('nan')
        with self.assertRaisesRegex(ValueError,'Nonfinite'):module.normalize(frame,2024)

class CollectedGenerationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=ROOT/'data/processed/section_b/generation_annual/generation_selected_2023_2025.csv'
        if not path.exists():raise unittest.SkipTest('Local collected dataset not present')
        cls.data=pd.read_csv(path);cls.data['timestamp']=pd.to_datetime(cls.data.timestamp,utc=True).dt.tz_convert('Asia/Seoul')
    def test_full_axis(self):
        expected=pd.date_range('2023-01-01','2025-12-31 23:00',freq='h',tz='Asia/Seoul')
        self.assertTrue(pd.DatetimeIndex(self.data.timestamp).equals(expected))
    def test_2023_and_2025_fully_populated(self):
        for year in [2023,2025]:self.assertFalse(self.data[self.data.timestamp.dt.year==year].isna().any().any())
    def test_2024_absence_not_hidden(self):
        missing=self.data[self.data.timestamp.dt.year==2024].drop(columns='timestamp')
        self.assertEqual(len(missing),8784);self.assertTrue(missing.isna().all().all())
    def test_coal_sum_with_csv_precision(self):
        data=self.data[self.data.timestamp.dt.year.isin([2023,2025])]
        np.testing.assert_allclose(data.coal_generation_mwh,data.bituminous_coal_generation_mwh+data.anthracite_coal_generation_mwh,rtol=0,atol=1e-9)

if __name__=='__main__':unittest.main()
