"""Synthetic technical tests only; no graduation SMP performance is claimed."""
import importlib.util
import json
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from smp_forecast import common_v2 as contract
spec=importlib.util.spec_from_file_location('lstm_algorithm_v2',ROOT/'models/lstm/algorithm.py')
algorithm=importlib.util.module_from_spec(spec);spec.loader.exec_module(algorithm)


class LSTMTechnicalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng=np.random.default_rng(42)
        cls.h=rng.normal(size=(8,4,3)).astype('float32')
        cls.c=rng.normal(size=(8,72,2)).astype('float32')
        cls.y=(100+3*cls.c[:,:,0]).astype('float32')
        cls.params=dict(hidden_size=4,layers=1,learning_rate=.01,batch_size=4,epochs=3,patience=2)
        cls.model=algorithm.Estimator(cls.params,jobs=1).fit(cls.h,cls.c,cls.y,(cls.h[:2]+20,cls.c[:2]+10,cls.y[:2]))
    def test_output_72(self):
        self.assertEqual(self.model.predict(self.h,self.c).shape,(8,72))
    def test_scalers_use_train_only(self):
        np.testing.assert_allclose(self.model.history_mean,self.h.mean((0,1)))
        np.testing.assert_allclose(self.model.context_mean,self.c.mean((0,1)))
    def test_reload_equal(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'model.pt';self.model.save(path)
            restored=algorithm.Estimator.load(path,jobs=1)
            np.testing.assert_allclose(self.model.predict(self.h,self.c),restored.predict(self.h,self.c),rtol=0,atol=0)
    def test_bad_input_rejected(self):
        with self.assertRaises(ValueError):self.model.predict(self.h,self.c[:,:71])
        bad=self.c.copy();bad[0,0,0]=np.nan
        with self.assertRaises(ValueError):self.model.predict(self.h,bad)
    def test_incomplete_origin_hour_excluded(self):
        origin=pd.Timestamp('2024-01-10 23:00',tz='Asia/Seoul')
        index=pd.date_range(origin-pd.Timedelta(hours=4),periods=10,freq='h')
        frame=pd.DataFrame(1.,index=index,columns=contract.HISTORY)
        frame['available_at']=index+pd.Timedelta(hours=1)
        before=contract.window(frame,origin,4)
        frame.loc[origin:,contract.HISTORY]=1e8
        np.testing.assert_array_equal(before,contract.window(frame,origin,4))
    def test_unavailable_history_rejected(self):
        origin=pd.Timestamp('2024-01-10 23:00',tz='Asia/Seoul')
        index=pd.date_range(origin-pd.Timedelta(hours=4),periods=4,freq='h')
        frame=pd.DataFrame(1.,index=index,columns=contract.HISTORY);frame['available_at']=origin+pd.Timedelta(hours=1)
        with self.assertRaisesRegex(ValueError,'unavailable'):contract.window(frame,origin,4)
    def test_no_excluded_source_required(self):
        for source in ['solar_forecast','solar_weather_forecast','weather_forecast']:
            self.assertNotIn(source,contract.SOURCES)
        self.assertIn('midrange_forecast',contract.SOURCES)
    def test_split_boundaries(self):
        cfg=dict(train_start='2023-01-01',train_end='2024-12-31')
        origins=contract.split_origins(cfg,'train')
        self.assertEqual(len(origins),729)
        self.assertEqual(origins[-1]+pd.Timedelta(hours=72),pd.Timestamp('2024-12-31 23:00',tz='Asia/Seoul'))
    def test_missing_bundle_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            issues,bundle=contract.inspect(directory,{})
            self.assertIsNone(bundle);self.assertTrue(issues)


class CommonBundleTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)
        self.cfg=dict(train_start='2024-01-10',train_end='2024-01-12',validation_start='2024-01-13',validation_end='2024-01-15',test_start='2024-01-16',test_end='2024-01-18',lookbacks=[4],fuel_policy='test_conditional_lng')
        index=pd.date_range('2024-01-01','2024-01-18 23:00',freq='h',tz='Asia/Seoul')
        hourly=pd.DataFrame({col:np.ones(len(index)) for col in contract.HISTORY})
        hourly['timestamp']=index;hourly['available_at']=index+pd.Timedelta(hours=1);hourly['smp_available_at']=index-pd.Timedelta(days=1)
        hourly.to_csv(self.path/'hourly.csv',index=False)
        rows=[];origins=[];targets=[]
        for split in contract.SPLITS:
            for origin in contract.split_origins(self.cfg,split):
                origins.append(dict(split=split,forecast_origin=origin))
                for target in pd.date_range(origin+pd.Timedelta(hours=1),periods=72,freq='h'):
                    targets.append(dict(split=split,forecast_origin=origin,target_timestamp=target))
                    rows.append(dict({col:1. for col in contract.FUTURE},forecast_origin=origin,target_timestamp=target,
                        latest_nonfuel_source_timestamp=origin,baseline_origin_day_latest_available_at=origin,
                        baseline_origin_day=1.,baseline_weekly=1.,international_asof_date=(origin-pd.Timedelta(days=2)).strftime('%Y-%m-%d'),latest_international_observation_date='2024-01-01'))
        pd.DataFrame(rows).to_csv(self.path/'forecast_inputs.csv',index=False)
        pd.DataFrame(origins).to_csv(self.path/'evaluation_origins.csv',index=False)
        pd.DataFrame(targets).to_csv(self.path/'evaluation_targets.csv',index=False)
        pd.DataFrame([dict(feature=feature,unit='synthetic',scope='synthetic',source_field='fixture',availability_rule='fixture',missing_rule='reject',transform='identity',role='synthetic') for feature in contract.HISTORY+contract.FUTURE]).to_csv(self.path/'feature_manifest.csv',index=False)
        pd.DataFrame({'month':['2024-01'],'value':[1.]}).to_csv(self.path/'evidence.csv',index=False)
        self.manifest=dict(schema_version='smp-common-v2',dataset_version='SYNTHETIC_TECHNICAL_ONLY',fuel_policy=self.cfg['fuel_policy'],history_features=contract.HISTORY,future_features=contract.FUTURE,
            decisions={key:dict(status='resolved',rule='synthetic technical fixture',evidence='test fixture') for key in contract.DECISIONS},
            sources={key:dict(status='complete',evidence_file='evidence.csv',unit='synthetic',scope='synthetic',mapping='test',availability_rule='test') for key in contract.SOURCES})
        self.refresh()
    def tearDown(self):self.temp.cleanup()
    def refresh(self):
        self.manifest['file_hashes']={file.name:hashlib.sha256(file.read_bytes()).hexdigest() for file in self.path.glob('*.csv')}
        (self.path/'manifest.json').write_text(json.dumps(self.manifest))
    def test_valid_bundle_and_shapes(self):
        issues,bundle=contract.inspect(self.path,self.cfg);self.assertEqual(issues,[])
        h,c,y=contract.arrays(bundle[0],bundle[1],contract.split_origins(self.cfg,'test'),4)
        self.assertEqual(h.shape,(1,4,len(contract.HISTORY)));self.assertEqual(c.shape,(1,72,len(contract.FUTURE)));self.assertEqual(y.shape,(1,72))
    def test_pending_team_decision_blocks(self):
        self.manifest['decisions']['midrange_72h_mapping']['status']='pending';self.refresh()
        issues,bundle=contract.inspect(self.path,self.cfg)
        self.assertIsNone(bundle);self.assertTrue(any(x['variable']=='midrange_72h_mapping' for x in issues))
    def test_future_issued_forecast_blocks(self):
        data=pd.read_csv(self.path/'forecast_inputs.csv');data.loc[0,'latest_nonfuel_source_timestamp']='2024-02-01T00:00:00+09:00';data.to_csv(self.path/'forecast_inputs.csv',index=False);self.refresh()
        issues,bundle=contract.inspect(self.path,self.cfg);self.assertIsNone(bundle);self.assertIn('Future source',issues[0]['reason'])
    def test_wrong_lng_month_blocks(self):
        data=pd.read_csv(self.path/'forecast_inputs.csv');data['domestic_lng_cost_krw_kwh']=9;data.to_csv(self.path/'forecast_inputs.csv',index=False);self.refresh()
        issues,bundle=contract.inspect(self.path,self.cfg);self.assertIsNone(bundle);self.assertIn('LNG',issues[0]['reason'])
    def test_changed_hash_blocks(self):
        with (self.path/'hourly.csv').open('a') as file:file.write('\n')
        issues,bundle=contract.inspect(self.path,self.cfg);self.assertIsNone(bundle);self.assertTrue(any('SHA-256' in x['reason'] for x in issues))
    def test_international_fuel_changes_block(self):
        data=pd.read_csv(self.path/'forecast_inputs.csv');data.loc[0,'wti_usd_bbl']=2;data.to_csv(self.path/'forecast_inputs.csv',index=False);self.refresh()
        issues,bundle=contract.inspect(self.path,self.cfg);self.assertIsNone(bundle);self.assertIn('International fuel',issues[0]['reason'])

if __name__=='__main__':unittest.main()
