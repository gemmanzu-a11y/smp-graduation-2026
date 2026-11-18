"""Download official public CSV files (no API key/calls) and export the requested 2023–2025 source files."""
from pathlib import Path
from io import BytesIO
import hashlib
import json
import sys
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT/'1120gradpj'
sys.path.insert(0,str(PROJECT/'src'))
from smp_forecast.http import Client,write_json,now
FILES=[
 'uddi:76850689-e74c-402e-bfec-9142976b96c8',
 'uddi:57e66d86-ea1d-4efb-9eb3-a6d575336841',
 'uddi:0da6dc76-cff3-4759-b86f-b0ff631e5b32',
 'uddi:4dec37b2-15e1-480b-94e3-87bdc2ecff1b',
 'uddi:68afdd00-4055-4049-b0da-89ba5157a43c',
 'uddi:b98e93d3-ce0d-47df-a23b-a46844552ac4',
 'uddi:166a7ee3-161a-4dc2-9f59-cedb6b1c7213',
]


def main():
    folder=ROOT/'shared_datasets/kpx_renewables';folder.mkdir(parents=True,exist_ok=True)
    client=Client();records=[]
    for number,uid in enumerate(FILES):
        # These are the ordinary public portal file-download form and attachment URL, not apis.data.go.kr.
        payload,_=client.fetch('renewables_public_download','https://www.data.go.kr/tcs/dss/selectFileDataDownload.do',
            dict(publicDataDetailPk=uid,publicDataPk='15065269',atchFileId='',fileDetailSn='1',publicDataTyCode='PR0051'),post=True,refresh=True)
        metadata=json.loads(payload)
        if not metadata.get('status'):raise ValueError('Public CSV download unavailable: source '+str(number))
        payload,receipt=client.fetch('renewables_public_download','https://www.data.go.kr/cmm/cmm/fileDownload.do',
            dict(atchFileId=metadata['atchFileId'],fileDetailSn=metadata['fileDetailSn'],insertDataPrcus='N'),refresh=True)
        for encoding in ['utf-8-sig','cp949']:
            try:source=pd.read_csv(BytesIO(payload),encoding=encoding,dtype=str,keep_default_na=False);break
            except UnicodeDecodeError:continue
        else:raise ValueError('Unknown source encoding')
        datecol=next(col for col in source if '거래일' in col)
        dates=pd.to_datetime(source[datecol],errors='raise')
        selected=source[dates.dt.year.between(2023,2025)].copy()
        if selected.empty:raise ValueError('No requested rows: '+str(number))
        # Keep all original columns/field strings. Only source_6 loses out-of-scope 2017–2022 rows.
        path=folder/f'renewable_source_{number}.csv'
        selected.to_csv(path,index=False,encoding='utf-8-sig')
        check=pd.read_csv(path,encoding='utf-8-sig',dtype=str,keep_default_na=False)
        pd.testing.assert_frame_equal(selected.reset_index(drop=True),check)
        record=dict(file=path.name,source_dataset='15065269',source_file_id=uid,
            original_title=metadata.get('dataSetFileDetailInfo',{}).get('dataNm'),
            original_filename=metadata.get('dataSetFileDetailInfo',{}).get('orginlFileNm'),
            source_encoding=encoding,export_encoding='UTF-8 BOM',original_rows=len(source),export_rows=len(selected),
            start=dates[selected.index].min().strftime('%Y-%m-%d'),end=dates[selected.index].max().strftime('%Y-%m-%d'),
            scope_filter='2023–2025 only; source_6 excludes original 2017–2022 rows',columns=list(selected.columns),
            raw_sha256=receipt['sha256'],export_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size,
            retrieved_at=receipt['first_received_at'])
        records.append(record)
        write_json(folder/'manifest.json',dict(at=now(),source_page='https://www.data.go.kr/data/15065269/fileData.do',
            api_calls=0,authentication_used=False,unit='MWh',files=records,all_seven_files_complete=len(records)==7,
            values_imputed=False,files_combined=False))
        print(json.dumps({key:record[key] for key in ['file','export_rows','start','end','bytes']},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
