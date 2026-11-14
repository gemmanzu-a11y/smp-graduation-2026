# 1120gradpj — 육지 SMP D+1·D+2·D+3 예측

기존 `v20/`, `presentation/`와 독립된 새 연구 프로젝트입니다. 매일 **23:00 KST를 기준으로 다음 날·2일 뒤·3일 뒤 각각 00~23시, 총 72시간**을 직접 예측합니다. 7개 알고리즘을 같은 원천 입력·시간 분할·평가 지표로 실행합니다.

VS Code: `1120gradpj.code-workspace`를 열면 됩니다. 최초 작업에서 새 창 열기 명령을 실행했습니다.

## 실행

프로젝트 폴더 안에서 실행합니다. macOS/Linux:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/collect_data.py --prompt-keys
python scripts/build_dataset.py
python scripts/run_all.py
python -m unittest discover -s tests -v
python scripts/check_artifacts.py
```

이번 환경에서는 이미 설치된 과학 계산 라이브러리를 재사용하려고 `--system-site-packages` 가상환경을 만들고, XGBoost와 holidays만 프로젝트 가상환경에 추가 설치했습니다. 정확한 실행 버전은 `reports/environment.json`, `requirements-lock.txt`에 있습니다. 위 독립 설치 명령 자체를 별도 빈 환경에서 재검증한 것은 아닙니다.

Windows는 `.venv\Scripts\Activate.ps1`로 활성화하면 같은 Python 명령을 사용할 수 있습니다. 이번 실행·시간 측정은 macOS CPU 기준이며 Windows 실행은 별도 검증하지 않았습니다.

키는 수집 명령의 비표시 프롬프트에 넣거나 프로세스 환경변수 `KPX_SERVICE_KEY`, `KMA_APIHUB_AUTH_KEY`로 설정합니다. **저장소에 키를 쓰지 않습니다.** Windows의 User 환경변수를 설정한 것만으로 macOS Python에 키가 전달되지는 않습니다. `.env.example`은 이름 안내용이며 `.env` 자동 로드는 구현하지 않았습니다. 모델 학습·예측·평가는 수집된 데이터만 읽으므로 키가 필요 없습니다.

```sh
# 이미 수집된 데이터로 모델 한 개만 다시 실행
python models/hgb/train.py
python models/lstm/train.py
# 여러 모델을 지정해 순서대로 실행
python scripts/run_all.py hgb lightgbm xgboost
# 저장된 가중치로 예측만 실행
python scripts/predict.py --model hgb  # 현재는 재생발전 이력 부족으로 종료 코드 2
# 역사적 참조 시점을 지정 (실제 과거 발급을 주장하지 않음)
python scripts/predict.py --model lstm --origin 2025-12-28T23:00:00+09:00
```

수집 CLI 기본 범위는 2023-01-01~한국시간 어제입니다. `--start`, `--end`, `--only smp power weather fuel renewable holidays`로 변경할 수 있습니다. 성공한 동일 요청은 해시 검증된 캐시를 재사용합니다. 이미 캐시된 원본을 현재 응답으로 재확인하는 자동 정정 수집은 이번 버전에 포함하지 않았습니다. 데이터 기간을 바꿔도 평가 분할은 `configs/experiment.json`을 별도로 수정해야 합니다.

## 폴더

```text
configs/experiment.json        공통 분할·seed·입력 지연·모델 설정
src/smp_forecast/http.py       TLS 검증·키 비저장·원본/수신 증거
src/smp_forecast/collect.py    공식 자료 수집·명시적 파싱
src/smp_forecast/dataset.py    23시 기준 72개 직접 타깃과 과거 입력
src/smp_forecast/training.py   공통 학습·저장·평가
models/lstm/                  PyTorch LSTM
models/hgb/                   HistGradientBoostingRegressor
models/lightgbm/              LGBMRegressor
models/extra_trees/           ExtraTreesRegressor
models/linear_regression/     최소제곱 LinearRegression
models/random_forest/         RandomForestRegressor
models/xgboost/               XGBRegressor
scripts/                      수집·데이터 구성·일괄 실행·추론·검증
reports/                      API 결과·품질·성능 비교·최종 보고
 data/raw/                    요청 인자(키 제외)·해시·불변 원본
 data/processed/              정규화 CSV·동일 학습 NPZ
