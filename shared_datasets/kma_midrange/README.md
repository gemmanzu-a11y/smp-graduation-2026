# 기상청 과거 중기 날씨 예보 — 공통 데이터

사용자가 기상자료개방포털에서 내려받은 `FCT_MEDM_20261118001247.csv`를 정규화한 자료입니다. **기온 예보가 아닌 날씨 상태·강수확률 예보**입니다. 동서발전의 `icsrPred`, `temp`, `ws`와 다른 자료이며 해당 변수의 결측을 대신 채우지 않습니다.

- 출처: 기상청 기상자료개방포털 [중기예보](https://data.kma.go.kr/data/weatherReport/mrfList.do?pgmNo=646)
- 발표시각 범위: 2023-01-01 06:00 ~ 2026-11-17 18:00 (KST)
- 예보 대상일 범위: 2023-01-04 ~ 2026-11-27
- 전체 325,220행, 발표월 기준 47개 CSV. UTF-8 BOM, 원본 순서 대신 발표시각·지역·대상일·구간 순 정렬.
- 원본 행은 삭제하거나 합산하지 않았습니다. 보간·결측 대체·범주 인코딩도 하지 않았습니다.
- 복합키(발표시각, 지역, 대상일, 구간) 중복 0행, 현재 열의 빈값 0개입니다. 이는 모든 예상 발표일·지역의 이력이 완전하다는 뜻은 아닙니다.
- 원본 및 CSV별 SHA-256, 파일 크기·행 수는 `manifest.json`에 있습니다. API 인증키는 필요하지 않습니다.

## 열 정의

| 열 | 뜻 |
|---|---|
| `issued_at_kst` | 발표시각, ISO 8601 +09:00. 원본 `발표시각` |
| `region` | 원본 `지역`. 전라북도/전북자치도 표기도 원문 유지 |
| `target_date` | 원본 `예보시각`의 대상 날짜 |
| `target_period` | 오전=AM, 오후=PM, 오전·오후 표시가 없는 날짜=DAY. 시간 구간의 정확한 경계를 임의 지정하지 않음 |
| `weather_text` | 원본 `예보`의 날씨 문구 |
| `precip_probability_pct` | 원본 `강수확률(%)`, 0~100, 실제 강수량과 다름 |
| `lead_days` | 대상일 − 발표일의 달력 날짜 차이, 3~10일 |

## 읽는 방법

```python
from pathlib import Path
import pandas as pd

folder = Path('shared_datasets/kma_midrange')
df = pd.concat(
    [pd.read_csv(p, encoding='utf-8-sig') for p in sorted(folder.glob('forecast_*.csv'))],
    ignore_index=True,
)
df['issued_at_kst'] = pd.to_datetime(df['issued_at_kst'], utc=True).dt.tz_convert('Asia/Seoul')
```

서울만 필요한 경우 `df[df['region'].eq('서울.인천.경기')]`를 사용합니다. 원본이 서울 단독 자료가 아닌 수도권 묶음 예보임을 유지하세요.

## SMP 모델에 연결하기 전

예측 기준시각까지 발표된 행만 고른 뒤, 같은 지역·대상일·구간 중 가장 최근 발표본을 선택해야 합니다. 예측 기준시각 이후의 새 발표본으로 과거 입력을 덮어쓰면 안 됩니다. 이 자료는 대상일 전체 또는 오전·오후 예보이며 시간별 자료가 아닙니다. D+1·D+2의 기상 입력이나 일사량·풍속·기온을 이 파일만으로 만들 수 없습니다. D+3~D+10 자료를 72시간 전체 예보라고 표시하지 마세요.

이번 작업은 데이터 정리·공유이며, 기존 4개 모델의 입력 목록 변경이나 학습은 실행하지 않았습니다.

재생성: `1120gradpj/.venv/bin/python scripts/prepare_midrange_csv.py /path/to/FCT_MEDM_20261118001247.csv`
