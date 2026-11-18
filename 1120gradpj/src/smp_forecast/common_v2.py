"""Versioned shared contract for the revised twelve input groups; no source substitutions."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

SOURCES = ['demand_actual','demand_forecast','holidays','calendar','generation','renewables',
           'reserve','domestic_lng','oil','international_fuel','weather_actual','midrange_forecast']
HISTORY = ['smp','demand_actual','generation_lng','generation_coal','generation_nuclear',
           'solar_actual','wind_actual','reserve_mw','reserve_pct','temperature_c','irradiance_mj_m2','wind_ms']
FUTURE = ['demand_forecast','hour_sin','hour_cos','weekday','month','season','is_weekend','is_holiday',
          'domestic_lng_cost_krw_kwh','wti_usd_bbl','brent_usd_bbl','international_lng_usd_mmbtu',
          'international_coal_usd_tonne','weather_code','precip_probability_pct','temperature_min_c','temperature_max_c']
DECISIONS = ['demand_actual_definition','midrange_72h_mapping','demand_forecast_72h_mapping','baseline_origin_day']
SPLITS = ['train','validation','test']


def timestamps(values):
    if not values.astype(str).str.contains(r'(?:Z|[+-]\d{2}:?\d{2})$',regex=True).all():
        raise ValueError('All timestamps need an explicit timezone offset')
    return pd.to_datetime(values,utc=True).dt.tz_convert('Asia/Seoul')


def split_origins(cfg, split):
    start=pd.Timestamp(cfg[split+'_start'],tz='Asia/Seoul')
    end=pd.Timestamp(cfg[split+'_end'],tz='Asia/Seoul')+pd.Timedelta(hours=23)
    return pd.date_range(start-pd.Timedelta(hours=1),end-pd.Timedelta(hours=72),freq='D')


def window(hourly, origin, lookback):
    # Hour labels represent interval START. At 23:00 the 23:00–24:00 observation is unfinished.
    index=pd.date_range(origin-pd.Timedelta(hours=lookback),periods=lookback,freq='h')
    frame=hourly.reindex(index)
    if frame[HISTORY].isna().any().any(): raise ValueError('Incomplete historical sequence')
    if not (frame.available_at<=origin).all(): raise ValueError('Historical actual unavailable at origin')
    return frame[HISTORY].to_numpy(dtype='float32')


def arrays(hourly, future, selected_origins, lookback):
    history=[];context=[];labels=[]
    grouped={origin:rows.sort_values('target_timestamp') for origin,rows in future.groupby('forecast_origin')}
    for origin in selected_origins:
        rows=grouped.get(origin)
        expected=pd.date_range(origin+pd.Timedelta(hours=1),periods=72,freq='h')
        if rows is None or not pd.DatetimeIndex(rows.target_timestamp).equals(expected):
            raise ValueError('Expected one complete 72h block at '+str(origin))
        if not (rows.latest_nonfuel_source_timestamp<=origin).all(): raise ValueError('Future source exceeds origin')
        history.append(window(hourly,origin,lookback));context.append(rows[FUTURE].to_numpy(dtype='float32'))
        labels.append(hourly.smp.reindex(expected).to_numpy(dtype='float32'))
    result=tuple(np.asarray(x,dtype='float32') for x in (history,context,labels))
    if any(not np.isfinite(x).all() for x in result): raise ValueError('NaN/inf in required model arrays')
    return result


def inspect(shared,cfg):
    shared=Path(shared);issues=[]
    required=['manifest.json','hourly.csv','forecast_inputs.csv','evaluation_origins.csv','evaluation_targets.csv','feature_manifest.csv']
    def issue(variable,reason): issues.append(dict(variable=variable,reason=reason,action='공통 데이터 정의·근거·정규화 보완 후 재검사'))
    for file in required:
        if not (shared/file).is_file(): issue(file,'공통 버전 파일 없음')
    if issues: return issues,None
    try:
        manifest=json.loads((shared/'manifest.json').read_text())
        if manifest.get('schema_version')!='smp-common-v2': issue('schema_version','최종 12개 입력 그룹 계약과 불일치')
        if not manifest.get('dataset_version'): issue('dataset_version','버전 없음')
        if manifest.get('history_features')!=HISTORY or manifest.get('future_features')!=FUTURE:
            issue('features','공통 열 목록·순서 불일치; 모델 단독 변경 금지')
        if manifest.get('fuel_policy')!=cfg['fuel_policy']: issue('fuel_policy','연료 정책 불일치')
        for decision in DECISIONS:
            record=manifest.get('decisions',{}).get(decision,{})
            if record.get('status')!='resolved' or not record.get('rule') or not record.get('evidence'):
                issue(decision,'팀 공통 규칙 또는 확정 근거 없음')
        for source in SOURCES:
            record=manifest.get('sources',{}).get(source,{})
            if record.get('status')!='complete': issue(source,'유지한 필수 출처 미완료')
            for field in ['evidence_file','unit','scope','mapping','availability_rule']:
                if not record.get(field): issue(source,'출처 명세 누락: '+field)
            evidence=shared/record.get('evidence_file','__missing__')
            if not evidence.is_file(): issue(source,'실제 근거 파일 없음')
        for file in required[1:]:
            actual=hashlib.sha256((shared/file).read_bytes()).hexdigest()
            if manifest.get('file_hashes',{}).get(file)!=actual: issue(file,'공통 파일 SHA-256 불일치')
        if issues:return issues,None
        hourly=pd.read_csv(shared/'hourly.csv');future=pd.read_csv(shared/'forecast_inputs.csv')
        for col in ['timestamp','available_at']:hourly[col]=timestamps(hourly[col])
        for col in ['forecast_origin','target_timestamp','latest_nonfuel_source_timestamp']:
            future[col]=timestamps(future[col])
        hourly=hourly.sort_values('timestamp').set_index('timestamp')
        expected=pd.date_range(pd.Timestamp(cfg['train_start'],tz='Asia/Seoul')-pd.Timedelta(hours=max(cfg['lookbacks'])+24*7),
                               pd.Timestamp(cfg['test_end']+' 23:00',tz='Asia/Seoul'),freq='h')
        if hourly.index.has_duplicates or not expected.isin(hourly.index).all():raise ValueError('Missing historical hour or initial lookback/baseline history')
        if not np.isfinite(hourly[HISTORY].to_numpy(dtype=float)).all():raise ValueError('Required historical inputs have NaN/inf')
        if not (hourly.available_at>=hourly.index+pd.Timedelta(hours=1)).all():raise ValueError('Actual availability precedes interval completion')
        if future.duplicated(['forecast_origin','target_timestamp']).any():raise ValueError('Duplicate forecast rows')
        if not np.isfinite(future[FUTURE].to_numpy(dtype=float)).all():raise ValueError('Required future inputs have NaN/inf')
        if not (future.latest_nonfuel_source_timestamp<=future.forecast_origin).all():raise ValueError('Future source timestamp exceeds origin')
        origins=pd.read_csv(shared/'evaluation_origins.csv');origins['forecast_origin']=timestamps(origins.forecast_origin)
        targets=pd.read_csv(shared/'evaluation_targets.csv')
        for col in ['forecast_origin','target_timestamp']:targets[col]=timestamps(targets[col])
        if targets.duplicated(['split','forecast_origin','target_timestamp']).any():raise ValueError('Duplicate evaluation targets')
        for split in SPLITS:
            chosen=split_origins(cfg,split)
            listed=pd.DatetimeIndex(origins.loc[origins.split==split,'forecast_origin'].sort_values())
            if not chosen.equals(listed):raise ValueError('Common origin list differs: '+split)
            # Validate all input blocks, not just a sample. Labels remain evaluation-only.
            arrays(hourly,future,chosen,max(cfg['lookbacks']))
            expected_keys={(origin,target) for origin in chosen for target in pd.date_range(origin+pd.Timedelta(hours=1),periods=72,freq='h')}
            actual_keys=set(zip(targets.loc[targets.split==split,'forecast_origin'],targets.loc[targets.split==split,'target_timestamp']))
            if expected_keys!=actual_keys:raise ValueError('Common evaluation rows differ: '+split)
        # Verify that the actual common tables follow the declared fuel policy.
        monthly=pd.read_csv(shared/manifest['sources']['domestic_lng']['evidence_file'])
        if not {'month','value'}.issubset(monthly):raise ValueError('LNG evidence needs month,value columns, 원/kWh')
        mapping=monthly.set_index('month').value
        expected_lng=future.target_timestamp.dt.strftime('%Y-%m').map(mapping)
        if not np.allclose(expected_lng,future.domestic_lng_cost_krw_kwh):raise ValueError('Domestic LNG target-month mismatch')
        international=FUTURE[9:13]
        if (future.groupby('forecast_origin')[international].nunique()>1).any().any():raise ValueError('International fuel must remain fixed for 72h')
        for col in ['international_asof_date','latest_international_observation_date']:
            if col not in future:raise ValueError('Missing FRED provenance: '+col)
        asof=pd.to_datetime(future.international_asof_date).dt.date
        rule=(future.forecast_origin-pd.Timedelta(days=2)).dt.date
        observation=pd.to_datetime(future.latest_international_observation_date).dt.date
        if not (asof==rule).all() or not (observation<=asof).all():raise ValueError('FRED D−2 mapping mismatch')
        return [],(hourly,future,manifest)
    except (ValueError,KeyError,TypeError,OSError) as exc:
        issue('common_bundle',str(exc));return issues,None
