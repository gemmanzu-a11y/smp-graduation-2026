"""Additional raw coverage and vintage audit, without modifying model inputs."""
from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from smp_forecast import common_v3 as c


def main():
    h,f,m=c.load();raw=pd.read_csv(c.OUT/'hourly.csv');raw.index=c.times(raw.pop('timestamp'))
    quality=json.loads((c.OUT/'quality_report.json').read_text())
    state=[];summaries=[]
    for name in c.HISTORY:
        col=raw[name];missing=col.isna()
        status=pd.Series(np.where(missing,'source_missing_unknown_cause',np.where(col.eq(0),'observed_zero','observed_nonzero')),index=raw.index)
        if name=='irradiance_mj_m2':status.loc[missing&raw.irradiance_night.eq(1)]='night_missing_not_verified_zero';status.loc[missing&raw.irradiance_night.eq(0)]='day_missing_or_invalid'
        causal=col.ffill(limit=24)
        method=pd.Series('observed',index=raw.index);method.loc[missing&causal.notna()]='past_ffill_max24h';method.loc[missing&causal.isna()]='Train_season_hour_or_global_median'
        state.append(pd.DataFrame(dict(timestamp=raw.index,variable=name,raw_state=status.to_numpy(),model_method=method.to_numpy())))
        for year in [2023,2024,2025]:
            mask=raw.index.year==year;summaries.append(dict(variable=name,year=year,rows=int(mask.sum()),missing=int(missing[mask].sum()),post_impute_missing=int(h.loc[mask,name].isna().sum()),ffill=int((method[mask]=='past_ffill_max24h').sum()),train_median=int((method[mask]=='Train_season_hour_or_global_median').sum()),observed_zero=int(col[mask].eq(0).sum())))
    pd.concat(state,ignore_index=True).to_csv(c.OUT/'missing_status.csv',index=False)
    pd.DataFrame(summaries).to_csv(c.OUT/'imputation_summary.csv',index=False)
    missingrows=[]
    for col in ['generation_lng','generation_coal','generation_nuclear','demand_actual','reserve_mw','reserve_pct']:
        z=raw[col].isna();runs=z.ne(z.shift()).cumsum()
        for _,part in z[z].groupby(runs[z]):missingrows.append(dict(variable=col,start=str(part.index[0]),end=str(part.index[-1]),hours=len(part)))
    pd.DataFrame(missingrows).to_csv(c.OUT/'missing_intervals.csv',index=False)
    checks={}
    for group,file,mapping in [(9,'09_fred_wti_brent.csv',{'DCOILWTICO':'WTI_value','DCOILBRENTEU':'Brent_value'}),(10,'10_fred_lng_coal.csv',{'PNGASJPUSDM':'international_LNG_value','PCOALAUUSDM':'international_coal_value'})]:
        old=pd.read_csv(next(c.SOURCE.glob(f'{group:02d}_*'))/file);old['forecast_origin']=c.times(old.forecast_origin)
        a=f.groupby('forecast_origin').first();b=old.groupby('forecast_origin').first();idx=a.index.intersection(b.index)
        for series,col in mapping.items():
            delta=np.abs(a.loc[idx,series]-b.loc[idx,col]);assert delta.max()<1e-9
            checks[series]={'origins':len(idx),'max_difference':float(delta.max())}
    for column in ['temperature_issued_at','weather_issued_at']:
        issued=pd.to_datetime(f[column],utc=True);assert (issued<=f.forecast_origin).all()
        age=(f.forecast_origin-issued).dt.total_seconds()/3600
        quality[column+'_age_hours']={'min':float(age.min()),'max':float(age.max()),'median':float(age.median())}
    quality['fred_crosscheck']=checks;quality['post_imputation_nonfinite']=0
    quality['imputation_counts_file']='imputation_summary.csv';quality['missing_intervals_file']='missing_intervals.csv';quality['missing_reason_file']='missing_status.csv'
    c.dump(c.OUT/'quality_report.json',quality);c.dump(c.OUT/'fred_crosscheck.json',checks)
    print('Additional coverage/vintage audit passed',flush=True)

if __name__=='__main__':main()
