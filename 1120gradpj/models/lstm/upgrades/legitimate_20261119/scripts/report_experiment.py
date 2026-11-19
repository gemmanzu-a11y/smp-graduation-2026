"""Publish every tuning result and the failed confirmation without reselecting."""
from pathlib import Path
import argparse,json,gzip,shutil,sys,os
import numpy as np
import pandas as pd
from estimator import Estimator
from run_experiment import metrics,blocks,dump
BASE=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source-project',type=Path,required=True);parser.add_argument('--experiment-dir',type=Path);args=parser.parse_args();root=args.experiment_dir.resolve() if args.experiment_dir else BASE;source=args.source_project.resolve();sys.path.insert(0,str(source/'src'))
    from smp_forecast import common_v3 as c
    history,f,m=c.load();f=f.sort_values(['forecast_origin','horizon']);tune=blocks(f[f.split=='validation'],end=pd.Timestamp('2025-05-01',tz=c.TZ))
    candidates=json.loads((root/'outputs/metrics/tuning_candidates.json').read_text());choice=json.loads((root/'config/selection_before_confirmation.json').read_text());policy=json.loads((root/'config/final_policy_before_test.json').read_text());scores=pd.read_csv(root/'outputs/metrics/test_metrics.csv');checks=json.loads((root/'reports/verification.json').read_text())
    cache={};tuning_rows=[];table=[]
    for record in candidates:
        p=record['params'];lookback=p['lookback']
        if lookback not in cache:
            z=tune.copy();z['split']='selected';h,x,_=c.arrays((history,z,m),'selected',lookback);cache[lookback]=(h,x,z.baseline_weekly.to_numpy().reshape(-1,72))
        h,x,b=cache[lookback];model=Estimator.load(root/'models'/(p['id']+'_tuning.pt'));pred=model.predict(h,x,b).reshape(-1)
        assert abs(float(np.abs(pred-tune.actual_smp).mean())-record['raw_tuning_mae'])<1e-5
        alpha=record['blending']['alpha'];mixed=alpha*pred+(1-alpha)*b.reshape(-1)
        z=tune[['forecast_origin','target_timestamp','horizon','forecast_day','actual_smp']].copy();z['candidate_id']=p['id'];z['predicted_raw']=pred;z['predicted_mixed']=mixed;z['alpha']=alpha;tuning_rows.append(z)
        table.append(dict(candidate_id=p['id'],target=p['target'],loss=p['loss'],lookback=lookback,hidden=p['hidden'],best_epoch=record['best_epoch'],raw_mae=record['raw_tuning_mae'],mixed_mae=record['blending']['mae'],alpha=alpha))
    pd.concat(tuning_rows,ignore_index=True).to_csv(root/'outputs/predictions/tuning_predictions.csv',index=False);table=pd.DataFrame(table);table.to_csv(root/'outputs/metrics/tuning_summary.csv',index=False)
    predictions=pd.read_csv(root/'outputs/predictions/test_predictions.csv')
    predictions['split']='test';predictions['model_name']='LSTM';predictions['candidate_id']=choice['params']['id'];predictions['prediction_status']='ok'
    predictions.to_csv(root/'outputs/predictions/test_predictions.csv',index=False)
    for col in ['forecast_origin','target_timestamp','observed_cutoff']:predictions[col]=c.times(predictions[col])
    # Confirmation results are deliberately not used to select another candidate.
    confirmation=policy['confirmation'];assert policy['adopt']==('candidate' if confirmation['accepted'] else 'previous_lstm_upgrade')
    os.environ.setdefault('MPLCONFIGDIR',str(source/'data/cache/matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import plotly.graph_objects as go
    fig,axes=plt.subplots(1,2,figsize=(14,4))
    table.set_index('candidate_id').mixed_mae.plot.bar(ax=axes[0],title='Jan–Apr tuning only',ylabel='MAE (KRW/kWh)');axes[0].tick_params(axis='x',rotation=35)
    scores.set_index('experiment_id').mae.plot.bar(ax=axes[1],title='H2 reevaluation — candidate NOT adopted' if not confirmation['accepted'] else 'H2 reevaluation',ylabel='MAE (KRW/kWh)');axes[1].tick_params(axis='x',rotation=35)
    fig.tight_layout();fig.savefig(root/'outputs/figures/candidate_comparison.png');plt.close(fig)
    selected=predictions[predictions.forecast_origin==pd.Timestamp('2025-07-01T23:00:00+09:00')]
    fig,ax=plt.subplots(figsize=(13,4));chart=go.Figure();first=selected[selected.experiment_id=='previous_lstm'];ax.plot(first.target_timestamp,first.actual_smp,color='black',label='Actual');chart.add_scatter(x=first.target_timestamp,y=first.actual_smp,name='Actual')
    for name in ['previous_lstm','candidate_mixed','sarimax_frozen','weekly_baseline']:
        z=selected[selected.experiment_id==name];ax.plot(z.target_timestamp,z.predicted_smp,label=name);chart.add_scatter(x=z.target_timestamp,y=z.predicted_smp,name=name)
    for n in [24,48]:ax.axvline(first.target_timestamp.iloc[n],color='gray',linestyle='--');chart.add_vline(x=first.target_timestamp.iloc[n].to_pydatetime(),line_dash='dash')
    ax.set_ylabel('SMP (KRW/kWh)');ax.set_title('Selected 72h — confirmation policy retains previous LSTM');ax.legend();fig.autofmt_xdate();fig.tight_layout();fig.savefig(root/'outputs/figures/selected_72h.png');plt.close(fig);chart.update_layout(yaxis_title='SMP (KRW/kWh)');chart.write_html(str(root/'outputs/figures/selected_72h.html'),include_plotlyjs='cdn')
    monthly=predictions.assign(month=predictions.target_timestamp.dt.strftime('%Y-%m')).groupby(['month','experiment_id']).absolute_error.mean().unstack();ax=monthly[['previous_lstm','candidate_mixed','sarimax_frozen','weekly_baseline']].plot(figsize=(12,4),ylabel='MAE (KRW/kWh)',title='H2 monthly error — no post-Test selection');ax.figure.tight_layout();ax.figure.savefig(root/'outputs/figures/monthly_mae.png');plt.close(ax.figure)
    horizon=predictions.groupby(['horizon','experiment_id']).absolute_error.mean().unstack();ax=horizon[['previous_lstm','candidate_mixed','sarimax_frozen','weekly_baseline']].plot(figsize=(12,4),ylabel='MAE (KRW/kWh)');ax.figure.tight_layout();ax.figure.savefig(root/'outputs/figures/horizon_mae.png');plt.close(ax.figure)
    files=[]
    for file in (root/'outputs/predictions').glob('*.csv'):
        gz=file.with_suffix('.csv.gz')
        with file.open('rb') as inp,gzip.open(gz,'wb') as out:shutil.copyfileobj(inp,out)
        files.append(dict(name=gz.name,bytes=gz.stat().st_size))
    lines=['# LSTM의 사전 규칙 기반 개선 실험','','**이번 후보는 확인 구간의 채택 기준을 통과하지 못했습니다. 기존 LSTM 업그레이드를 유지합니다.** 실패한 결과를 숨기거나 하반기에서 유리한 후보로 교체하지 않았습니다.','','## 사전에 정한 절차','','- 발전량 보완 전 공통 v3, 동일 12개 입력 그룹·72시간 지연·기존 결측 처리·SMP 목표와 평가 행을 유지했습니다. 새 API나 외부 입력은 추가하지 않았습니다.','- 후보 6개와 seed42를 학습 전에 고정했습니다. 가격 직접 예측과 주간 기준선 대비 잔차 학습, MSE·MAE·SmoothL1(β=1), 48/168시간 이력을 비교했습니다. 모든 후보에 공통 입력을 제공했습니다.','- 2023~2024년 Train으로 학습하고, 2025년 1~4월만으로 epoch·후보·주간 혼합 가중치를 선택했습니다.','- 선택한 한 후보만 Train+1~4월로 재학습한 뒤, 5~6월에서 확인했습니다. 나머지 후보를 확인 구간에 재차 대입하지 않았습니다.','- 5~6월 MAE가 이전 LSTM의 같은 기간 순차 예측보다 1% 이상 낮고, 5·6월 각각 악화되지 않아야 채택하도록 정했습니다.','- 확인 후 정책을 저장하고 Train+Validation으로 고정 epoch 재학습한 후보를 하반기에서 한 번 평가했습니다. 후보가 실패했으므로 최종 선택은 이전 모델로 유지했습니다.','','## 1~4월 후보 전체 결과','','|후보|목표|손실|이력|epoch|단독 MAE|혼합 MAE|모델 비중|','|---|---|---|---:|---:|---:|---:|']
    for _,r in table.iterrows():lines.append(f'|{r.candidate_id}|{r.target}|{r.loss}|{r.lookback}|{r.best_epoch}|{r.raw_mae:.4f}|{r.mixed_mae:.4f}|{r.alpha:.1f}|')
    lines+=['',f'선택 후보: `{choice["params"]["id"]}`, epoch={choice["best_epoch"]}, 모델 비중={choice["blending"]["alpha"]:.1f}. 원래 6개 후보 모두의 설정·학습 곡선·체크포인트·튜닝 예측을 보존했습니다.','','## 5~6월 확인 결과','','|구간|후보 혼합 MAE|기존 LSTM 순차 예측 MAE|','|---|---:|---:|',f'|5~6월 전체|{confirmation["candidate_mae"]:.4f}|{confirmation["reference_mae"]:.4f}|']
    for r in confirmation['monthly']:lines.append(f'|{r["month"]}월|{r["candidate_mae"]:.4f}|{r["reference_mae"]:.4f}|')
    lines+=['','후보는 전체 MAE가 더 높았고 6월에도 악화됐습니다. 사전 채택 규칙에 따라 기각했습니다. 이 결정은 하반기 점수를 계산하기 전에 final_policy_before_test.json에 기록했습니다.','','## 하반기 후속 재평가','','|결과|MAE 원/kWh|RMSE 원/kWh|R²|','|---|---:|---:|---:|']
    for _,r in scores.iterrows():lines.append(f'|{r.experiment_id}|{r.mae:.4f}|{r.rmse:.4f}|{r.r2:.4f}|')
    lines+=['','candidate_raw는 새 LSTM 단독 출력이고 candidate_mixed는 고정 주간 혼합입니다. previous_lstm과 sarimax_frozen은 기존 혼합 결과를 읽기만 한 것입니다. adopted_lstm은 확인 구간에서 확정한 정책에 따른 선택 결과입니다. 하반기에서 가장 좋아 보이는 결과를 사후 선택한 것이 아닙니다.','','## 해석과 한계','','이번 6개 후보 안에서는 검증상 개선을 확인하지 못했습니다. 이것이 LSTM의 개선 가능성이 없다는 뜻은 아닙니다. 현재 자료와 규칙에서 새 후보를 채택할 근거가 부족하다는 뜻입니다. 입력별 결측·정보 지연, 가격 분포 변화 등의 제한도 그대로 남아 있습니다.','','주간 잔차 모델은 전주 같은 시간 가격에 LSTM이 예측한 변화량을 더하는 구조입니다. 이는 기존에 이용 가능했던 과거 SMP 기준선을 활용하는 구조 변경이며, 순수 LSTM 성능으로 포장하지 않습니다. α=0이면 LSTM이 기여하지 않는 기준선 단독 결과로 표시해야 합니다.','','하반기는 이미 여러 실험에서 확인한 기간입니다. 이번에도 새 독립 블라인드 시험으로 주장할 수 없습니다. 5~6월 또한 이전 실험에서 사용됐던 기간이지만 이번 후보 선택에는 쓰지 않고 확인에만 썼습니다. 확인 비교용 이전 LSTM의 설정은 원래 상반기 전체에서 정해졌다는 한계가 있습니다. 독립 성능 검증에는 새로운 미사용 기간이 필요합니다.','','동월 LNG 제공 조건부 입력·실측72시간 지연 가정·2025년 발전량99.726% 결측 대체·서울108 관측소·시장/육지 범위 차이 등 기존 v3의 한계는 유지합니다. 지역/공표시각 재조사나 새 수집은 하지 않았습니다. 표준화는 각 적합 구간만으로 맞추고 공통 대체값은 기존 Train 통계를 재사용했습니다.','','## 재현·검증','','```sh','python scripts/run_experiment.py --source-project /path/to/1120gradpj --output-dir /tmp/new-lstm-experiment','python scripts/report_experiment.py --source-project /path/to/1120gradpj --experiment-dir /tmp/new-lstm-experiment','```','','기존 결과는 덮어쓰지 않습니다. 재현에는 기존 공통 v3와 같은 브랜치의 원래 LSTM·SARIMAX 업그레이드 파일이 필요합니다. 새 실험은 LSTM 폴더 안에만 저장했습니다. 다른 세 모델과 기존 LSTM은 수정하지 않았습니다. 체크포인트 재로딩 예측 일치, 미래 정답 변경에 대한 입력 불변 및 보호 파일 해시를 확인했습니다.','','[SmoothL1 공식 문서](https://docs.pytorch.org/docs/stable/generated/torch.nn.SmoothL1Loss.html) / [검증 분리 원칙](https://scikit-learn.org/stable/modules/cross_validation.html).','','![후보 및 재평가](../outputs/figures/candidate_comparison.png)','![선택일](../outputs/figures/selected_72h.png)']
    (root/'reports/final_report.md').write_text('\n'.join(lines)+'\n')
    (root/'README.md').write_text('# LSTM 개선 실험 — 후보 미채택\n\n사전에 정한 6개 후보를 비교했지만 5~6월 확인 기준을 통과하지 못해 기존 LSTM을 유지했습니다.\n\n[전체 결과와 채택 규칙](reports/final_report.md)을 확인하세요. 모든 후보와 실패 결과를 보존했고, 하반기 점수를 보고 선택을 바꾸지 않았습니다. 원본과 다른 모델은 변경하지 않았습니다.\n')
    dump(root/'reports/published_artifacts.json',dict(predictions=files,policy=policy['adopt'],all_six_tuning_checkpoints_reproduce_scores=True))
    print('REPORT READY:',policy['adopt'],files)

if __name__=='__main__':main()
