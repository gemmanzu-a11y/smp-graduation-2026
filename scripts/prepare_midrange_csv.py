#!/usr/bin/env python3
"""Normalize the user-downloaded KMA medium-range weather CSV, preserving forecast vintages."""
import argparse
import hashlib
import json
from pathlib import Path
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, default=Path('shared_datasets/kma_midrange'))
    args = parser.parse_args()
    source = pd.read_csv(args.source, encoding='cp949')
    assert list(source.columns) == ['발표시각', '지역', '예보시각', '예보', '강수확률(%)']
    issued = pd.to_datetime(source['발표시각'], format='%Y-%m-%d %H시').dt.tz_localize('Asia/Seoul')
    target = pd.to_datetime(source['예보시각'].str[:10], format='%Y-%m-%d')
    period = source['예보시각'].str[11:]
    assert period.isin(['오전', '오후', '']).all(), sorted(period.unique())
    result = pd.DataFrame({
        'issued_at_kst': issued.map(lambda t: t.isoformat()),
        'region': source['지역'],
        'target_date': target.dt.strftime('%Y-%m-%d'),
        'target_period': period.map({'오전': 'AM', '오후': 'PM', '': 'DAY'}),
        'weather_text': source['예보'],
        'precip_probability_pct': source['강수확률(%)'],
        'lead_days': (target - issued.dt.tz_localize(None).dt.normalize()).dt.days,
    }).sort_values(['issued_at_kst', 'region', 'target_date', 'target_period']).reset_index(drop=True)
    assert result.notna().all().all()
    assert result['precip_probability_pct'].between(0, 100).all()
    args.output.mkdir(parents=True, exist_ok=True)
    entries = []
    for month, rows in result.groupby(result['issued_at_kst'].str[:7], sort=True):
        path = args.output / f'forecast_{month}.csv'
        rows.to_csv(path, index=False, encoding='utf-8-sig')
        check = pd.read_csv(path, encoding='utf-8-sig')
        assert len(check) == len(rows)
        assert path.stat().st_size < 5 * 1024 * 1024
        entries.append(dict(file=path.name, rows=len(rows), bytes=path.stat().st_size,
                            sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    key = ['issued_at_kst', 'region', 'target_date', 'target_period']
    manifest = dict(source_filename=args.source.name, source_encoding='CP949',
        source_sha256=hashlib.sha256(args.source.read_bytes()).hexdigest(),
        source_page='https://data.kma.go.kr/data/weatherReport/mrfList.do?pgmNo=646',
        timezone='Asia/Seoul', rows=len(result),
        issued_min=result.issued_at_kst.min(), issued_max=result.issued_at_kst.max(),
        target_min=result.target_date.min(), target_max=result.target_date.max(),
        regions=sorted(result.region.unique()), lead_days=sorted(map(int,result.lead_days.unique())),
        duplicate_key_rows=int(result.duplicated(key,keep=False).sum()),
        missing_cells=int(result.isna().sum().sum()), files=entries,
        contains_temperature=False, contains_hourly_forecast=False,
        imputation_performed=False, historical_completeness_guaranteed=False)
    (args.output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in manifest.items() if k!='files'}, ensure_ascii=False, indent=2))
    print('Files:',len(entries),'Bytes:',sum(x['bytes'] for x in entries))

if __name__ == '__main__':
    main()
