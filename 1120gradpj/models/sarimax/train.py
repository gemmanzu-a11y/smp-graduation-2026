"""SARIMAX entry: audit first, stop on any missing agreed input, then select by validation."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import time
import numpy as np
import pandas as pd
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'src'))
from smp_forecast.http import write_json, now
from algorithm import Estimator
from contract import FEATURES, SOURCES, inspect_bundle, origins
from fuel import read_lng, fuel_for_targets


def audit(cfg, shared):
    issues, bundle = inspect_bundle(shared, cfg)
    local_files = {
        'demand_actual': 'power_hourly.csv',
        'demand_forecast': 'section_a/demand_forecast_mainland_2023_2025.csv',
        'holidays': 'section_a/holidays_official_2023_2025.csv',
        'renewables': 'renewable_hourly.csv', 'reserve': 'power_hourly.csv',
        'weather_actual': 'weather_hourly.csv',
    }
    inventory = []
    for source, label in SOURCES.items():
        filename = local_files.get(source)
        path = ROOT/'data/processed'/filename if filename else None
        row = dict(source=source, variable=label, required_period='2023-01-01~2025-12-31')
        if path is not None and path.is_file():
            data = pd.read_csv(path)
            timecol = next((c for c in ['timestamp','date','month'] if c in data), None)
            row.update(file=filename, rows=len(data), first=str(data[timecol].min()) if timecol else None,
                last=str(data[timecol].max()) if timecol else None,
                state='기존 파일 존재; 새 공통 정의·품질·출처 검증 필요')
            if source == 'reserve': row['state'] = '기존 예비율 있음; 공급예비력 MW 정규화는 미완료'
            if source == 'holidays': row['state'] = '2023~2025 공식 API 자료 확보; 새 공통 입력 행렬 연결 필요'
            if source == 'demand_forecast': row['state'] = '공식 연간 육지 수요예측 26,304시간 확보; 원본 공표 이력은 미검증'
            if source == 'demand_actual': row['state'] = '기존 EPSIS 실적 1,095시간 결측 유지; 결측 없는 공식 전국 발전단 후보 별도 확보, 혼합하지 않음'
        elif source == 'domestic_lng':
            row['state'] = '아래 지정 엑셀에서 직접 확인'
        elif source == 'calendar':
            row['state'] = '시간축에서 생성 가능; 공통 행렬 미생성'
        else:
            row['state'] = '전체 기간의 정규화 파일 없음; 표본 API 성공 여부와 별개'
        inventory.append(row)
    write_json(HERE/'source_inventory.json', inventory)
    # Always inspect the actual supplied workbook; never silently use the old fuel CSV.
    workbooks = list(ROOT.parent.glob('HOME_*.xlsx'))
    if len(workbooks) != 1:
        issues.append(dict(variable='domestic_lng', reason='지정 HOME 엑셀 파일을 유일하게 찾을 수 없음', action='원본 파일 경로 확인'))
    else:
        monthly, evidence = read_lng(workbooks[0])
        expected = pd.period_range(cfg['train_start'][:7], cfg['test_end'][:7], freq='M').astype(str)
        missing = sorted(set(expected)-set(monthly.month))
        if missing: issues.append(dict(variable='domestic_lng', reason='월 누락: '+','.join(missing), action='동일 원본 표의 누락월 확보'))
        (ROOT/'data/processed').mkdir(parents=True, exist_ok=True)
        monthly.to_csv(ROOT/'data/processed/lng_workbook_monthly.csv', index=False)
        write_json(HERE/'data_audit_fuel.json', dict(**evidence, first=monthly.month.min(), last=monthly.month.max(), rows=len(monthly), november_demo_ready='2026-10' in set(monthly.month)))
        if bundle is not None:
            history, future, _ = bundle
            actual = fuel_for_targets(monthly, history.index, pd.Timestamp('2025-12-31 23:00', tz='Asia/Seoul'))
            if not np.allclose(history.domestic_lng_cost_krw_kwh, actual):
                issues.append(dict(variable='domestic_lng', reason='학습 입력의 동월 파일 값 불일치', action='지정 파일 값으로 병합'))
            for origin, block in future.groupby('forecast_origin'):
                expected_fuel = fuel_for_targets(monthly, pd.DatetimeIndex(block.target_timestamp), origin)
                if not np.allclose(block.domestic_lng_cost_krw_kwh, expected_fuel):
                    issues.append(dict(variable='domestic_lng', reason='예측 입력의 대상월 매핑 불일치', action='동월 값 연결'))
                    break
    if bundle is None:
        for row in inventory:
            if row['source'] not in ['calendar','domestic_lng']:
                issues.append(dict(variable=row['variable'], reason=row['state'], action='2023~2025 공통 입력 정규화·근거 확인; 수집 오류 원인 미확정'))
    status = dict(at=now(), status='BLOCKED' if issues else 'READY', can_train=not issues,
        model='sarimax', shared_directory=str(shared), issues=issues, required_sources=SOURCES,
        limitation='동월 LNG 제공 조건부 실험; 실제 운영 공개시각 검증 아님')
    write_json(HERE/'data_status.json', status)
    lines = ['# SARIMAX 데이터 상태', '', '상태: '+status['status'], '',
        '| 항목 | 차단 원인 | 조치 |', '|---|---|---|']
    lines += ['| '+r['variable']+' | '+r['reason'].replace('|','/')+' | '+r['action']+' |' for r in issues]
    lines += ['', '공통 입력 미생성은 API 오류를 의미하지 않습니다. 기존 일부 자료만으로는 새 필수 변수 전체를 충족하지 못합니다.',
        '필요 기간: 2023-01-01~2025-12-31. 원자료 미수집·과거 조회 불가·인증 실패 여부는 별도 실제 수집 진단으로 구분해야 합니다.']
    (HERE/'DATA_STATUS.md').write_text('\n'.join(lines)+'\n')
    return status, bundle


def backtest(model, hourly, future, begin, end):
    rows = []
    for origin in origins(begin, end):
        recent = hourly[(hourly.index > model.last_timestamp) & (hourly.index <= origin)]
        if len(recent): model.update(recent.smp, recent[FEATURES], origin)
        block = future[future.forecast_origin == origin].set_index('target_timestamp')[FEATURES]
        forecast = model.predict72(block, origin)
        target = forecast.index
        forecast['actual_smp'] = hourly.smp.reindex(target).to_numpy()
        forecast['forecast_origin'] = origin
        forecast['target_timestamp'] = target
        forecast['horizon'] = np.arange(1,73)
        forecast['forecast_day'] = np.repeat([1,2,3],24)
        forecast['baseline_origin_day'] = hourly.smp.reindex(origin.normalize()+pd.to_timedelta(target.hour,unit='h')).to_numpy()
        forecast['baseline_weekly'] = hourly.smp.reindex(target-pd.Timedelta(days=7)).to_numpy()
        rows.append(forecast.reset_index(drop=True))
    return pd.concat(rows, ignore_index=True)


def metrics(frame):
    result = []
    for split, data in frame.groupby('split'):
        for horizon, g in [('all', data)]+[(str(k),g) for k,g in data.groupby('forecast_day')]:
            for model, col in [('sarimax','predicted_smp'),('origin_day','baseline_origin_day'),('weekly','baseline_weekly')]:
                error = g.actual_smp-g[col]
                result.append(dict(split=split, forecast_day=horizon, model=model, rows=len(g), MAE=float(abs(error).mean()), RMSE=float(np.sqrt((error**2).mean()))))
    return pd.DataFrame(result)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--audit-only',action='store_true')
    parser.add_argument('--shared-dir',type=Path)
    args=parser.parse_args()
    cfg=json.loads((ROOT/'configs/sarimax.json').read_text())
    shared=args.shared_dir or (ROOT/cfg['shared_directory']).resolve()
    status,bundle=audit(cfg,shared)
    print(json.dumps(status,ensure_ascii=False,indent=2))
    if not status['can_train']: return 2
    if args.audit_only: return 0
    hourly,future,manifest=bundle
    out=HERE/'artifacts';out.mkdir(exist_ok=True)
    train=hourly.loc[cfg['train_start']:cfg['train_end']]
    trials=[];best=float('inf');winner=None
    for i, candidate in enumerate(cfg['candidates']):
        started=time.monotonic()
        try:
            model=Estimator(**candidate,maxiter=cfg['maxiter']).fit(train.smp,train[FEATURES])
            candidate_dir=out/f'candidate_{i}'
            model.save(candidate_dir)  # Save train-end state before validation updates.
            validation=backtest(model,hourly,future,cfg['validation_start'],cfg['validation_end'])
            mae=float(abs(validation.actual_smp-validation.predicted_smp).mean())
            trials.append(dict(candidate=i,**candidate,validation_MAE=mae,seconds=time.monotonic()-started,status='completed',warnings=model.fit_warnings))
            if mae<best:best,winner=mae,i
        except (RuntimeError,ValueError,np.linalg.LinAlgError) as exc:
            trials.append(dict(candidate=i,**candidate,status='failed',reason=str(exc),seconds=time.monotonic()-started))
        write_json(out/'search.json',trials)
    if winner is None:raise RuntimeError('All candidates failed; no final test result produced')
    selected=out/f'candidate_{winner}'
    val=backtest(Estimator.load(selected),hourly,future,cfg['validation_start'],cfg['validation_end']);val['split']='validation'
    test=backtest(Estimator.load(selected),hourly,future,cfg['test_start'],cfg['test_end']);test['split']='test'
    frame=pd.concat([val,test],ignore_index=True);frame['model_name']='SARIMAX';frame['absolute_error']=abs(frame.actual_smp-frame.predicted_smp)
    frame['forecast_date']=frame.target_timestamp.dt.date
    frame['fuel_input_policy']='target_month_LNG_conditional'
    frame.to_csv(out/'predictions.csv',index=False)
    metrics(frame).to_csv(out/'metrics.csv',index=False)
    frame.groupby(['split','forecast_origin','forecast_day']).absolute_error.mean().to_csv(out/'daily_mae.csv')
    frame.assign(month=frame.target_timestamp.dt.strftime('%Y-%m')).groupby(['split','month','forecast_day']).absolute_error.mean().to_csv(out/'monthly_mae.csv')
    # Verify persisted train-end state makes identical forecasts after the same causal update.
    a,b=Estimator.load(selected),Estimator.load(selected)
    first=origins(cfg['validation_start'],cfg['validation_end'])[0]
    fx=future[future.forecast_origin==first].set_index('target_timestamp')[FEATURES]
    np.testing.assert_allclose(a.predict72(fx,first),b.predict72(fx,first))
    write_json(out/'run.json',dict(at=now(),status='completed',winner=winner,validation_MAE=best,
        test_used_for_selection=False,source_manifest=manifest,fuel_policy=cfg['fuel_policy'],
        forecast_intervals='conditional Gaussian 95%; not calibrated and exclude exog uncertainty',
        bundle_sha256={p:hashlib.sha256((shared/p).read_bytes()).hexdigest() for p in ['hourly.csv','forecast_inputs.csv','manifest.json']}))
    print(metrics(frame).to_string(index=False))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
