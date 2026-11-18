"""Generation-only supplementation must preserve every common evaluation target."""
import unittest,sys,json
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from smp_forecast import common_v3 as old
from smp_forecast import common_v4 as new

@unittest.skipUnless((new.OUT/'manifest.json').exists(),'v4 dataset not built yet')
class GenerationV4Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.h,cls.f,cls.m=new.load()
    def test_identical_evaluation_keys(self):
        for name in ['evaluation_origins.csv','evaluation_targets.csv']:
            self.assertEqual((new.OUT/name).read_bytes(),(old.OUT/name).read_bytes())
    def test_generation_coverage_and_raw_missing(self):
        raw=pd.read_csv(new.OUT/'hourly.csv');year=pd.to_datetime(raw.timestamp).dt.year
        for y in [2023,2025]:
            self.assertFalse(raw.loc[year==y,['generation_lng','generation_coal','generation_nuclear']].isna().any().any())
        self.assertEqual(raw.loc[year==2024,'generation_lng'].isna().sum(),24)
        for name in ['generation_coal','generation_nuclear']:self.assertEqual(raw.loc[year==2024,name].isna().sum(),768)
    def test_other_inputs_identical_and_all_arrays_finite(self):
        h,f,m=old.load()
        cols=[c for c in self.h if not c.startswith(('generation_lng','generation_coal','generation_nuclear'))]
        pd.testing.assert_frame_equal(self.h[cols],h[cols])
        cols=[c for c in self.f if not c.startswith(('generation_lng','generation_coal','generation_nuclear'))]
        pd.testing.assert_frame_equal(self.f[cols],f[cols])
        for split in ['train','validation','test']:
            arrays=new.arrays((self.h,self.f,self.m),split,168)
            self.assertTrue(all(np.isfinite(x).all() for x in arrays))

if __name__=='__main__':unittest.main()
