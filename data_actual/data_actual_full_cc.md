# Attached Dataset Evaluation - cross_correlation

Total CSV files evaluated: 320

- upload_status: {200: 319, 400: 1}
- profile_status: {-1: 1, 200: 319}
- recommend_status: {-1: 1, 200: 319}
- transform_status: {-1: 1, 200: 311, 204: 8}
- analysis_status: {-1: 1, 200: 319}

## By bucket

| bucket         |   upload_200 |   analysis_200 |
|:---------------|-------------:|---------------:|
| other          |            2 |              2 |
| salient        |          178 |            178 |
| trends_figures |           59 |             59 |
| world          |           80 |             80 |

## Remaining non-200 analysis cases

| archive     | file                                             |   analysis_status | error                                                                                                      |
|:------------|:-------------------------------------------------|------------------:|:-----------------------------------------------------------------------------------------------------------|
| mcs2026.zip | commodities/unknown/MCS2026_Commodities_Data.csv |               nan | {"detail":"unable to parse CSV: 'utf-8' codec can't decode byte 0x97 in position 170: invalid start byte"} |