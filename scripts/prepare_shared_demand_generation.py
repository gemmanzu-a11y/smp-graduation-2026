"""Export approved public datasets 2 and 5 without credentials or source-version splicing."""
from pathlib import Path
import hashlib
import json
import sys
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'1120gradpj'
sys.path.insert(0,str(PROJECT/'src'));sys.path.insert(0,str(PROJECT/'scripts'))
from smp_forecast.http import items_from
from collect_generation_history import validate


def write_manifest(folder,details):
    files=[]
    for path in sorted(folder.glob('*.csv')):
        assert path.stat().st_size<5*1024*1024
        files.append(dict(file=path.name,rows=len(pd.read_csv(path)),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    (folder/'manifest.json').write_text(json.dumps(dict(**details,files=files),ensure_ascii=False,indent=2)+'\n')
    print(folder.relative_to(ROOT),[(r['file'],r['rows']) for r in files])


def main():
    demand=ROOT/'shared_datasets/kpx_day_ahead_demand';demand.mkdir(parents=True,exist_ok=True)
    source=PROJECT/'data/processed/section_a/demand_forecast_mainland_2023_2025.csv'
    frame=pd.read_csv(source)
    columns=['timestamp','target_date','source_hour','demand_forecast_mw','geography']
    assert len(frame)==26304 and frame.demand_forecast_mw.notna().all() and not frame.timestamp.duplicated().any()
    frame[columns].to_csv(demand/'mainland_demand_forecast_2023_2025.csv',index=False,encoding='utf-8-sig')
    provenance=[]
    for year,rows in frame.groupby(frame.timestamp.str[:4]):
        entry=dict(year=year,rows=len(rows))
        for col in frame.columns.difference(columns):
            values=rows[col].drop_duplicates()
            assert len(values)==1,(year,col)
            entry[col]=None if pd.isna(values.iloc[0]) else str(values.iloc[0])
        provenance.append(entry)
    write_manifest(demand,dict(input_number=2,unit='MW',scope='mainland',complete_2023_2025=True,
        source_page='https://new.kpx.or.kr/pssInland.es?mid=a10606090100&device=pc',
        original_file_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),source_metadata_by_year=provenance,
        field_mapping={'demand_forecast_mw':'mlfd: verified against 2352 overlapping API hours'},
        historical_first_publication_verified=False,d2_d3_rule_resolved=False))
    generation=ROOT/'shared_datasets/kpx_generation';generation.mkdir(parents=True,exist_ok=True)
    annual=pd.read_csv(PROJECT/'data/processed/section_b/generation_annual/generation_selected_2023_2025.csv')
    for year in ['2023','2025']:
        rows=annual[annual.timestamp.str.startswith(year)]
        assert len(rows)==8760 and not rows.isna().any().any()
        rows.to_csv(generation/f'annual_generation_{year}.csv',index=False,encoding='utf-8-sig')
    api=[];seen=set()
    for marker in list((PROJECT/'data/raw/section_b_generation').glob('*.json'))+list((PROJECT/'data/raw/generation_2024_new_approval_probe').glob('*.json')):
        record=json.loads(marker.read_text());date=str(record.get('params',{}).get('tradeYmd',''))
        if not '20230101'<=date<='20251231' or record.get('params',{}).get('pageNo')!=1:continue
        try:
            rows,total=items_from((marker.parent/record['raw']).read_bytes())
            if len(rows)!=total:continue
            parsed=validate(rows,date)
            if len(parsed)!=192 or date in seen:continue
            seen.add(date);api.append(parsed)
        except (RuntimeError,ValueError,KeyError):continue
    api=pd.concat(api,ignore_index=True).sort_values(['timestamp','fuelTpCd'])
    api.to_csv(generation/'api_generation_partial_2023_2025.csv',index=False,encoding='utf-8-sig')
    subset=api[api.tradeYmd.astype(str).str.startswith('2024')]
    subset.to_csv(generation/'api_generation_2024_partial.csv',index=False,encoding='utf-8-sig')
    available=set(subset.tradeYmd.astype(str))
    missing=[date for date in pd.date_range('2024-01-01','2024-12-31').strftime('%Y%m%d') if date not in available]
    pd.DataFrame({'tradeYmd':missing}).to_csv(generation/'pending_dates_2024.csv',index=False,encoding='utf-8-sig')
    report=json.loads((PROJECT/'reports/generation_annual_collection.json').read_text())
    write_manifest(generation,dict(input_number=5,complete_2023_2025=False,
        annual_unit='MWh',api_unit='not independently confirmed; original amgo preserved',
        annual_source_page='https://www.data.go.kr/data/15127395/fileData.do',
        api_source_page='https://www.data.go.kr/data/15106744/openapi.do',
        api_days=len(seen),api_2024_days=len(available),pending_2024_days=len(missing),
        api_and_annual_versions_spliced=False,api_comparison=report['api_comparison'],
        annual_source_receipts=report['receipts'],
        scope='market settlement generation; mainland/Jeju separation not verified',
        blocker_2024=report['blocker'],model_ready=False))

if __name__=='__main__':main()
