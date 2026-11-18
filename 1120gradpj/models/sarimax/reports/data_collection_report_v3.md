# 공통 v3 자료 재사용

새 수집 없이 LSTM과 동일한 원본·해시·전처리 버전을 사용했습니다. 자료별 선택·단위·품질은 `../../lstm/reports/data_collection_report_v3.md`, 상세 결측은 공통 버전 quality_report.json을 확인하세요.

{
  "raw_missing": {
    "demand_actual": 1095,
    "smp": 0,
    "demand_forecast_history": 0,
    "generation_lng": 15216,
    "generation_nuclear": 15960,
    "generation_coal": 15960,
    "solar_actual": 1,
    "solar_actual_regional_missing": 0,
    "wind_actual": 0,
    "wind_actual_regional_missing": 0,
    "reserve_mw": 703,
    "reserve_pct": 703,
    "temperature_c": 42,
    "wind_ms": 69,
    "irradiance_mj_m2": 11956,
    "irradiance_night": 0
  },
  "raw_rows": 26304,
  "split_origins": {
    "test": 182,
    "train": 718,
    "validation": 179
  },
  "excluded_origins": 11,
  "forecast_missing": {
    "mid_tmin": 0.0,
    "mid_tmax": 0.0,
    "mid_rain": 0.0
  },
  "checks": {
    "fixed_origin_cutoff": true,
    "issued_before_origin": true,
    "finite_model_arrays": true,
    "target_split_blocks": true
  },
  "generation_missing_by_year": {
    "generation_lng": {
      "2023": 0.736986301369863,
      "2024": 0.00273224043715847,
      "2025": 0.9972602739726028
    },
    "generation_nuclear": {
      "2023": 0.736986301369863,
      "2024": 0.08743169398907104,
      "2025": 0.9972602739726028
    },
    "generation_coal": {
      "2023": 0.736986301369863,
      "2024": 0.08743169398907104,
      "2025": 0.9972602739726028
    }
  },
  "temperature_issued_at_age_hours": {
    "min": 5.0,
    "max": 89.0,
    "median": 29.0
  },
  "weather_issued_at_age_hours": {
    "min": 5.0,
    "max": 89.0,
    "median": 41.0
  },
  "fred_crosscheck": {
    "DCOILWTICO": {
      "origins": 1079,
      "max_difference": 0.0
    },
    "DCOILBRENTEU": {
      "origins": 1079,
      "max_difference": 0.0
    },
    "PNGASJPUSDM": {
      "origins": 1079,
      "max_difference": 0.0
    },
    "PCOALAUUSDM": {
      "origins": 1079,
      "max_difference": 0.0
    }
  },
  "post_imputation_nonfinite": 0,
  "imputation_counts_file": "imputation_summary.csv",
  "missing_intervals_file": "missing_intervals.csv",
  "missing_reason_file": "missing_status.csv"
}
