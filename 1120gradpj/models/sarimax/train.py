"""Shared v3 constrained SARIMAX, causal state filtering and 145h bridge forecast."""
import argparse,hashlib,json,platform,sys,time
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'src'))
from smp_forecast import common_v3 as contract
from algorithm_v3 import Estimator
# Generic score/CSV export without importing the other model's algorithm module.
import importlib.util
spec=importlib.util.spec_from_file_location('lstm_export_helpers',ROOT/'models/lstm/train_v2.py')
# The helper module imports algorithm.Estimator; preserve SARIMAX's own module namespace.
from algorithm import Estimator as LegacyEstimator
helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
export=helpers.export


def prepare(bundle):
    history,future,manifest=bundle
    hourly=future.sort_values('forecast_origin').drop_duplicates('target_timestamp',keep='last').set_index('target_timestamp').sort_index()
    features=manifest['context_features']
    if not (hourly.index.to_series().diff().iloc[1:]==pd.Timedelta(hours=1)).all():raise ValueError('Hourly exog grid is not continuous')
    train=hourly[hourly.split=='train']
    return hourly,features,train


def evaluate(model,bundle,hourly,features,split):
    _,future,manifest=bundle;data=future[future.split==split].sort_values(['forecast_origin','horizon']);frames=[]
    first=data.forecast_origin.iloc[0];cutoff=first-pd.Timedelta(hours=72)
    prefix=hourly[hourly.index<cutoff]
    model.reset(prefix.actual_smp.to_numpy(),prefix[features].to_numpy(),prefix.index[-1])
    for n,(origin,block) in enumerate(data.groupby('forecast_origin',sort=True),1):
        cutoff=origin-pd.Timedelta(hours=72)
        observed=hourly[(hourly.index>model.last_timestamp)&(hourly.index<cutoff)]
        if len(observed):model.update(observed.actual_smp.to_numpy(),observed[features].to_numpy(),observed.index,cutoff)
        # No observed y is supplied across the bridge or future forecast range.
        bridge=hourly.loc[(hourly.index>=cutoff)&(hourly.index<=origin)]
        if (bridge.forecast_origin>origin).any():raise ValueError('Future issue in bridge')
        x=np.vstack([bridge[features].to_numpy(),block[features].to_numpy()])
        pred,ci,steps=model.predict(x,origin,cutoff)
        frame=block[['split','forecast_origin','observed_cutoff','target_timestamp','horizon','forecast_day','actual_smp','baseline_origin_day','baseline_weekly']].copy()
        frame['dataset_version']=contract.VERSION;frame['model_name']='SARIMAX';frame['predicted_smp']=pred
        frame['lower_95']=ci[:,0];frame['upper_95']=ci[:,1];frame['bridge_hours']=steps
        frame['absolute_error']=np.abs(pred-frame.actual_smp);frame['forecast_date']=frame.target_timestamp.dt.strftime('%Y-%m-%d')
        frame['prediction_status']='ok';frame['fuel_input_policy']=manifest['fuel_policy'];frames.append(frame)
        if n%40==0:print(split,'origins completed',n,'/',data.forecast_origin.nunique(),flush=True)
    return pd.concat(frames,ignore_index=True)


def figures(frame,directory,origin='2025-07-01T23:00:00+09:00'):
    import os
    os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'data/cache/matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import plotly.graph_objects as go
    directory.mkdir(parents=True,exist_ok=True)
    selected=frame[frame.forecast_origin==pd.Timestamp(origin)].sort_values('horizon')
    def comparison(z,name,title):
        fig,ax=plt.subplots(figsize=(12,4));ax.plot(z.target_timestamp,z.actual_smp,label='Actual');ax.plot(z.target_timestamp,z.predicted_smp,label='SARIMAX')
        if name=='selected_72h':
            for k in [24,48]:ax.axvline(z.target_timestamp.iloc[k],color='gray',linestyle='--')
        ax.legend();ax.set_ylabel('SMP (KRW/kWh)');ax.set_title(title);fig.autofmt_xdate();fig.tight_layout();fig.savefig(directory/(name+'.png'));plt.close(fig)
        chart=go.Figure([go.Scatter(x=z.target_timestamp,y=z.actual_smp,name='Actual'),go.Scatter(x=z.target_timestamp,y=z.predicted_smp,name='SARIMAX')]);chart.update_layout(title=title,yaxis_title='SMP (KRW/kWh)')
        if name=='selected_72h':
            for k in [24,48]:chart.add_vline(x=z.target_timestamp.iloc[k].to_pydatetime(),line_dash='dash')
        chart.write_html(str(directory/(name+'.html')),include_plotlyjs=True)
    comparison(selected,'selected_72h',f'72h SARIMAX — MAE {selected.absolute_error.mean():.2f} KRW/kWh; conditional LNG')
    for (split,day),z in frame.groupby(['split','forecast_day']):comparison(z.sort_values('target_timestamp'),f'{split}_D{day}_hourly',f'{split} D+{day}; conditional LNG')
    monthly=frame.assign(month=frame.target_timestamp.dt.strftime('%Y-%m')).groupby(['month','forecast_day']).absolute_error.mean().unstack()
    ax=monthly.plot.bar(figsize=(12,4),ylabel='MAE (KRW/kWh)',title='Validation Jan–Jun | Final Test Jul–Dec');ax.axvline(5.5,color='gray',linestyle='--');ax.figure.tight_layout();ax.figure.savefig(directory/'monthly_mae.png');plt.close(ax.figure)
    for column in ['horizon','forecast_day','target_hour']:
        z=frame.assign(target_hour=frame.target_timestamp.dt.hour).groupby(['split',column]).absolute_error.mean().unstack(0)
        z.to_csv(directory.parent/(column+'_mae.csv'));ax=z.plot(figsize=(10,4),ylabel='MAE (KRW/kWh)');ax.figure.tight_layout();ax.figure.savefig(directory/(column+'_mae.png'));plt.close(ax.figure)
    ax=frame.plot.scatter(x='actual_smp',y='predicted_smp',s=3,alpha=.2);ax.figure.tight_layout();ax.figure.savefig(directory/'scatter.png');plt.close(ax.figure)


