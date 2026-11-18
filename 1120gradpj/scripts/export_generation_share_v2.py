"""Versioned 2023–2025 group-05 share; annual whole years, raw API 2024 gaps."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT.parent
sys.path.insert(0,str(ROOT/'src'))
from smp_forecast import common_v3 as c
OUT=WORK/'shared_datasets/kpx_generation/20261119_v2'
MAP={'LNG':'lng_generation_mwh','유연탄':'bituminous_coal_generation_mwh','무연탄':'anthracite_coal_generation_mwh','원자력':'nuclear_generation_mwh'}

def read(path):
    for enc in ['utf-8-sig','cp949']:
        try:return pd.read_csv(path,encoding=enc)
        except UnicodeDecodeError:pass
    raise ValueError('Unknown encoding')

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    folder=c.SOURCE/'05_generation_by_fuel_amgo';api_path=folder/'api_generation_partial_2023_2025_merged_20261119.csv'
    api=read(api_path);api['timestamp']=pd.to_datetime(api.tradeYmd.astype(str),format='%Y%m%d').dt.tz_localize(c.TZ)+pd.to_timedelta(pd.to_numeric(api.tradeNo)-1,unit='h')
    assert not api.duplicated(['timestamp','fuelTpCd']).any()
    hashes={str(api_path.relative_to(WORK)):hashlib.sha256(api_path.read_bytes()).hexdigest()}
    summaries=[];frames=[];comparisons={}
    for year in [2023,2024,2025]:
        expected=pd.date_range(f'{year}-01-01',f'{year}-12-31 23:00',freq='h',tz=c.TZ)
        if year in [2023,2025]:
            path=next((folder/'user_provided_annual_csvs').glob(f'*{year}1231.csv'))
            d=read(path);d.columns=d.columns.str.strip()
            datecol=next(col for col in ['거래일자','거래일'] if col in d)
            hourcol=next(col for col in ['거래시간','시간'] if col in d)
            fuelcol=next(col for col in ['연료원별','연료원'] if col in d)
            assert pd.to_numeric(d[hourcol]).between(1,24).all()
            d['timestamp']=pd.to_datetime(d[datecol]).dt.tz_localize(c.TZ)+pd.to_timedelta(pd.to_numeric(d[hourcol])-1,unit='h')
            selected=d[d[fuelcol].isin(MAP)].copy()
            selected['value']=pd.to_numeric(selected['전력거래량(MWh)'],errors='raise')
            assert not selected.duplicated(['timestamp',fuelcol]).any()
            wide=selected.pivot(index='timestamp',columns=fuelcol,values='value').reindex(index=expected,columns=list(MAP))
            assert len(selected)==len(expected)*4 and wide.notna().all().all()
            assert np.isfinite(wide.to_numpy()).all() and wide.ge(0).all().all()
            a=api[api.timestamp.dt.year.eq(year)&api.fuelTpCd.isin(MAP)]
            pairs=selected.merge(a[['timestamp','fuelTpCd','amgo']],left_on=['timestamp',fuelcol],right_on=['timestamp','fuelTpCd'],validate='one_to_one')
            delta=(pairs.value-pairs.amgo).abs()
            comparisons[str(year)]={'pairs':len(pairs),'dates':int(a.timestamp.dt.date.nunique()),'max_absolute_difference_mwh':float(delta.max()),'mean_absolute_difference_mwh':float(delta.mean()),'differences_gt_1_mwh':int(delta.gt(1).sum()),'policy':'annual whole year retained; API is comparison only, not spliced'}
            if year==2025:assert delta.le(.0005001).all()
            hashes[str(path.relative_to(WORK))]=hashlib.sha256(path.read_bytes()).hexdigest()
            kind=f'annual_{year}'
        else:
            a=api[api.timestamp.dt.year.eq(year)]
            wide=a.pivot(index='timestamp',columns='fuelTpCd',values='amgo').reindex(index=expected,columns=list(MAP))
            kind='api_2024'
        wide=wide.rename(columns=MAP);wide.columns.name=None
        wide['coal_generation_mwh']=wide[['bituminous_coal_generation_mwh','anthracite_coal_generation_mwh']].sum(axis=1,min_count=2)
        numeric=list(wide.columns)
        summary={'year':year,'rows':len(wide),'source_kind':kind,'missing':{col:int(wide[col].isna().sum()) for col in numeric}}
        for col in numeric:wide[col+'_missing']=wide[col].isna().astype('int8')
        wide['source_kind']=kind;wide.index.name='timestamp'
        wide.to_csv(OUT/f'generation_{year}_hourly.csv',encoding='utf-8-sig',float_format='%.9f')
        summaries.append(summary);frames.append(wide)
    combined=pd.concat(frames)
    assert len(combined)==26304 and not combined.index.duplicated().any()
    assert (combined.index.to_series().diff().iloc[1:]==pd.Timedelta(hours=1)).all()
    combined.to_csv(OUT/'generation_2023_2025_hourly.csv',encoding='utf-8-sig',float_format='%.9f')
    missing=[]
    for col in MAP.values():
        s=combined[col].isna();groups=s.ne(s.shift()).cumsum()
        for _,part in s[s].groupby(groups[s]):missing.append(dict(variable=col,start=str(part.index[0]),end=str(part.index[-1]),hours=len(part)))
    pd.DataFrame(missing).to_csv(OUT/'missing_intervals.csv',index=False,encoding='utf-8-sig')
    # Explicitly verify why the existing 2024 annual candidate cannot replace API.
    bad=next((folder/'user_provided_annual_csvs').glob('*20241231.csv'));b=read(bad);b.columns=b.columns.str.strip();fuelcol=next(col for col in ['연료원별','연료원','원료원'] if col in b)
    assert not b[fuelcol].isin(MAP).any()
    files={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in OUT.glob('*.csv')}
    assert all(row['bytes']<5*1024*1024 for row in files.values())
    manifest=dict(dataset_version='generation_20261119_v2',input_group=5,source_commit=c.SHA,sources_sha256=hashes,coverage=summaries,comparison=comparisons,files=files,unit='MWh',timezone=c.TZ,interval_label='start; source trading hour 1..24 => 00..23',geography='market-traded sent-out energy; no mainland/Jeju distinction available',coal_definition='bituminous + anthracite; both required',missing_policy='blank NaN, never filled or zeroed; *_missing=1 means missing',availability_policy='unshifted raw measurements; consumers must enforce interval end <= forecast_origin - 72h; historical releases/vintages not reconstructed',training_performed=False,previous_dataset_modified=False)
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    text=['# 5번 발전량 — 2023~2025 팀 공유 v2','','**팀원은 `generation_2023_2025_hourly.csv`를 받으세요.** 26,304개 시간 행이며 2023·2025년은 연간 공식 CSV, 2024년은 API 원본입니다. 원본 결측을 남긴 자료이며 학습용 대체값이나 72시간 지연을 아직 적용하지 않았습니다.','','|연도|시간 행|LNG 결측|유연탄 결측|무연탄 결측|원자력 결측|출처|','|---|---:|---:|---:|---:|---:|---|']
    for s in summaries:
        m=s['missing'];text.append(f'|{s["year"]}|{s["rows"]:,}|{m[MAP["LNG"]]}|{m[MAP["유연탄"]]}|{m[MAP["무연탄"]]}|{m[MAP["원자력"]]}|{s["source_kind"]}|')
    text+=['','## 파일·열','','- 통합: generation_2023_2025_hourly.csv. 연도별: generation_2023_hourly.csv / generation_2024_hourly.csv / generation_2025_hourly.csv. 두 종류를 중복 합산하지 마세요.','- timestamp: Asia/Seoul 시간 구간 시작. 00:00은00~01시 구간.','- lng_generation_mwh / bituminous_coal_generation_mwh / anthracite_coal_generation_mwh / nuclear_generation_mwh: LNG·유연탄·무연탄·원자력 MWh.','- coal_generation_mwh: 유연탄+무연탄. 한 성분이라도 빠지면 합계도 결측.','- 각 *_missing: 1은 결측, 0은 값 존재. 실제 발전량0과 구분합니다.','- source_kind: annual_2023 / api_2024 / annual_2025. 개별 출처 파일·SHA256은 manifest.json.','- missing_intervals.csv: 남은 핵심 발전원 누락 구간.','','## 채택 근거·주의','','2025년 필수4종 모두8,760시간입니다. API와 겹치는1월1일96개 값은 최대0.0005MWh 차이로 반올림 범위에서 일치합니다. 2023년도 필수4종 모두8,760시간이지만 API대조에서는 반올림 이상 차이가 있으므로 연간 파일을 한 해 단일 출처로 사용했습니다. 서로 동일한 정산 발표본이라고 주장하지 않습니다. 차이 통계는 manifest.json에 있습니다.','','2024년 연간 후보에는 신재생 연료원만 있어 LNG·석탄·원자력 보충에 사용할 수 없습니다. API의2024-02-29 전체24시간과8월 원자력·무연탄744시간 누락을 그대로 유지했습니다. 석탄 합계는 총768시간 결측입니다. **2023~2025년 완전 무결측 자료가 아닙니다.**','','정의: 전력시장 참여 발전기의 송전단 전력거래량입니다. 설비용량 MW·입찰량·전국 총발전량과 다릅니다. 지역 필드가 없어 육지 단독이라고 표시하지 않습니다. [연간 공식 자료](https://www.data.go.kr/data/15127395/fileData.do) / [API](https://www.data.go.kr/data/15106744/openapi.do).','','## 학습 연결','','이 CSV는 동일 시각 원자료입니다. 모든72시간 목표에 공통 마감 `forecast_origin−72h`를 적용하고, 해당 마감에 종료한 구간까지만 사용해야 합니다. target_timestamp별72시간 차감 방식은 금지합니다. 결측 대체는Train으로만 적합하고 결측 표시를 보존하세요. 연간 자료의 과거 공개시각·수정 이력을 복원하지 않았으므로72시간 지연은 여전히 연구 가정입니다.','','이 버전은 기존 공통 v3 및 LSTM/SARIMAX 학습 결과를 덮어쓰지 않습니다. 재학습 시 네 모델 모두 새 공통 버전과 같은 평가 행을 사용하세요. 현재는 원자료 재추출·검사·공유까지만 수행했습니다.','','재현: `1120gradpj/.venv/bin/python 1120gradpj/scripts/export_generation_share_v2.py`.']
    (OUT/'README.md').write_text('\n'.join(text)+'\n')
    print(json.dumps({'coverage':summaries,'comparison':comparisons,'file_sizes':{k:v['bytes'] for k,v in files.items()}},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
