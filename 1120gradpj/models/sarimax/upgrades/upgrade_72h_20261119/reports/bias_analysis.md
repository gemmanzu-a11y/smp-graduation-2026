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
      "holdout_mae": 8.249404401064304,
      "monthly_nonworsening": true,
      "eligible": true
    },
    {
      "mode": "global",
      "calibration_bias": {
        "1": -2.537712159857486,
        "2": -2.537712159857486,
        "3": -2.537712159857486
      },
      "holdout_mae": 8.864121077089832,
      "monthly_nonworsening": false,
      "eligible": false
    },
    {
      "mode": "by_day",
      "calibration_bias": {
        "1": -2.466183583494125,
        "2": -2.5656986314877996,
        "3": -2.5812542645905334
      },
      "holdout_mae": 8.863388367203088,
      "monthly_nonworsening": false,
      "eligible": false
    }
  ]
}


Test실제값으로편향보정값을계산하지않았습니다. none이면E4는E3와같습니다.
