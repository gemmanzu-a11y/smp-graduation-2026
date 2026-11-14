# 육지 SMP 72시간 예측 공동 연구

매일 23시 KST에 다음 날부터 3일 뒤까지 예측합니다. 현재 모델 폴더는 네 개만 유지합니다.

| 모델 | 경로 | 상태 |
|---|---|---|
| SARIMAX | models/sarimax | 알고리즘 구현·데이터 완비 검사 연결. 필수 공통 데이터 미완료로 학습 차단 |
| LSTM | models/lstm | 기존 부분 입력 실험 보존. 새 공통 입력 연결 전 학습 비활성화 |
| XGBoost | models/xgboost | 기존 부분 입력 실험 보존. 새 공통 입력 연결 전 학습 비활성화 |
| LightGBM | models/lightgbm | 기존 부분 입력 실험 보존. 새 공통 입력 연결 전 학습 비활성화 |

ExtraTrees·HGB·선형회귀·RandomForest 폴더와 모델 설정은 삭제했습니다. 과거 보고서는 당시 실험의 이력으로 남기며 새 네 모델 비교 결과가 아닙니다.

## SARIMAX 시작

```sh
# 1120gradpj 폴더 안에서
.venv/bin/python models/sarimax/train.py --audit-only
.venv/bin/python models/sarimax/train.py
.venv/bin/python -m unittest discover -s tests -v
```

필수 입력 미확보 시 종료 코드 2로 중단하며 부분 입력으로 학습하지 않습니다. 상세 알고리즘·공통 파일 형식·현재 누락은 `models/sarimax/README.md`, `DATA_STATUS.md`, `source_inventory.json`을 확인하세요.

기간: 2023~2024 학습, 2025년 상반기 검증, 하반기 평가. 72시간 목표가 구간 경계를 넘는 블록은 제외합니다. 설정 선택은 검증 MAE만 사용합니다.

국내 LNG는 공유 폴더의 HOME 엑셀에서 연료비단가/LNG/원/kWh 열을 직접 추출합니다. 과거 평가는 동월 값을 사용하는 조건부 실험이고 2026년 11월 시연은 10월 값으로 고정합니다. 열량단가 API와 2개월 지연 가정은 이번 입력에서 제외합니다.

과거 수집 코드와 자료는 보존했습니다. 자료 수집용 키는 환경변수 또는 개인 .env에서만 읽어야 하며 GitHub에 올리지 않습니다. 기존 수집기의 키 이름은 `KPX_SERVICE_KEY`, `KMA_APIHUB_AUTH_KEY`이고 새 수집 연동 시 공통 이름과의 매핑을 명시해야 합니다.

`run_all.py`는 새 데이터 게이트를 먼저 확인합니다. 세 ML/DL 모델은 기존 부분 입력으로 새 비교를 실행하지 않도록 중단하며 공통 입력 연결 후 별도로 갱신해야 합니다. 기존 predict·과거 요약 도구의 출력은 운영 시연이나 새 공통 비교 결과로 취급하지 않습니다.

GitHub 자동 공유 설정은 상위 폴더 GITHUB_SHARING.md를 확인하세요. 원자료·가상환경·학습 모델 바이너리는 별도 공유 대상입니다.
