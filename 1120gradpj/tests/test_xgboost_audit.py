"""Actual dataset temporal guards of the independent XGBoost experiment."""
import importlib.util
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('validated_xgb', ROOT/'models/xgboost/train_validated.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class XGBoostAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = np.load(ROOT/'data/processed/training_dataset.npz')
        cls.x, cls.y = data['x'], data['y'].reshape(-1)
        cls.meta = pd.read_csv(ROOT/'data/processed/training_metadata.csv')

    def test_real_data_passes(self):
        module.audit(self.meta, self.x, self.y)

    def test_future_source_is_rejected(self):
        bad = self.meta.copy()
        bad.loc[0, 'latest_source_timestamp'] = bad.loc[0, 'timestamp']
        with self.assertRaises(AssertionError):
            module.audit(bad, self.x, self.y)

    def test_test_row_cannot_enter_training(self):
        bad = self.meta.copy()
        bad.loc[bad.split == 'test', 'split'] = 'train'
        with self.assertRaises(AssertionError):
            module.audit(bad, self.x, self.y)

if __name__ == '__main__':
    unittest.main()
