# 기상청 중기 기온 예보 — 서울

출처: 기상청 [기상자료개방포털 중기예보](https://data.kma.go.kr/data/weatherReport/mrfList.do?pgmNo=646)의 육상 → 기온(WT) CSV 다운로드. 공식 다운로드 응답에서 도시명이 `서울`인 행만 추출했습니다. 기존 날씨 예보의 `서울.인천.경기` 권역과 공간 범위가 다릅니다.

발표시각 기준 2023-01-01~2026-11-17을 수집 대상으로 합니다. 실제 수집 범위·행 수·결측·중복은 `manifest.json`, 월별 원본 다운로드 조건과 SHA-256은 `collection_receipts.json`을 확인하세요. 원본은 CP949이며 공유 CSV는 UTF-8 BOM입니다. API 인증키가 필요하지 않은 공식 CSV 다운로드를 사용했습니다.

## 열과 단위

원본 10개 열을 보존했습니다.

- `발표시각`: 예보가 발표된 시각(KST)
- `지역`, `도시`: 기상청 원본 지역·도시명
- `예보시각`: 예보 대상 날짜
- `최저기온`, `최고기온`: 일 최저·최고기온 예측(℃)
- `최저기온하한`, `최저기온상한`, `최고기온하한`, `최고기온상한`: 기상청이 제공하는 기온예보 상·하한(℃). 임의의 확률 수준을 부여하지 않음

편의 열 `issued_at_kst`(ISO 8601, +09:00)와 `target_date`(YYYY-MM-DD)를 추가했습니다. 월별 파일 구분은 **발표월** 기준입니다. 미래 대상일이 다음 달·다음 해로 넘어갈 수 있습니다.

## 읽기

```python
from pathlib import Path
import pandas as pd
folder = Path('shared_datasets/kma_midrange_temperature_seoul')
df = pd.concat([pd.read_csv(p, encoding='utf-8-sig')
                for p in sorted(folder.glob('temperature_*.csv'))], ignore_index=True)
df['issued_at_kst'] = pd.to_datetime(df['issued_at_kst'], utc=True).dt.tz_convert('Asia/Seoul')
```

## 사용 조건

과거 예측을 재현할 때는 예측 기준시각까지 발표된 예보만 선택하세요. 같은 대상일의 여러 발표본은 서로 다른 예보이므로 한 행으로 무조건 중복 제거하면 안 됩니다. 상·하한이 없는 값은 그대로 빈칸으로 보존하며 대체하지 않습니다. 이 자료는 일 최저·최고기온 예보로, 시간별 기온·풍속·일사량 예보가 아닙니다. 단기예보나 동서발전 기상예측을 자동 대체하지 않았고 모델 학습도 실행하지 않았습니다.

재수집: 저장소 루트에서 `1120gradpj/.venv/bin/python scripts/collect_midrange_temperature.py`. 전체 도시 원본은 로컬 `1120gradpj/data/raw/kma_midrange_temperature`에만 보존합니다.
