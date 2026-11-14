# LSTM

48시간×8개 변수의 이력을 LSTM으로 인코딩하고, 72개 목표 시간의 달력·시차 조건과 결합해 D+1~D+3의 72개 값을 직접 출력합니다. 예측값을 되먹이지 않습니다. 탭형 모델과 동일한 원천 X의 이력 블록을 시간축으로 재배열합니다. Adam, MSE 학습, validation MAE 조기 종료를 사용합니다.

프로젝트 루트에서 `.venv/bin/python models/lstm/train.py`로 실행합니다.
