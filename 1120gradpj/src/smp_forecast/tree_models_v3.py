"""Common v3 direct tree regression: exactly the same 83 context features.

This module does not collect, impute, or aggregate sources again. It reads the
frozen common matrix, selects only by Validation, then evaluates Test once.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,platform,time,warnings
import numpy as np
import pandas as pd
from . import common_v3 as contract


def matrices(future,manifest,split):
    frame=future[future.split==split].sort_values(['forecast_origin','horizon']).copy()
    x=frame[manifest['context_features']].to_numpy(dtype=np.float32);y=frame.actual_smp.to_numpy(dtype=np.float32)
    if not len(frame) or not np.isfinite(x).all() or not np.isfinite(y).all():raise ValueError('Empty/nonfinite tree inputs')
    return frame,x,y


def candidates(name):
    if name=='xgboost':
        return [dict(n_estimators=1200,learning_rate=.03,max_depth=3,min_child_weight=20,subsample=.85,colsample_bytree=.85,reg_lambda=10,reg_alpha=.1),dict(n_estimators=1200,learning_rate=.03,max_depth=5,min_child_weight=30,subsample=.85,colsample_bytree=.85,reg_lambda=20,reg_alpha=.1),dict(n_estimators=1000,learning_rate=.05,max_depth=4,min_child_weight=50,subsample=.8,colsample_bytree=.8,reg_lambda=30,reg_alpha=1)]
    return [dict(n_estimators=1200,learning_rate=.03,num_leaves=15,max_depth=5,min_child_samples=100,subsample=.85,subsample_freq=1,colsample_bytree=.85,reg_lambda=10,reg_alpha=.1),dict(n_estimators=1200,learning_rate=.03,num_leaves=31,max_depth=6,min_child_samples=150,subsample=.85,subsample_freq=1,colsample_bytree=.85,reg_lambda=20,reg_alpha=.1),dict(n_estimators=1000,learning_rate=.05,num_leaves=15,max_depth=5,min_child_samples=200,subsample=.8,subsample_freq=1,colsample_bytree=.8,reg_lambda=30,reg_alpha=1)]


def factory(name):
    path=contract.ROOT/'models'/name/'algorithm.py';spec=importlib.util.spec_from_file_location(name+'_factory',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m.create


def fit(name,params,x,y,vx,vy):
    if name=='xgboost':
        model=factory(name)(dict(params,tree_method='hist',eval_metric='mae',early_stopping_rounds=40),seed=42,jobs=2)
        model.fit(x,y,eval_set=[(vx,vy)],verbose=False)
        rounds=int(model.best_iteration)+1
    else:
        import lightgbm as lgb
        model=factory(name)(dict(params,objective='regression',metric='mae',verbosity=-1),seed=42,jobs=2)
        model.fit(x,y,eval_set=[(vx,vy)],eval_metric='mae',callbacks=[lgb.early_stopping(40,first_metric_only=True,verbose=False)])
        rounds=int(model.best_iteration_)
    return model,rounds


def score(frame):
    e=frame.predicted_smp-frame.actual_smp;y=frame.actual_smp;den=float(((y-y.mean())**2).sum())
    r=dict(rows=len(frame),mae=float(np.abs(e).mean()),rmse=float(np.sqrt((e**2).mean())),r2=1-float((e**2).sum())/den if den else None,coverage=1.)
    for col in ['baseline_origin_day','baseline_weekly']:
        b=float(np.abs(frame[col]-y).mean());r[col+'_mae']=b;r[col+'_improvement_pct']=100*(1-r['mae']/b) if b else None
    return r


def export(frame,run):
    frame.to_csv(run/'predictions.csv',index=False);frame=frame.copy();frame['target_month']=frame.target_timestamp.dt.strftime('%Y-%m');frame['target_hour']=frame.target_timestamp.dt.hour
    metrics={}
    for name,columns in [('overall',['split']),('daily',['split','forecast_origin']),('monthly',['split','target_month','forecast_day']),('forecast_days',['split','forecast_day']),('horizons',['split','horizon']),('target_hour',['split','target_hour'])]:
        rows=[]
        for keys,z in frame.groupby(columns):
            if not isinstance(keys,tuple):keys=(keys,)
            rows.append(dict(zip(columns,keys),**score(z)))
        metrics[name]=pd.DataFrame(rows);metrics[name].to_csv(run/(name+'_metrics.csv'),index=False)
    return metrics


def figures(frame,directory,name):
    os.environ.setdefault('MPLCONFIGDIR',str(contract.ROOT/'data/cache/matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import plotly.graph_objects as go
    directory.mkdir(parents=True,exist_ok=True)
    def comparison(z,title,file):
        fig,ax=plt.subplots(figsize=(12,4));ax.plot(z.target_timestamp,z.actual_smp,label='Actual');ax.plot(z.target_timestamp,z.predicted_smp,label=name)
        chart=go.Figure([go.Scatter(x=z.target_timestamp,y=z.actual_smp,name='Actual'),go.Scatter(x=z.target_timestamp,y=z.predicted_smp,name=name)])
        if file=='selected_72h':
            for k in [24,48]:
                ax.axvline(z.target_timestamp.iloc[k],color='gray',linestyle='--');chart.add_vline(x=z.target_timestamp.iloc[k].to_pydatetime(),line_dash='dash')
        ax.legend();ax.set_ylabel('SMP (KRW/kWh)');ax.set_title(title);fig.autofmt_xdate();fig.tight_layout();fig.savefig(directory/(file+'.png'));plt.close(fig)
        chart.update_layout(title=title,yaxis_title='SMP (KRW/kWh)');chart.write_html(str(directory/(file+'.html')),include_plotlyjs=True)
    selected=frame[frame.forecast_origin==pd.Timestamp('2025-07-01T23:00:00+09:00')]
    comparison(selected,f'{name} 72h — MAE {selected.absolute_error.mean():.2f} KRW/kWh; conditional LNG','selected_72h')
    for (split,day),z in frame.groupby(['split','forecast_day']):comparison(z.sort_values('target_timestamp'),f'{name} {split} D+{day}; conditional LNG',f'{split}_D{day}_hourly')
    monthly=frame.assign(month=frame.target_timestamp.dt.strftime('%Y-%m')).groupby(['month','forecast_day']).absolute_error.mean().unstack()
    ax=monthly.plot.bar(figsize=(12,4),ylabel='MAE (KRW/kWh)',title=name+' — Validation Jan–Jun | Test Jul–Dec');ax.axvline(5.5,color='gray',linestyle='--');ax.figure.tight_layout();ax.figure.savefig(directory/'monthly_mae.png');plt.close(ax.figure)
    for col in ['horizon','forecast_day','target_hour']:
        z=frame.assign(target_hour=frame.target_timestamp.dt.hour).groupby(['split',col]).absolute_error.mean().unstack(0);ax=z.plot(figsize=(10,4),ylabel='MAE (KRW/kWh)');ax.figure.tight_layout();ax.figure.savefig(directory/(col+'_mae.png'));plt.close(ax.figure)
    ax=frame.plot.scatter(x='actual_smp',y='predicted_smp',s=3,alpha=.2);ax.figure.tight_layout();ax.figure.savefig(directory/'scatter.png');plt.close(ax.figure)


def run(name):
    parser=argparse.ArgumentParser();parser.add_argument('--audit-only',action='store_true');args=parser.parse_args()
    history,future,manifest=contract.load()
    if manifest['dataset_version']!=contract.VERSION or manifest['all_groups']!=list(range(1,13)):raise ValueError('Expected v3 with all12 groups')
    frames={s:matrices(future,manifest,s) for s in ['train','validation','test']}
    for s,(f,x,y) in frames.items():print(s,len(f),'features',x.shape[1],flush=True)
    if args.audit_only:return
    here=contract.ROOT/'models'/name;reports=here/'reports/v3_common';reports.mkdir(parents=True,exist_ok=True)
    run=here/'outputs'/contract.VERSION/pd.Timestamp.now(tz=contract.TZ).strftime('%Y%m%dT%H%M%S');run.mkdir(parents=True,exist_ok=False)
    grid=candidates(name);config=dict(model=name,dataset_version=contract.VERSION,candidates=grid,seed=42,jobs=2,early_stopping_rounds=40,selection='Validation MAE only',features=manifest['context_features'],structure='one direct regression per target row; no recursion; 72 target rows per origin',scaling='not needed for trees; frozen common Train-fitted imputation retained',test_refit=False)
    contract.dump(run/'config_before_training.json',config)
    _,x,y=frames['train'];_,vx,vy=frames['validation'];start=time.perf_counter();best=None;records=[]
    for number,params in enumerate(grid,1):
        print('CANDIDATE',number,params,flush=True)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always');model,rounds=fit(name,params,x,y,vx,vy);pred=model.predict(vx)
        mae=float(np.abs(pred-vy).mean());records.append(dict(params=params,best_rounds=rounds,validation_mae=mae,warnings=sorted(set(str(w.message) for w in caught))))
        contract.dump(run/'candidate_results.json',records);print('CANDIDATE DONE',number,'rounds',rounds,'validation_mae',mae,flush=True)
        if best is None or mae<best[0]:best=(mae,model,rounds,params)
    mae,model,rounds,params=best
    contract.dump(run/'selected_before_test.json',dict(params=params,best_rounds=rounds,validation_mae=mae))
    if name=='xgboost':model.save_model(run/'model.ubj')
    else:model.booster_.save_model(str(run/'model.txt'),num_iteration=rounds)
    outputs=[]
    for split in ['validation','test']:
        frame,xx,yy=frames[split];frame=frame[['split','forecast_origin','observed_cutoff','target_timestamp','horizon','forecast_day','actual_smp','baseline_origin_day','baseline_weekly']].copy()
        frame['predicted_smp']=model.predict(xx);frame['absolute_error']=np.abs(frame.predicted_smp-frame.actual_smp)
        frame['dataset_version']=contract.VERSION;frame['model_name']='XGBoost' if name=='xgboost' else 'LightGBM';frame['forecast_date']=frame.target_timestamp.dt.strftime('%Y-%m-%d');frame['prediction_status']='ok';frame['fuel_input_policy']=manifest['fuel_policy'];outputs.append(frame)
    allrows=pd.concat(outputs,ignore_index=True);metrics=export(allrows,run);figures(allrows,run/'figures',allrows.model_name.iloc[0])
    import xgboost,lightgbm
    experiment=dict(config=config,selected=params,best_rounds=rounds,seconds=time.perf_counter()-start,python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,xgboost=xgboost.__version__,lightgbm=lightgbm.__version__,manifest_sha256=hashlib.sha256((contract.OUT/'manifest.json').read_bytes()).hexdigest(),source_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),training_performed=True,test_refit=False)
    contract.dump(run/'experiment.json',experiment)
    for metric in metrics:metrics[metric].to_csv(reports/(metric+'_metrics.csv'),index=False)
    contract.dump(reports/'latest_run.json',dict(path=str(run),dataset_version=contract.VERSION,metrics=metrics['overall'].to_dict('records'),experiment=experiment))
    print(metrics['overall'].to_string(index=False),flush=True);print('RESULTS',run,flush=True)
