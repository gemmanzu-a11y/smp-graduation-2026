import sys,unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from smp_forecast.dataset import sample,config,split_for,VARIABLES
from smp_forecast.collect import parse_weather,parse_power,parse_smp
from smp_forecast.training import Preprocessor
from smp_forecast.inference import input_gate
class PipelineTest(unittest.TestCase):
 def setUp(self):
  idx=pd.date_range('2025-01-01',periods=24*20,freq='h',tz='Asia/Seoul');self.base=pd.DataFrame({v:np.arange(len(idx),dtype=float)+i for i,v in enumerate(VARIABLES)},index=idx);self.origin=pd.Timestamp('2025-01-10 23:00',tz='Asia/Seoul');self.cfg=config()
 def test_future_realizations_do_not_change_inputs(self):
  s,c,x,y,m=sample(self.base,self.origin,self.cfg,set());changed=self.base.copy();changed.loc[changed.index>self.origin,:]=999999;_,_,x2,y2,_=sample(changed,self.origin,self.cfg,set());np.testing.assert_allclose(x,x2,equal_nan=True);self.assertFalse(np.array_equal(y,y2));self.assertTrue((pd.to_datetime(m.latest_source_timestamp)<=self.origin).all())
 def test_exact_72_hour_horizons_and_baselines(self):
  s,c,x,y,m=sample(self.base,self.origin,self.cfg,set());self.assertEqual(x.shape,(72,406));self.assertEqual(m.timestamp.min(),pd.Timestamp('2025-01-11',tz='Asia/Seoul'));self.assertEqual(m.timestamp.max(),pd.Timestamp('2025-01-13 23:00',tz='Asia/Seoul'));self.assertEqual(m.groupby('horizon_days').size().tolist(),[24,24,24]);np.testing.assert_array_equal(m.baseline_weekly,self.base.smp.reindex(m.timestamp-pd.Timedelta(days=7)).values)
 def test_observation_delay_is_real(self):
  seq,_,_,_,_=sample(self.base,self.origin,self.cfg,set());self.assertEqual(seq[-1,VARIABLES.index('demand_mw')],self.base.loc[self.origin-pd.Timedelta(hours=24),'demand_mw']);self.assertEqual(seq[-1,VARIABLES.index('wind_mwh')],self.base.loc[self.origin-pd.Timedelta(hours=48),'wind_mwh'])
 def test_target_date_split_purges_boundaries(self):
  t=pd.Series(pd.date_range('2024-12-31',periods=72,freq='h',tz='Asia/Seoul'));self.assertIsNone(split_for(t,self.cfg));self.assertEqual(split_for(pd.Series(pd.date_range('2025-01-01',periods=72,freq='h',tz='Asia/Seoul')),self.cfg),'validation')
 def test_train_only_preprocessing(self):
  x=np.array([[1.,np.nan],[3.,np.nan]]);p=Preprocessor(True).fit(x);z=p.transform(np.array([[1000.,12.]]));self.assertEqual(p.imputer.statistics_[0],2.);self.assertEqual(p.scaler.mean_[0],2.);self.assertEqual(p.all_missing_features,[1]);self.assertTrue(np.isfinite(z).all())
 def test_asos_minus9_temperature_is_not_missing(self):
  row=['0']*48;row[0]='202501010000';row[1]='108';row[3]='2.3';row[11]='-9';row[-12]='0.12';f=parse_weather((' '.join(row)).encode(),[108]);self.assertEqual(f.temperature_c.iloc[0],-9.);self.assertEqual(f.solar_radiation_mj_m2.iloc[0],.12)
 def test_partial_power_hour_is_missing(self):
  block=lambda minute:f'c1 = textFormmat("100",0);c2 = textFormmat("80",0);c5 = textFormmat("20",0);c6 = textFormmat("25",0);gridData.push({{"year":"2025-01-01 00:{minute:02d}"}});'
  f=parse_power(''.join(block(i) for i in range(0,55,5)).encode());self.assertTrue(pd.isna(f.demand_mw.iloc[0]));self.assertEqual(f.samples_5m.iloc[0],11)
 def test_complete_power_hour_mean(self):
  block=lambda minute:f'c1 = textFormmat("100",0);c2 = textFormmat("80",0);c5 = textFormmat("20",0);c6 = textFormmat("25",0);gridData.push({{"year":"2025-01-01 00:{minute:02d}"}});'
  f=parse_power(''.join(block(i) for i in range(0,60,5)).encode());self.assertEqual(f.demand_mw.iloc[0],80.)
 def test_missing_full_source_blocks_latest(self):
  _,_,x,_,_=sample(self.base,self.origin,self.cfg,set());self.assertTrue(input_gate(x)['can_predict']);x[:,:384].reshape(72,48,8)[:,:,VARIABLES.index('wind_mwh')]=np.nan;g=input_gate(x);self.assertFalse(g['can_predict']);self.assertEqual(g['issues'][0]['variable'],'wind_mwh')
 def test_real_manifest_matches_training(self):
  folder=Path(__file__).resolve().parents[1]/'data/processed';m=pd.read_csv(folder/'training_metadata.csv');d=np.load(folder/'training_dataset.npz');self.assertEqual(len(m),d['y'].size);self.assertFalse(m.duplicated(['origin','timestamp']).any());self.assertEqual(m.groupby('origin').size().unique().tolist(),[72]);bounds={k:pd.to_datetime(g.timestamp,utc=True) for k,g in m.groupby('split')};self.assertLess(bounds['train'].max(),bounds['validation'].min());self.assertLess(bounds['validation'].max(),bounds['test'].min())
if __name__=='__main__':unittest.main()
