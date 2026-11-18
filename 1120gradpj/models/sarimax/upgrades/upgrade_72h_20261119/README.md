# SARIMAX 72시간 업그레이드

현재v3의읽기전용재사용으로실행했습니다. 결과와한계는[최종보고서](reports/final_upgrade_report.md)를확인하세요.

최종채택=E3, 모델가중치α=0.4, 기준선=baseline_weekly.

하반기MAE=10.6648원/kWh,RMSE=15.1910,R²=0.5662. 원본결과는변경하지않았습니다.

실행: `python scripts/run_upgrade.py --source-project /path/to/1120gradpj`. 기존출력은덮어쓰지않으므로재실행은새업그레이드출력위치를사용하세요.
