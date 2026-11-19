# OOF 편향 보정 선택

{
  "selected": {
    "mode": "none",
    "bias_by_day": {
      "1": 0.0,
      "2": 0.0,
      "3": 0.0
    },
    "policy": "Jan-Apr OOF fit, May-Jun validation; >=1% MAE improvement and neither month worsens; selected bias refitted on all OOF"
  },
  "candidates": [
    {
      "mode": "none",
      "calibration_bias": {
        "1": 0.0,
        "2": 0.0,
        "3": 0.0
      },
      "holdout_mae": 8.543070965718414,
      "monthly_nonworsening": true,
      "eligible": true
    },
    {
      "mode": "global",
      "calibration_bias": {
        "1": -0.7309314288398848,
        "2": -0.7309314288398848,
        "3": -0.7309314288398848
      },
      "holdout_mae": 8.743866792120976,
      "monthly_nonworsening": false,
      "eligible": false
    },
    {
      "mode": "by_day",
      "calibration_bias": {
        "1": -0.5753073645076613,
        "2": -0.7583810129165726,
        "3": -0.8591059090954213
      },
      "holdout_mae": 8.74417356775993,
      "monthly_nonworsening": false,
      "eligible": false
    }
  ]
}


Test실제값으로편향보정값을계산하지않았습니다. none이면E4는E3와같습니다.
