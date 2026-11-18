"""Train LSTM on the frozen common v3 contract; v2 remains in train_v2.py."""
import argparse,json,platform,sys,time
from pathlib import Path
import numpy as np
import pandas as pd
import torch
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'src'))
from smp_forecast import common_v3 as contract
from algorithm import Estimator
from train_v2 import export,figures


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',action='store_true')
    parser.add_argument('--audit-only',action='store_true')
    parser.add_argument('--selected-origin',default='2025-07-01T23:00:00+09:00')
    args=parser.parse_args()
    if args.build or not (contract.OUT/'manifest.json').exists():contract.build()
    bundle=contract.load();history,future,manifest=bundle
    if manifest['all_groups']!=list(range(1,13)):raise ValueError('12-group contract mismatch')
    datasets={split:contract.arrays(bundle,split,168) for split in ['train','validation','test']}
    for split,(h,c,y) in datasets.items():
        Estimator.check(h,c,y);print(split,h.shape,c.shape,y.shape,flush=True)
    if args.audit_only:return
    candidates=[dict(lookback=48,hidden_size=32,layers=1,dropout=0.,learning_rate=.001,batch_size=32,epochs=100,patience=10),dict(lookback=168,hidden_size=64,layers=1,dropout=0.,learning_rate=.001,batch_size=32,epochs=100,patience=10),dict(lookback=168,hidden_size=32,layers=2,dropout=.1,learning_rate=.0005,batch_size=32,epochs=100,patience=10)]
    stamp=pd.Timestamp.now(tz=contract.TZ).strftime('%Y%m%dT%H%M%S')
    run=HERE/'outputs'/contract.VERSION/stamp;run.mkdir(parents=True,exist_ok=False)
    config=dict(dataset_version=contract.VERSION,candidates=candidates,seed=42,jobs=2,selection_metric='validation MAE',test_refit=False,selected_origin=args.selected_origin)
    contract.dump(run/'config_before_training.json',config)
    start=time.perf_counter();best=None;results=[]
    def sliced(split,lookback):
        h,c,y=datasets[split];return h[:,-lookback:],c,y
    for number,params in enumerate(candidates,1):
        print('CANDIDATE',number,params,flush=True)
        model=Estimator(params,seed=42,jobs=2).fit(*sliced('train',params['lookback']),sliced('validation',params['lookback']))
        results.append(dict(params=params,best_epoch=model.best_epoch,validation_mae=model.validation_mae,epochs=model.history))
        contract.dump(run/'candidate_results.json',results)
        print('CANDIDATE FINISHED',number,model.validation_mae,flush=True)
        if best is None or model.validation_mae<best.validation_mae:best=model
    best.save(run/'model.pt')
    contract.dump(run/'selected_before_test.json',dict(params=best.params,best_epoch=best.best_epoch,validation_mae=best.validation_mae))
    frames=[]
    for split in ['validation','test']:
        h,c,y=sliced(split,best.lookback);prediction=best.predict(h,c)
        frame=future[future.split==split].sort_values(['forecast_origin','horizon']).copy()
        frame['predicted_smp']=prediction.reshape(-1);frame['absolute_error']=np.abs(frame.predicted_smp-frame.actual_smp)
        frame['dataset_version']=contract.VERSION;frame['model_name']='LSTM';frame['prediction_status']='ok'
        frame['forecast_date']=frame.target_timestamp.dt.strftime('%Y-%m-%d');frame['fuel_input_policy']=manifest['fuel_policy']
        columns=['dataset_version','model_name','split','forecast_origin','observed_cutoff','target_timestamp','forecast_date','horizon','forecast_day','actual_smp','predicted_smp','absolute_error','baseline_origin_day','baseline_weekly','prediction_status','fuel_input_policy']
        frames.append(frame[columns])
    frame=pd.concat(frames,ignore_index=True);metrics=export(frame,run)
    figures(frame,run/'figures',args.selected_origin)
    elapsed=time.perf_counter()-start
    contract.dump(run/'experiment.json',dict(config=config,selected=best.params,best_epoch=best.best_epoch,seconds=elapsed,python=platform.python_version(),torch=str(torch.__version__),numpy=np.__version__,pandas=pd.__version__,training_performed=True,history_features=manifest['history_features'],context_features=manifest['context_features']))
    overall=metrics['overall'];days=metrics['forecast_days']
    reports=HERE/'reports';reports.mkdir(exist_ok=True)
    overall.to_csv(reports/'v3_overall_metrics.csv',index=False);days.to_csv(reports/'v3_forecast_day_metrics.csv',index=False)
    quality=json.loads((contract.OUT/'quality_report.json').read_text())
    lines=['# LSTM 72시간 최종 평가 — 공통 v3','','실제 PyTorch 학습·Validation 선택·Final Test 평가를 실행했습니다.','',f'- 데이터 버전: `{contract.VERSION}`',f'- 입력 커밋: `{contract.SHA}`',f'- 결과 경로: `{run.relative_to(contract.WORK)}`',f'- 학습 시간: {elapsed:.1f}초',f'- 선택 모델: {best.params}; best epoch={best.best_epoch}',f'- 입력: 과거 {best.lookback}시간 × {len(manifest["history_features"])}변수, 미래 72시간 × {len(manifest["context_features"])}변수','- Train으로만 표준화·대체 통계를 적합. Validation MAE로 설정·epoch 선택. Train+Validation 재학습 없음. Test 재튜닝 없음.','- 직접 72시간 출력. 미래 SMP teacher forcing 없음.','','## 전체 성능','','|구간|MAE 원/kWh|RMSE 원/kWh|R²|최근 일별 패턴 MAE|전주 패턴 MAE|전주 대비 개선율|','|---|---:|---:|---:|---:|---:|---:|']
    for _,r in overall.iterrows():lines.append(f'|{r["split"]}|{r.mae:.4f}|{r.rmse:.4f}|{r.r2:.4f}|{r.baseline_origin_day_mae:.4f}|{r.baseline_weekly_mae:.4f}|{r.baseline_weekly_improvement_pct:.2f}%|')
    lines+=['','## 예측일별 성능','','|구간|예측일|MAE|RMSE|','|---|---:|---:|---:|']
    for _,r in days.iterrows():lines.append(f'|{r["split"]}|D+{int(r.forecast_day)}|{r.mae:.4f}|{r.rmse:.4f}|')
    lines+=['','## 해석 및 한계','','실제 수요, 발전량, 예비력 및 기상 관측자료의 개별 공표시각을 모두 확인할 수 없어, 본 연구에서는 예측 기준시각보다 72시간 이전의 실측 자료만 활용하는 보수적 지연 규칙을 가정하였다. 이 규칙은 각 자료의 실제 공개시각을 검증한 결과가 아니다.','','- **동월 LNG 단가 제공 조건부 과거 예측 실험**입니다. 당시 공개 여부가 확인된 운영 예측 성능으로 해석할 수 없습니다.','- SMP도 공표 이력 미확인으로 72시간 지연했습니다. 기준 예측에도 동일한 제한을 적용했습니다. 23시에는 대상일 일부 공식 SMP가 이미 공개되어 있을 가능성이 있어 운영적 효용은 별도 검토해야 합니다.','- 발전량 2025년 원본은 1일뿐입니다. 장기 결측을 Train 계절·시간대 대표값으로 대체하므로 실제 공급 변동을 대부분 반영하지 못합니다. 결측 자체를 수집 완료로 표시하지 않습니다.','- 중기예보는 대상 날짜가 일치하고 발행시각이 origin 이전인 최신 자료를 사용합니다. D+1/2에는 이전 발행본이 연결될 수 있으며, 이를 당일 발표 단기예보로 해석하지 않습니다. 시간별 기온·풍속·일사 예보를 생성하지 않았습니다.','- EPSIS 수요 원본을 사용했습니다. 전국/육지 범위는 원자료 정의를 따르며, 제주 차감이나 육지 명칭 변경을 하지 않았습니다. 공급·발전량도 원본 시장 범위가 SMP 육지 범위와 완전히 동일하다고 보장하지 않습니다.','- ASOS는 서울108 단일 지점입니다. 전국 대표 기상으로 간주하지 않습니다. 야간 플래그는 근사 태양고도이며 관측 정상 여부의 증거가 아닙니다. 결측 일사량을 0으로 바꾸지 않았습니다.','- Final Test는 7~12월로 사계절 전체 검증이 아닙니다. 인접 72시간 블록의 목표 시간이 겹치므로 행별 오차는 독립 표본이 아닙니다.','','## 결측과 커버리지','',json.dumps(quality,ensure_ascii=False,indent=2),'','## 재현','', '```sh','PYTHONPATH=1120gradpj/src 1120gradpj/.venv/bin/python -m smp_forecast.common_v3','1120gradpj/.venv/bin/python 1120gradpj/models/lstm/train.py','```','', '결과 CSV는 모든 평가 발행일의 72시간 값을 보존합니다. 월별·발행일별·horizon별 지표와 선택일 PNG/HTML은 위 결과 경로에 저장되어 있습니다.']
    report='\n'.join(lines)+'\n';(reports/'final_evaluation_report_v3.md').write_text(report)
    (reports/'model_experiment_report_v3.md').write_text('# LSTM 실험 기록\n\n'+json.dumps(dict(candidates=results,selected=best.params),ensure_ascii=False,indent=2)+'\n')
    contract.dump(reports/'latest_run_v3.json',dict(path=str(run),dataset_version=contract.VERSION,metrics=overall.to_dict('records'),seconds=elapsed))
    print(overall.to_string(index=False),flush=True);print('RESULTS',run,flush=True)

if __name__=='__main__':main()
