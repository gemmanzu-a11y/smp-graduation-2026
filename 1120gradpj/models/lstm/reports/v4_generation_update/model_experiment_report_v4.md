# LSTM 실험 기록

{
  "candidates": [
    {
      "params": {
        "lookback": 48,
        "hidden_size": 32,
        "layers": 1,
        "dropout": 0.0,
        "learning_rate": 0.001,
        "batch_size": 32,
        "epochs": 100,
        "patience": 10
      },
      "best_epoch": 23,
      "validation_mae": 11.573634147644043,
      "epochs": [
        {
          "epoch": 1,
          "train_scaled_mse": 0.6691634322939477,
          "validation_mae": 16.102561950683594
        },
        {
          "epoch": 2,
          "train_scaled_mse": 0.32022514740072583,
          "validation_mae": 14.900693893432617
        },
        {
          "epoch": 3,
          "train_scaled_mse": 0.2478875495431151,
          "validation_mae": 13.454131126403809
        },
        {
          "epoch": 4,
          "train_scaled_mse": 0.22058058880829878,
          "validation_mae": 13.131464004516602
        },
        {
          "epoch": 5,
          "train_scaled_mse": 0.2098676101161909,
          "validation_mae": 13.08580493927002
        },
        {
          "epoch": 6,
          "train_scaled_mse": 0.20086732315817915,
          "validation_mae": 13.104265213012695
        },
        {
          "epoch": 7,
          "train_scaled_mse": 0.1944655915903846,
          "validation_mae": 12.633021354675293
        },
        {
          "epoch": 8,
          "train_scaled_mse": 0.1894051944811032,
          "validation_mae": 13.000772476196289
        },
        {
          "epoch": 9,
          "train_scaled_mse": 0.1845614571425244,
          "validation_mae": 12.768182754516602
        },
        {
          "epoch": 10,
          "train_scaled_mse": 0.17928913883180006,
          "validation_mae": 12.584931373596191
        },
        {
          "epoch": 11,
          "train_scaled_mse": 0.17466041674022886,
          "validation_mae": 12.507678985595703
        },
        {
          "epoch": 12,
          "train_scaled_mse": 0.16994835855569015,
          "validation_mae": 12.556059837341309
        },
        {
          "epoch": 13,
          "train_scaled_mse": 0.1656814523062002,
          "validation_mae": 12.259706497192383
        },
        {
          "epoch": 14,
          "train_scaled_mse": 0.16099312036067331,
          "validation_mae": 12.21622371673584
        },
        {
          "epoch": 15,
          "train_scaled_mse": 0.15670411197421943,
          "validation_mae": 12.175817489624023
        },
        {
          "epoch": 16,
          "train_scaled_mse": 0.153702901017367,
          "validation_mae": 12.153104782104492
        },
        {
          "epoch": 17,
          "train_scaled_mse": 0.14780462755300208,
          "validation_mae": 12.125853538513184
        },
        {
          "epoch": 18,
          "train_scaled_mse": 0.14338332835927314,
          "validation_mae": 11.808982849121094
        },
        {
          "epoch": 19,
          "train_scaled_mse": 0.13954289336390482,
          "validation_mae": 11.93190860748291
        },
        {
          "epoch": 20,
          "train_scaled_mse": 0.13584863359217525,
          "validation_mae": 12.216451644897461
        },
        {
          "epoch": 21,
          "train_scaled_mse": 0.13410135896093,
          "validation_mae": 11.872904777526855
        },
        {
          "epoch": 22,
          "train_scaled_mse": 0.12901808267516346,
          "validation_mae": 11.790862083435059
        },
        {
          "epoch": 23,
          "train_scaled_mse": 0.12636146721401587,
          "validation_mae": 11.573634147644043
        },
        {
          "epoch": 24,
          "train_scaled_mse": 0.12411023736581164,
          "validation_mae": 12.330605506896973
        },
        {
          "epoch": 25,
          "train_scaled_mse": 0.1223132007425874,
          "validation_mae": 11.615228652954102
        },
        {
          "epoch": 26,
          "train_scaled_mse": 0.11847078221173007,
          "validation_mae": 11.783468246459961
        },
        {
          "epoch": 27,
          "train_scaled_mse": 0.11632611098229718,
          "validation_mae": 11.610703468322754
        },
        {
          "epoch": 28,
          "train_scaled_mse": 0.11546672378409872,
          "validation_mae": 12.05544662475586
        },
        {
          "epoch": 29,
          "train_scaled_mse": 0.11528518250144623,
          "validation_mae": 11.869301795959473
        },
        {
          "epoch": 30,
          "train_scaled_mse": 0.11462900357990212,
          "validation_mae": 11.75202465057373
        },
        {
          "epoch": 31,
          "train_scaled_mse": 0.11204702955019508,
          "validation_mae": 12.127717971801758
        },
        {
          "epoch": 32,
          "train_scaled_mse": 0.10891622155489696,
          "validation_mae": 12.287717819213867
        },
        {
          "epoch": 33,
          "train_scaled_mse": 0.10747787034694199,
          "validation_mae": 11.98150634765625
        }
      ]
    },
    {
      "params": {
        "lookback": 168,
        "hidden_size": 64,
        "layers": 1,
        "dropout": 0.0,
        "learning_rate": 0.001,
        "batch_size": 32,
        "epochs": 100,
        "patience": 10
      },
      "best_epoch": 27,
      "validation_mae": 11.664175987243652,
      "epochs": [
        {
          "epoch": 1,
          "train_scaled_mse": 0.636607897148823,
          "validation_mae": 15.95174789428711
        },
        {
          "epoch": 2,
          "train_scaled_mse": 0.29807286923310217,
          "validation_mae": 13.786824226379395
        },
        {
          "epoch": 3,
          "train_scaled_mse": 0.23486978724640392,
          "validation_mae": 13.076519012451172
        },
        {
          "epoch": 4,
          "train_scaled_mse": 0.21200514678171417,
          "validation_mae": 12.978577613830566
        },
        {
          "epoch": 5,
          "train_scaled_mse": 0.20255500613646918,
          "validation_mae": 12.819931983947754
        },
        {
          "epoch": 6,
          "train_scaled_mse": 0.1945962941580164,
          "validation_mae": 13.038799285888672
        },
        {
          "epoch": 7,
          "train_scaled_mse": 0.1863594230337063,
          "validation_mae": 12.572402954101562
        },
        {
          "epoch": 8,
          "train_scaled_mse": 0.18044996631012652,
          "validation_mae": 13.000665664672852
        },
        {
          "epoch": 9,
          "train_scaled_mse": 0.17403175360147002,
          "validation_mae": 12.869450569152832
        },
        {
          "epoch": 10,
          "train_scaled_mse": 0.1674873369815954,
          "validation_mae": 12.551898956298828
        },
        {
          "epoch": 11,
          "train_scaled_mse": 0.16156499540241315,
          "validation_mae": 12.601266860961914
        },
        {
          "epoch": 12,
          "train_scaled_mse": 0.15669598876599813,
          "validation_mae": 12.871657371520996
        },
        {
          "epoch": 13,
          "train_scaled_mse": 0.1510728363539183,
          "validation_mae": 12.76358413696289
        },
        {
          "epoch": 14,
          "train_scaled_mse": 0.14493884378655042,
          "validation_mae": 12.309041023254395
        },
        {
          "epoch": 15,
          "train_scaled_mse": 0.1376998342345352,
          "validation_mae": 12.133285522460938
        },
        {
          "epoch": 16,
          "train_scaled_mse": 0.1322462520559518,
          "validation_mae": 12.169672012329102
        },
        {
          "epoch": 17,
          "train_scaled_mse": 0.12793729012225,
          "validation_mae": 12.03605842590332
        },
        {
          "epoch": 18,
          "train_scaled_mse": 0.12525745105610583,
          "validation_mae": 11.904742240905762
        },
        {
          "epoch": 19,
          "train_scaled_mse": 0.12216515720803757,
          "validation_mae": 11.920485496520996
        },
        {
          "epoch": 20,
          "train_scaled_mse": 0.11823585332685194,
          "validation_mae": 12.272945404052734
        },
        {
          "epoch": 21,
          "train_scaled_mse": 0.11482816988545208,
          "validation_mae": 11.92374324798584
        },
        {
          "epoch": 22,
          "train_scaled_mse": 0.11186986364694027,
          "validation_mae": 12.059263229370117
        },
        {
          "epoch": 23,
          "train_scaled_mse": 0.11003679800830511,
          "validation_mae": 12.118215560913086
        },
        {
          "epoch": 24,
          "train_scaled_mse": 0.11121591317537435,
          "validation_mae": 12.069522857666016
        },
        {
          "epoch": 25,
          "train_scaled_mse": 0.1087800875555174,
          "validation_mae": 11.864794731140137
        },
        {
          "epoch": 26,
          "train_scaled_mse": 0.10384543924942655,
          "validation_mae": 11.98260498046875
        },
        {
          "epoch": 27,
          "train_scaled_mse": 0.10641827355437292,
          "validation_mae": 11.664175987243652
        },
        {
          "epoch": 28,
          "train_scaled_mse": 0.10390427756359318,
          "validation_mae": 12.367294311523438
        },
        {
          "epoch": 29,
          "train_scaled_mse": 0.10176573996756402,
          "validation_mae": 11.920090675354004
        },
        {
          "epoch": 30,
          "train_scaled_mse": 0.099293358374937,
          "validation_mae": 11.874021530151367
        },
        {
          "epoch": 31,
          "train_scaled_mse": 0.09882803377500815,
          "validation_mae": 11.950545310974121
        },
        {
          "epoch": 32,
          "train_scaled_mse": 0.09833816561360213,
          "validation_mae": 12.129135131835938
        },
        {
          "epoch": 33,
          "train_scaled_mse": 0.09581239087750985,
          "validation_mae": 11.885322570800781
        },
        {
          "epoch": 34,
          "train_scaled_mse": 0.0939881663178003,
          "validation_mae": 12.172942161560059
        },
        {
          "epoch": 35,
          "train_scaled_mse": 0.09284871986815524,
          "validation_mae": 11.755125999450684
        },
        {
          "epoch": 36,
          "train_scaled_mse": 0.09349703045774635,
          "validation_mae": 12.160638809204102
        },
        {
          "epoch": 37,
          "train_scaled_mse": 0.09158105008864469,
          "validation_mae": 12.174825668334961
        }
      ]
    },
    {
      "params": {
        "lookback": 168,
        "hidden_size": 32,
        "layers": 2,
        "dropout": 0.1,
        "learning_rate": 0.0005,
        "batch_size": 32,
        "epochs": 100,
        "patience": 10
      },
      "best_epoch": 47,
      "validation_mae": 11.914227485656738,
      "epochs": [
        {
          "epoch": 1,
          "train_scaled_mse": 0.9229602526489407,
          "validation_mae": 20.111366271972656
        },
        {
          "epoch": 2,
          "train_scaled_mse": 0.604378776713002,
          "validation_mae": 17.062082290649414
        },
        {
          "epoch": 3,
          "train_scaled_mse": 0.4046332624463318,
          "validation_mae": 15.917409896850586
        },
        {
          "epoch": 4,
          "train_scaled_mse": 0.31206737786614464,
          "validation_mae": 14.72968578338623
        },
        {
          "epoch": 5,
          "train_scaled_mse": 0.27627056978207115,
          "validation_mae": 14.175006866455078
        },
        {
          "epoch": 6,
          "train_scaled_mse": 0.25070182435359795,
          "validation_mae": 13.736079216003418
        },
        {
          "epoch": 7,
          "train_scaled_mse": 0.23576316104625925,
          "validation_mae": 13.611307144165039
        },
        {
          "epoch": 8,
          "train_scaled_mse": 0.22776913194603243,
          "validation_mae": 13.755234718322754
        },
        {
          "epoch": 9,
          "train_scaled_mse": 0.22163525580695745,
          "validation_mae": 13.790181159973145
        },
        {
          "epoch": 10,
          "train_scaled_mse": 0.21576196577887682,
          "validation_mae": 13.372055053710938
        },
        {
          "epoch": 11,
          "train_scaled_mse": 0.2109770844573762,
          "validation_mae": 13.409977912902832
        },
        {
          "epoch": 12,
          "train_scaled_mse": 0.2075681069601213,
          "validation_mae": 13.314494132995605
        },
        {
          "epoch": 13,
          "train_scaled_mse": 0.20476570484697984,
          "validation_mae": 13.31784439086914
        },
        {
          "epoch": 14,
          "train_scaled_mse": 0.20078224690843757,
          "validation_mae": 13.44048023223877
        },
        {
          "epoch": 15,
          "train_scaled_mse": 0.19709250181498303,
          "validation_mae": 13.408526420593262
        },
        {
          "epoch": 16,
          "train_scaled_mse": 0.1946138799149014,
          "validation_mae": 13.365645408630371
        },
        {
          "epoch": 17,
          "train_scaled_mse": 0.19119663856155694,
          "validation_mae": 13.160901069641113
        },
        {
          "epoch": 18,
          "train_scaled_mse": 0.18907997788326986,
          "validation_mae": 13.29394245147705
        },
        {
          "epoch": 19,
          "train_scaled_mse": 0.18636815324633235,
          "validation_mae": 13.179869651794434
        },
        {
          "epoch": 20,
          "train_scaled_mse": 0.18363278992162774,
          "validation_mae": 13.149413108825684
        },
        {
          "epoch": 21,
          "train_scaled_mse": 0.1812376873904948,
          "validation_mae": 13.092851638793945
        },
        {
          "epoch": 22,
          "train_scaled_mse": 0.17884275989612164,
          "validation_mae": 13.15310287475586
        },
        {
          "epoch": 23,
          "train_scaled_mse": 0.1760401754824232,
          "validation_mae": 13.031947135925293
        },
        {
          "epoch": 24,
          "train_scaled_mse": 0.1734289951975299,
          "validation_mae": 13.043371200561523
        },
        {
          "epoch": 25,
          "train_scaled_mse": 0.1714996346441152,
          "validation_mae": 13.101223945617676
        },
        {
          "epoch": 26,
          "train_scaled_mse": 0.16886417223218425,
          "validation_mae": 12.968805313110352
        },
        {
          "epoch": 27,
          "train_scaled_mse": 0.1660204753072149,
          "validation_mae": 12.943693161010742
        },
        {
          "epoch": 28,
          "train_scaled_mse": 0.16386164895007205,
          "validation_mae": 12.925999641418457
        },
        {
          "epoch": 29,
          "train_scaled_mse": 0.1613669540307648,
          "validation_mae": 12.581347465515137
        },
        {
          "epoch": 30,
          "train_scaled_mse": 0.1594757779727075,
          "validation_mae": 12.52110767364502
        },
        {
          "epoch": 31,
          "train_scaled_mse": 0.156199419315811,
          "validation_mae": 12.469112396240234
        },
        {
          "epoch": 32,
          "train_scaled_mse": 0.15312393312666742,
          "validation_mae": 12.415247917175293
        },
        {
          "epoch": 33,
          "train_scaled_mse": 0.15037331545419347,
          "validation_mae": 12.399433135986328
        },
        {
          "epoch": 34,
          "train_scaled_mse": 0.14702729471961767,
          "validation_mae": 12.392885208129883
        },
        {
          "epoch": 35,
          "train_scaled_mse": 0.14457719065352734,
          "validation_mae": 12.453831672668457
        },
        {
          "epoch": 36,
          "train_scaled_mse": 0.14284107574679394,
          "validation_mae": 12.284964561462402
        },
        {
          "epoch": 37,
          "train_scaled_mse": 0.13938274224156458,
          "validation_mae": 12.132131576538086
        },
        {
          "epoch": 38,
          "train_scaled_mse": 0.1367956723052811,
          "validation_mae": 12.242477416992188
        },
        {
          "epoch": 39,
          "train_scaled_mse": 0.13482167411979526,
          "validation_mae": 12.053892135620117
        },
        {
          "epoch": 40,
          "train_scaled_mse": 0.13272759320427116,
          "validation_mae": 12.240870475769043
        },
        {
          "epoch": 41,
          "train_scaled_mse": 0.13102559214016854,
          "validation_mae": 12.20875072479248
        },
        {
          "epoch": 42,
          "train_scaled_mse": 0.1286585610723097,
          "validation_mae": 12.23114013671875
        },
        {
          "epoch": 43,
          "train_scaled_mse": 0.12804733683720937,
          "validation_mae": 12.368891716003418
        },
        {
          "epoch": 44,
          "train_scaled_mse": 0.12615195377457442,
          "validation_mae": 11.954465866088867
        },
        {
          "epoch": 45,
          "train_scaled_mse": 0.12450998809842347,
          "validation_mae": 12.227063179016113
        },
        {
          "epoch": 46,
          "train_scaled_mse": 0.12361489431439668,
          "validation_mae": 11.933087348937988
        },
        {
          "epoch": 47,
          "train_scaled_mse": 0.1218928271141889,
          "validation_mae": 11.914227485656738
        },
        {
          "epoch": 48,
          "train_scaled_mse": 0.1208114855842338,
          "validation_mae": 11.950457572937012
        },
        {
          "epoch": 49,
          "train_scaled_mse": 0.11986428117353604,
          "validation_mae": 11.987549781799316
        },
        {
          "epoch": 50,
          "train_scaled_mse": 0.11858668607921653,
          "validation_mae": 12.184070587158203
        },
        {
          "epoch": 51,
          "train_scaled_mse": 0.11772568216728965,
          "validation_mae": 12.209230422973633
        },
        {
          "epoch": 52,
          "train_scaled_mse": 0.11644961927760611,
          "validation_mae": 12.096687316894531
        },
        {
          "epoch": 53,
          "train_scaled_mse": 0.1163408488740828,
          "validation_mae": 11.939803123474121
        },
        {
          "epoch": 54,
          "train_scaled_mse": 0.11556402990246882,
          "validation_mae": 12.034262657165527
        },
        {
          "epoch": 55,
          "train_scaled_mse": 0.11445414235498912,
          "validation_mae": 12.109557151794434
        },
        {
          "epoch": 56,
          "train_scaled_mse": 0.11281299090900129,
          "validation_mae": 12.123868942260742
        },
        {
          "epoch": 57,
          "train_scaled_mse": 0.11205363823593825,
          "validation_mae": 11.928356170654297
        }
      ]
    }
  ],
  "selected": {
    "lookback": 48,
    "hidden_size": 32,
    "layers": 1,
    "dropout": 0.0,
    "learning_rate": 0.001,
    "batch_size": 32,
    "epochs": 100,
    "patience": 10
  }
}
