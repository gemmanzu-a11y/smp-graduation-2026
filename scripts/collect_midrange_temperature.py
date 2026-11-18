#!/usr/bin/env python3
"""Download official KMA medium-range temperature CSVs; preserve Seoul forecast vintages."""
import hashlib
import io
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import certifi
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / '1120gradpj/data/raw/kma_midrange_temperature'
OUT = ROOT / 'shared_datasets/kma_midrange_temperature_seoul'
REQUEST_LOCK = threading.Lock()
USED_FILES = set()


def read_valid(payload, month):
    df = pd.read_csv(io.BytesIO(payload), encoding='cp949')
    assert {'최저기온', '최고기온', '도시'}.issubset(df.columns)
    assert set(df['발표시각'].str[:7]) == {str(month)}, 'Returned month differs from request'
    return df


def collect(month):
    raw = RAW / f'temperature_{month}.csv'
    params = dict(pgmNo='646', elementCds='WT', stnIds='_108',
                  startDt=month.start_time.strftime('%Y%m%d'),
                  endDt=min(month.end_time.strftime('%Y%m%d'), '20261117'),
                  lrgClssCd='WTF', mddlClssCd='WTF04', serviceSe='F00102',
                  dataFormCd='F00502', menuNo='635', fileType='csv')
    df = None
    if raw.exists():
        try:
            df = read_valid(raw.read_bytes(), month)
        except (AssertionError, ValueError, pd.errors.ParserError, UnicodeError):
            pass  # Re-download invalid cached responses, never skip malformed rows.
    for attempt in range(3):
        if df is not None:
            break
        try:
            with requests.Session() as session:
                # Server uses second-resolution temporary filenames. Stagger requests.
                with REQUEST_LOCK:
                    time.sleep(1.1)
                response = session.post('https://data.kma.go.kr/data/weatherReport/downloadMrfDataCSV.do',
                                        data=params, timeout=60, verify=certifi.where())
                response.raise_for_status()
                file = response.text.strip()
                assert file.startswith('/n027/') and file.endswith('.csv'), 'Unexpected file response'
                with REQUEST_LOCK:
                    assert file not in USED_FILES, 'Server reused a temporary filename; retry'
                    USED_FILES.add(file)
                response = session.post('https://data.kma.go.kr/download/fileDownload.do',
                                        data={'file': file}, timeout=60, verify=certifi.where())
                response.raise_for_status()
                df = read_valid(response.content, month)
                raw.write_bytes(response.content)
        except (requests.RequestException, AssertionError, ValueError, pd.errors.ParserError, UnicodeError) as exc:
            if attempt == 2:
                raise RuntimeError(f'{month}: {type(exc).__name__}; download not accepted') from None
    seoul = df[df['도시'].eq('서울')].copy()
    assert len(seoul) > 0
    issued = pd.to_datetime(seoul['발표시각'], format='%Y-%m-%d %H시').dt.tz_localize('Asia/Seoul')
    seoul.insert(0, 'issued_at_kst', issued.map(lambda value: value.isoformat()))
    seoul.insert(1, 'target_date', pd.to_datetime(seoul['예보시각']).dt.strftime('%Y-%m-%d'))
    destination = OUT / f'temperature_{month}.csv'
    seoul.to_csv(destination, index=False, encoding='utf-8-sig')
    assert destination.stat().st_size < 5 * 1024 * 1024
    return dict(month=str(month), source_rows=len(df), seoul_rows=len(seoul),
                source_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(), params=params)


def validate():
    files = sorted(OUT.glob('temperature_*.csv'))
    assert len(files) == 47
    df = pd.concat([pd.read_csv(path) for path in files], ignore_index=True)
    issued = pd.to_datetime(df.issued_at_kst)
    target = pd.to_datetime(df.target_date)
    keys = ['issued_at_kst', '도시', 'target_date']
    expected = pd.date_range('2023-01-01 06:00', '2026-11-17 18:00', freq='12h', tz='Asia/Seoul')
    missing = expected.difference(pd.DatetimeIndex(issued.unique()))
    manifest = dict(source_page='https://data.kma.go.kr/data/weatherReport/mrfList.do?pgmNo=646',
                    city='서울', unit='℃', rows=len(df), issued_min=df.issued_at_kst.min(),
                    issued_max=df.issued_at_kst.max(), target_min=df.target_date.min(),
                    target_max=df.target_date.max(),
                    lead_days=sorted(map(int, (target-issued.dt.tz_localize(None).dt.normalize()).dt.days.unique())),
                    duplicate_key_rows=int(df.duplicated(keys, keep=False).sum()),
                    missing_cells_by_column={key: int(value) for key, value in df.isna().sum().items()},
                    missing_issuances_count=len(missing), missing_issuances=[value.isoformat() for value in missing],
                    target_count_by_issuance_histogram={str(k):int(v) for k,v in df.groupby('issued_at_kst').size().value_counts().items()},
                    files=[dict(file=path.name, rows=len(pd.read_csv(path)),
                                sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in files])
    assert df['도시'].eq('서울').all()
    assert (target == pd.to_datetime(df['예보시각'])).all()
    flags = df[df['최저기온'] > df['최고기온']]
    flags.to_csv(OUT / 'min_above_max_review.csv', index=False, encoding='utf-8-sig')
    manifest['min_above_max_review_rows'] = len(flags)
    df.to_csv(OUT / 'all_seoul.csv', index=False, encoding='utf-8-sig')
    manifest['combined_file'] = dict(file='all_seoul.csv', rows=len(df), sha256=hashlib.sha256((OUT/'all_seoul.csv').read_bytes()).hexdigest())
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({key:value for key,value in manifest.items() if key not in ('files','missing_issuances')}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    receipts = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(collect, month) for month in pd.period_range('2023-01', '2026-11', freq='M')]
        for future in as_completed(futures):
            receipt = future.result()
            receipts.append(receipt)
            (OUT / 'collection_receipts.json').write_text(json.dumps(sorted(receipts,key=lambda x:x['month']), ensure_ascii=False, indent=2)+'\n')
            print(receipt['month'], receipt['seoul_rows'], 'validated', flush=True)
    validate()
