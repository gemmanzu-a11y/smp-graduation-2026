"""Audit-first LSTM pipeline. Exit 2 means no real training or final results were produced."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time
import warnings
import numpy as np
import pandas as pd
import torch

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'src'))
from smp_forecast import common_v2 as contract
from smp_forecast.http import write_json,now
from algorithm import Estimator


def audit(shared,cfg):
    issues,bundle=contract.inspect(shared,cfg)
    inventory={
        'demand_actual':'EPSIS 결측 1,095시간; 공식 전국 수요 후보와 공통 선택 미확정',
        'demand_forecast':'2023~2025 공식 연간 자료 확보; D+2/3 사용 규칙 필요',
        'holidays':'공식 API 자료 확보; 공통 버전 연결 필요',
        'calendar':'날짜에서 생성; 공통 인코딩 연결 필요',
        'generation':'표본 API 성공; 전체 기간·단위·범위 검증 필요',
        'renewables':'2023~2025 수집본 존재; 태양광 1시간 결측·버전 차이 검토 필요',
        'reserve':'1,095시간 결측 및 공급능력·수요·예비력 관계 검토 필요',
        'domestic_lng':'지정 HOME 파일과 section_c 정규화본 존재; 동월 값 조건부 정책',
        'oil':'FRED 과거 기록 수집본 존재; D−2·72시간 고정값 사용',
        'international_fuel':'과거 기록 수집본 존재; 오래된 관측값 경과일 보존',
        'weather_actual':'ASOS 이력 존재; 일사량 결측/야간 구분 및 지역 정의 필요',
        'midrange_forecast':'공유 CSV 확보; 일 최저·최고기온 및 날씨·강수확률의 72시간 연결 미확정',
    }
    # Known facts are a diagnostic inventory, never a fabricated replacement for a validated bundle.
    if bundle is None:
        for key in contract.DECISIONS:
            if not any(row['variable']==key for row in issues):
                issues.append(dict(variable=key,reason='확정된 공통 manifest 없음',action='팀 공통 선택·규칙과 근거를 manifest에 기록'))
    state=dict(at=now(),model='LSTM',status='BLOCKED' if issues else 'READY',can_train=not issues,
               model_training_performed=False,shared_directory=str(shared),issues=issues,
               required_sources=contract.SOURCES,inventory=inventory,
               excluded=['EWP solgenKpx','EWP icsrPred/temp/ws','KMA short-range forecast','KPX calorific fuel cost'],
               limitation='동월 LNG 제공 조건부 과거 실험; 운영 공개시각 검증 아님')
    report=HERE/'reports';report.mkdir(exist_ok=True)
    write_json(report/'data_status.json',state)
    lines=['# LSTM 데이터 사전 검사','','상태: '+state['status'],'','실제 SMP 학습·튜닝·평가 미실행.','',
           '| 항목 | 원인 | 조치 |','|---|---|---|']
    lines+=['| '+row['variable']+' | '+row['reason'].replace('|','/')+' | '+row['action']+' |' for row in issues]
    lines+=['','## 수집 현황 참고','']+['- '+key+': '+value for key,value in inventory.items()]
    lines+=['','제외한 동서발전·단기예보·열량단가의 미확보는 차단 사유가 아닙니다.']
    (report/'data_blockers.md').write_text('\n'.join(lines)+'\n')
    return state,bundle


def prediction_rows(model,bundle,cfg,split):
    hourly,future,manifest=bundle;origins=contract.split_origins(cfg,split)
    history,context,y=contract.arrays(hourly,future,origins,model.lookback)
    pred=model.predict(history,context);rows=[]
    for i,origin in enumerate(origins):
        block=future[future.forecast_origin==origin].sort_values('target_timestamp').copy()
        block['actual_smp']=y[i];block['predicted_smp']=pred[i]
        block['dataset_version']=manifest['dataset_version'];block['model_name']='LSTM';block['split']=split
        block['horizon']=np.arange(1,73);block['forecast_day']=np.repeat([1,2,3],24)
        block['forecast_date']=block.target_timestamp.dt.strftime('%Y-%m-%d')
        block['absolute_error']=np.abs(y[i]-pred[i]);block['prediction_status']='ok'
        block['fuel_input_policy']=cfg['fuel_policy'];rows.append(block)
    return pd.concat(rows,ignore_index=True)


def score(frame):
    error=frame.predicted_smp-frame.actual_smp;y=frame.actual_smp.to_numpy();denom=float(((y-y.mean())**2).sum())
    result=dict(rows=len(frame),mae=float(np.abs(error).mean()),rmse=float(np.sqrt((error**2).mean())),
                r2=float(1-(error**2).sum()/denom) if denom>0 else None,coverage=1.0)
    for column in ['baseline_origin_day','baseline_weekly']:
        base=float(np.abs(frame[column]-frame.actual_smp).mean());result[column+'_mae']=base
        result[column+'_improvement_pct']=100*(1-result['mae']/base) if base else None
    return result


def export(frame,directory):
    directory.mkdir(parents=True,exist_ok=True);frame.to_csv(directory/'predictions.csv',index=False)
    frame=frame.copy();frame['target_month']=frame.target_timestamp.dt.strftime('%Y-%m')
    outputs={}
    for name,group in [('overall',['split']),('daily',['split','forecast_origin']),
                       ('daily_horizon',['split','forecast_origin','forecast_day']),
                       ('monthly',['split','target_month','forecast_day']),
                       ('forecast_days',['split','forecast_day']),('horizons',['split','horizon'])]:
        records=[]
        for keys,subset in frame.groupby(group):
            keys=keys if isinstance(keys,tuple) else (keys,)
            records.append(dict(zip(group,keys),**score(subset)))
        outputs[name]=pd.DataFrame(records);outputs[name].to_csv(directory/(name+'_metrics.csv'),index=False)
    return outputs


def figures(frame,directory,selected=None):
    os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'data/cache/matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import plotly.graph_objects as go
    directory.mkdir(parents=True,exist_ok=True)
    def save(data,path,x='target_timestamp'):
        fig,ax=plt.subplots(figsize=(12,4));ax.plot(data[x],data.actual_smp,label='Actual');ax.plot(data[x],data.predicted_smp,label='LSTM')
        ax.set_ylabel('SMP (KRW/kWh)');ax.legend()
        if path.name=='selected_72h':
            for boundary in [24,48]:ax.axvline(data[x].iloc[boundary],color='gray',linestyle='--')
            ax.set_title('72h forecast — D+1 / D+2 / D+3; conditional on target-month LNG')
        fig.autofmt_xdate();fig.tight_layout();fig.savefig(path.with_suffix('.png'));plt.close(fig)
        html=go.Figure([go.Scatter(x=data[x],y=data.actual_smp,name='Actual'),go.Scatter(x=data[x],y=data.predicted_smp,name='LSTM')])
        html.update_layout(title=path.name+' — conditional on target-month LNG',yaxis_title='KRW/kWh')
        if path.name=='selected_72h':
            for boundary in [24,48]:html.add_vline(x=data[x].iloc[boundary].to_pydatetime(),line_dash='dash')
        html.write_html(str(path.with_suffix('.html')),include_plotlyjs=True)
    if selected:
        origin=pd.Timestamp(selected)
        if origin.tzinfo is None:raise ValueError('Selected origin needs timezone')
        subset=frame[frame.forecast_origin==origin]
        if len(subset)!=72:raise ValueError('Selected origin absent from prediction outputs')
        save(subset,directory/'selected_72h')
    for (split,day),data in frame.groupby(['split','forecast_day']):
        data=data.sort_values('target_timestamp');save(data,directory/f'{split}_D{day}_hourly')
        daily=data.assign(target_date=data.target_timestamp.dt.floor('D')).groupby('target_date')[['actual_smp','predicted_smp']].mean().reset_index()
        save(daily,directory/f'{split}_D{day}_daily',x='target_date')
    monthly=frame.assign(month=frame.target_timestamp.dt.strftime('%Y-%m'))
    monthly=monthly.groupby(['month','forecast_day']).absolute_error.mean().unstack()
    ax=monthly.plot.bar(figsize=(12,4),ylabel='MAE (KRW/kWh)');ax.figure.tight_layout();ax.figure.savefig(directory/'monthly_mae.png');plt.close(ax.figure)
    go.Figure([go.Bar(x=monthly.index,y=monthly[col],name='D+'+str(col)) for col in monthly]).write_html(str(directory/'monthly_mae.html'),include_plotlyjs=True)
    for column in ['forecast_day','horizon']:
        metric=frame.groupby(['split',column]).absolute_error.mean().unstack(0)
        ax=metric.plot(figsize=(10,4),ylabel='MAE (KRW/kWh)');ax.figure.tight_layout();ax.figure.savefig(directory/(column+'_mae.png'));plt.close(ax.figure)
    ax=frame.plot.scatter(x='actual_smp',y='predicted_smp',s=3,alpha=.2);ax.figure.savefig(directory/'scatter.png');plt.close(ax.figure)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=ROOT/'configs/lstm.json')
    parser.add_argument('--shared',type=Path);parser.add_argument('--audit-only',action='store_true')
    parser.add_argument('--selected-origin',help='Optional predetermined origin, including +09:00')
    args=parser.parse_args();cfg=json.loads(args.config.read_text())
    shared=args.shared or Path(os.environ.get('SHARED_DATA_DIR',str(ROOT/cfg['shared_directory'])))
    state,bundle=audit(shared,cfg)
    if not state['can_train']:
        print('BLOCKED: 학습 미실행. models/lstm/reports/data_blockers.md 확인');return 2
    if args.audit_only:print('READY: 데이터 검사 통과, 학습 미실행');return 0
    # Verify plotting dependencies before any expensive fitting.
    import plotly
    hourly,future,manifest=bundle;started=time.perf_counter();best=None;candidates=[]
    for candidate in cfg['candidates']:
        lookback=candidate['lookback']
        training=contract.arrays(hourly,future,contract.split_origins(cfg,'train'),lookback)
        validation=contract.arrays(hourly,future,contract.split_origins(cfg,'validation'),lookback)
        try:
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter('always')
                model=Estimator(candidate,cfg['seed'],cfg['jobs']).fit(*training,validation)
            candidates.append(dict(params=candidate,validation_mae=model.validation_mae,best_epoch=model.best_epoch,
                                   status='ok',warnings=[str(item.message) for item in captured]))
        except (ValueError,RuntimeError) as exc:
            candidates.append(dict(params=candidate,status='failed',reason=str(exc)))
            continue
        if best is None or model.validation_mae<best.validation_mae:best=model
    if best is None:
        write_json(HERE/'reports/training_failures.json',candidates)
        raise RuntimeError('All candidates failed; no final results generated')
    # No test information was passed to fit or preprocessing. No train+validation refit.
    run=HERE/'outputs'/manifest['dataset_version']/pd.Timestamp.now(tz='Asia/Seoul').strftime('%Y%m%dT%H%M%S')
    run.mkdir(parents=True,exist_ok=False);best.save(run/'model.pt')
    validation=prediction_rows(best,bundle,cfg,'validation');test=prediction_rows(best,bundle,cfg,'test')
    frame=pd.concat([validation,test],ignore_index=True);metrics=export(frame,run)
    figures(frame,run/'figures',args.selected_origin)
    write_json(run/'experiment.json',dict(dataset_version=manifest['dataset_version'],config=cfg,candidates=candidates,
        history_features=contract.HISTORY,future_features=contract.FUTURE,manifest_sha256=hashlib.sha256((shared/'manifest.json').read_bytes()).hexdigest(),
        python=platform.python_version(),torch=str(torch.__version__),numpy=np.__version__,pandas=pd.__version__,plotly=plotly.__version__,elapsed_seconds=time.perf_counter()-started,
        model_training_performed=True,test_refit=False,limitation=state['limitation']))
    (run/'final_evaluation_report.md').write_text('# LSTM 조건부 과거 평가\n\n'+state['limitation']+'\n\n'+metrics['overall'].to_string(index=False)+'\n')
    print('완료:',run);return 0

if __name__=='__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        (HERE/'reports').mkdir(exist_ok=True)
        write_json(HERE/'reports/execution_failure.json',dict(at=now(),status='FAILED',error_type=type(exc).__name__,reason=str(exc)))
        print('FAILED: reports/execution_failure.json 확인; 최종 결과로 사용하지 마세요')
        raise SystemExit(1)
