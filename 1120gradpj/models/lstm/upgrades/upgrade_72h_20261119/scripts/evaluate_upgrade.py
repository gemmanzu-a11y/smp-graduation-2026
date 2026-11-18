"""Reports/plots from already completed upgrades; never fits or chooses on Test."""
from pathlib import Path
import argparse,json,gzip,shutil,sys,os
import numpy as np
import pandas as pd
from protocol import metrics,dump


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--model',choices=['lstm','sarimax'],default='lstm');parser.add_argument('--source-project',type=Path,required=True);args=parser.parse_args()
    scripts=Path(__file__).resolve().parent;models=scripts.parents[3];upgrade=models/args.model/'upgrades/upgrade_72h_20261119'
    source=args.source_project.resolve();sys.path.insert(0,str(source/'src'))
    from smp_forecast import common_v3 as c
    config=json.loads((upgrade/'config/experiment_config.json').read_text());selection=json.loads((upgrade/'config/selection_before_test.json').read_text());verification=json.loads((upgrade/'reports/verification.json').read_text())
    data=pd.concat([pd.read_csv(upgrade/'outputs/predictions'/name) for name in ['experiments_validation.csv','final_test_predictions.csv']],ignore_index=True)
    for col in ['forecast_origin','target_timestamp','observed_cutoff']:data[col]=c.times(data[col])
    result=pd.read_csv(upgrade/'outputs/metrics/experiment_comparison.csv')
    result['evaluation_role']=np.where((result.split=='validation')&result.experiment_id.isin(['E2','E3','E4']),'post-refit in-sample; not generalization or selection',np.where(result.split=='test','known Test reevaluation','validation selection'))
    result.to_csv(upgrade/'outputs/metrics/experiment_comparison.csv',index=False)
    # True hourly jumps use Train-fitted thresholds and are diagnostics only.
    raw=pd.read_csv(c.OUT/'hourly.csv');raw.index=c.times(raw.pop('timestamp'));delta=raw.smp.diff()
    lower=float(delta.loc[:'2024-12-31'].quantile(.05));upper=float(delta.loc[:'2024-12-31'].quantile(.95))
    change=delta.reindex(data.target_timestamp).to_numpy();data['event']=np.where(change>=upper,'sharp_rise',np.where(change<=lower,'sharp_fall','other'))
    event=[]
    for keys,z in data.groupby(['split','experiment_id','event']):event.append(dict(zip(['split','experiment_id','event'],keys),**metrics(z.actual_smp,z.predicted_smp)))
    pd.DataFrame(event).to_csv(upgrade/'outputs/metrics/extreme_event_metrics.csv',index=False)
    _,future,_=c.load();price=[];missing=[]
    for split,z in future.groupby('split'):
        unique=z.drop_duplicates('target_timestamp').actual_smp
        price.append(dict(split=split,hours=len(unique),mean=float(unique.mean()),median=float(unique.median()),std=float(unique.std(ddof=0)),p05=float(unique.quantile(.05)),p95=float(unique.quantile(.95))))
        one=z.drop_duplicates('forecast_origin')
        missing.append(dict(split=split,origins=len(one),**{col:float(one[col].mean()) for col in one if col.endswith('_missing_last')}))
    pd.DataFrame(price).to_csv(upgrade/'outputs/metrics/price_distribution.csv',index=False);pd.DataFrame(missing).to_csv(upgrade/'outputs/metrics/input_missing_rates.csv',index=False)
    os.environ.setdefault('MPLCONFIGDIR',str(source/'data/cache/matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import plotly.graph_objects as go
    figures=upgrade/'outputs/figures';names=['E0','E1','E2','E3','weekly_baseline']
    fig,axes=plt.subplots(1,2,figsize=(13,4))
    for ax,split in zip(axes,['validation','test']):
        z=result[result.split==split].set_index('experiment_id').reindex(names)
        bars=ax.bar(names,z.mae)
        if split=='validation':
            for j in [2,3]:bars[j].set_hatch('//')
        ax.set_title(split+(' (E2/E3: refit in-sample)' if split=='validation' else ' — known holdout reevaluation'));ax.set_ylabel('MAE (KRW/kWh)');ax.tick_params(axis='x',rotation=25)
    fig.tight_layout();fig.savefig(figures/'model_comparison.png');plt.close(fig)
    selected=data[(data.split=='test')&(data.forecast_origin==pd.Timestamp('2025-07-01T23:00:00+09:00'))]
    fig,ax=plt.subplots(figsize=(13,4));chart=go.Figure()
    first=selected[selected.experiment_id=='E0'];ax.plot(first.target_timestamp,first.actual_smp,color='black',label='Actual');chart.add_scatter(x=first.target_timestamp,y=first.actual_smp,name='Actual')
    for name in ['E0','E2','E3','weekly_baseline']:
        z=selected[selected.experiment_id==name];ax.plot(z.target_timestamp,z.predicted_smp,label=name);chart.add_scatter(x=z.target_timestamp,y=z.predicted_smp,name=name)
    for n in [24,48]:ax.axvline(first.target_timestamp.iloc[n],color='gray',linestyle='--');chart.add_vline(x=first.target_timestamp.iloc[n].to_pydatetime(),line_dash='dash')
    ax.legend();ax.set_ylabel('SMP (KRW/kWh)');ax.set_title(args.model.upper()+' — 72h, conditional LNG');fig.autofmt_xdate();fig.tight_layout();fig.savefig(figures/'selected_72h_forecast.png');plt.close(fig)
    chart.update_layout(title=args.model.upper()+' upgraded 72h (conditional LNG)',yaxis_title='SMP (KRW/kWh)');chart.write_html(str(figures/'selected_72h_forecast.html'),include_plotlyjs='cdn')
    for group,filename in [('month','monthly_mae.png'),('horizon','horizon_mae.png')]:
        fig,axes=plt.subplots(1,2,figsize=(14,4))
        for ax,split in zip(axes,['validation','test']):
            z=data[(data.split==split)&data.experiment_id.isin(names)].copy();z['month']=z.target_timestamp.dt.strftime('%Y-%m')
            table=z.groupby([group,'experiment_id']).absolute_error.mean().unstack().reindex(columns=names)
            table.plot(ax=ax);ax.set_title(split+(' (refit E2/E3 in-sample)' if split=='validation' else ''));ax.set_ylabel('MAE (KRW/kWh)');ax.tick_params(axis='x',rotation=30)
        fig.tight_layout();fig.savefig(figures/filename);plt.close(fig)
    # Publish lossless compressed predictions; keep large uncompressed working CSVs local.
    compressed=[]
    for file in (upgrade/'outputs/predictions').glob('*.csv'):
        target=file.with_suffix(file.suffix+'.gz')
        with file.open('rb') as inp,gzip.open(target,'wb') as out:shutil.copyfileobj(inp,out)
        compressed.append(dict(file=target.name,bytes=target.stat().st_size))
    # Remove personal absolute paths from published configuration; keep an ignored local map.
    if not (upgrade/'config/local_paths.json').exists():dump(upgrade/'config/local_paths.json',dict(source_project=config['source_project'],original_run=config['original_run']))
    config['source_project']='provided locally by --source-project; contains the frozen v3 inputs'
    config['original_run']=str(Path(config['original_run']).relative_to(source)) if Path(config['original_run']).is_absolute() else config['original_run'];dump(upgrade/'config/experiment_config.json',config)
    protected=json.loads((upgrade/'config/protected_source_hashes.json').read_text());dump(upgrade/'config/protected_source_hashes.json',{str(Path(k).relative_to(source.parent)) if Path(k).is_absolute() else k:v for k,v in protected.items()})
    artifact=json.loads((upgrade/'config/final_artifact.json').read_text());artifact['checkpoint']='models/'+Path(artifact['checkpoint']).name;dump(upgrade/'config/final_artifact.json',artifact)
    chosen=result[(result.split=='test')&(result.experiment_id==artifact['adopted_experiment'])].iloc[0]
    old=result[(result.split=='test')&(result.experiment_id=='E0')].iloc[0];weekly=result[(result.split=='test')&(result.experiment_id=='weekly_baseline')].iloc[0]
    rule=selection['blending']
    lines=[f'# {args.model.upper()} 72시간 예측 업그레이드',
        '', '발전량 보완 전 공통 v3 입력을 그대로 사용한 실제 실행 결과입니다. LSTM·SARIMAX만 업그레이드했으며, 원본 모델·데이터·보고서와 LightGBM·XGBoost는 변경하지 않았습니다.',
        '', f'데이터 버전: `{c.VERSION}`',
        '', '## 사전에 확정한 최종 방식',
        '', f'최종 예측 = {rule["alpha"]:.1f} × 재학습 모델 + {1-rule["alpha"]:.1f} × 주간 기준선',
        '', f'채택 실험은 **{artifact["adopted_experiment"]}**입니다. 혼합 가중치는 Validation으로 선택했고 하반기 결과를 보고 다시 고르지 않았습니다. 편향 보정은 `{selection["correction"]["mode"]}`입니다. none이면 보정을 적용하지 않아 E4는 E3와 같습니다.',
        '', '## 하반기 재평가', '', '|실험|MAE 원/kWh|RMSE 원/kWh|R²|평균 편향|', '|---|---:|---:|---:|---:|']
    for _,r in result[result.split=='test'].iterrows():lines.append(f'|{r.experiment_id}|{r.mae:.4f}|{r.rmse:.4f}|{r.r2:.4f}|{r.bias:.4f}|')
    lines += [
        '', f'기존 MAE {old.mae:.4f} → 채택 결과 {chosen.mae:.4f}원/kWh입니다. 오차 감소율은 기존 모델 대비 {100*(1-chosen.mae/old.mae):.2f}%, 주간 기준선({weekly.mae:.4f}) 대비 {100*(1-chosen.mae/weekly.mae):.2f}%입니다. **채택 결과는 모델 단독이 아니라 재학습 모델과 기준선의 혼합 성능입니다.**',
        '', 'E0는 기존 모델, E1은 기존 모델과 기준선 혼합, E2는 Train+Validation 재학습 단독, E3는 재학습과 고정 가중치 혼합, E4는 검증에서 선택한 편향 보정입니다. daily/weekly_baseline은 기준선 단독입니다. α가 0으로 선택될 경우 기준선만 사용하는 결과로 표시해야 합니다.',
        '', '## 1. 기준선 혼합 검증',
        '', '기존 Validation 예측에서 일별·주간 기준선과 α=0.0~1.0(0.1 간격)을 비교했습니다. 모든 72시간에 같은 가중치를 적용했습니다. 모든 후보의 값은 outputs/metrics/blend_validation_grid.csv에 있습니다. 기준선이 참조하는 SMP의 시간 구간이 origin−72시간 이전에 완결되는지도 확인했습니다.',
        '', '## 2. 순차 검증과 편향 보정',
        '', '최종 재학습 전에 1~2월, 3~4월, 5~6월을 순서대로 예측했습니다. 각 구간 이전의 정답만 계수·가중치 적합에 사용했으며, 경계를 넘는 72시간 블록은 제외했습니다.',
        '', '1~4월 OOF에서 전체·D+1/D+2/D+3별 평균 편향을 계산하고 5~6월에서 보정 효과를 비교했습니다. MAE가 1% 이상 개선되고 5월·6월 모두 악화되지 않아야 채택하도록 미리 정했습니다. 채택되지 않은 보정을 하반기 실제값으로 다시 계산하지 않았습니다.',
        '', f'OOF는 {verification["rolling_oof_rows"]:,}행입니다. 두 내부 경계의 블록을 제외해 전체 Validation 12,888행보다 288행 적습니다. 이는 실패하거나 어려운 예측을 골라 뺀 것이 아닙니다. 하반기 평가 행은 모든 실험에서 13,104행으로 같습니다.',
        '', '원래 모델 설정·epoch와 혼합 가중치 선택에 이미 Validation을 사용했으므로, 이 OOF를 완전한 중첩 검증 또는 새 독립 시험이라고 해석하지 않습니다. 고정 설정의 시간순 안정성과 편향 보정을 점검한 보조 검증입니다.',
        '', '## 3. Train+Validation 재학습',
        '', f'고정 설정: `{selection["parameters"]}`.',
        '', '원래 모델 구조와 Validation에서 선택한 설정을 유지해 2023년~2025년 상반기를 학습했습니다. LSTM은 기존에 선택한 epoch를 고정하고, 재학습 중 Validation 조기 종료를 다시 하지 않았습니다. SARIMAX는 기존 order·계절 order 및 외생계수 최소노름 OLS 고정 후 시계열 계수를 추정하는 2단계 제약 방식을 유지했습니다.',
        '', '공통 결측 대체 통계는 기존 Train 기준을 유지했습니다. 모델의 표준화만 실제 적합 구간으로 다시 맞췄으며 Test로 통계를 적합하지 않았습니다.',
        '', '**E2~E4의 Validation 값은 재학습에 포함된 표본의 학습내 오차입니다. 일반화 성능이나 설정 선택의 근거로 사용하지 않습니다.** 비교 그래프에도 이를 표시했습니다.',
        '', '## 4. 오차·편향 분석',
        '', 'D+1~D+3, horizon 1~72, 월별 MAE·RMSE·R², 평균 편향, 과대·과소예측 비율, 실제값과 예측값의 분산을 outputs/metrics에 저장했습니다. 평균 편향이 양수이면 과대예측, 음수이면 과소예측입니다.',
        '', f'급등·급락은 Train 시간별 SMP 차분의 5/95백분위로 정의했습니다. 급락 기준은 시간 변화≤{lower:.4f}, 급등 기준은 ≥{upper:.4f}원/kWh입니다. Test 정답은 이 구간의 사후 오차 분석에만 사용했습니다. 기간별 가격 분포와 입력 결측 비율도 함께 보존했습니다.',
        '', 'D+1/D+2/D+3별 별도 모델은 추가하지 않았습니다. 이번에는 고정된 구조의 시간순 검증과 편향 보정 비교까지만 수행했습니다.',
        '', '## 유지한 연구 조건과 한계',
        '', '- 매일 23시 발행, 다음 3일 총 72시간. 모든 목표시간에 공통 observed_cutoff=origin−72시간을 적용했습니다.',
        '- 개별 실측 공개시각을 검증한 것이 아니라 72시간 지연을 가정했습니다. 과거 SMP도 같은 보수적 지연을 적용했습니다.',
        '- 국내 LNG는 동월 단가 제공 조건부 실험입니다. FRED D−2 vintage, 중기예보 발표시각, 과거 수요예측 이력 규칙을 바꾸지 않았습니다.',
        '- 2025년 발전량 99.726% 결측 대체 등 기존 v3의 입력 한계도 그대로입니다. 지역 범위·공표시각 재조사와 새 API 수집은 하지 않았습니다.',
        '- 하반기는 이미 기존 성능을 확인한 기간이므로 이번 결과는 후속 재평가입니다. 새 블라인드 시험이나 독립 미래 성능으로 주장하지 않습니다.',
        '- Train+Validation 전체 정답을 쓰는 오프라인 분할 실험입니다. 첫 Test 발행 시점에 학습 정답이 실제로 모두 공개됐는지까지 검증한 운영 시험은 아닙니다.',
        '', '## 파일과 재현',
        '', '```sh', f'python scripts/run_upgrade.py --source-project /path/to/1120gradpj', f'python scripts/evaluate_upgrade.py --model {args.model} --source-project /path/to/1120gradpj', '```',
        '', '코드·모델·설정·예측·그래프·보고서는 이 업그레이드 폴더에만 저장했습니다. 기존 공통 자료는 복사하지 않고 읽기 전용으로 참조합니다. SARIMAX 실행기는 LSTM 업그레이드 폴더의 공통 실험 프로토콜을 재사용합니다.',
        '', '전체 예측은 outputs/predictions/*.csv.gz로 손실 없이 압축했습니다. 새 체크포인트는 models/에 있습니다. 원본 파일의 해시 불변과 저장 모델 재로딩 예측 일치를 검사했습니다. 선택일 HTML은 Plotly CDN 연결이 필요합니다.',
        '', 'Git 브랜치: `codex/lstm-sarimax-72h-upgrade-20261119`. 원격 커밋과 PR 링크는 GitHub에서 확인할 수 있습니다.',
        '', '![단계별 비교](../outputs/figures/model_comparison.png)', '![선택일 72시간](../outputs/figures/selected_72h_forecast.png)']
    (upgrade/'reports/final_upgrade_report.md').write_text('\n'.join(lines)+'\n')
    (upgrade/'reports/baseline_comparison.md').write_text('# 기준선 혼합 검증\n\n'+json.dumps(selection['blending'],ensure_ascii=False,indent=2)+'\n\n모든후보의Validation성능은outputs/metrics/blend_validation_grid.csv에있습니다. 가중치는하반기평가전에확정했습니다.\n')
    (upgrade/'reports/retraining_report.md').write_text('# Train+Validation 재학습\n\n'+json.dumps(selection['parameters'],ensure_ascii=False,indent=2)+'\n\n계수/가중치는2023~2025년상반기표본으로적합했습니다. 대체통계는원래Train기준을유지하며표준화는재학습표본만사용했습니다. E2~E4Validation은학습내오차로구분했습니다.\n')
    (upgrade/'reports/bias_analysis.md').write_text('# OOF 편향 보정 선택\n\n'+(upgrade/'config/stage4_bias_selection.json').read_text()+'\n\nTest실제값으로편향보정값을계산하지않았습니다. none이면E4는E3와같습니다.\n')
    (upgrade/'README.md').write_text(f'# {args.model.upper()} 72시간 업그레이드\n\n현재v3의읽기전용재사용으로실행했습니다. 결과와한계는[최종보고서](reports/final_upgrade_report.md)를확인하세요.\n\n최종채택={artifact["adopted_experiment"]}, 모델가중치α={selection["blending"]["alpha"]}, 기준선={selection["blending"]["baseline"]}.\n\n하반기MAE={chosen.mae:.4f}원/kWh,RMSE={chosen.rmse:.4f},R²={chosen.r2:.4f}. 원본결과는변경하지않았습니다.\n\n실행: `python scripts/run_upgrade.py --source-project /path/to/1120gradpj`. 기존출력은덮어쓰지않으므로재실행은새업그레이드출력위치를사용하세요.\n')
    dump(upgrade/'reports/published_files.json',dict(compressed_predictions=compressed,selected_test_metrics=chosen.to_dict(),baseline_weekly_mae=float(weekly.mae)))
    print(args.model,'reports ready',chosen.mae,chosen.r2,compressed)

if __name__=='__main__':main()
