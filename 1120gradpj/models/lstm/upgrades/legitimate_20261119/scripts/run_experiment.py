"""Predeclared LSTM improvements; no candidate selection from 2025H2 metrics."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys,time
import numpy as np
import pandas as pd
from estimator import Estimator
HERE=Path(__file__).resolve().parents[1]
MODEL_BASE=HERE.parents[2]
OLD_UPGRADE=HERE.parent/'upgrade_72h_20261119'
spec=importlib.util.spec_from_file_location('shared_validation',HERE.parent/'upgrade_72h_20261119/scripts/protocol.py');shared=importlib.util.module_from_spec(spec);spec.loader.exec_module(shared)
dump=shared.dump;metrics=shared.metrics;blocks=shared.complete_blocks


def candidates():
    grid=[('absolute_huber48','absolute','huber',48,32,.001),('residual_mse48','weekly_residual','mse',48,32,.001),('residual_mae48','weekly_residual','mae',48,32,.001),('residual_huber48','weekly_residual','huber',48,32,.001),('residual_huber168','weekly_residual','huber',168,32,.001),('residual_mae168','weekly_residual','mae',168,64,.0005)]
    return [dict(id=k,target=t,loss=l,lookback=b,hidden=h,lr=r,max_epochs=60,patience=8) for k,t,l,b,h,r in grid]


def gate(candidate,reference):
    if not candidate.target_timestamp.between(pd.Timestamp('2025-05-01',tz='Asia/Seoul'),pd.Timestamp('2025-07-01',tz='Asia/Seoul'),inclusive='left').all():raise ValueError('Confirmation must be May-Jun, never Test')
    base=float(np.abs(reference.predicted_smp-reference.actual_smp).mean());score=float(np.abs(candidate.predicted_smp-candidate.actual_smp).mean())
    monthly=[]
    for month,z in candidate.groupby(candidate.target_timestamp.dt.month):
        r=reference[reference.target_timestamp.dt.month==month]
        monthly.append(dict(month=int(month),candidate_mae=float(np.abs(z.predicted_smp-z.actual_smp).mean()),reference_mae=float(np.abs(r.predicted_smp-r.actual_smp).mean())))
    return dict(accepted=bool(score<=.99*base and all(r['candidate_mae']<=r['reference_mae'] for r in monthly)),candidate_mae=score,reference_mae=base,monthly=monthly,rule='>=1% holdout MAE improvement, neither May nor June worsens')


def main():
    global HERE
    parser=argparse.ArgumentParser();parser.add_argument('--source-project',type=Path,required=True);parser.add_argument('--output-dir',type=Path);args=parser.parse_args()
    if args.output_dir:
        HERE=args.output_dir.resolve()
        if HERE.exists() and any(HERE.iterdir()):raise RuntimeError('New output directory must be empty')
    source=args.source_project.resolve();sys.path.insert(0,str(source/'src'))
    from smp_forecast import common_v3 as c
    if (HERE/'config/protocol_before_training.json').exists():raise RuntimeError('Existing experiment preserved; use a new output folder for another experiment')
    for folder in ['config','models','outputs/predictions','outputs/metrics','outputs/figures','reports']:(HERE/folder).mkdir(parents=True,exist_ok=True)
    start=time.perf_counter();history,future,manifest=c.load();assert manifest['dataset_version']==c.VERSION
    old_upgrade=OLD_UPGRADE;sarimax=MODEL_BASE/'sarimax/upgrades/upgrade_72h_20261119'
    raw_original=Path(json.loads((source/'models/lstm/CURRENT_RUN.json').read_text())['path']);assert c.VERSION in str(raw_original)
    protected=[c.OUT/'manifest.json',old_upgrade/'models/final_model.pt',old_upgrade/'outputs/predictions/final_test_predictions.csv.gz',sarimax/'models/final_model.npz',raw_original/'model.pt']
    for name in ['lstm','sarimax','xgboost','lightgbm']:protected.append(source/'models'/name/'CURRENT_RUN.json')
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    dump(HERE/'config/local_paths.json',dict(source_project=str(source)))
    protocol=dict(dataset_version=c.VERSION,candidates=candidates(),tuning_period=['2025-01-01','2025-04-30'],confirmation_period=['2025-05-01','2025-06-30'],alpha_grid=[round(float(x),1) for x in np.linspace(0,1,11)],seed=42,jobs=2,fit_period='Train only during tuning; Train+Jan-Apr for confirmation; Train+Validation final',acceptance='>=1% May-Jun MAE reduction against cached previous-upgrade rolling fold3; no month worsens',input_groups=12,context_features=manifest['context_features'],new_external_data=False,baseline_usage='existing known weekly SMP baseline, optional residual output skip connection; no new raw source',test_rule='single frozen candidate; no Test-driven further trials; previous Test already observed')
    dump(HERE/'config/protocol_before_training.json',protocol)
    f=future.sort_values(['forecast_origin','horizon']);train=f[f.split=='train'];val=f[f.split=='validation']
    boundary=pd.Timestamp('2025-05-01',tz=c.TZ)
    tune=blocks(val,end=boundary);confirm=blocks(val,start=boundary)
    frames=dict(train=train,tune=tune,confirm=confirm,train_apr=blocks(f[f.split.isin(['train','validation'])],end=boundary),trainval=f[f.split.isin(['train','validation'])])
    cache={}
    def arrays(frame,lookback):
        data=frame.copy();data['split']='selected';h,x,_=c.arrays((history,data,manifest),'selected',lookback)
        z=data.sort_values(['forecast_origin','horizon'])
        return h,x,z.actual_smp.to_numpy().reshape(-1,72),z.baseline_weekly.to_numpy().reshape(-1,72)
    def data(phase,lookback):
        key=(phase,lookback)
        if key not in cache:cache[key]=arrays(frames[phase],lookback)
        return cache[key]
    # No Test array or Test metric is created in this selection section.
    records=[];selection=None
    for params in protocol['candidates']:
        print('TUNING',params['id'],flush=True)
        model=Estimator(params).fit(*data('train',params['lookback']),validation=data('tune',params['lookback']))
        h,x,y,b=data('tune',params['lookback']);prediction=model.predict(h,x,b)
        weights=[]
        for alpha in protocol['alpha_grid']:weights.append(dict(alpha=alpha,mae=float(np.abs(alpha*prediction+(1-alpha)*b-y).mean())))
        chosen=min(weights,key=lambda r:(r['mae'],r['alpha']))
        record=dict(params=params,best_epoch=model.best_epoch,raw_tuning_mae=float(np.abs(prediction-y).mean()),blending=chosen,weights=weights,history=model.history)
        records.append(record);model.save(HERE/'models'/(params['id']+'_tuning.pt'))
        if selection is None or (chosen['mae'],chosen['alpha'])<(selection['blending']['mae'],selection['blending']['alpha']):selection=record
        dump(HERE/'outputs/metrics/tuning_candidates.json',records)
        print('TUNED',params['id'],'raw',record['raw_tuning_mae'],'mixed',chosen,'epoch',model.best_epoch,flush=True)
    freeze={k:selection[k] for k in ['params','best_epoch','blending']};dump(HERE/'config/selection_before_confirmation.json',freeze)
    # Confirm only one already-selected candidate; do not try runners-up on May-Jun.
    model=Estimator(selection['params']).fit(*data('train_apr',selection['params']['lookback']),epochs=selection['best_epoch'])
    h,x,y,b=data('confirm',selection['params']['lookback']);raw=model.predict(h,x,b);alpha=selection['blending']['alpha']
    candidate=confirm[['forecast_origin','target_timestamp','horizon','forecast_day','actual_smp']].copy();candidate['predicted_smp']=(alpha*raw+(1-alpha)*b).reshape(-1)
    reference=pd.read_csv(old_upgrade/'outputs/predictions/rolling_oof.csv.gz');reference['target_timestamp']=c.times(reference.target_timestamp);reference['forecast_origin']=c.times(reference.forecast_origin);reference=reference[reference.fold==3].sort_values(['forecast_origin','horizon'])
    assert list(zip(candidate.forecast_origin,candidate.target_timestamp))==list(zip(reference.forecast_origin,reference.target_timestamp))
    decision=gate(candidate,reference);candidate.to_csv(HERE/'outputs/predictions/confirmation_candidate.csv',index=False)
    print('CONFIRMATION',decision,flush=True)
    final_policy=dict(chosen_candidate=freeze,confirmation=decision,adopt='candidate' if decision['accepted'] else 'previous_lstm_upgrade',fit_target_end='2025-06-30',test_used_for_choice=False,no_further_candidate_search=True)
    dump(HERE/'config/final_policy_before_test.json',final_policy)
    # Fixed epochs and policy. The complete, previously-seen H2 period is evaluated once.
    final=Estimator(selection['params']).fit(*data('trainval',selection['params']['lookback']),epochs=selection['best_epoch']);final.save(HERE/'models/final_candidate.pt')
    test=f[f.split=='test'].copy();h,x,y,b=arrays(test,selection['params']['lookback']);raw=final.predict(h,x,b);mixed=alpha*raw+(1-alpha)*b
    previous=pd.read_csv(old_upgrade/'outputs/predictions/final_test_predictions.csv.gz');previous=previous[previous.experiment_id=='E3'].copy()
    benchmark=pd.read_csv(sarimax/'outputs/predictions/final_test_predictions.csv.gz');benchmark=benchmark[benchmark.experiment_id=='E3'].copy()
    for frame in [previous,benchmark]:
        frame['forecast_origin']=c.times(frame.forecast_origin);frame['target_timestamp']=c.times(frame.target_timestamp)
        assert list(zip(test.forecast_origin,test.target_timestamp))==list(zip(frame.forecast_origin,frame.target_timestamp))
    variants=dict(candidate_raw=raw.reshape(-1),candidate_mixed=mixed.reshape(-1),previous_lstm=previous.predicted_smp.to_numpy(),sarimax_frozen=benchmark.predicted_smp.to_numpy(),weekly_baseline=b.reshape(-1))
    variants['adopted_lstm']=variants['candidate_mixed'] if decision['accepted'] else variants['previous_lstm']
    outputs=[];scores=[]
    for name,p in variants.items():
        rows=test[['forecast_origin','observed_cutoff','target_timestamp','horizon','forecast_day','actual_smp']].copy();rows['predicted_smp']=p;rows['absolute_error']=np.abs(p-rows.actual_smp);rows['experiment_id']=name;rows['dataset_version']=c.VERSION;rows['weekly_baseline']=b.reshape(-1);rows['candidate_alpha']=alpha;outputs.append(rows)
        scores.append(dict(experiment_id=name,**metrics(rows.actual_smp,p)))
    output=pd.concat(outputs,ignore_index=True);output.to_csv(HERE/'outputs/predictions/test_predictions.csv',index=False);pd.DataFrame(scores).to_csv(HERE/'outputs/metrics/test_metrics.csv',index=False)
    for name,cols in [('by_forecast_day',['forecast_day']),('by_horizon',['horizon']),('by_month',['month'])]:
        temp=output.assign(month=output.target_timestamp.dt.strftime('%Y-%m'));rows=[]
        for keys,z in temp.groupby(['experiment_id']+cols):rows.append(dict(zip(['experiment_id']+cols,keys),**metrics(z.actual_smp,z.predicted_smp)))
        pd.DataFrame(rows).to_csv(HERE/'outputs/metrics'/(name+'.csv'),index=False)
    # Serialization and future-target mutation tests do not refit or select anything.
    restored=Estimator.load(HERE/'models/final_candidate.pt');np.testing.assert_allclose(restored.predict(h,x,b),raw,rtol=1e-6,atol=1e-5)
    one=test[test.forecast_origin==test.forecast_origin.iloc[0]].copy();before=arrays(one,selection['params']['lookback']);one['actual_smp']=-1e9;after=arrays(one,selection['params']['lookback'])
    np.testing.assert_array_equal(before[0],after[0]);np.testing.assert_array_equal(before[1],after[1]);np.testing.assert_array_equal(before[3],after[3]);assert not np.array_equal(before[2],after[2])
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==v for p,v in hashes.items())
    checks=dict(checkpoint_roundtrip=True,future_actual_mutation_invariant_inputs=True,protected_files_unchanged=True,test_rows_per_variant=13104,tuning_rows=len(tune),confirmation_rows=len(confirm),excluded_validation_boundary_rows=len(val)-len(tune)-len(confirm),selection_frozen_before_confirmation=True,policy_frozen_before_test=True,seconds=time.perf_counter()-start,torch=__import__('torch').__version__,numpy=np.__version__,pandas=pd.__version__)
    dump(HERE/'reports/verification.json',checks)
    dump(HERE/'config/protected_hashes.json',{str(Path(p).relative_to(source.parent)) if Path(p).is_relative_to(source.parent) else 'prior_upgrade/'+str(Path(p).relative_to(MODEL_BASE)):v for p,v in hashes.items()})
    print(pd.DataFrame(scores).to_string(index=False),flush=True);print('FINISHED adopted',final_policy['adopt'],flush=True)

if __name__=='__main__':main()
