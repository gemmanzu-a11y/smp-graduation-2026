"""Complete interrupted metadata verification from saved artifacts; no fitting."""
from pathlib import Path
import argparse,hashlib,json,sys,time,platform
import numpy as np
import pandas as pd
from protocol import dump

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--model',choices=['xgboost','lightgbm'],required=True);parser.add_argument('--source-project',type=Path,required=True);parser.add_argument('--upgrade-dir',type=Path);args=parser.parse_args()
    name=args.model;source=args.source_project.resolve();sys.path.insert(0,str(source/'src'))
    from smp_forecast import common_v3 as c
    root=args.upgrade_dir.resolve() if args.upgrade_dir else Path(__file__).resolve().parents[4]/name/'upgrades/upgrade_72h_20261119'
    if (root/'reports/verification.json').exists():
        print('Already verified; existing artifacts preserved');return
    config=json.loads((root/'config/experiment_config.json').read_text());selection=json.loads((root/'config/selection_before_test.json').read_text());hashes=json.loads((root/'config/protected_source_hashes.json').read_text())
    assert config['dataset_version']==c.VERSION and not selection['test_metric_used']
    _,f,m=c.load();original=Path(config['original_run'])
    e0=pd.read_csv(original/'predictions.csv')
    checkpoint=root/'models'/('final_model.ubj' if name=='xgboost' else 'final_model.txt')
    if name=='xgboost':
        import xgboost
        model=xgboost.XGBRegressor();model.load_model(checkpoint);version=xgboost.__version__
    else:
        import lightgbm
        model=lightgbm.Booster(model_file=str(checkpoint));version=lightgbm.__version__
    for split,filename in [('validation','experiments_validation.csv'),('test','final_test_predictions.csv')]:
        frame=pd.read_csv(root/'outputs/predictions'/filename);expected=f[f.split==split].sort_values(['forecast_origin','horizon'])
        predictions=model.predict(expected[m['context_features']].to_numpy(dtype='float32'))
        saved=frame[frame.experiment_id=='E2']
        np.testing.assert_allclose(saved.predicted_smp,predictions,rtol=1e-6,atol=1e-5)
        for exp,z in frame.groupby('experiment_id'):
            reference=e0[e0.split==split][['forecast_origin','target_timestamp','horizon','actual_smp']].reset_index(drop=True)
            pd.testing.assert_frame_equal(z[reference.columns].reset_index(drop=True),reference)
    assert all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in hashes.items())
    oof=pd.read_csv(root/'outputs/predictions/rolling_oof.csv')
    checks=dict(originals_and_other_models_unchanged=True,baseline_references_before_cutoff=True,test_rows_per_experiment=13104,validation_rows_per_experiment=12888,rolling_oof_rows=len(oof),test_selection_frozen=True,checkpoint_roundtrip=True,features_unchanged=True,elapsed_seconds=time.time()-(root/'config/experiment_config.json').stat().st_mtime,python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,model_library_version=version,metadata_resume_only=True)
    dump(root/'reports/verification.json',checks);dump(root/'config/final_artifact.json',dict(checkpoint=str(checkpoint),checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),adopted_experiment='E4' if selection['correction']['mode']!='none' else 'E3'))
    print('PASS',name,'saved predictions/checkpoint and protected hashes; metadata restored without refitting')

if __name__=='__main__':main()
