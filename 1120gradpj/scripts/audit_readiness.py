"""Distinguish collected research data from the user's full, publication-certified input contract."""
import sys,json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from smp_forecast.http import write_json,now
fuel=pd.read_csv(ROOT/'data/processed/fuel_monthly.csv');cal=pd.read_csv(ROOT/'data/processed/holidays.csv');quality=json.loads((ROOT/'reports/data_quality.json').read_text());latest=pd.read_csv(ROOT/'data/processed/latest_metadata.csv');origin=pd.to_datetime(latest.origin.iloc[0],utc=True);renew=pd.read_csv(ROOT/'data/processed/renewable_hourly.csv');last_renew=pd.to_datetime(renew.timestamp,utc=True).max()
issues=[]
if fuel.publicly_released_at.isna().any():issues.append({'field':'lng_public_release','detail':f'{int(fuel.publicly_released_at.isna().sum())} monthly release timestamps unknown; LNG excluded from historical training'})
if not cal.official_api_verified.all():issues.append({'field':'holidays_api','detail':'KASI returned 403; named python-holidays fallback used'})
if last_renew<origin-pd.Timedelta(hours=48):issues.append({'field':'latest_solar_wind','detail':'archive ends '+str(last_renew)+'; latest forecast history is missing renewables'})
issues.append({'field':'historical_vintages','detail':'Original historical public release/revision times of retrospective observation files unverified; 24h/48h delays are assumptions'})
issues.append({'field':'load_geography','detail':'EPSIS load/reserve scope is not independently certified as mainland-only'})
record={'at':now(),'all_seven_models_executed':all((ROOT/'models'/m/'artifacts/run.json').exists() for m in ['lstm','hgb','lightgbm','extra_trees','linear_regression','random_forest','xgboost']),'full_requested_data_contract_ready':not issues,'research_execution_ready':True,'issues':issues};write_json(ROOT/'reports/readiness.json',record);print(json.dumps(record,ensure_ascii=False,indent=2))
if '--strict' in sys.argv and issues:raise SystemExit(2)
