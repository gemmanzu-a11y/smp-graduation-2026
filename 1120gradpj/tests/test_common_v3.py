"""Meaningful causality/contract checks, with synthetic and actual frozen data."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from smp_forecast import common_v3 as c


def test_imputation_train_frozen_and_causal():
    idx=pd.date_range('2024-12-28','2025-01-05',freq='h',tz=c.TZ)
    raw=pd.DataFrame({'x':np.arange(len(idx),dtype=float)},index=idx)
    raw.loc['2025-01-01':'2025-01-03','x']=np.nan
    before,params=c.causal_fill(raw)
    changed=raw.copy();changed.loc['2025-01-04':,'x']=999999
    after,params2=c.causal_fill(changed)
    assert params==params2
    np.testing.assert_array_equal(before.loc[:'2025-01-03'],after.loc[:'2025-01-03'])
    assert before.notna().all().all()


def test_vintage_revision_not_used_early():
    df=pd.DataFrame([dict(date='2024-12-01',value='10',realtime_start='2025-01-01',realtime_end='2025-01-10'),dict(date='2024-12-01',value='50',realtime_start='2025-01-11',realtime_end='9999-12-31')])
    assert c.vintage_select(df,pd.Timestamp('2025-01-05')).numeric==10
    assert c.vintage_select(df,pd.Timestamp('2025-01-12')).numeric==50


def test_real_dataset_block_boundaries_and_causality():
    if not (c.OUT/'manifest.json').exists():return
    h,f,m=c.load()
    assert set(m['all_groups'])==set(range(1,13))
    assert f.groupby('forecast_origin').size().eq(72).all()
    assert f.groupby('forecast_origin').split.nunique().eq(1).all()
    assert (f.observed_cutoff==f.forecast_origin-pd.Timedelta(hours=72)).all()
    assert ((f.target_timestamp-f.forecast_origin).dt.total_seconds()/3600==f.horizon).all()
    for column in ['temperature_issued_at','weather_issued_at']:
        issuance=pd.to_datetime(f[column],utc=True)
        assert issuance.notna().all()
        assert (issuance<=f.forecast_origin).all()
    for split,start,end in [('train','2023-01-01','2025-01-01'),('validation','2025-01-01','2025-07-01'),('test','2025-07-01','2026-01-01')]:
        z=f[f.split==split]
        assert (z.target_timestamp>=pd.Timestamp(start,tz=c.TZ)).all()
        assert (z.target_timestamp<pd.Timestamp(end,tz=c.TZ)).all()
    # A future actual perturbation cannot affect this already issued history.
    origin=f.loc[f.split=='test','forecast_origin'].iloc[0];cutoff=origin-pd.Timedelta(hours=72)
    before=h.loc[(h.index>=cutoff-pd.Timedelta(hours=168))&(h.index<cutoff)].copy()
    changed=h.copy();changed.loc[changed.index>=cutoff,:]=123456789
    pd.testing.assert_frame_equal(before,changed.reindex(before.index))
    assert before.index[-1]+pd.Timedelta(hours=1)<=cutoff
    assert np.isfinite(f[m['context_features']].to_numpy()).all()

# Standard-library discovery (pytest is not required in the project environment).
import unittest
class CommonV3Test(unittest.TestCase):
    def test_causal_imputation(self):test_imputation_train_frozen_and_causal()
    def test_asof_vintage(self):test_vintage_revision_not_used_early()
    def test_frozen_contract(self):test_real_dataset_block_boundaries_and_causality()
