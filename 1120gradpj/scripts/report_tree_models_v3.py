"""Verify completed v3 boosting models and report all four under identical targets."""
from pathlib import Path
import json,sys,hashlib,shutil,os
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from smp_forecast import common_v3 as c
from smp_forecast.tree_models_v3 import matrices
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'data/cache/matplotlib'))


def main():
    import xgboost,lightgbm
    _,future,manifest=c.load();allmetrics=[];reference=None
    common_keys=['split','forecast_origin','target_timestamp','horizon','actual_smp','baseline_origin_day','baseline_weekly','observed_cutoff']
    for name in ['lstm','sarimax','lightgbm','xgboost']:
        here=ROOT/'models'/name
        if name in ['lstm','sarimax']:latest_path=here/'CURRENT_RUN.json'
        else:latest_path=here/'reports/v3_common/latest_run.json'
        latest=json.loads(latest_path.read_text());assert latest['dataset_version']==c.VERSION
        run=Path(latest['path']);frame=pd.read_csv(run/'predictions.csv');assert frame.dataset_version.eq(c.VERSION).all()
        stable=frame[common_keys].sort_values(common_keys[:4]).reset_index(drop=True)
        assert len(frame)==25992 and not frame.duplicated(common_keys[:4]).any()
        if reference is None:reference=stable
        else:pd.testing.assert_frame_equal(reference,stable)
        overall=pd.read_csv(run/'overall_metrics.csv');overall.insert(0,'model',name.upper());allmetrics.append(overall)
        if name in ['lstm','sarimax']:continue
        reports=here/'reports/v3_common';config=json.loads((run/'config_before_training.json').read_text());assert config['features']==manifest['context_features']
        if name=='xgboost':
            restored=xgboost.XGBRegressor();restored.load_model(run/'model.ubj');importance=restored.get_booster().get_score(importance_type='gain');gain=np.array([importance.get('f'+str(k),0.) for k in range(len(config['features']))])
        else:
            restored=lightgbm.Booster(model_file=str(run/'model.txt'));gain=restored.feature_importance(importance_type='gain')
        for split in ['validation','test']:
            original,x,y=matrices(future,manifest,split);pred=restored.predict(x)
            saved=frame[frame.split==split].sort_values(['forecast_origin','horizon'])
            np.testing.assert_allclose(pred,saved.predicted_smp,rtol=1e-7,atol=1e-5)
            np.testing.assert_allclose(original.actual_smp.to_numpy(),saved.actual_smp,rtol=0,atol=1e-10)
        # Endogenous future truth is an output, never a selected exogenous field.
        block=future[future.split=='test'].iloc[:72].copy();_,x,y=matrices(block,manifest,'test')
        block.actual_smp=-999999;_,changed,_=matrices(block,manifest,'test');np.testing.assert_array_equal(x,changed)
        np.testing.assert_array_equal(restored.predict(x),restored.predict(changed))
        checks=dict(dataset_version=c.VERSION,same_25992_keys_as_active_lstm_sarimax=True,saved_model_reproduces_validation_and_test=True,future_truth_mutation_invariant=True,all_83_common_features=True,model_sha256=hashlib.sha256((run/('model.ubj' if name=='xgboost' else 'model.txt')).read_bytes()).hexdigest())
        c.dump(reports/'verification.json',checks)
        importance=pd.DataFrame({'feature':config['features'],'gain':gain}).sort_values('gain',ascending=False);importance.to_csv(reports/'feature_importance.csv',index=False)
        for picture in ['selected_72h','monthly_mae']:shutil.copyfile(run/'figures'/(picture+'.png'),reports/(picture+'.png'))
        days=pd.read_csv(run/'forecast_days_metrics.csv');candidates=json.loads((run/'candidate_results.json').read_text());experiment=latest['experiment']
        lines=[f'# {name.upper()} — 발전량 보완 전 공통 v3','','실제 학습·Validation 설정 선택·하반기 평가를 완료했습니다.','',f'- 데이터: `{c.VERSION}`',f'- 결과: `{run.relative_to(c.WORK)}`','- 공통 입력83개를 그대로 사용했습니다. 목표SMP·정답·기준예측은 입력 열에 포함하지 않습니다.','- 입력 그룹12개를 유지하며 기존Train 대체값·결측 표시를 그대로 읽습니다. 자체 수집·재집계·v4발전량 대체는 하지 않았습니다.','- 한 모델이 각 대상시간을 직접 회귀합니다. 하루72개 행을 예측하며 미래SMP를 재귀 입력하거나 teacher forcing하지 않습니다.','- 후보3개, seed42,CPU2threads. Train 학습,Validation MAE로40회 patience 조기 종료·후보 선택. 하반기는 선택 후 평가하며 재튜닝·Train+Validation 재학습을 하지 않았습니다.','',f'- 선택: {experiment["selected"]}; 최적 boosting rounds={experiment["best_rounds"]}',f'- 소요 시간: {experiment["seconds"]:.1f}초','','## 성능','','|구간|MAE 원/kWh|RMSE 원/kWh|R²|전주 기준 MAE|','|---|---:|---:|---:|---:|']
        for _,r in overall.iterrows():lines.append(f'|{r["split"]}|{r.mae:.4f}|{r.rmse:.4f}|{r.r2:.4f}|{r.baseline_weekly_mae:.4f}|')
        lines+=['','## 예측일별','','|구간|예측일|MAE|RMSE|','|---|---:|---:|---:|']
        for _,r in days.iterrows():lines.append(f'|{r["split"]}|D+{int(r.forecast_day)}|{r.mae:.4f}|{r.rmse:.4f}|')
        lines+=['','## 한계','','동월 LNG 단가 제공 조건부 과거 실험입니다. 실측 공개시각을 검증한 것이 아니라72시간 지연을 가정했고 과거SMP에도 같은 보수적 지연을 적용했습니다. 2025년 발전량 원본은1일뿐이므로99.726% 결측을 대체한 조건입니다. 나중에 검증한2023/2025년 연간 발전량을 이번 입력에 반영하지 않았습니다. 원자료 시장/육지 범위 차이와서울108단일관측소 등의 한계도 그대로입니다.','','기존 모델의 하반기 결과를 이미 확인한 뒤 추가하는 모델 비교입니다. 미사용 자료에 대한 새 독립 시험으로 주장하지 않습니다. 중요도는 트리의 분할 기여를 나타내며 인과적 경제 효과가 아닙니다.','','## 구현 및 공식 문서','','XGBoost는 XGBRegressor의 hist 트리·규제·행/열 샘플링을 사용합니다. LightGBM은 LGBMRegressor의 leaf 수·최소 leaf 표본·규제로 복잡도를 제한합니다. 알고리즘 자체 구현을 새로 복제하지 않고 공식 라이브러리를 사용했습니다. [XGBoost 문서](https://xgboost.readthedocs.io/en/stable/python/python_api.html) / [LightGBM 문서](https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.LGBMRegressor.html).','','## 재현','','```sh',f'1120gradpj/.venv/bin/python 1120gradpj/models/{name}/train.py','1120gradpj/.venv/bin/python 1120gradpj/scripts/report_tree_models_v3.py','```','','후보별 설정·경고·Validation MAE는 candidate_results.json, 라이브러리·코드해시·원본해시는 experiment.json을 확인하세요. 저장 모델의 Validation/Test 예측 재현과 평가키 일치·미래정답변경 불변을 검사했습니다. 전체25,992개 예측과 월별·발행일별·예측거리별 지표, PNG/확대HTML은 로컬결과에 저장했습니다.','', '```json',json.dumps(candidates,ensure_ascii=False,indent=2),'```']
        (reports/'final_evaluation_report.md').write_text('\n'.join(lines)+'\n')
        latest['verification']=checks;latest['report_directory']=str(reports);latest['active']=True
        c.dump(here/'CURRENT_RUN.json',latest)
    combined=pd.concat(allmetrics,ignore_index=True);out=ROOT/'reports/four_models_v3';out.mkdir(parents=True,exist_ok=True);combined.to_csv(out/'comparison.csv',index=False)
    lines=['# 4개 모델 — 발전량 보완 전 공통 v3 비교','','데이터·평가 날짜·정답·기준예측이 같은4개 모델의 실제 실행 결과입니다. 현재 선택된 LSTM·SARIMAX v3와 새 LightGBM·XGBoost를 비교합니다. 기존 LSTM·SARIMAX 모델 및 결과는 변경하지 않았습니다.','','|모델|구간|MAE 원/kWh|RMSE 원/kWh|R²|전주 기준 MAE|','|---|---|---:|---:|---:|---:|']
    for _,r in combined.iterrows():lines.append(f'|{r.model}|{r["split"]}|{r.mae:.4f}|{r.rmse:.4f}|{r.r2:.4f}|{r.baseline_weekly_mae:.4f}|')
    lines+=['','各모델의 평가행은25,992개(Validation12,888·하반기13,104)로 모두 일치합니다. 후보·조기종료 선택은Validation으로만 수행했습니다. 이번 비교로 하반기 성능을 보고 새 후보를 추가하지 않았습니다.','','동월LNG조건부 입력·실측72시간공개지연가정·2025년발전량99.726%결측대체 등 공통한계가 유지됩니다. 이 하반기 기간은 이전 모델 결과를 이미 확인한 기간이므로 후속모델 비교로 구분합니다.','','- [LightGBM 보고서](../../models/lightgbm/reports/v3_common/final_evaluation_report.md)','- [XGBoost 보고서](../../models/xgboost/reports/v3_common/final_evaluation_report.md)']
    (out/'README.md').write_text('\n'.join(lines).replace('各모델','각 모델')+'\n')
    print(combined[combined.split=='test'][['model','mae','rmse','r2']].sort_values('mae').to_string(index=False),flush=True)
    print('PASS all four v3 models: identical targets and both tree model checkpoint predictions')

if __name__=='__main__':main()
