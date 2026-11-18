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
      "best_epoch": 22,
      "validation_mae": 12.881725311279297,
      "epochs": [
        {
          "epoch": 1,
          "train_scaled_mse": 0.6605491116850489,
          "validation_mae": 20.65030860900879
        },
        {
          "epoch": 2,
          "train_scaled_mse": 0.3196873067149213,
          "validation_mae": 17.63465690612793
        },
        {
          "epoch": 3,
          "train_scaled_mse": 0.2502912599230211,
          "validation_mae": 16.503170013427734
        },
        {
          "epoch": 4,
          "train_scaled_mse": 0.22179025988558873,
          "validation_mae": 17.146575927734375
        },
        {
          "epoch": 5,
          "train_scaled_mse": 0.2105782870462678,
          "validation_mae": 17.496444702148438
        },
        {
          "epoch": 6,
          "train_scaled_mse": 0.20198841779012866,
          "validation_mae": 16.4789981842041
        },
        {
          "epoch": 7,
          "train_scaled_mse": 0.19456731069386834,
          "validation_mae": 15.34718132019043
        },
        {
          "epoch": 8,
          "train_scaled_mse": 0.1890799471677844,
          "validation_mae": 15.69556713104248
        },
        {
          "epoch": 9,
          "train_scaled_mse": 0.1831776386017919,
          "validation_mae": 15.49659538269043
        },
        {
          "epoch": 10,
          "train_scaled_mse": 0.17786550094324236,
          "validation_mae": 14.506071090698242
        },
        {
          "epoch": 11,
          "train_scaled_mse": 0.172781889236073,
          "validation_mae": 15.19087028503418
        },
        {
          "epoch": 12,
          "train_scaled_mse": 0.1680912837842713,
          "validation_mae": 14.656638145446777
        },
        {
          "epoch": 13,
          "train_scaled_mse": 0.16404415621398882,
          "validation_mae": 13.707898139953613
        },
        {
          "epoch": 14,
          "train_scaled_mse": 0.1596495674347147,
          "validation_mae": 13.922487258911133
        },
        {
          "epoch": 15,
          "train_scaled_mse": 0.15583127081228165,
          "validation_mae": 13.818018913269043
        },
        {
          "epoch": 16,
          "train_scaled_mse": 0.1517038128668219,
          "validation_mae": 14.007427215576172
        },
        {
          "epoch": 17,
          "train_scaled_mse": 0.14614972754441263,
          "validation_mae": 13.274940490722656
        },
        {
          "epoch": 18,
          "train_scaled_mse": 0.142519516159565,
          "validation_mae": 14.33220100402832
        },
        {
          "epoch": 19,
          "train_scaled_mse": 0.14001628320695297,
          "validation_mae": 13.672539710998535
        },
        {
          "epoch": 20,
          "train_scaled_mse": 0.1362810880360829,
          "validation_mae": 13.661641120910645
        },
        {
          "epoch": 21,
          "train_scaled_mse": 0.13405800438524954,
          "validation_mae": 14.369539260864258
        },
        {
          "epoch": 22,
          "train_scaled_mse": 0.12885345437649565,
          "validation_mae": 12.881725311279297
        },
        {
          "epoch": 23,
          "train_scaled_mse": 0.12546496126479093,
          "validation_mae": 13.387054443359375
        },
        {
          "epoch": 24,
          "train_scaled_mse": 0.1231025339916224,
          "validation_mae": 14.209224700927734
        },
        {
          "epoch": 25,
          "train_scaled_mse": 0.1206809245361259,
          "validation_mae": 13.687357902526855
        },
        {
          "epoch": 26,
          "train_scaled_mse": 0.11766640372927142,
          "validation_mae": 14.180671691894531
        },
        {
          "epoch": 27,
          "train_scaled_mse": 0.11638675476515194,
          "validation_mae": 13.997645378112793
        },
        {
          "epoch": 28,
          "train_scaled_mse": 0.11579720094841503,
          "validation_mae": 13.81128978729248
        },
        {
          "epoch": 29,
          "train_scaled_mse": 0.1140551882533974,
          "validation_mae": 13.233414649963379
        },
        {
          "epoch": 30,
          "train_scaled_mse": 0.11314625863743359,
          "validation_mae": 13.541057586669922
        },
        {
          "epoch": 31,
          "train_scaled_mse": 0.11101358450305827,
          "validation_mae": 13.005496978759766
        },
        {
          "epoch": 32,
          "train_scaled_mse": 0.10834557224781068,
          "validation_mae": 13.118989944458008
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
      "best_epoch": 25,
      "validation_mae": 13.109661102294922,
      "epochs": [
        {
          "epoch": 1,
          "train_scaled_mse": 0.6303462784602449,
          "validation_mae": 17.326351165771484
        },
        {
          "epoch": 2,
          "train_scaled_mse": 0.2960937773616865,
          "validation_mae": 15.482430458068848
        },
        {
          "epoch": 3,
          "train_scaled_mse": 0.23555102433832906,
          "validation_mae": 14.401422500610352
        },
        {
          "epoch": 4,
          "train_scaled_mse": 0.21164700583993226,
          "validation_mae": 14.790688514709473
        },
        {
          "epoch": 5,
          "train_scaled_mse": 0.20064112004463386,
          "validation_mae": 15.174256324768066
        },
        {
          "epoch": 6,
          "train_scaled_mse": 0.19252138840122807,
          "validation_mae": 14.98827838897705
        },
        {
          "epoch": 7,
          "train_scaled_mse": 0.18437113320262982,
          "validation_mae": 14.058821678161621
        },
        {
          "epoch": 8,
          "train_scaled_mse": 0.1786277892695828,
          "validation_mae": 15.11086654663086
        },
        {
          "epoch": 9,
          "train_scaled_mse": 0.1718114525660831,
          "validation_mae": 15.141161918640137
        },
        {
          "epoch": 10,
          "train_scaled_mse": 0.16644917357930897,
          "validation_mae": 14.859545707702637
        },
        {
          "epoch": 11,
          "train_scaled_mse": 0.16012140664383562,
          "validation_mae": 14.80047607421875
        },
        {
          "epoch": 12,
          "train_scaled_mse": 0.15442607786330007,
          "validation_mae": 14.598692893981934
        },
        {
          "epoch": 13,
          "train_scaled_mse": 0.1482624792205922,
          "validation_mae": 14.166805267333984
        },
        {
          "epoch": 14,
          "train_scaled_mse": 0.14295314086346905,
          "validation_mae": 14.170234680175781
        },
        {
          "epoch": 15,
          "train_scaled_mse": 0.1376422770051571,
          "validation_mae": 14.0352144241333
        },
        {
          "epoch": 16,
          "train_scaled_mse": 0.13163160227633453,
          "validation_mae": 13.999093055725098
        },
        {
          "epoch": 17,
          "train_scaled_mse": 0.1274521238790581,
          "validation_mae": 14.095026969909668
        },
        {
          "epoch": 18,
          "train_scaled_mse": 0.12368304226391827,
          "validation_mae": 13.677264213562012
        },
        {
          "epoch": 19,
          "train_scaled_mse": 0.12018270336070765,
          "validation_mae": 13.42522144317627
        },
        {
          "epoch": 20,
          "train_scaled_mse": 0.11684370262958213,
          "validation_mae": 13.345916748046875
        },
        {
          "epoch": 21,
          "train_scaled_mse": 0.11442547160768908,
          "validation_mae": 13.7848482131958
        },
        {
          "epoch": 22,
          "train_scaled_mse": 0.11308481062770222,
          "validation_mae": 13.369946479797363
        },
        {
          "epoch": 23,
          "train_scaled_mse": 0.11086824644242821,
          "validation_mae": 13.3784818649292
        },
        {
          "epoch": 24,
          "train_scaled_mse": 0.11003449733542865,
          "validation_mae": 15.078886032104492
        },
        {
          "epoch": 25,
          "train_scaled_mse": 0.11143953961250178,
          "validation_mae": 13.109661102294922
        },
        {
          "epoch": 26,
          "train_scaled_mse": 0.10526074190989843,
          "validation_mae": 14.234214782714844
        },
        {
          "epoch": 27,
          "train_scaled_mse": 0.10188542754703245,
          "validation_mae": 13.352164268493652
        },
        {
          "epoch": 28,
          "train_scaled_mse": 0.10205265860952707,
          "validation_mae": 13.844786643981934
        },
        {
          "epoch": 29,
          "train_scaled_mse": 0.10029375310312738,
          "validation_mae": 13.24154281616211
        },
        {
          "epoch": 30,
          "train_scaled_mse": 0.09847204957914883,
          "validation_mae": 13.584752082824707
        },
        {
          "epoch": 31,
          "train_scaled_mse": 0.09851888606641286,
          "validation_mae": 14.045879364013672
        },
        {
          "epoch": 32,
          "train_scaled_mse": 0.09813391008416922,
          "validation_mae": 13.643129348754883
        },
        {
          "epoch": 33,
          "train_scaled_mse": 0.09432416151908114,
          "validation_mae": 14.255372047424316
        },
        {
          "epoch": 34,
          "train_scaled_mse": 0.0922832525125121,
          "validation_mae": 14.055747032165527
        },
        {
          "epoch": 35,
          "train_scaled_mse": 0.09075932125859273,
          "validation_mae": 14.181639671325684
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
      "best_epoch": 67,
      "validation_mae": 13.47233772277832,
      "epochs": [
        {
          "epoch": 1,
          "train_scaled_mse": 0.9285931623745761,
          "validation_mae": 24.236886978149414
        },
        {
          "epoch": 2,
          "train_scaled_mse": 0.6006116767447639,
          "validation_mae": 20.529693603515625
        },
        {
          "epoch": 3,
          "train_scaled_mse": 0.3992007570678477,
          "validation_mae": 17.873912811279297
        },
        {
          "epoch": 4,
          "train_scaled_mse": 0.3105690620403768,
          "validation_mae": 17.75798225402832
        },
        {
          "epoch": 5,
          "train_scaled_mse": 0.2763933215632744,
          "validation_mae": 18.153316497802734
        },
        {
          "epoch": 6,
          "train_scaled_mse": 0.25036384252452587,
          "validation_mae": 18.022478103637695
        },
        {
          "epoch": 7,
          "train_scaled_mse": 0.2355014484240816,
          "validation_mae": 17.104822158813477
        },
        {
          "epoch": 8,
          "train_scaled_mse": 0.22607811529988367,
          "validation_mae": 17.97821044921875
        },
        {
          "epoch": 9,
          "train_scaled_mse": 0.21920899552887196,
          "validation_mae": 17.879716873168945
        },
        {
          "epoch": 10,
          "train_scaled_mse": 0.21301922185507324,
          "validation_mae": 16.871196746826172
        },
        {
          "epoch": 11,
          "train_scaled_mse": 0.2082839628116002,
          "validation_mae": 16.695337295532227
        },
        {
          "epoch": 12,
          "train_scaled_mse": 0.20519575036667848,
          "validation_mae": 17.065824508666992
        },
        {
          "epoch": 13,
          "train_scaled_mse": 0.2020342649689624,
          "validation_mae": 17.435029983520508
        },
        {
          "epoch": 14,
          "train_scaled_mse": 0.1977276820741324,
          "validation_mae": 17.575275421142578
        },
        {
          "epoch": 15,
          "train_scaled_mse": 0.19452432026272032,
          "validation_mae": 17.20932388305664
        },
        {
          "epoch": 16,
          "train_scaled_mse": 0.19186789992792028,
          "validation_mae": 16.9887752532959
        },
        {
          "epoch": 17,
          "train_scaled_mse": 0.18876857657120422,
          "validation_mae": 16.742969512939453
        },
        {
          "epoch": 18,
          "train_scaled_mse": 0.18694786847799932,
          "validation_mae": 16.866233825683594
        },
        {
          "epoch": 19,
          "train_scaled_mse": 0.1840395677554574,
          "validation_mae": 16.883848190307617
        },
        {
          "epoch": 20,
          "train_scaled_mse": 0.18133405635449878,
          "validation_mae": 16.467782974243164
        },
        {
          "epoch": 21,
          "train_scaled_mse": 0.17919206943020516,
          "validation_mae": 16.760499954223633
        },
        {
          "epoch": 22,
          "train_scaled_mse": 0.17653513838819807,
          "validation_mae": 16.577177047729492
        },
        {
          "epoch": 23,
          "train_scaled_mse": 0.17419639047141858,
          "validation_mae": 16.73831558227539
        },
        {
          "epoch": 24,
          "train_scaled_mse": 0.17181311763594742,
          "validation_mae": 16.259016036987305
        },
        {
          "epoch": 25,
          "train_scaled_mse": 0.16986877635162853,
          "validation_mae": 16.26944351196289
        },
        {
          "epoch": 26,
          "train_scaled_mse": 0.16745772912143664,
          "validation_mae": 16.110092163085938
        },
        {
          "epoch": 27,
          "train_scaled_mse": 0.16454098728539884,
          "validation_mae": 16.651121139526367
        },
        {
          "epoch": 28,
          "train_scaled_mse": 0.16247709452441808,
          "validation_mae": 16.310155868530273
        },
        {
          "epoch": 29,
          "train_scaled_mse": 0.16009896175941052,
          "validation_mae": 15.898347854614258
        },
        {
          "epoch": 30,
          "train_scaled_mse": 0.15839450526204282,
          "validation_mae": 15.50615406036377
        },
        {
          "epoch": 31,
          "train_scaled_mse": 0.15553706971549722,
          "validation_mae": 15.45318603515625
        },
        {
          "epoch": 32,
          "train_scaled_mse": 0.15302810919650087,
          "validation_mae": 15.553994178771973
        },
        {
          "epoch": 33,
          "train_scaled_mse": 0.15023861646984282,
          "validation_mae": 15.823222160339355
        },
        {
          "epoch": 34,
          "train_scaled_mse": 0.14767377288145608,
          "validation_mae": 15.777612686157227
        },
        {
          "epoch": 35,
          "train_scaled_mse": 0.14516065334045122,
          "validation_mae": 15.463725090026855
        },
        {
          "epoch": 36,
          "train_scaled_mse": 0.14313793213503606,
          "validation_mae": 16.022624969482422
        },
        {
          "epoch": 37,
          "train_scaled_mse": 0.1407080774810321,
          "validation_mae": 15.17333698272705
        },
        {
          "epoch": 38,
          "train_scaled_mse": 0.13845911036792904,
          "validation_mae": 14.902219772338867
        },
        {
          "epoch": 39,
          "train_scaled_mse": 0.13614700572736416,
          "validation_mae": 14.91147518157959
        },
        {
          "epoch": 40,
          "train_scaled_mse": 0.1341936706168406,
          "validation_mae": 14.802002906799316
        },
        {
          "epoch": 41,
          "train_scaled_mse": 0.13244075180760334,
          "validation_mae": 15.06435775756836
        },
        {
          "epoch": 42,
          "train_scaled_mse": 0.13066604036142568,
          "validation_mae": 15.55971622467041
        },
        {
          "epoch": 43,
          "train_scaled_mse": 0.1295068198425856,
          "validation_mae": 15.009747505187988
        },
        {
          "epoch": 44,
          "train_scaled_mse": 0.1272649403900157,
          "validation_mae": 14.248831748962402
        },
        {
          "epoch": 45,
          "train_scaled_mse": 0.12541551327638972,
          "validation_mae": 14.783721923828125
        },
        {
          "epoch": 46,
          "train_scaled_mse": 0.12469828512758266,
          "validation_mae": 14.655574798583984
        },
        {
          "epoch": 47,
          "train_scaled_mse": 0.12259946441833024,
          "validation_mae": 14.614465713500977
        },
        {
          "epoch": 48,
          "train_scaled_mse": 0.12140202414358559,
          "validation_mae": 14.442794799804688
        },
        {
          "epoch": 49,
          "train_scaled_mse": 0.12014023295518084,
          "validation_mae": 14.6105318069458
        },
        {
          "epoch": 50,
          "train_scaled_mse": 0.11947341939865048,
          "validation_mae": 14.487102508544922
        },
        {
          "epoch": 51,
          "train_scaled_mse": 0.11807556547909394,
          "validation_mae": 14.246753692626953
        },
        {
          "epoch": 52,
          "train_scaled_mse": 0.11682068867852761,
          "validation_mae": 14.569426536560059
        },
        {
          "epoch": 53,
          "train_scaled_mse": 0.11720558531935169,
          "validation_mae": 14.660406112670898
        },
        {
          "epoch": 54,
          "train_scaled_mse": 0.11660022533454603,
          "validation_mae": 14.680732727050781
        },
        {
          "epoch": 55,
          "train_scaled_mse": 0.11471303652006935,
          "validation_mae": 14.321290016174316
        },
        {
          "epoch": 56,
          "train_scaled_mse": 0.11331342171078605,
          "validation_mae": 14.62175464630127
        },
        {
          "epoch": 57,
          "train_scaled_mse": 0.1123088115520132,
          "validation_mae": 14.163785934448242
        },
        {
          "epoch": 58,
          "train_scaled_mse": 0.1115781419331981,
          "validation_mae": 13.883103370666504
        },
        {
          "epoch": 59,
          "train_scaled_mse": 0.11130068930576771,
          "validation_mae": 14.19774055480957
        },
        {
          "epoch": 60,
          "train_scaled_mse": 0.1109149965735199,
          "validation_mae": 14.129335403442383
        },
        {
          "epoch": 61,
          "train_scaled_mse": 0.10939607501528058,
          "validation_mae": 13.923466682434082
        },
        {
          "epoch": 62,
          "train_scaled_mse": 0.10869469952284459,
          "validation_mae": 13.642895698547363
        },
        {
          "epoch": 63,
          "train_scaled_mse": 0.1084313580460203,
          "validation_mae": 13.920802116394043
        },
        {
          "epoch": 64,
          "train_scaled_mse": 0.10712697265623007,
          "validation_mae": 14.045347213745117
        },
        {
          "epoch": 65,
          "train_scaled_mse": 0.1068860761675994,
          "validation_mae": 14.126988410949707
        },
        {
          "epoch": 66,
          "train_scaled_mse": 0.10609097718611402,
          "validation_mae": 14.273599624633789
        },
        {
          "epoch": 67,
          "train_scaled_mse": 0.10621010503812088,
          "validation_mae": 13.47233772277832
        },
        {
          "epoch": 68,
          "train_scaled_mse": 0.10628950471333475,
          "validation_mae": 13.787498474121094
        },
        {
          "epoch": 69,
          "train_scaled_mse": 0.10454581881299989,
          "validation_mae": 13.840917587280273
        },
        {
          "epoch": 70,
          "train_scaled_mse": 0.10369453462966638,
          "validation_mae": 13.898148536682129
        },
        {
          "epoch": 71,
          "train_scaled_mse": 0.1037408900875235,
          "validation_mae": 13.870941162109375
        },
        {
          "epoch": 72,
          "train_scaled_mse": 0.1026918025152929,
          "validation_mae": 13.923253059387207
        },
        {
          "epoch": 73,
          "train_scaled_mse": 0.10227853246552035,
          "validation_mae": 14.0510892868042
        },
        {
          "epoch": 74,
          "train_scaled_mse": 0.10235084041247461,
          "validation_mae": 13.785022735595703
        },
        {
          "epoch": 75,
          "train_scaled_mse": 0.1013593372984849,
          "validation_mae": 13.815237998962402
        },
        {
          "epoch": 76,
          "train_scaled_mse": 0.10114856915221573,
          "validation_mae": 13.594249725341797
        },
        {
          "epoch": 77,
          "train_scaled_mse": 0.10098265321058815,
          "validation_mae": 13.789304733276367
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
