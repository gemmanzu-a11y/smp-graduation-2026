# LSTM: 공통 데이터로 향후 72시간 직접 예측

현재 구현은 `1120gradpj/models/lstm`을 재사용합니다. 별도의 `SMP_LSTM_2026`을 중복 생성하지 않았습니다. `artifacts/`의 기존 모델은 이전 입력을 사용한 미완성 실험이며 새 모델의 최종 결과가 아닙니다. 다른 모델의 코드는 수정하지 않았습니다.

## 실행

저장소 루트에서:

```sh
1120gradpj/.venv/bin/python 1120gradpj/models/lstm/train.py --audit-only
1120gradpj/.venv/bin/python 1120gradpj/models/lstm/train.py --shared /absolute/path/SMP_SHARED_DATA/versions/v2
```

`--audit-only`는 수집본과 공통 버전의 정합성을 검사합니다. 실제 학습 명령도 반드시 같은 검사를 먼저 실행합니다. BLOCKED이면 종료 코드 2이며 모델·성능·그림을 만들지 않습니다. 상태는 `reports/data_status.json`, 차단 항목은 `reports/data_blockers.md`입니다. 공통 정의나 파일이 빠졌을 때 임의의 입력 열로 자동 학습하지 않습니다. `SHARED_DATA_DIR` 환경변수도 지원합니다.

설정: `../../configs/lstm.json`. Train 2023~2024, Validation 2025 상반기, Test 2025 하반기입니다. 타깃 72시간 블록 전체가 한 분할에 들어가는 발행일만 사용합니다.

## 알고리즘이 하는 일

매일 23시 기준, 다음 날 00시부터 3일 뒤 23시까지 72개 가격을 한 번에 예측합니다.

1. **과거 이력 `[발행일 수, 48 또는 168시간, 12변수]`**: SMP, 수요, LNG·석탄·원자력 발전량, 태양광·풍력, 공급예비력·예비율, 기온·일사량·풍속입니다. LSTM이 최근 변화와 일중 패턴을 요약합니다. 시간 라벨이 구간 시작이면 23시~24시 실적은 23시에 아직 완결되지 않았으므로 제외합니다.
2. **미래 조건 `[발행일 수, 72시간, 17변수]`**: 이용 가능한 수요예측, 달력, 국내 LNG 및 국제가격, 중기 날씨·강수확률·일 최저/최고기온입니다. 같은 일 최저/최고기온을 시간 행에 연결하더라도 시간별 기온 예보로 해석하지 않습니다. 연결 규칙은 팀 공통으로 확정해야 합니다.
3. LSTM의 마지막 상태를 72개 목표 시간에 전달하고 각각의 미래 조건과 결합합니다. 공유된 작은 신경망이 각 시간의 SMP를 출력합니다. 미래 정답이나 이전 미래 실측값을 입력하지 않습니다.

과거 이력·미래 조건·목표 SMP의 평균과 표준편차는 **학습 분할만으로** 계산하고 저장합니다. 학습 손실은 표준화한 SMP의 MSE, 설정 선택과 조기 종료 기준은 원/kWh 단위의 Validation MAE입니다. Adam 최적화와 기울기 크기 제한 1.0을 적용합니다. 후보 3개, 최대 100 epoch, 개선이 10회 연속 없으면 중단합니다. 은닉 크기는 과거 패턴의 요약 차원, 층 수는 LSTM을 겹치는 깊이, 학습률은 가중치 갱신 크기, lookback은 기억할 과거 구간입니다.

최적 Validation epoch의 가중치를 복원합니다. Test를 설정 선택·표준화·조기 종료에 사용하지 않고, Train+Validation 재학습이나 Test 중 재학습도 하지 않습니다. 다음 발행일에는 그때까지의 새 과거 관측을 입력할 수 있습니다. 저장한 가중치·표준화 통계로 같은 예측이 재현됩니다.

## 공통 데이터 계약 v2

계약은 `src/smp_forecast/common_v2.py`에 있으며 네 모델에 재사용할 수 있습니다. 다른 모델의 기존 계약은 이번에 자동 교체하지 않았습니다. `shared_bundle_manifest.example.json`은 **미완료 템플릿**이며 READY인 실제 자료가 아닙니다.

필수 파일: `manifest.json`, `hourly.csv`, `forecast_inputs.csv`, `evaluation_origins.csv`, `evaluation_targets.csv`, `feature_manifest.csv`.

