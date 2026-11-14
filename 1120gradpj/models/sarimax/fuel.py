"""Read only the verified EPSIS workbook's fuel-cost / LNG / KRW-kWh column."""
from pathlib import Path
import hashlib
import pandas as pd
from openpyxl import load_workbook


def read_lng(path):
    path = Path(path)
    wb = load_workbook(path, read_only=True, data_only=True)
    matches = []
    for sheet in wb:
        rows = list(sheet.values)
        if len(rows) < 4:
            continue
        # Source uses three header rows with merged parent groups.
        group = None
        for col, parent in enumerate(rows[0]):
            if parent is not None:
                group = str(parent).strip()
            fuel = str(rows[1][col]).strip() if col < len(rows[1]) else ''
            unit = str(rows[2][col]).strip() if col < len(rows[2]) else ''
            if group == '연료비단가' and fuel == 'LNG' and unit.lower() == '원/kwh':
                values = []
                for row in rows[3:]:
                    if row[0] is None: continue
                    month = pd.to_datetime(str(row[0]), format='%Y/%m').strftime('%Y-%m')
                    values.append((month, float(row[col])))
                matches.append((sheet.title, col + 1, values))
    wb.close()
    if len(matches) != 1:
        raise ValueError('Expected one LNG fuel-cost column with unit 원/kWh')
    sheet, col, values = matches[0]
    frame = pd.DataFrame(values, columns=['month', 'domestic_lng_cost_krw_kwh']).sort_values('month')
    if frame.month.duplicated().any() or frame.domestic_lng_cost_krw_kwh.isna().any():
        raise ValueError('Duplicate/missing monthly LNG values')
    return frame, dict(file=path.name, sheet=sheet, column_number=col,
        header_rows=[1, 2, 3], indicator='연료비단가', fuel='LNG', unit='원/kWh',
        sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def fuel_for_targets(monthly, targets, origin, mode='historical'):
    targets = pd.DatetimeIndex(targets).tz_convert('Asia/Seoul')
    origin = pd.Timestamp(origin).tz_convert('Asia/Seoul')
    if mode == 'historical':
        months = targets.strftime('%Y-%m')
    elif mode == 'november_demo' and origin.strftime('%Y-%m') == '2026-11':
        months = ['2026-10'] * len(targets)
    else:
        raise ValueError('Unknown mode or demo origin outside November 2026')
    values = monthly.set_index('month').domestic_lng_cost_krw_kwh.reindex(months)
    if values.isna().any():
        raise ValueError('Required LNG month missing; no fallback permitted')
    return values.to_numpy(dtype=float)
