"""Full agreed information contract; partial old datasets cannot unlock training."""
import json
from pathlib import Path
import numpy as np
import pandas as pd

SOURCES = {
    'demand_actual': '전력수요 실적', 'demand_forecast': '하루전 육지 수요예측 mlfd',
    'holidays': '공식 공휴일', 'calendar': '달력',
    'generation': 'LNG·석탄·원자력 발전량', 'renewables': '태양광·풍력 실적',
    'solar_forecast': '하루전 시장 태양광 예측 solgenKpx',
    'reserve': '공급예비력·예비율', 'domestic_lng': '파일 LNG 연료비단가 원/kWh',
    'oil': 'FRED WTI·Brent', 'international_fuel': 'FRED 국제 LNG·석탄',
    'weather_actual': 'ASOS 기온·일사·풍속', 'weather_forecast': '기상청 과거 기온·풍속 예보',
    'solar_weather_forecast': '동서발전 일사·기온·풍속 예측',
}
FEATURES = [
    'demand_history', 'demand_forecast', 'hour_sin', 'hour_cos', 'weekday', 'month',
    'is_weekend', 'is_holiday', 'generation_lng_history', 'generation_coal_history',
    'generation_nuclear_history', 'solar_history', 'wind_history', 'solar_forecast',
    'reserve_mw_history', 'reserve_pct_history', 'domestic_lng_cost_krw_kwh',
    'wti_usd_bbl', 'brent_usd_bbl', 'international_lng_usd_mmbtu',
    'international_coal_usd_tonne', 'temperature_history', 'irradiance_history',
    'wind_history_ms', 'temperature_forecast', 'wind_forecast_ms',
    'ewp_irradiance_forecast', 'ewp_temperature_forecast', 'ewp_wind_forecast_ms',
]


def parse_time(series):
    # Reject naive input rather than interpreting local hours as UTC.
    if not series.astype(str).str.contains(r'(?:Z|[+-]\d{2}:?\d{2})$', regex=True).all():
        raise ValueError('Timezone offset is required in all timestamps')
    return pd.to_datetime(series, utc=True).dt.tz_convert('Asia/Seoul')


def origins(start, end):
    # Only whole 72h blocks inside one target split.
    return pd.date_range(pd.Timestamp(start, tz='Asia/Seoul')-pd.Timedelta(hours=1),
        pd.Timestamp(end, tz='Asia/Seoul')-pd.Timedelta(days=2, hours=1), freq='D')


def inspect_bundle(shared, cfg):
    shared = Path(shared)
    issues = []
    required = ['manifest.json', 'hourly.csv', 'forecast_inputs.csv']
    for name in required:
        if not (shared/name).is_file():
            issues.append({'variable': name, 'reason': '공통 입력 파일 미생성',
                'action': 'README 형식으로 공통 데이터 준비; 부분 입력으로 학습하지 않음'})
    if issues:
        return issues, None
    try:
        manifest = json.loads((shared/'manifest.json').read_text())
        for source, label in SOURCES.items():
            rec = manifest.get('sources', {}).get(source, {})
            if rec.get('status') != 'complete':
                issues.append({'variable': label, 'reason': '필수 출처의 전체 기간 수집·정규화 미완료',
                    'action': '누락 기간과 실제 실패 원인을 수집 보고서에 기록'})
            for key in ['evidence_file', 'unit', 'scope', 'mapping', 'availability_rule']:
                if not rec.get(key):
                    issues.append({'variable': label, 'reason': '출처 명세 누락: '+key,
                        'action': '원자료 근거와 필드 매핑 보완'})
            evidence = shared / rec.get('evidence_file', '__missing__')
            if not evidence.is_file():
                issues.append({'variable': label, 'reason': '원자료 근거 파일 없음', 'action': '실제 수집 파일 연결'})
        if manifest.get('fuel_policy') != cfg['fuel_policy']:
            issues.append({'variable': 'fuel_policy', 'reason': '공통 연료 규칙 불일치', 'action': '동월 LNG 조건부 실험 규칙 적용'})
        if issues: return issues, None
        hourly = pd.read_csv(shared/'hourly.csv')
        future = pd.read_csv(shared/'forecast_inputs.csv')
        for col in ['timestamp', 'feature_origin', 'latest_nonfuel_source_timestamp']:
            hourly[col] = parse_time(hourly[col])
        for col in ['forecast_origin', 'target_timestamp', 'latest_nonfuel_source_timestamp']:
            future[col] = parse_time(future[col])
        expected = pd.date_range(cfg['train_start'], cfg['test_end']+' 23:00', freq='h', tz='Asia/Seoul')
        hourly = hourly.sort_values('timestamp').set_index('timestamp')
        if not hourly.index.equals(expected): raise ValueError('hourly.csv must contain every 2023–2025 hour exactly once')
        if not (hourly.feature_origin < hourly.index).all(): raise ValueError('Historical feature origin must precede target hour')
        if not (hourly.latest_nonfuel_source_timestamp <= hourly.feature_origin).all():
            raise ValueError('Future nonfuel information in historical training inputs')
        if not (future.latest_nonfuel_source_timestamp <= future.forecast_origin).all():
            raise ValueError('Future actual/forecast issuance timestamp exceeds origin')
        if future.duplicated(['forecast_origin', 'target_timestamp']).any(): raise ValueError('Duplicate forecast rows')
        if not np.isfinite(hourly[['smp']+FEATURES].to_numpy(dtype=float)).all(): raise ValueError('Required hourly inputs contain NaN/inf')
        if not np.isfinite(future[FEATURES].to_numpy(dtype=float)).all(): raise ValueError('Required future inputs contain NaN/inf')
        future = future.sort_values(['forecast_origin', 'target_timestamp'])
        required_origins = origins(cfg['validation_start'], cfg['validation_end']).union(origins(cfg['test_start'], cfg['test_end']))
        for origin in required_origins:
            block = future[future.forecast_origin == origin]
            targets = pd.date_range(origin+pd.Timedelta(hours=1), periods=72, freq='h')
            if len(block) != 72 or not pd.DatetimeIndex(block.target_timestamp).equals(targets):
                raise ValueError('Missing 72h block: '+str(origin))
        return [], (hourly, future, manifest)
    except (ValueError, KeyError, TypeError) as exc:
        return [{'variable': 'common_bundle', 'reason': str(exc), 'action': '공통 데이터 정합성 보완; 학습 금지'}], None