- `hourly.csv`: timezone offset이 있는 `timestamp`, 모든 과거 열(HISTORY), 완결된 관측의 이용 가능 시각 `available_at`, SMP 자체의 이용 가능 시각 `smp_available_at`. Train 시작 전 최대 lookback+7일 이력도 필요합니다. 가격은 시간 시작 전에 이미 공개될 수 있으므로 SMP 공표시각은 다른 실측의 완결 시각과 분리합니다.
- `forecast_inputs.csv`: `forecast_origin`, `target_timestamp`, FUTURE의 모든 열, `latest_nonfuel_source_timestamp`, 두 기준 예측값 및 `baseline_origin_day_latest_available_at`, FRED의 `international_asof_date`, `latest_international_observation_date`.
- `evaluation_origins.csv`: `split`(train/validation/test), `forecast_origin`. 전체 블록 날짜 목록을 공유하며 누락을 조용히 제외하지 않습니다.
- `evaluation_targets.csv`: `split`, `forecast_origin`, `target_timestamp`.
- `feature_manifest.csv`: `feature`, `unit`, `scope`, `source_field`, `availability_rule`, `missing_rule`, `transform`, `role`. 모든 실제 입력 열을 설명합니다. 날씨 문구의 공통 숫자 코드와 미지 범주 정의도 여기에 기록합니다. 현재 코드는 이 공통 코드를 숫자 조건으로 받으며 임의로 지역·문구를 재인코딩하지 않습니다.
- `manifest.json`: 데이터 버전, schema_version=smp-common-v2, 필수 출처와 증거 파일, 열 순서, 파일 SHA-256, 연료 정책, 네 가지 공통 결정의 확정 근거가 필요합니다. 국내 LNG 증거 CSV는 `month,value` 열과 원/kWh 단위를 사용하며 지정 HOME 원본의 추출 근거를 출처 명세에 기록합니다.

직접 확인하는 항목: 필수 출처·단위·지역·매핑 근거, 입력 파일 해시, 시간 누락·중복·비유한 값, 완결되지 않은 실측, 기준시각 이후 자료, 전체 발행일·목표 행, 국내 LNG 대상월 매핑, FRED D−2와 관측일·72시간 고정, 기준 예측 값과 SMP 이용 가능 시각입니다. 원자료의 실제 의미·발표 이력을 메타데이터만으로 새롭게 입증하지는 않으므로 근거 자료가 필요합니다.

## 아직 필요한 팀 공통 결정

- EPSIS 수요와 별도 전국 수요 후보 중 최종 정의 선택.
- 중기예보가 제공하지 않는 D+1/D+2 등 구간을 처리하는 공통 방식. 없는 날짜를 복사하거나 실측으로 채우지 않습니다.
- 하루전 수요예측의 D+2/D+3 연결 방식.
- 발행일 같은 시간 반복 기준 예측의 23시 SMP 이용 가능성.

동서발전 태양광 예측·기상 예측, 시간별 단기예보, 열량단가 API는 새 필수 검사에서 제외했습니다. 국내 LNG 과거 공개일 미확인 자체는 차단 사유가 아니며 **동월 LNG 제공 조건부 과거 실험**으로 표시합니다. 11월 시연의 10월 LNG 고정은 후속 운영 설정으로 분리하며 이 학습 명령은 과거 평가 전용입니다.

## 데이터가 준비된 뒤의 결과

`outputs/<dataset_version>/<실행시각>/`에 새 결과를 저장합니다. 기존 결과를 덮어쓰지 않습니다.

- Validation·Test 72시간 예측 CSV: 발행일, 목표 시간, horizon, D+구분, 실제/예측, 기준 예측, 절대오차, 데이터 버전·연료 정책.
- 전체·발행일·발행일×D+·목표월×D+·D+·1~72거리별 MAE/RMSE/R² 및 기준 대비 개선율.
- 모델, 후보 설정, 선택 epoch, 입력 목록, 환경·시간·공통 manifest 해시.
- D+구분을 유지한 6개월 시간별 HTML·일평균 PNG, 월별 MAE PNG/HTML, 거리별 오차와 산점도.
- 선택일은 `--selected-origin '2025-07-01T23:00:00+09:00'`처럼 미리 지정합니다. 전체 발행일 그래프를 생성하지 않습니다.

MAE는 평균 가격 오차, RMSE는 큰 오차에 더 민감한 지표입니다. 원/kWh 단위이며 정확도 %가 아닙니다. 개선율은 `100*(1-모델 MAE/기준 MAE)`, 기준 MAE가 0이면 정의하지 않습니다. 네 모델 비교에는 같은 공통 평가 행을 사용해야 합니다.

## 기술 검증

```sh
1120gradpj/.venv/bin/python -m unittest discover -s 1120gradpj/tests -p test_lstm_v2.py -v
```

작은 합성 자료로 72시간 출력, Train 전용 표준화, 저장/복원, 시간 경계, 미래 데이터 차단, 누락 공통 규칙·변경 해시·LNG 오매핑·국제가격 변경 시 학습 차단을 검증합니다. 합성 테스트는 실제 SMP 성능 평가가 아닙니다.
