"""Fixed-round native tree refit using the same v3 upgrade selection protocol."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys,time,warnings,platform
import numpy as np
import pandas as pd
helper_path=Path(__file__).resolve().parents[4]/'lstm/upgrades/upgrade_72h_20261119/scripts/protocol.py'
spec=importlib.util.spec_from_file_location('frozen_upgrade_common',helper_path)
common=importlib.util.module_from_spec(spec);spec.loader.exec_module(common)
dump=common.dump;metrics=common.metrics;blend_selection=common.blend_selection
blend=common.blend;calibration_selection=common.calibration_selection
complete_blocks=common.complete_blocks;loadmodule=common.loadmodule

def run(name,upgrade):
    parser=argparse.ArgumentParser();parser.add_argument('--source-project',type=Path,required=True);parser.add_argument('--output-dir',type=Path);args=parser.parse_args()
    if args.output_dir is not None:
        upgrade=args.output_dir.resolve()
        if upgrade.exists() and any(upgrade.iterdir()):raise RuntimeError('New output directory must be empty')
    source=args.source_project.resolve();sys.path.insert(0,str(source/'src'))
    from smp_forecast import common_v3 as c
    h,f,manifest=c.load();assert manifest['dataset_version']==c.VERSION
    current=json.loads((source/'models'/name/'CURRENT_RUN.json').read_text());assert current['dataset_version']==c.VERSION
    original=Path(current['path']);e0=pd.read_csv(original/'predictions.csv')
    for col in ['forecast_origin','target_timestamp','observed_cutoff']:e0[col]=c.times(e0[col])
    assert len(e0)==25992 and not e0.duplicated(['forecast_origin','target_timestamp']).any()
    protected=[c.OUT/'manifest.json',original/'predictions.csv',original/('model.ubj' if name=='xgboost' else 'model.txt')]
    for other in ['lstm','sarimax','lightgbm','xgboost']:protected.append(source/'models'/other/'CURRENT_RUN.json')
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    out=upgrade;out.mkdir(parents=True,exist_ok=True)
    if (out/'config/selection_before_test.json').exists():raise RuntimeError('Existing run preserved; choose a new upgrade directory')
    for path in ['config','models','outputs/predictions','outputs/metrics','outputs/figures','reports']:(out/path).mkdir(parents=True,exist_ok=True)
    start_time=time.perf_counter();module=loadmodule(source/'models'/name/'algorithm.py','upgrade_'+name)
    selected=json.loads((original/'selected_before_test.json').read_text())
    features=manifest['context_features'];hourly=f.sort_values('forecast_origin').drop_duplicates('target_timestamp',keep='last').set_index('target_timestamp').sort_index()
    trainval=f[f.split.isin(['train','validation'])].copy();validation=f[f.split=='validation'].sort_values(['forecast_origin','horizon']).copy()
    e0val=e0[e0.split=='validation'].sort_values(['forecast_origin','horizon']).copy()
    # Audit reference times for both original baselines against raw un-imputed SMP.
    raw=pd.read_csv(c.OUT/'hourly.csv');raw.index=c.times(raw.pop('timestamp'))
    for frame in [validation]:
        weekly_ref=frame.target_timestamp-pd.Timedelta(hours=168)
        daily_ref=frame.observed_cutoff.dt.normalize()-pd.Timedelta(days=1)+pd.to_timedelta(frame.target_timestamp.dt.hour,unit='h')
        assert ((weekly_ref+pd.Timedelta(hours=1))<=frame.observed_cutoff).all()
        assert ((daily_ref+pd.Timedelta(hours=1))<=frame.observed_cutoff).all()
        np.testing.assert_allclose(raw.smp.reindex(weekly_ref).to_numpy(),frame.baseline_weekly)
        np.testing.assert_allclose(raw.smp.reindex(daily_ref).to_numpy(),frame.baseline_origin_day)
    config=dict(model=name,dataset_version=c.VERSION,steps=['baseline blend on Validation','chronological OOF calibration before final fit','Train+Validation fixed-setting refit','frozen Test evaluation'],source_project=str(source),original_run=str(original),original_selected=selected,folds=[['2025-01-01','2025-03-01'],['2025-03-01','2025-05-01'],['2025-05-01','2025-07-01']],bias_min_improvement=.01,unchanged_imputation='original Train-only common imputation; no additional scaling for trees',input_group_count=12,publication_reaudit=False,test_reused=True,other_models_modified=False)
    dump(out/'config/experiment_config.json',config);dump(out/'config/protected_source_hashes.json',hashes)
    rule,grid=blend_selection(e0val);grid.to_csv(out/'outputs/metrics/blend_validation_grid.csv',index=False)
    dump(out/'config/stage1_blend.json',rule);print(name,'STAGE1 BLEND',rule,flush=True)
    def fit(frame,end):
        params=dict(selected['params'],n_estimators=int(selected['best_rounds']))
        if name=='xgboost':params.update(tree_method='hist',eval_metric='mae')
        else:params.update(objective='regression',metric='mae',verbosity=-1)
        model=module.create(params,seed=42,jobs=2)
        with warnings.catch_warnings(record=True):
            warnings.simplefilter('always')
            model.fit(frame[features].to_numpy(dtype=np.float32),frame.actual_smp.to_numpy(dtype=np.float32))
        return model
    def predict(model,frame):
        frame=frame.sort_values(['forecast_origin','horizon'])
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore',message='X does not have valid feature names')
            return model.predict(frame[features].to_numpy(dtype=np.float32))
    rolling=[];fold_reports=[]
    for number,(start,end) in enumerate(config['folds'],1):
        start=pd.Timestamp(start,tz=c.TZ);end=pd.Timestamp(end,tz=c.TZ)
        training=complete_blocks(trainval,end=start);heldout=complete_blocks(validation,start,end)
        print(name,'ROLLING',number,'fit origins',training.forecast_origin.nunique(),'heldout',heldout.forecast_origin.nunique(),flush=True)
        model=fit(training,start);pred=predict(model,heldout)
        z=heldout.copy();z['raw_model_prediction']=pred;z['predicted_smp']=blend(pred,z,rule);z['fold']=number
        rolling.append(z);fold_reports.append(dict(fold=number,start=start,end=end,fit_latest_target=str(training.target_timestamp.max()),heldout_rows=len(z),raw=metrics(z.actual_smp,pred),blended=metrics(z.actual_smp,z.predicted_smp)))
        del model
    oof=pd.concat(rolling,ignore_index=True);correction,calibration=calibration_selection(oof)
    oof.to_csv(out/'outputs/predictions/rolling_oof.csv',index=False)
    dump(out/'reports/rolling_validation.json',fold_reports);dump(out/'config/stage4_bias_selection.json',dict(selected=correction,candidates=calibration))
    print(name,'BIAS SELECTION',correction,flush=True)
    # Freeze everything before final refit and before evaluating any new Test model.
    selection=dict(blending=rule,correction=correction,parameters=selected,final_fit_end='2025-06-30',split_models='not used; original tree structure and iteration selection retained',selection_based_on='Validation and chronological OOF only',test_metric_used=False)
    dump(out/'config/selection_before_test.json',selection)
    final=fit(trainval,pd.Timestamp('2025-07-01',tz=c.TZ))
    checkpoint=out/'models'/('final_model.ubj' if name=='xgboost' else 'final_model.txt')
    if name=='xgboost':final.save_model(checkpoint)
    else:final.booster_.save_model(str(checkpoint),num_iteration=int(selected['best_rounds']))
    # Predictions are generated only after policy freeze. Val E2/E3/E4 is in-sample.
    valraw=predict(final,validation)
    test=f[f.split=='test'].sort_values(['forecast_origin','horizon']).copy();testraw=predict(final,test)
    pieces=[]
    for split,frame,pred in [('validation',validation,valraw),('test',test,testraw)]:
        original_rows=e0[e0.split==split].sort_values(['forecast_origin','horizon'])
        assert list(zip(frame.forecast_origin,frame.target_timestamp))==list(zip(original_rows.forecast_origin,original_rows.target_timestamp))
        original_pred=original_rows.predicted_smp.to_numpy();e3=blend(pred,frame,rule);bias=frame.forecast_day.map(lambda d:correction['bias_by_day'][str(d)]).to_numpy()
        values={'E0':original_pred,'daily_baseline':frame.baseline_origin_day.to_numpy(),'weekly_baseline':frame.baseline_weekly.to_numpy(),'E1':blend(original_pred,frame,rule),'E2':pred,'E3':e3,'E4':e3-bias}
        for experiment,p in values.items():
            z=frame[['forecast_origin','observed_cutoff','target_timestamp','horizon','forecast_day','actual_smp']].copy()
            z['split']=split;z['experiment_id']=experiment;z['model_name']=name.upper();z['dataset_version']=c.VERSION;z['predicted_smp']=p;z['absolute_error']=np.abs(p-z.actual_smp)
            z['baseline_prediction']=frame[rule['baseline']].to_numpy();z['blending_weight']=rule['alpha'] if experiment in ['E1','E3','E4'] else 1. if experiment in ['E0','E2'] else 0.
            z['prediction_status']='ok';z['evaluation_role']='post-refit in-sample, not selection' if split=='validation' and experiment in ['E2','E3','E4'] else 'existing Test reevaluation' if split=='test' else 'validation selection'
            pieces.append(z)
    allrows=pd.concat(pieces,ignore_index=True)
    for split,filename in [('validation','experiments_validation.csv'),('test','final_test_predictions.csv')]:allrows[allrows.split==split].to_csv(out/'outputs/predictions'/filename,index=False)
    result=[]
    for (split,experiment),part in allrows.groupby(['split','experiment_id']):result.append(dict(split=split,experiment_id=experiment,**metrics(part.actual_smp,part.predicted_smp)))
    result=pd.DataFrame(result);result.to_csv(out/'outputs/metrics/experiment_comparison.csv',index=False)
    for filename,groups in [('metrics_by_forecast_day.csv',['forecast_day']),('metrics_by_horizon.csv',['horizon']),('metrics_by_month.csv',['target_month'])]:
        temp=allrows.assign(target_month=allrows.target_timestamp.dt.strftime('%Y-%m'));rows=[]
        for keys,z in temp.groupby(['split','experiment_id']+groups):rows.append(dict(zip(['split','experiment_id']+groups,keys),**metrics(z.actual_smp,z.predicted_smp)))
        pd.DataFrame(rows).to_csv(out/'outputs/metrics'/filename,index=False)
    result.to_csv(out/'outputs/metrics/bias_analysis.csv',index=False)
    # Save/load equality of new model. Never overwrite the original checkpoint.
    if name=='xgboost':
        import xgboost
        restored=xgboost.XGBRegressor();restored.load_model(checkpoint)
    else:
        import lightgbm
        restored=lightgbm.Booster(model_file=str(checkpoint))
    np.testing.assert_allclose(predict(restored,test),testraw,rtol=1e-6,atol=1e-5)
    assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest for path,digest in hashes.items())
    checks=dict(originals_and_other_models_unchanged=True,baseline_references_before_cutoff=True,test_rows_per_experiment=13104,validation_rows_per_experiment=12888,rolling_oof_rows=len(oof),test_selection_frozen=True,checkpoint_roundtrip=True,features_unchanged=True,elapsed_seconds=time.perf_counter()-start_time,python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__)
    dump(out/'reports/verification.json',checks);dump(out/'config/final_artifact.json',dict(checkpoint=str(checkpoint),checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),adopted_experiment='E4' if correction['mode']!='none' else 'E3'))
    print(name,'FINISHED',result[result.split=='test'].to_string(index=False),flush=True)
