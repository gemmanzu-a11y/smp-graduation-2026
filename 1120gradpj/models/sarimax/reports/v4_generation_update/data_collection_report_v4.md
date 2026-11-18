# 공통 v4 자료 재사용

발전량만 shared_datasets/kpx_generation/20261119_v2의 검증된 자료로 교체했습니다. 나머지11개 그룹은 기존 공통v3와 값이 같습니다. 원본 및 파생자료 SHA256은 공통v4 manifest.json에 보존했습니다. 2023/2025년 발전량 결측0,2024년 LNG24시간·석탄/원자력768시간 결측입니다. 상세 통계:

{
  "raw_missing": {
    "demand_actual": 1095,
    "smp": 0,
    "demand_forecast_history": 0,
    "generation_lng": 24,
    "generation_coal": 768,
    "generation_nuclear": 768,
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
      "2023": 0.0,
      "2024": 0.00273224043715847,
      "2025": 0.0
    },
    "generation_coal": {
      "2023": 0.0,
      "2024": 0.08743169398907104,
      "2025": 0.0
    },
    "generation_nuclear": {
      "2023": 0.0,
      "2024": 0.08743169398907104,
      "2025": 0.0
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
