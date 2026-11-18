# SARIMAX — 공통 v3 72시간 육지 SMP

## 최신 실행: 발전량 보완 v4

`reports/v4_generation_update/`에서 새 결과를 확인하세요. `CURRENT_RUN.json`이 현재 실행 위치를 가리킵니다. 재현 명령은 `1120gradpj/.venv/bin/python 1120gradpj/models/sarimax/train.py --dataset-version v4`입니다. 아래 v3 설명과 이전 결과는 보존했습니다.

최신 실행기는 `train.py`, 신규 추정기는 `algorithm_v3.py`입니다. 이전 실행기는 `train_v2.py`, 기존 알고리즘은 `algorithm.py`로 보존했습니다. LSTM과 동일한 `SMP_SHARED_DATA/versions/v3_a90141b81ecd_lag72`를 읽으며 새 API 수집이나 공통 데이터 변경을 하지 않습니다.

```sh
1120gradpj/.venv/bin/python 1120gradpj/models/sarimax/train.py --audit-only
1120gradpj/.venv/bin/python -m unittest discover -s 1120gradpj/tests -p 'test_sarimax_v3.py' -q
1120gradpj/.venv/bin/python 1120gradpj/models/sarimax/train.py
1120gradpj/.venv/bin/python 1120gradpj/models/sarimax/report_v3.py
1120gradpj/.venv/bin/python 1120gradpj/models/sarimax/verify_v3.py
```

## 알고리즘

`SMP(t) = 외생변수 83개의 선형 효과 + 계절 ARIMA 오차(t)`입니다. 외생변수에는 공통 12개 그룹의 시차 요약·마스크·연료·중기예보·달력이 포함됩니다. LSTM의 시퀀스 인코더 대신 선형 외생효과와 ARIMA 오차 상태를 사용합니다. Train에서는 72시간 블록이 겹친 목표시간을 중복 학습하지 않고, 같은 목표시간의 가장 최근 발행 입력 한 행으로 시간별 시계열을 구성합니다.

공통 Train 입력 83열의 행렬 계수는 69이며 상수·선형 종속 관계가 있습니다. 입력을 삭제하지 않기 위해 다음 **2단계 제약 추정**을 사용합니다.

1. Train으로만 표준화하고 전체 83열의 최소노름 OLS 계수(beta)를 구합니다. 상수 열의 scale은 1입니다. SVD 기준 rcond=1e-10입니다. 개별 계수는 유일하게 식별된다고 해석하지 않습니다.
2. statsmodels `SARIMAX(..., exog=전체83열).fit_constrained(...)`에서 beta를 고정한 채 AR/MA/24시간 계절계수·오차분산을 조건부 최대우도로 추정합니다. beta와 ARIMA를 동시에 최적화한 공동 MLE는 아닙니다. 외생변수 없는 SARIMA로 대체하지 않습니다.

후보는 `(1,0,0)×(1,0,0,24)`, `(1,0,1)×(1,0,0,24)`, `(2,0,0)×(1,0,0,24)`입니다. Validation MAE만으로 선택하며 수렴 실패 후보는 기록하고 제외합니다. Final Test로 설정을 바꾸지 않습니다.

## 72시간 지연과 상태

예측 기준 D일23시, 실측 마감은 D−3일23시입니다. 시간 구간의 종료가 이 마감을 넘지 않도록 마지막 SMP 상태는 마감 직전 시작 시간에 둡니다. 미래 72시간만 바로 예측하면 이 공백을 누락하게 되므로, **공백 73시간 + 목표 72시간 = 145시간**을 실제 SMP 없이 연속 예측하고 뒤 72시간을 결과로 저장합니다.

공백의 외생변수는 공통 데이터에 이미 저장된 이전 발행 입력을 사용하며 해당 발행시각이 현재 기준시각을 넘지 않는지 검사합니다. 미래 목표 72시간은 현재 발행일의 공통 입력을 그대로 사용합니다. 이 차이도 재현 규칙의 일부입니다.

계수는 고정합니다. 다음 발행일에 실측 마감이 이동하면 새로 이용 가능한 과거 SMP에 대해서만 Kalman 상태를 갱신합니다. LSTM과 마찬가지로 Validation의 과거 실측을 Final Test 입력에 활용하는 것은 허용되며, Test 미래 정답을 미리 넣지는 않습니다. Train 끝의 상태를 그대로 평가에 쓰지 않고 첫 평가 발행일의 실측 마감까지의 이력만 다시 필터링합니다.

Train 계수는 2024년 말까지의 학습 정답으로 추정합니다. 이는 합의한 오프라인 분할 평가 규칙입니다. 실제 지연 공개 환경에서 연말 학습자료가 최초 2025년 예측 전에 전부 확보되었는지까지 증명하는 실시간 운용 시험은 아닙니다.

## 한계와 결과

동월 LNG 제공 조건부 실험·실측72시간 지연 가정·2025년 발전량 대규모 대체값이라는 공통 한계가 그대로 적용됩니다. 95% 구간은 고정 beta와 모형을 조건으로 한 모델 구간이며, 대체값·연료·예보 불확실성과 beta 추정 불확실성을 모두 반영한 보정된 확률구간이 아닙니다.

모든 원본과 LSTM 결과는 보존합니다. 전체 예측과 모델은 로컬 `outputs/<version>/<run>/`에 보존하고, 코드·지표·보고서·작은 PNG만 기존 GitHub 공유에 반영합니다. 최신 결과 위치는 `reports/latest_run_v3.json`, 최종 설명은 `reports/final_evaluation_report_v3.md`입니다.

계수별 표준오차는 계산하지 않습니다(`cov_type=none`). 이는 예측을 위한 상태 공분산·혁신분산을 제거한다는 뜻이 아닙니다.
