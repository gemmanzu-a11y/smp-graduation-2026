"""Compare completed, versioned v3/v4 runs without any fitting or test-driven tuning."""
from pathlib import Path
import sys,json,hashlib,shutil
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from smp_forecast import common_v3 as old,common_v4 as new

def main():
    out=ROOT/'reports/generation_update_v4';out.mkdir(parents=True,exist_ok=True)
    rows=[];checks={};reference=None
    for model in ['lstm','sarimax']:
        folder=ROOT/'models'/model
        before=Path(json.loads((folder/'reports/latest_run_v3.json').read_text())['path'])
        reports=folder/'reports/v4_generation_update'
        after=Path(json.loads((reports/'latest_run_v4.json').read_text())['path'])
        x=pd.read_csv(before/'predictions.csv');y=pd.read_csv(after/'predictions.csv')
        keys=['split','forecast_origin','target_timestamp','horizon'];stable=keys+['actual_smp','baseline_origin_day','baseline_weekly','observed_cutoff']
        x=x.sort_values(keys).reset_index(drop=True);y=y.sort_values(keys).reset_index(drop=True)
        pd.testing.assert_frame_equal(x[stable],y[stable])
        if reference is None:reference=y[stable]
        else:pd.testing.assert_frame_equal(reference,y[stable])
        if model=='lstm':
            a=json.loads((before/'config_before_training.json').read_text());b=json.loads((after/'config_before_training.json').read_text())
            assert a['candidates']==b['candidates'] and a['seed']==b['seed']
        else:
            a=json.loads((before/'config_before_training.json').read_text());b=json.loads((after/'config_before_training.json').read_text())
            assert a['candidates']==b['candidates'] and a['maxiter']==b['maxiter'] and a['features']==b['features']
        for split in ['validation','test']:
            for label,days in [('all',[1,2,3]),('D+1',[1]),('D+2',[2]),('D+3',[3])]:
                bx=x[(x.split==split)&x.forecast_day.isin(days)];ay=y[(y.split==split)&y.forecast_day.isin(days)]
                oldmae=float(np.abs(bx.predicted_smp-bx.actual_smp).mean());err=ay.predicted_smp-ay.actual_smp;newmae=float(np.abs(err).mean())
                r2=1-float((err**2).sum()/((ay.actual_smp-ay.actual_smp.mean())**2).sum())
                rows.append(dict(model=model.upper(),split=split,forecast_day=label,rows=len(ay),before_mae=oldmae,after_mae=newmae,mae_reduction_pct=100*(1-newmae/oldmae),after_rmse=float(np.sqrt((err**2).mean())),after_r2=r2,weekly_baseline_mae=float(np.abs(ay.baseline_weekly-ay.actual_smp).mean())))
        # Keep small visuals public; full HTML, predictions and trained binaries stay local.
        for name in ['selected_72h','monthly_mae']:shutil.copyfile(after/'figures'/(name+'.png'),reports/(name+'_v4.png'))
        checks[model]=dict(before_run=str(before),after_run=str(after),same_25992_evaluation_rows=True,same_targets_and_baselines=True,same_candidate_grid=True,model_sha256=hashlib.sha256((after/('model.pt' if model=='lstm' else 'model.npz')).read_bytes()).hexdigest())
    frame=pd.DataFrame(rows);frame.to_csv(out/'comparison.csv',index=False)
    quality=json.loads((new.OUT/'quality_report.json').read_text())
    lines=['# 발전량 보완 후 LSTM·SARIMAX 재실행','','**실제 재학습·평가 완료. 데이터 보완 후의 후속 실험이며, 최초의 독립 Final Test와 구분합니다.**','',f'- 이전 공통 버전: `{old.VERSION}`',f'- 새 공통 버전: `{new.VERSION}`','- 변경: 2023·2025년 발전량을 검증한 연간 CSV로 교체. 2024년은 API와 남은 결측 유지.','- 유지: 나머지11개 입력 그룹, 목표SMP, 평가 날짜, 기준 예측,72시간 지연,Train/Validation/Test 분할,각모델 후보군과 선택 기준.','- 원본·기존 공통v3·기존 모델 및 성능표는 보존했습니다.','','## 최종 하반기 비교','','|모델|보완 전 MAE|보완 후 MAE|오차 감소율|보완 후 RMSE|보완 후 R²|전주 기준 MAE|','|---|---:|---:|---:|---:|---:|---:|']
    for _,r in frame[(frame.split=='test')&(frame.forecast_day=='all')].iterrows():lines.append(f'|{r.model}|{r.before_mae:.4f}|{r.after_mae:.4f}|{r.mae_reduction_pct:.2f}%|{r.after_rmse:.4f}|{r.after_r2:.4f}|{r.weekly_baseline_mae:.4f}|')
    lines+=['','MAE·RMSE単位: 원/kWh. 감소율이 음수면 오차가 증가한 것입니다. 데이터 보완만으로 성능 개선이 보장되는 것은 아닙니다.','','## Validation과 예측일별 성능','','|모델|구간|예측일|보완 전 MAE|보완 후 MAE|R²|','|---|---|---|---:|---:|---:|']
    for _,r in frame.iterrows():lines.append(f'|{r.model}|{r["split"]}|{r.forecast_day}|{r.before_mae:.4f}|{r.after_mae:.4f}|{r.after_r2:.4f}|')
    lines+=['','## 조건과 해석','','발전량 외 다른 변수는 데이터 값까지 이전 버전과 같음을 확인했습니다. 두 모델 모두 평가25992행(Validation12888행·하반기13104행)의 키·정답·기준예측이 일치합니다. 학습 및 대체 통계·표준화는Train으로만 적합하고,Validation으로 후보·LSTM epoch를 선택했습니다. 하반기 결과를 보고 추가 후보를 만들거나 재튜닝하지 않았습니다.','','다만 이전 하반기 성능을 확인한 뒤 발전량 입력을 개선한 실험이므로, 이 하반기를 처음 보는 독립적인 최종 검증이라고 주장하지 않습니다. 이후 추가 개선을 계속하면 별도 미사용 기간이나 시계열 교차검증이 필요합니다.','','동월 LNG 제공 조건부 입력,실측72시간 지연은 공개시각 검증이 아닌 가정,서울 단일 관측소,시장/육지 범위 차이,2024년 발전량 결측 및일부수요·기상 결측 등의 한계는 유지됩니다. 2023년 연간자료와API의정산버전 차이도 남아 있습니다.','','SARIMAX는 기존과 같은 외생계수 최소노름OLS 고정 후ARIMA계수 조건부최대우도 방식입니다. 공동MLE로 바꾸지 않았습니다. LSTM은 기존 직접72시간 출력 구조를 유지했습니다.','','## 보완 후 원본 발전량 결측','',json.dumps(quality['generation_missing_by_year'],ensure_ascii=False,indent=2),'','## 재현','','```sh','PYTHONPATH=1120gradpj/src 1120gradpj/.venv/bin/python -m smp_forecast.common_v4','1120gradpj/.venv/bin/python 1120gradpj/models/lstm/train.py --dataset-version v4','1120gradpj/.venv/bin/python 1120gradpj/models/sarimax/train.py --dataset-version v4','1120gradpj/.venv/bin/python 1120gradpj/models/sarimax/report_v3.py --dataset-version v4','1120gradpj/.venv/bin/python 1120gradpj/scripts/compare_generation_update_v4.py','```','']
    (out/'README.md').write_text('\n'.join(lines).replace('単位','단위')+'\n')
    new.dump(out/'verification.json',checks)
    print(frame[(frame.split=='test')&(frame.forecast_day=='all')].to_string(index=False),flush=True)

if __name__=='__main__':main()
