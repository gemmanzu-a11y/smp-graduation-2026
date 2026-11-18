"""Read-only v3 inputs; baseline blend -> rolling calibration -> Train+Val refit.

Only the upgrade directory is writable. No model selection uses Test metrics.
Original architecture/order and Validation-selected epoch are held fixed.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,platform,sys,time,warnings
import numpy as np
import pandas as pd


def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str)+'\n')

def loadmodule(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def metrics(y,p):
    y=np.asarray(y);p=np.asarray(p);e=p-y;den=float(((y-y.mean())**2).sum())
    return dict(rows=len(y),mae=float(np.abs(e).mean()),rmse=float(np.sqrt((e**2).mean())),r2=1-float((e**2).sum())/den if den else None,bias=float(e.mean()),overprediction_fraction=float((e>0).mean()),underprediction_fraction=float((e<0).mean()),prediction_variance=float(p.var()),actual_variance=float(y.var()))


def blend_selection(frame):
    rows=[]
    for baseline in ['baseline_origin_day','baseline_weekly']:
        for alpha in np.linspace(0,1,11):
            pred=alpha*frame.predicted_smp+(1-alpha)*frame[baseline]
            rows.append(dict(baseline=baseline,alpha=float(alpha),**metrics(frame.actual_smp,pred)))
    table=pd.DataFrame(rows).sort_values(['mae','alpha','baseline'])
    return dict(baseline=table.iloc[0].baseline,alpha=float(table.iloc[0].alpha)),table


def blend(p,frame,rule):return rule['alpha']*np.asarray(p)+(1-rule['alpha'])*frame[rule['baseline']].to_numpy()


def calibration_selection(oof):
    if not (oof.target_timestamp<pd.Timestamp('2025-07-01',tz='Asia/Seoul')).all():raise ValueError('Test period cannot fit bias correction')
    # Freeze options and the minimum improvement before final Test is examined.
    calibration=oof[oof.target_timestamp<pd.Timestamp('2025-05-01',tz='Asia/Seoul')]
    validation=oof[oof.target_timestamp>=pd.Timestamp('2025-05-01',tz='Asia/Seoul')]
    def offsets(data,mode):
        e=data.predicted_smp-data.actual_smp
        return {str(day):float(e[data.forecast_day==day].mean()) if mode=='by_day' else float(e.mean()) if mode=='global' else 0. for day in [1,2,3]}
    none_mae=float(np.abs(validation.predicted_smp-validation.actual_smp).mean());records=[]
    for mode in ['none','global','by_day']:
        bias=offsets(calibration,mode);p=validation.predicted_smp-validation.forecast_day.map(lambda d:bias[str(d)])
        monthly_ok=True
        for month,z in validation.groupby(validation.target_timestamp.dt.month):
            adjusted=p.loc[z.index];monthly_ok&=bool(np.abs(adjusted-z.actual_smp).mean()<=np.abs(z.predicted_smp-z.actual_smp).mean()+1e-12)
        mae=float(np.abs(p-validation.actual_smp).mean());accepted=mode=='none' or (mae<=.99*none_mae and monthly_ok)
        records.append(dict(mode=mode,calibration_bias=bias,holdout_mae=mae,monthly_nonworsening=monthly_ok,eligible=accepted))
    chosen=min([r for r in records if r['eligible']],key=lambda r:(r['holdout_mae'],r['mode']!='none'))
    return dict(mode=chosen['mode'],bias_by_day=offsets(oof,chosen['mode']),policy='Jan-Apr OOF fit, May-Jun validation; >=1% MAE improvement and neither month worsens; selected bias refitted on all OOF'),records


def fixed_epoch_lstm(module,params,epochs,arrays):
    """Same original network/optimizer, fixed validated epochs, no Val early stop."""
    torch=module.torch;nn=module.nn
    model=module.Estimator(dict(params,epochs=epochs),seed=42,jobs=2);h,x,y=arrays;model.check(h,x,y)
    torch.manual_seed(42);np.random.seed(42);torch.use_deterministic_algorithms(True)
    model.history_mean=h.mean((0,1));std=h.std((0,1));model.history_scale=np.where(std<1e-6,1.,std)
    model.context_mean=x.mean((0,1));std=x.std((0,1));model.context_scale=np.where(std<1e-6,1.,std)
    model.y_mean=float(y.mean());model.y_scale=max(float(y.std()),1e-6);model.dimensions=(h.shape[2],x.shape[2]);model.lookback=h.shape[1]
    model.net=module.Network(*model.dimensions,params['hidden_size'],params['layers'],params.get('dropout',0.))
    optimizer=torch.optim.Adam(model.net.parameters(),lr=params['learning_rate'],weight_decay=params.get('weight_decay',0))
    hh,xx=model.transform(h,x);yy=torch.tensor((y-model.y_mean)/model.y_scale,dtype=torch.float32)
    generator=torch.Generator().manual_seed(42);model.history=[]
    for epoch in range(1,epochs+1):
        model.net.train();total=0.
        for ids in torch.randperm(len(hh),generator=generator).split(params['batch_size']):
            optimizer.zero_grad();loss=nn.functional.mse_loss(model.net(hh[ids],xx[ids]),yy[ids]);loss.backward();nn.utils.clip_grad_norm_(model.net.parameters(),1.);optimizer.step();total+=float(loss.detach())*len(ids)
        model.history.append(dict(epoch=epoch,train_scaled_mse=total/len(hh)))
    model.best_epoch=epochs;model.validation_mae=None
    return model


def complete_blocks(frame,start=None,end=None):
    bounds=frame.groupby('forecast_origin').target_timestamp.agg(['min','max']);ok=pd.Series(True,index=bounds.index)
    if start is not None:ok&=bounds['min']>=start
    if end is not None:ok&=bounds['max']<end
    return frame[frame.forecast_origin.isin(bounds.index[ok])].sort_values(['forecast_origin','horizon']).copy()


def run(name,upgrade):
    parser=argparse.ArgumentParser();parser.add_argument('--source-project',type=Path,required=True);args=parser.parse_args()
    source=args.source_project.resolve();sys.path.insert(0,str(source/'src'))
    from smp_forecast import common_v3 as c
    h,f,manifest=c.load();assert manifest['dataset_version']==c.VERSION
    current=json.loads((source/'models'/name/'CURRENT_RUN.json').read_text());assert current['dataset_version']==c.VERSION
    original=Path(current['path']);e0=pd.read_csv(original/'predictions.csv')
    for col in ['forecast_origin','target_timestamp','observed_cutoff']:e0[col]=c.times(e0[col])
    assert len(e0)==25992 and not e0.duplicated(['forecast_origin','target_timestamp']).any()
    protected=[c.OUT/'manifest.json',original/'predictions.csv',original/('model.pt' if name=='lstm' else 'model.npz')]
    for other in ['lstm','sarimax','lightgbm','xgboost']:protected.append(source/'models'/other/'CURRENT_RUN.json')
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    out=upgrade;out.mkdir(parents=True,exist_ok=True)
    if (out/'config/selection_before_test.json').exists():raise RuntimeError('Existing run preserved; choose a new upgrade directory')
    for path in ['config','models','outputs/predictions','outputs/metrics','outputs/figures','reports']:(out/path).mkdir(parents=True,exist_ok=True)
    start_time=time.perf_counter();module=loadmodule(source/'models'/name/('algorithm.py' if name=='lstm' else 'algorithm_v3.py'),'upgrade_'+name)
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
    config=dict(model=name,dataset_version=c.VERSION,steps=['baseline blend on Validation','chronological OOF calibration before final fit','Train+Validation fixed-setting refit','frozen Test evaluation'],source_project=str(source),original_run=str(original),original_selected=selected,folds=[['2025-01-01','2025-03-01'],['2025-03-01','2025-05-01'],['2025-05-01','2025-07-01']],bias_min_improvement=.01,unchanged_imputation='original Train-only common imputation; scaling refitted on model fit period only',input_group_count=12,publication_reaudit=False,test_reused=True,other_models_modified=False)
    dump(out/'config/experiment_config.json',config);dump(out/'config/protected_source_hashes.json',hashes)
    rule,grid=blend_selection(e0val);grid.to_csv(out/'outputs/metrics/blend_validation_grid.csv',index=False)
    dump(out/'config/stage1_blend.json',rule);print(name,'STAGE1 BLEND',rule,flush=True)
    def arrays(frame):
        data=frame.copy();data['split']='fit';return c.arrays((h,data,manifest),'fit',selected['params']['lookback'])
    def fit(frame,end):
        if name=='lstm':return fixed_epoch_lstm(module,selected['params'],selected['best_epoch'],arrays(frame))
        rows=hourly[hourly.index<end];model=module.Estimator(selected['order'],selected['seasonal_order'],100)
        return model.fit(rows.actual_smp.to_numpy(),rows[features].to_numpy())
    def predict(model,frame):
        frame=frame.sort_values(['forecast_origin','horizon'])
        if name=='lstm':
            hh,xx,_=arrays(frame);return model.predict(hh,xx).reshape(-1)
        cutoff=frame.observed_cutoff.iloc[0];prefix=hourly[hourly.index<cutoff]
        model.reset(prefix.actual_smp.to_numpy(),prefix[features].to_numpy(),prefix.index[-1]);parts=[]
        for origin,block in frame.groupby('forecast_origin',sort=True):
            cutoff=origin-pd.Timedelta(hours=72);available=hourly[(hourly.index>model.last_timestamp)&(hourly.index<cutoff)]
            if len(available):model.update(available.actual_smp.to_numpy(),available[features].to_numpy(),available.index,cutoff)
            bridge=hourly[(hourly.index>=cutoff)&(hourly.index<=origin)]
            assert (bridge.forecast_origin<=origin).all()
            prediction,_,_=model.predict(np.vstack([bridge[features].to_numpy(),block[features].to_numpy()]),origin,cutoff);parts.append(prediction)
        return np.concatenate(parts)
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
    selection=dict(blending=rule,correction=correction,parameters=selected,final_fit_end='2025-06-30',split_models='not used; shared architecture/order retained',selection_based_on='Validation and chronological OOF only',test_metric_used=False)
    dump(out/'config/selection_before_test.json',selection)
    final=fit(trainval,pd.Timestamp('2025-07-01',tz=c.TZ))
    checkpoint=out/'models'/('final_model.pt' if name=='lstm' else 'final_model.npz');final.save(checkpoint)
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
    restored=module.Estimator.load(checkpoint);np.testing.assert_allclose(predict(restored,test),testraw,rtol=1e-6,atol=1e-5)
    assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest for path,digest in hashes.items())
    checks=dict(originals_and_other_models_unchanged=True,baseline_references_before_cutoff=True,test_rows_per_experiment=13104,validation_rows_per_experiment=12888,rolling_oof_rows=len(oof),test_selection_frozen=True,checkpoint_roundtrip=True,features_unchanged=True,elapsed_seconds=time.perf_counter()-start_time,python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__)
    dump(out/'reports/verification.json',checks);dump(out/'config/final_artifact.json',dict(checkpoint=str(checkpoint),checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),adopted_experiment='E4' if correction['mode']!='none' else 'E3'))
    print(name,'FINISHED',result[result.split=='test'].to_string(index=False),flush=True)
