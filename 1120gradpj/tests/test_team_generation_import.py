"""Verify the pinned teammate CSV and distinguish received days from complete required fuels."""
from pathlib import Path
import hashlib
import unittest
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'data/raw/team_generation/42b48265194b5afa24a932345f77e876a279999c/api_generation_partial_2023_2025_merged_20261119.csv'

class TeamGenerationImportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SOURCE.exists():raise unittest.SkipTest('Pinned imported dataset is not present locally')
        cls.frame=pd.read_csv(SOURCE,dtype={'tradeYmd':str,'tradeNo':str})
    def test_original_git_blob(self):
        data=SOURCE.read_bytes();actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        self.assertEqual(actual,'42b48265194b5afa24a932345f77e876a279999c')
    def test_rows_and_unique_keys(self):
        self.assertEqual(len(self.frame),86472)
        self.assertFalse(self.frame.duplicated(['tradeYmd','tradeNo','fuelTpCd']).any())
    def test_2024_expected_gaps_are_not_hidden(self):
        frame=self.frame[self.frame.tradeYmd.str.startswith('2024')]
        self.assertEqual(frame.tradeYmd.nunique(),365)
        self.assertFalse(frame.tradeYmd.eq('20240229').any())
        for fuel in ['LNG','유연탄']:self.assertEqual(frame.fuelTpCd.eq(fuel).sum(),8760)
        for fuel in ['원자력','무연탄']:self.assertEqual(frame.fuelTpCd.eq(fuel).sum(),8016)
        august=frame[frame.tradeYmd.str.startswith('202408')]
        self.assertEqual(august.tradeYmd.nunique(),31)
        self.assertFalse(august.fuelTpCd.isin(['원자력','무연탄']).any())
    def test_public_copy_identical(self):
        public=ROOT.parent/'shared_datasets/kpx_generation'/SOURCE.name
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),hashlib.sha256(public.read_bytes()).hexdigest())

if __name__=='__main__':unittest.main()
