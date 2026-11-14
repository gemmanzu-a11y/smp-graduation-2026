# 출처와 실제 접근 경로

확인일: 2026-11-14 KST. 인증 쿼리와 인증키는 이 문서·원본 영수증에 저장하지 않습니다.

| 정보 | 공식 자료/명세 | 실제 접근 |
|---|---|---|
| 최신 SMP/수요예측 | [공공데이터포털 15131225](https://www.data.go.kr/data/15131225/openapi.do) | `https://apis.data.go.kr/B552115/SmpWithForecastDemand/getSmpWithForecastDemand`, 인증 성공. 수요예측은 실측 수요로 쓰지 않음 |
| 과거 육지 SMP | [EPSIS 시간별 SMP](https://epsis.kpx.or.kr/epsisnew/selectEkmaSmpShdChart.do?menuId=040202) | 공개 `selectEkmaSmpShd.ajax`, `selKind=land`, 1~24시를 당일 00~23시 시작 슬롯으로 정규화 |
| 수급 실측 | [EPSIS 실시간 수급](https://epsis.kpx.or.kr/epsisnew/selectEkgeEpsMepRealChart.do?menuId=030300) | 공개 `selectEkgeEpsMepRealGridAjax.ajax`, 기준 날짜 하루씩. c2 현재부하 MW, c6 공급예비율 %, c1 공급능력 MW, c5 공급예비력 MW |
| LNG 연료비단가 | [EPSIS 연료비용](https://epsis.kpx.or.kr/epsisnew/selectEkmaFucUpfChart.do?menuId=040100) | 공개 `selectEkmaFucUpf.ajax`, c15 LNG 원/kWh. 개별 월의 최초 공개일은 응답에 없음 |
| 과거 발전원별 발전량 | [공공데이터포털 15106744](https://www.data.go.kr/data/15106744/openapi.do) | 공식 Swagger에서 `/PvAmountByPwrGen/getPvAmountByPwrGen` 확인 후 호출, 403 |
| 지역별 태양광 | [공공데이터포털 15103243](https://www.data.go.kr/data/15103243/openapi.do) | `/PvAmountByLocHr/getPvAmountByLocHr`, 인증 성공. 광역지역×시간 408행인 예시에서 100행 샘플은 권한 확인용이며 학습에는 전체 공개 파일을 사용 |
| 최신 발전 현황 | [공공데이터포털 15158491](https://www.data.go.kr/data/15158491/openapi.do) | `/sumperfuel5m/getSumperfuel5m`, 인증 성공. fuelPwr8 태양광 MW, fuelPwr9 풍력 MW. 최신 5분의 출력이지 과거 시간당 발전량 MWh가 아님 |
| 과거 태양광·풍력 | [공공데이터포털 15065269](https://www.data.go.kr/data/15065269/fileData.do) | 공식 CSV 현재본·이력본 다운로드. 지역 ‘제주’ 제외, 연료원별 또는 wide 열 파싱 후 합계. 오래된 이력 파일과 현재 2024/25 파일이 겹치면 최신 목록 우선 |
| 기상 관측 | [기상청 API허브](https://apihub.kma.go.kr/apiList.do) | `typ01/url/kma_sfctm3.php`, authKey 인증 성공. 공식 응답 help=1의 TM/STN/TA/WS/SI 설명을 확인하고 구분자·가변 WW 꼬리를 구분해 파싱 |
| 국내 공휴일 | [한국천문연구원 특일 정보](https://www.data.go.kr/data/15012690/openapi.do) | `SpcdeInfoService/getRestDeInfo`, 403. [python-holidays KR](https://holidays.readthedocs.io/en/latest/auto_gen_docs/south_korea/)의 2023~2027 달력으로 명시적 대체 |

기상청 단기예보는 앞선 세션에서 403을 확인했습니다. 본 프로젝트는 사용자 요청의 시간별 **관측**을 과거 이력으로 사용하며 예보로 둔갑시키지 않았습니다.

## 알고리즘 공식 문서

- [PyTorch LSTM](https://docs.pytorch.org/docs/stable/generated/torch.nn.LSTM.html): 순환 인코더, 실제 LSTM 사용.
- [scikit-learn ensembles](https://scikit-learn.org/stable/modules/ensemble.html): HGB, ExtraTrees, RandomForest.
- [scikit-learn LinearRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html): 최소제곱 선형회귀.
- [LightGBM Python API](https://lightgbm.readthedocs.io/en/stable/Python-API.html): LGBMRegressor.
- [XGBoost Python API](https://xgboost.readthedocs.io/en/stable/python/python_api.html): XGBRegressor.

라이브러리 최신 문서 버전과 실제 설치 버전은 다를 수 있으며, 실제 실행 버전은 environment.json과 requirements-lock.txt를 기준으로 합니다.

## 공개 시각 원칙

1. `first_received_at` = 이번 실행이 실제 응답을 수신한 시각. 과거 최초 공개일이 아님.
2. `publicly_released_at` = 날짜와 근거를 확보한 때만 기록. 현재 LNG 46개 월은 비어 있음.
3. 과거 실측의 관측시각과 모델의 기준시각을 구분함. 시차를 둬도 과거 공개일이 자동 증명되지 않음.
4. 정산자료는 수정될 수 있고, 이번 다운로드가 당시 사용 가능했던 정산본인지 인증하지 않음.
5. 원본 응답은 SHA-256으로 고정하고, 키 없는 endpoint·요청 인자·수신시각을 manifest에 기록함.
