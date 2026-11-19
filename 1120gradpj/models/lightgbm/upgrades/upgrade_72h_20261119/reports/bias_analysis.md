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
      "holdout_mae": 8.924602007872819,
      "monthly_nonworsening": true,
      "eligible": true
    },
    {
      "mode": "global",
      "calibration_bias": {
        "1": -1.3359427129648698,
        "2": -1.3359427129648698,
        "3": -1.3359427129648698
      },
      "holdout_mae": 9.340758957507523,
      "monthly_nonworsening": false,
      "eligible": false
    },
    {
      "mode": "by_day",
      "calibration_bias": {
        "1": -1.1792584914705082,
        "2": -1.3644126610624725,
        "3": -1.464156986361628
      },
      "holdout_mae": 9.340331020363788,
      "monthly_nonworsening": false,
      "eligible": false
    }
  ]
}


Test실제값으로편향보정값을계산하지않았습니다. none이면E4는E3와같습니다.
