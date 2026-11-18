"""Tree integration: frozen feature scope, no target leakage and checkpoint parity."""
from pathlib import Path
import sys,tempfile,unittest
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from smp_forecast import tree_models_v3 as tree
from smp_forecast import common_v3 as c

class TreeV3Test(unittest.TestCase):
    def test_targets_and_baselines_never_become_features(self):
        _,f,m=c.load();one=f[f.split=='validation'].iloc[:72].copy()
        frame,x,y=tree.matrices(one,m,'validation')
        changed=one.copy();changed['actual_smp']=-999999;changed['baseline_weekly']=888888
        _,x2,y2=tree.matrices(changed,m,'validation')
        self.assertEqual(x.shape,(72,83));np.testing.assert_array_equal(x,x2);self.assertFalse(np.array_equal(y,y2))
        for key in ['actual_smp','baseline_weekly','forecast_origin','target_timestamp']:self.assertNotIn(key,m['context_features'])
    def test_nonfinite_feature_rejected(self):
        _,f,m=c.load();one=f[f.split=='validation'].iloc[:72].copy();one.loc[one.index[0],m['context_features'][0]]=np.nan
        with self.assertRaises(ValueError):tree.matrices(one,m,'validation')
    def test_early_stopping_checkpoint_roundtrip_both_models(self):
        # Match production's separate processes: macOS native OpenMP conflicts
        # when this test fits XGBoost after the full suite has trained PyTorch.
        import os,subprocess
        if os.environ.get('SMP_TREE_NATIVE_CHILD')!='1':
            env=dict(os.environ,SMP_TREE_NATIVE_CHILD='1',MPLCONFIGDIR=str(ROOT/'data/cache/matplotlib'))
            result=subprocess.run([sys.executable,__file__,'TreeV3Test.test_early_stopping_checkpoint_roundtrip_both_models'],env=env,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            return
        import xgboost,lightgbm
        rng=np.random.default_rng(42);x=rng.normal(size=(240,4)).astype('float32');y=(100+10*x[:,0]).astype('float32')
        for name in ['xgboost','lightgbm']:
            params=dict(n_estimators=12,learning_rate=.1,max_depth=2)
            if name=='lightgbm':params.update(num_leaves=4,min_child_samples=5)
            else:params['min_child_weight']=1
            model,rounds=tree.fit(name,params,x[:180],y[:180],x[180:],y[180:]);self.assertTrue(1<=rounds<=12)
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/('model.ubj' if name=='xgboost' else 'model.txt')
                if name=='xgboost':
                    model.save_model(path);restored=xgboost.XGBRegressor();restored.load_model(path)
                else:
                    model.booster_.save_model(str(path),num_iteration=rounds);restored=lightgbm.Booster(model_file=str(path))
                np.testing.assert_allclose(model.predict(x[180:]),restored.predict(x[180:]),rtol=1e-7,atol=1e-6)

if __name__=='__main__':unittest.main()
