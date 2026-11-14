"""Validation-selected XGBoost, daily 23:00 origins, direct 72-hour forecasts.
Run from project root: .venv/bin/python models/xgboost/train_validated.py
No network requests. Never select parameters using test errors.
"""
from pathlib import Path
import sys, json, time
import numpy as np
import pandas as pd
from xgboost import XGBRegressor
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from smp_forecast.http import ROOT, write_json, now
from smp_forecast.training import scores, plot_results


def audit(meta, x, y):
    """Fail before fitting if target periods overlap or sources exceed origin."""
    origin = pd.to_datetime(meta.origin, utc=True)
    target = pd.to_datetime(meta.timestamp, utc=True)
    source = pd.to_datetime(meta.latest_source_timestamp, utc=True)
    assert (source <= origin).all()
    assert (target > origin).all()
    assert not meta.duplicated(['origin', 'timestamp']).any()
    assert meta.groupby('origin').size().eq(72).all()
    assert meta.groupby(['origin', 'horizon_days']).size().eq(24).all()
    assert len(x) == len(meta) == len(y) and np.isfinite(y).all()
    periods = {'train': ('2023-01-01', '2024-12-31'),
               'validation': ('2025-01-01', '2025-06-30'),
               'test': ('2025-07-01', '2025-12-31')}
    local = target.dt.tz_convert('Asia/Seoul').dt.strftime('%Y-%m-%d')
    for split, (lo, hi) in periods.items():
        dates = local[meta.split == split]
        assert len(dates) and dates.between(lo, hi).all()
    # Every 72h forecast block belongs to one split; boundary blocks were purged.
    assert meta.groupby('origin').split.nunique().eq(1).all()


def main():
    raise SystemExit('기존 부분 입력 XGBoost 실험은 비활성화했습니다. 공통 입력 연결 후 새 실험으로 재구현해야 합니다.')
    start = time.monotonic()
    out = ROOT / 'models/xgboost/artifacts_validated'
    out.mkdir(parents=True, exist_ok=True)
    data = np.load(ROOT / 'data/processed/training_dataset.npz')
    x, y = data['x'], data['y'].reshape(-1)
    meta = pd.read_csv(ROOT / 'data/processed/training_metadata.csv')
    names = json.loads((ROOT / 'data/processed/feature_names.json').read_text())
    audit(meta, x, y)
    tr, va, te = [meta.split.eq(s).to_numpy() for s in ['train', 'validation', 'test']]
    # Remove unavailable features using training data only. XGBoost handles other NaN.
    keep = ~np.isnan(x[tr]).all(axis=0)
    used_names = np.asarray(names)[keep].tolist()
    x = x[:, keep]
    common = dict(objective='reg:squarederror', eval_metric='mae',
                  tree_method='hist', learning_rate=0.045, n_estimators=1000,
                  min_child_weight=10, subsample=0.9, colsample_bytree=0.85,
                  random_state=42, n_jobs=4, early_stopping_rounds=50)
    trials, best_model, best_score = [], None, float('inf')
    for depth in [3, 5]:
        for regularization in [5.0, 15.0]:
            model = XGBRegressor(**common, max_depth=depth, reg_lambda=regularization)
            model.fit(x[tr], y[tr], eval_set=[(x[tr], y[tr]), (x[va], y[va])], verbose=False)
            validation_mae = float(np.mean(np.abs(model.predict(x[va]) - y[va])))
            trial = dict(max_depth=depth, reg_lambda=regularization,
                         best_trees=model.best_iteration + 1, validation_MAE=validation_mae)
            trials.append(trial)
            print(json.dumps(trial), flush=True)
            if validation_mae < best_score:
                best_model, best_score = model, validation_mae
                write_json(out / 'learning_curve.json', model.evals_result())
    # Freeze the winner. Do not fit on validation/test or choose by test scores.
    pd.DataFrame(trials).to_csv(out / 'validation_search.csv', index=False)
    best_model.save_model(out / 'model.ubj')
    write_json(out / 'features.json', dict(used=used_names, dropped=np.asarray(names)[~keep].tolist()))
    frame = meta[va | te].copy()
    frame['actual_smp'] = y[va | te]
    frame['predicted_smp'] = best_model.predict(x[va | te])
    frame['model'] = 'xgboost_validated'
    frame.to_csv(out / 'predictions.csv', index=False)
    metrics = pd.DataFrame(scores(frame))
    for label, col in [('origin_day', 'baseline_last_origin_day'), ('weekly', 'baseline_weekly')]:
        baseline = frame.copy()
        baseline['predicted_smp'] = baseline[col]
        b = pd.DataFrame(scores(baseline))[['split', 'horizon_days', 'MAE', 'RMSE']]
        b = b.rename(columns={'MAE': label + '_MAE', 'RMSE': label + '_RMSE'})
        metrics = metrics.merge(b, on=['split', 'horizon_days'], validate='one_to_one')
        metrics[label + '_MAE_improvement_pct'] = 100 * (1 - metrics.MAE / metrics[label + '_MAE'])
    metrics.to_csv(out / 'metrics.csv', index=False)
    monthly = frame[frame.split == 'test'].copy()
    monthly['month'] = pd.to_datetime(monthly.timestamp, utc=True).dt.tz_convert('Asia/Seoul').dt.strftime('%Y-%m')
    monthly['absolute_error'] = abs(monthly.actual_smp - monthly.predicted_smp)
    monthly.groupby(['month', 'horizon_days']).absolute_error.agg(['mean', 'count']).to_csv(out / 'monthly_mae.csv')
    pd.DataFrame({'feature': used_names, 'gain_importance': best_model.feature_importances_}).sort_values('gain_importance', ascending=False).to_csv(out / 'feature_importance.csv', index=False)
    restored = XGBRegressor()
    restored.load_model(out / 'model.ubj')
    np.testing.assert_allclose(restored.predict(x[te][:72]), best_model.predict(x[te][:72]))
    plot_results(frame, out, 'XGBoost validation-selected')
    manifest = json.loads((ROOT / 'reports/dataset_manifest.json').read_text())
    write_json(out / 'run.json', dict(at=now(), seconds=time.monotonic()-start,
        trials=trials, selected=min(trials, key=lambda t: t['validation_MAE']),
        selection='validation MAE only; early stopping patience 50; test never used for selection',
        split_rows=meta.groupby('split').size().to_dict(),
        split_origins=meta.groupby('split').origin.nunique().to_dict(),
        target_ranges=manifest['target_ranges'], dataset_fingerprint=manifest['fingerprint'],
        parameters={k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in best_model.get_params().items()}, feature_count=len(used_names),
        limitations=['historical publication vintages unverified',
                    'fuel excluded: no release timestamps', 'no target-day weather/load/solar forecasts included',
                    'previous experiments have already reported test performance; not an untouched external holdout'],
        saved_model_roundtrip='passed', temporal_audit='passed'))
    print(metrics[metrics.split == 'test'].to_string(index=False), flush=True)

if __name__ == '__main__':
    main()