def main():
    global contract
    parser=argparse.ArgumentParser();parser.add_argument('--dataset-version',choices=['v3','v4'],default='v3');parser.add_argument('--audit-only',action='store_true');args=parser.parse_args()
    if args.dataset_version=='v4':
        from smp_forecast import common_v4 as contract
    tag=args.dataset_version
    bundle=contract.load();hourly,features,train=prepare(bundle)
    if bundle[2]['all_groups']!=list(range(1,13)):raise ValueError('Input group contract mismatch')
    print('Training hourly samples',len(train),'exog',len(features),flush=True)
    if args.audit_only:return
    run=HERE/'outputs'/contract.VERSION/pd.Timestamp.now(tz=contract.TZ).strftime('%Y%m%dT%H%M%S');run.mkdir(parents=True,exist_ok=False)
    candidates=[dict(order=(1,0,0),seasonal_order=(1,0,0,24)),dict(order=(1,0,1),seasonal_order=(1,0,0,24)),dict(order=(2,0,0),seasonal_order=(1,0,0,24))]
    contract.dump(run/'config_before_training.json',dict(candidates=candidates,maxiter=100,selection='Validation MAE',beta_estimator='Train-only min-norm OLS, rcond=1e-10; fixed in conditional SARIMAX MLE',features=features,seed='deterministic numerical fit'))
    best=None;results=[];start=time.perf_counter()
    for n,params in enumerate(candidates,1):
        print('CANDIDATE',n,params,flush=True);ts=time.perf_counter()
        try:
            model=Estimator(**params,maxiter=100).fit(train.actual_smp.to_numpy(),train[features].to_numpy())
            print('FITTED',n,'rank',model.rank,'seconds',time.perf_counter()-ts,flush=True)
            validation=evaluate(model,bundle,hourly,features,'validation');mae=float(validation.absolute_error.mean())
            results.append(dict(params=params,validation_mae=mae,rank=int(model.rank),constant_features=[features[i] for i in model.constant_indices],converged=model.converged,warnings=model.warnings,seconds=time.perf_counter()-ts,status='ok'))
            if best is None or mae<best[0]:best=(mae,model,validation)
        except (ValueError,RuntimeError,np.linalg.LinAlgError) as exc:
            results.append(dict(params=params,status='failed',reason=str(exc)))
        contract.dump(run/'candidate_results.json',results);print('CANDIDATE DONE',results[-1],flush=True)
    if best is None:raise RuntimeError('All SARIMAX candidates failed; no final evaluation')
    mae,model,validation=best;model.save(run/'model.npz')
    contract.dump(run/'selected_before_test.json',dict(order=model.order,seasonal_order=model.seasonal_order,validation_mae=mae))
    test=evaluate(model,bundle,hourly,features,'test');frame=pd.concat([validation,test],ignore_index=True)
    metrics=export(frame,run);figures(frame,run/'figures')
    reports=HERE/'reports'/('v4_generation_update' if tag=='v4' else '');reports.mkdir(parents=True,exist_ok=True)
    for name in ['overall','forecast_days','monthly','horizons','daily']:metrics[name].to_csv(reports/(tag+'_'+name+'_metrics.csv'),index=False)
    experiment=dict(dataset_version=contract.VERSION,source_commit=contract.SHA,order=model.order,seasonal_order=model.seasonal_order,beta_estimator='two-stage fixed OLS; conditional MLE ARIMA',rank=int(model.rank),features=features,python=platform.python_version(),statsmodels=statsmodels.__version__,numpy=np.__version__,pandas=pd.__version__,seconds=time.perf_counter()-start,manifest_sha256=hashlib.sha256((contract.OUT/'manifest.json').read_bytes()).hexdigest(),source_code_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [HERE/'train.py',HERE/'algorithm_v3.py']},training_performed=True,test_refit=False)
    contract.dump(run/'experiment.json',experiment)
    contract.dump(reports/f'latest_run_{tag}.json',dict(path=str(run),metrics=metrics['overall'].to_dict('records'),experiment=experiment))
    print(metrics['overall'].to_string(index=False),flush=True);print('RESULTS',run,flush=True)

if __name__=='__main__':main()
