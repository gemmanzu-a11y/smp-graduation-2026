from pathlib import Path
import sys,unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from protocol import blend_selection,blend,calibration_selection,complete_blocks

class ProtocolTest(unittest.TestCase):
    def test_alpha_zero_is_really_baseline_only(self):
        f=pd.DataFrame(dict(actual_smp=[100.,120.],predicted_smp=[900.,900.],baseline_origin_day=[110.,110.],baseline_weekly=[100.,120.]))
        rule,_=blend_selection(f);self.assertEqual(rule,dict(baseline='baseline_weekly',alpha=0.))
        np.testing.assert_array_equal(blend(f.predicted_smp,f,rule),f.actual_smp)
    def test_bias_fit_only_earlier_data_and_holdout_gate(self):
        dates=pd.date_range('2025-01-01','2025-06-30',freq='D',tz='Asia/Seoul').repeat(3)
        d=pd.DataFrame(dict(target_timestamp=dates,forecast_day=np.tile([1,2,3],len(dates)//3),actual_smp=100.,predicted_smp=105.))
        rule,_=calibration_selection(d);self.assertEqual(rule['mode'],'global');self.assertEqual(rule['bias_by_day'],{'1':5.,'2':5.,'3':5.})
        changed=d.copy();changed.loc[changed.target_timestamp>=pd.Timestamp('2025-05-01',tz='Asia/Seoul'),'predicted_smp']=95.
        rule,_=calibration_selection(changed);self.assertEqual(rule['mode'],'none')
    def test_test_data_rejected_as_calibration(self):
        d=pd.DataFrame(dict(target_timestamp=[pd.Timestamp('2025-07-01',tz='Asia/Seoul')]))
        with self.assertRaisesRegex(ValueError,'Test period'):calibration_selection(d)
    def test_cross_boundary_blocks_are_purged(self):
        origin=pd.Timestamp('2025-02-27 23:00',tz='Asia/Seoul')
        f=pd.DataFrame(dict(forecast_origin=origin,target_timestamp=pd.date_range(origin+pd.Timedelta(hours=1),periods=72,freq='h'),horizon=range(1,73)))
        self.assertEqual(len(complete_blocks(f,end=pd.Timestamp('2025-03-01',tz='Asia/Seoul'))),0)

if __name__=='__main__':unittest.main()
