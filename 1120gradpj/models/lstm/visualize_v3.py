"""Additional selected-origin MAE and target-hour error views; no refitting."""
from pathlib import Path
import os
import pandas as pd
import numpy as np
HERE=Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR',str(HERE.parents[1]/'data/cache/matplotlib'))

def extras(frame,directory,origin):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import plotly.graph_objects as go
    selected=frame[frame.forecast_origin==pd.Timestamp(origin)].sort_values('horizon')
    assert len(selected)==72
    mae=float(selected.absolute_error.mean())
    title=f'72h LSTM forecast — MAE {mae:.2f} KRW/kWh (conditional target-month LNG)'
    fig,ax=plt.subplots(figsize=(13,4));ax.plot(selected.target_timestamp,selected.actual_smp,label='Actual');ax.plot(selected.target_timestamp,selected.predicted_smp,label='LSTM')
    for n in [24,48]:ax.axvline(selected.target_timestamp.iloc[n],color='gray',linestyle='--')
    ax.set_title(title);ax.set_ylabel('SMP (KRW/kWh)');ax.legend();fig.autofmt_xdate();fig.tight_layout();fig.savefig(directory/'selected_72h.png');plt.close(fig)
    chart=go.Figure([go.Scatter(x=selected.target_timestamp,y=selected.actual_smp,name='Actual'),go.Scatter(x=selected.target_timestamp,y=selected.predicted_smp,name='LSTM')]);chart.update_layout(title=title,yaxis_title='SMP (KRW/kWh)')
    for n in [24,48]:chart.add_vline(x=selected.target_timestamp.iloc[n].to_pydatetime(),line_dash='dash')
    chart.write_html(str(directory/'selected_72h.html'),include_plotlyjs=True)
    hourly=frame.assign(target_hour=frame.target_timestamp.dt.hour).groupby(['split','target_hour']).absolute_error.mean().unstack(0)
    hourly.to_csv(directory.parent/'target_hour_mae.csv')
    ax=hourly.plot(figsize=(10,4),ylabel='MAE (KRW/kWh)',title='Error by target hour');ax.figure.tight_layout();ax.figure.savefig(directory/'target_hour_mae.png');plt.close(ax.figure)
    # Explicit split marker makes validation/test distinction visible in the monthly plot.
    monthly=frame.assign(month=frame.target_timestamp.dt.strftime('%Y-%m')).groupby(['month','forecast_day']).absolute_error.mean().unstack()
    ax=monthly.plot.bar(figsize=(12,4),ylabel='MAE (KRW/kWh)',title='Validation Jan–Jun | Final Test Jul–Dec');ax.axvline(5.5,color='black',linestyle='--');ax.figure.tight_layout();ax.figure.savefig(directory/'monthly_mae.png');plt.close(ax.figure)

if __name__=='__main__':
    import json
    run=Path(json.loads((HERE/'reports/latest_run_v3.json').read_text())['path'])
    frame=pd.read_csv(run/'predictions.csv')
    for col in ['forecast_origin','target_timestamp']:frame[col]=pd.to_datetime(frame[col])
    extras(frame,run/'figures','2025-07-01T23:00:00+09:00')
