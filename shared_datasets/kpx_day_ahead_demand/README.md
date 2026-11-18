# 2번 — 하루전 육지 전력수요 예측

통합 CSV: **mainland_demand_forecast_2023_2025.csv**

- 기간: 2023-01-01~2025-12-31, 26,304시간, 값 결측 0.
- 출처: [KPX 육지 발전계획용 수요예측 공식 연간 다운로드](https://new.kpx.or.kr/pssInland.es?mid=a10606090100&device=pc).
- API의 `mlfd`와 겹치는 2,352시간을 대조해 값이 모두 같았습니다. 전체 기간은 공식 연간 파일로 통일했습니다.
- UTF-8 BOM CSV. timestamp는 Asia/Seoul +09:00, 시간 시작 기준입니다. source_hour는 원본 1~24를 보존하며 timestamp에는 00~23으로 연결했습니다.

| 열 | 의미 |
|---|---|
| timestamp | 시간 구간 시작 시각(KST) |
| target_date | 예측 대상일. 발표일이 아님 |
| source_hour | 원본 거래시간 1~24 |
| demand_forecast_mw | 육지 하루전 수요예측, MW. API 필드 mlfd 대응 |
| geography | mainland |

실제 수요가 아니라 **예측값**입니다. 과거 최초 발표시각·당시 수정 전 발표본은 미검증입니다. 예측 기준일 D의 23시에 아직 발표되지 않은 D+2/D+3 대상일의 하루전 예측을 미리 넣으면 안 됩니다. 미래 72시간 연결 규칙은 별도 공통 합의가 필요합니다.

원본 출처·URL·해시·조회/검증 시각·공표시각 미확인은 manifest.json의 연도별 메타데이터에 보존했습니다. 원본에서 반복되던 이 정보를 매 행에 중복 저장하지 않았습니다. 공표시각 미확인을 수요예측 값의 결측과 혼동하지 마세요.

```python
import pandas as pd
df = pd.read_csv('shared_datasets/kpx_day_ahead_demand/mainland_demand_forecast_2023_2025.csv', encoding='utf-8-sig')
df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True).dt.tz_convert('Asia/Seoul')
```
