"""Generate an honest final report from an actually completed SARIMAX run."""
from pathlib import Path
import json,sys,shutil
import pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'src'))
from smp_forecast import common_v3 as contract


def main():
    reports=HERE/'reports';latest=json.loads((reports/'latest_run_v3.json').read_text());run=Path(latest['path'])
    overall=pd.read_csv(run/'overall_metrics.csv');days=pd.read_csv(run/'forecast_days_metrics.csv');candidates=json.loads((run/'candidate_results.json').read_text());exp=latest['experiment']
    quality=json.loads((contract.OUT/'quality_report.json').read_text())
    lines=['# SARIMAX 72시간 최종 평가 — 공통 v3','','실제 statsmodels SARIMAX 학습·Validation 선택·Final Test 평가를 수행했습니다.','',f'- 데이터: `{contract.VERSION}` / 팀 원본 커밋 `{contract.SHA}`',f'- 결과: `{run.relative_to(contract.WORK)}`',f'- 모델: order={exp["order"]}, seasonal_order={exp["seasonal_order"]}',f'- 학습·평가 소요: {exp["seconds"]:.1f}초',f'- 외생변수 83열 유지, Train 행렬 rank={exp["rank"]}. Train 시간별 표본 17,280개.','- **전체 외생계수 최소노름 OLS → 계수 고정 → ARIMA/계절/분산 조건부 최대우도**의 2단계 추정입니다. 모든 계수를 공동 MLE로 최적화한 결과는 아닙니다. 상수·중복 열을 임의 삭제하거나 외생변수 없는 SARIMA로 축소하지 않았습니다.','','## 전체 성능','','|구간|행 수|MAE 원/kWh|RMSE 원/kWh|R²|전주 패턴 MAE|전주 대비 개선율|','|---|---:|---:|---:|---:|---:|---:|']
    for _,r in overall.iterrows():lines.append(f'|{r["split"]}|{int(r.rows)}|{r.mae:.4f}|{r.rmse:.4f}|{r.r2:.4f}|{r.baseline_weekly_mae:.4f}|{r.baseline_weekly_improvement_pct:.2f}%|')
    lines+=['','## 예측일별 성능','','|구간|예측일|MAE|RMSE|','|---|---:|---:|---:|']
    for _,r in days.iterrows():lines.append(f'|{r["split"]}|D+{int(r.forecast_day)}|{r.mae:.4f}|{r.rmse:.4f}|')
    lstmfile=ROOT/'models/lstm/reports/v3_overall_metrics.csv'
    if lstmfile.exists():
        lstm=pd.read_csv(lstmfile);lines+=['','## 동일 평가 대상 LSTM 비교','','|구간|SARIMAX MAE|LSTM MAE|','|---|---:|---:|']
        for split in ['validation','test']:
            a=overall[overall.split==split].iloc[0];b=lstm[lstm.split==split].iloc[0];lines.append(f'|{split}|{a.mae:.4f}|{b.mae:.4f}|')
    lines+=['','## 시간 기준 및 검증','','- 매일 23시 발행, 다음 3일 00~23시 총72시간입니다. 실측 마감은 발행시각−72시간으로 고정합니다.','- 마지막 상태는 실측 마감에 종료된 SMP까지만 필터링합니다. 이후 공백73시간과 목표72시간을 함께145시간 예측하고 뒤72시간을 저장합니다. 중간 미래 SMP를 주입하지 않습니다.','- 후보마다 계수는 Train만으로 적합합니다. Validation은 설정 선택, Final Test는 선택 후 평가에만 사용합니다. Train+Validation 재학습 및 매일 계수 재추정은 하지 않습니다.','- 상태 갱신은 계수 재학습과 다릅니다. 이미 이용 가능한 과거 SMP만 새로 필터링합니다.','- Train 마지막 상태를 평가에 그대로 연결하지 않고, 첫 평가의 마감까지의 과거만 다시 필터링합니다.','- 학습용 중복 목표시간은 최신 발행 입력 한 행을 채택합니다. 평가에서는 겹치는 모든 72시간 블록을 보존합니다.','- 공통 evaluation_origins/targets를 그대로 사용했습니다. Validation179개·Final Test182개 발행일, 각72행입니다.','','## 데이터 및 해석 한계','','실제 수요, 발전량, 예비력 및 기상 관측자료의 개별 공표시각을 모두 확인할 수 없어, 본 연구에서는 예측 기준시각보다 72시간 이전의 실측 자료만 활용하는 보수적 지연 규칙을 가정하였다. 이 규칙은 각 자료의 실제 공개시각을 검증한 결과가 아니다.','','- **동월 LNG 단가 제공 조건부 과거 예측 실험**입니다. 실제 운영에서 당시 이용 가능한 단가임이 검증된 것은 아닙니다.','- 2025년 발전량 핵심 변수의 원본 결측률은99.726%, 2023년은73.699%입니다. 이를 Train 대표값 등으로 대체한 조건이며 발전량 수집 완료를 의미하지 않습니다. 수요1095시간, 예비력703시간, ASOS 일사11956시간 결측도 공통 규칙을 유지합니다.','- EPSIS 수요의 원자료 범위를 유지하며 전국 자료를 육지라고 이름 바꾸지 않았습니다. 발전량·예비력의 시장/지역 범위와 육지 SMP의 범위 차이도 남아 있습니다.','- 중기예보는 실제 발표시각과 대상 날짜로 연결합니다. 과거 발행본을 당일 발표 단기예보로 표현하지 않습니다.','- SMP도 추가로72시간 지연했습니다. 23시에는 일부 대상일 SMP가 공식 공표되었을 수 있으며, 이 연구의 운영상 효용은 별도 검토해야 합니다.','- Train 전체로 계수를 추정하는 오프라인 분할 평가입니다. 실제 공개 지연을 고려할 때 연말 Train 정답이 첫 Validation 발행일 전에 모두 확보되었는지 증명하는 운영 실험이 아닙니다.','- rank 결손으로 개별 외생계수의 유일한 경제적 효과를 주장할 수 없습니다. OLS와 ARIMA의 2단계 추정은 공동추정보다 비효율적일 수 있습니다.','- 예측구간은 모형·고정 beta 조건부 구간입니다. 외생예보/대체값/연료/계수 추정의 모든 불확실성을 포함하는 보정 확률구간이 아닙니다.','- 최종 테스트는7~12월로 사계절 전체 검증이 아니며 겹치는 목표시간의 오차는 독립 표본이 아닙니다.','','## 후보별 수렴·경고','', '```json',json.dumps(candidates,ensure_ascii=False,indent=2),'```','','## 산출물·재현','','전체 예측 CSV, 발행일·월·예측거리별 지표, 선택일 PNG/HTML과6개월 비교는 위 결과 폴더에 있습니다. 원본과 LSTM 결과는 보존했습니다. 인증키가 필요 없는 기존 공통 데이터 재사용입니다.','', '```sh','1120gradpj/.venv/bin/python 1120gradpj/models/sarimax/train.py','1120gradpj/.venv/bin/python 1120gradpj/models/sarimax/report_v3.py','```','']
    (reports/'final_evaluation_report_v3.md').write_text('\n'.join(lines)+'\n')
    (reports/'model_experiment_report_v3.md').write_text('# SARIMAX 실험 설정\n\n'+json.dumps(exp,ensure_ascii=False,indent=2)+'\n')
    (reports/'data_collection_report_v3.md').write_text('# 공통 v3 자료 재사용\n\n새 수집 없이 LSTM과 동일한 원본·해시·전처리 버전을 사용했습니다. 자료별 선택·단위·품질은 `../../lstm/reports/data_collection_report_v3.md`, 상세 결측은 공통 버전 quality_report.json을 확인하세요.\n\n'+json.dumps(quality,ensure_ascii=False,indent=2)+'\n')
    (reports/'data_blockers.md').write_text('# 현재 상태\n\n필수 그룹 원본을 모두 확인하고 합의된 결측 처리로 실제 학습·평가를 완료했습니다. 개별 공개시각 미확인·발전량 큰 결측·동월 LNG 조건부 입력·rank 결손 및 제약 추정의 한계는 최종 보고서에 공개했습니다.\n')
    shutil.copyfile(run/'figures/selected_72h.png',reports/'selected_72h_v3.png');shutil.copyfile(run/'figures/monthly_mae.png',reports/'monthly_mae_v3.png')
    print('Report generated',reports/'final_evaluation_report_v3.md')

if __name__=='__main__':main()