```

모델별 `algorithm.py`는 해당 알고리즘을 정의하며 `train.py`로 따로 실행합니다. `artifacts/`에는 모델 가중치, train-only 전처리기, `predictions.csv`, `metrics.csv`, `reference_forecast.csv`, `latest_forecast_status.json`, 예시 그래프, 시간대별 오차, 설정·입력 해시·실행 시간 `run.json`을 저장합니다. LSTM은 추가로 epoch별 `training_history.json`을 저장합니다.

## 데이터 확보 결과와 범위

| 요청 정보 | 저장 파일 | 확보/의미 |
|---|---|---|
| 육지 시간별 SMP | `data/processed/smp_hourly.csv` | EPSIS 공개 과거 자료 + 인증 API 최신 응답 대조. 2023~2026-11-13 |
| 월별 LNG 연료비단가 | `fuel_monthly.csv` | EPSIS c15, 원/kWh. 2023-01~2026-10 46개월 |
| LNG 확인 가능한 공개일 | 위 파일의 `publicly_released_at`, `release_evidence` | **과거 개별 공개일 미확보 → 빈값**. `first_received_at`은 이번 수신 시각이며 첫 공개일로 바꾸지 않음 |
| 시간별 수요 실적·공급예비율 | `power_hourly.csv` | EPSIS 5분 현재부하 MW·공급예비율 %를 12개 모두 있을 때 시간평균. EPSIS 표시 수급, 육지 단독 범위인지 별도 확인되지 않음 |
| 태양광·풍력 | `renewable_hourly.csv` | 공식 공개 파일. 제주 제외, 시장참여 발전기의 시간별 전력거래량 MWh. 2023~2025, 비시장·자가소비 발전 포함 안 됨 |
| 기온·일사량·풍속 | `weather_stations.csv`, `weather_hourly.csv` | 인증 ASOS API 6개 육지 관측소. °C, MJ/m², m/s. 모델에는 관측소별 단순평균 사용 |
| 국내 공휴일 | `holidays.csv` | 특일 API 403 → python-holidays KR 대체. `official_api_verified=False` 명시 |

`reports/api_probes.json`에서 실제 인증 API 호출 결과를 확인할 수 있습니다. SMP, 지역별 태양광, 최신 발전 현황은 성공했고, 과거 발전원별 발전량·특일 API는 403이었습니다. 따라서 ‘모든 항목을 인증 API로 받았다’고 주장하지 않습니다. 과거 태양광·풍력은 공식 파일 다운로드 경로, 수급과 연료는 EPSIS 공개 조회 경로로 보완했습니다.

기상 관측소는 108 서울, 133 대전, 143 대구, 156 광주, 159 부산, 105 강릉입니다. 육지 공간의 대표성을 최적화한 가중평균은 아닙니다. ASOS `TM`은 관측시각이며 `SI`는 해당 자료 정의의 시간 일사량입니다. 야간 SI의 미관측 `-9`를 임의로 0으로 바꾸지 않았습니다. 영하 -9°C는 결측으로 처리하지 않습니다.

## 예측·평가 설계

- 매일 23시 origin → D+1~D+3 72개 타깃. 미래 실측 기상·수급·발전량을 입력하지 않습니다.
- 과거 48시간의 8개 변수, 목표 시각 달력 정보, origin 당일 동일 시각 SMP, 목표일 전주 같은 시각 SMP, 결측 비율 등 **406개 공통 특성**. LSTM은 동일 X의 48×8 블록을 시계열로 재배열하고 나머지 문맥과 결합합니다.
- 수요·예비율·기상 관측은 최소 24시간, 재생발전 정산자료는 48시간 지연을 둡니다. 이 지연은 **실제 과거 공개 시각 인증이 아니라 연구 가정**입니다. 연간 확정 파일의 당시 최초 공개·정정 이력은 없습니다.
- LNG는 공개 근거 시각이 origin 이하인 경우에만 입력합니다. 현재 과거 공개일이 없으므로 학습 전 기간 해당 두 특성은 비어 있으며, 실제 이번 비교에서 LNG 값은 사용하지 않았습니다. 값을 수집한 것과 모델에 사용할 수 있는 것을 구분합니다.
- 분할은 모든 72개 정답이 해당 기간 안에 있을 때만 편입: 2023~2024 학습 720개 origin, 2025 상반기 검증 179개, 하반기 테스트 182개. 경계의 타깃이 섞이는 origin은 제외합니다.
- 결측 대체 중앙값·표준화 평균/분산은 train에서만 적합합니다. HGB의 무작위 내부 조기종료는 껐습니다. LSTM epoch만 validation MAE로 선택합니다. 트리의 반복 수 등은 고정 초안이며 광범위 하이퍼파라미터 탐색을 한 결과가 아닙니다.
- MAE·RMSE(원/kWh), R²를 validation/test 각각 D+1·D+2·D+3 및 전체로 저장합니다. 동일 origin과 실제 정답을 모든 모델에 사용합니다. 비교용 원점 당일 가격 반복·전주 반복 기준선도 함께 평가합니다.
- 최종 모델 선택은 validation MAE만 사용합니다. 테스트를 보고 설정·모델을 재선택하지 않습니다.

## 최신 예측과 운영 한계

최신 입력의 48시간 이력에서 필수 변수 하나라도 전부 빠지면 `inference.py`가 예측을 차단합니다. 현재 2026년 태양광·풍력 이력이 없으므로 각 모델의 `latest_forecast_status.json`은 `blocked_missing_input`입니다. `latest_forecast.csv`를 생성하지 않으며, `predict.py`의 기본 최신 추론은 종료 코드 2와 누락 사유를 반환합니다. 결측 대체만으로 숫자가 나온다고 운영 가능한 예측으로 내보내지 않습니다.

각 폴더의 `reference_forecast.csv`는 **2025-12-28 23시 참조 → 2025-12-29~31의 72시간 과거 테스트 재생**입니다. 생성시각과 참조시점을 구분하며, 최신 예측이라고 표시하지 않습니다. `predictions.csv`에는 검증·테스트 전체 결과가 있습니다.

평가 모델은 2024년 말까지 학습한 동결 모델이며, 2025 테스트나 2026 데이터로 자동 재학습하지 않았습니다. 최신 추론 검수 중 LSTM에 2026년 재생발전 전체 결측을 넣었을 때 비정상적으로 큰 출력이 나타나는 것을 발견했습니다. 숫자를 임의로 자르거나 다른 모델 값으로 바꾸지 않고, 모든 모델에 동일한 입력 적격성 차단을 추가했습니다. 초기 최신 출력은 삭제하고 실제 저장 가중치의 과거 72시간 재생을 다시 검증했습니다.

**SMP는 하루전 공개 가격입니다.** 실제 23시에는 D+1 가격이 이미 공개되어 있을 수 있습니다. 이번 D+1 성능은 과거 시계열을 가린 연구 비교이며, 운영에서는 해당 시점 수신한 공식 가격과 모델 예측을 구분해야 합니다. 최신 인증 API가 반환한 공식 가격은 원본/수신 영수증에 따로 보존했으며 미래 정답을 모델 입력으로 사용하지 않았습니다.

자동 23시 실행 작업·운영 배포는 등록하지 않았습니다. 실제 공개일 이력, 공휴일 API 승인, 최신 재생발전 입력이 보완되어야 모든 요청 변수를 사용한 시점 인증 운영 평가가 가능합니다. 현재 결과는 **공개 시각 미검증을 명시한 후향 실험**입니다.

공식 출처·상세 결과·검증은 `reports/SOURCES.md`, `reports/FINAL_REPORT.md`, `reports/artifact_verification.json`을 보세요.

일일 수동 실행용 `scripts/daily_run.py`도 있습니다. 환경변수의 키를 읽어 수집·입력 재구성·저장된 7개 모델의 추론을 순서대로 실행합니다. 자동 재학습이나 OS 예약 작업 등록은 하지 않습니다.

전체 입력 요건 확인: `python scripts/audit_readiness.py --strict`는 미충족 항목이 있으면 종료 코드 2를 반환합니다. 연구 모델 실행 성공과 최신 운영 예측 가능 여부를 구분합니다.
