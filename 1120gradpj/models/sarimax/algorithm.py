"""Fixed-parameter SARIMAX with train-only scaling and causal state updates."""
from pathlib import Path
import json
import warnings
import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX, SARIMAXResults


def hourly(frame):
    if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is None:
        raise ValueError('Timezone-aware hourly index required')
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError('Duplicate or unsorted timestamps')
    if len(frame) > 1 and not (frame.index.to_series().diff().iloc[1:] == pd.Timedelta(hours=1)).all():
        raise ValueError('Missing hourly timestamps')
    if not np.isfinite(frame.to_numpy(dtype=float)).all():
        raise ValueError('Missing/nonfinite required input; no automatic column deletion')
    return frame.asfreq('h')


class Estimator:
    def __init__(self, order=(1, 0, 1), seasonal_order=(1, 0, 0, 24), maxiter=100):
        self.order = tuple(order)
        self.seasonal_order = tuple(seasonal_order)
        self.maxiter = maxiter

    def _x(self, x):
        x = hourly(x)
        if list(x.columns) != self.columns:
            raise ValueError('Feature names/order changed')
        return (x - self.mean) / self.scale

    def fit(self, y, x):
        y, x = hourly(y), hourly(x)
        if not y.index.equals(x.index):
            raise ValueError('Training y/exog timestamps differ')
        self.columns = list(x.columns)
        self.y_mean = float(y.mean())
        self.y_scale = float(y.std(ddof=0)) or 1.0
        self.mean, self.scale = x.mean(), x.std(ddof=0).replace(0, 1)
        # Keep all agreed inputs. Constant columns are not silently removed.
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            self.result = SARIMAX((y.astype(float)-self.y_mean)/self.y_scale, exog=self._x(x), order=self.order,
                seasonal_order=self.seasonal_order, trend='n',
                enforce_stationarity=True, enforce_invertibility=True).fit(
                    disp=False, maxiter=self.maxiter)
        self.fit_warnings = [str(w.message) for w in caught]
        if not self.result.mle_retvals.get('converged', False):
            raise RuntimeError('SARIMAX did not converge; candidate rejected')
        if not np.isfinite(self.result.params).all():
            raise RuntimeError('Nonfinite estimated parameters')
        self.last_timestamp = y.index[-1]
        return self

    def update(self, y, x, origin):
        """Filter newly observed history only; extend never re-estimates coefficients."""
        origin = pd.Timestamp(origin)
        if origin.tzinfo is None:
            raise ValueError('Origin must have timezone')
        y, x = hourly(y), hourly(x)
        if not y.index.equals(x.index) or not len(y):
            raise ValueError('Update y/exog mismatch or empty block')
        if y.index[0] != self.last_timestamp + pd.Timedelta(hours=1):
            raise ValueError('Update must immediately follow previous state')
        if y.index[-1] > origin:
            raise ValueError('Future actuals cannot enter state')
        self.result = self.result.extend((y.astype(float)-self.y_mean)/self.y_scale, exog=self._x(x))
        self.last_timestamp = y.index[-1]

    def predict72(self, future_x, origin):
        origin = pd.Timestamp(origin)
        if origin.tzinfo is None:
            raise ValueError('Origin must have timezone')
        origin = origin.tz_convert('Asia/Seoul')
        if origin.hour != 23 or origin.minute or origin.second:
            raise ValueError('Daily issue must be exactly 23:00 KST')
        if self.last_timestamp != origin:
            raise ValueError('State must end at issue origin, not at a future actual')
        future_x = hourly(future_x)
        expected = pd.date_range(origin + pd.Timedelta(hours=1), periods=72, freq='h')
        if len(future_x) != 72 or not future_x.index.equals(expected):
            raise ValueError('Exactly the next 72 hourly exog rows are required')
        forecast = self.result.get_forecast(steps=72, exog=self._x(future_x))
        ci = np.asarray(forecast.conf_int(alpha=.05))
        output = pd.DataFrame({'predicted_smp': np.asarray(forecast.predicted_mean)*self.y_scale+self.y_mean,
            'lower_95': ci[:, 0]*self.y_scale+self.y_mean, 'upper_95': ci[:, 1]*self.y_scale+self.y_mean}, index=expected)
        if not np.isfinite(output.to_numpy()).all():
            raise RuntimeError('Nonfinite SARIMAX forecast')
        return output

    def save(self, folder):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        self.result.save(folder / 'state.pkl')
        metadata = dict(order=self.order, seasonal_order=self.seasonal_order,
            maxiter=self.maxiter, y_mean=self.y_mean, y_scale=self.y_scale, columns=self.columns, mean=self.mean.to_dict(),
            scale=self.scale.to_dict(), last_timestamp=str(self.last_timestamp),
            fit_warnings=self.fit_warnings)
        (folder / 'preprocessing.json').write_text(json.dumps(metadata, indent=2, allow_nan=False))

    @classmethod
    def load(cls, folder):
        folder = Path(folder)
        meta = json.loads((folder / 'preprocessing.json').read_text())
        obj = cls(meta['order'], meta['seasonal_order'], meta['maxiter'])
        obj.columns = meta['columns']
        obj.y_mean, obj.y_scale = meta['y_mean'], meta['y_scale']
        obj.mean, obj.scale = pd.Series(meta['mean']), pd.Series(meta['scale'])
        obj.last_timestamp = pd.Timestamp(meta['last_timestamp'])
        obj.fit_warnings = meta['fit_warnings']
        obj.result = SARIMAXResults.load(folder / 'state.pkl')
        return obj
