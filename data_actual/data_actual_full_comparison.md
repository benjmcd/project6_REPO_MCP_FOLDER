# data_actual Full Evaluation Comparison

Generated: 2026-03-09 12:41:55 -07:00
Input archives: mcs2024.zip, mcs2025.zip, mcs2026.zip
Run scope: full corpus (`--max-files 0`)

## Overall summary

| method | files | upload_200 | profile_200 | recommend_200 | transform_ok_(200_or_204) | analysis_200 | runs_with_artifacts | total_artifacts | avg_caveats | avg_assumptions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_correlation | 320 | 319 | 319 | 319 | 319 | 319 | 294 | 588 | 1.08 | 1.99 |
| decomposition | 320 | 319 | 319 | 319 | 319 | 319 | 0 | 0 | 7.16 | 18.48 |
| structural_break | 320 | 319 | 319 | 319 | 319 | 319 | 11 | 62 | 8 | 12.32 |

## Artifact yield by method

- **cross_correlation**: 294 / 320 runs produced artifacts (91.88%).
  Artifact type distribution:
  - cross_correlation_plot,cross_correlation_result: 294
  - <none>: 26
- **decomposition**: 0 / 320 runs produced artifacts (0%).
  Artifact type distribution:
  - <none>: 320
- **structural_break**: 11 / 320 runs produced artifacts (3.44%).
  Artifact type distribution:
  - <none>: 309
  - structural_break_plot,structural_break_result: 11

## By archive (analysis_200 and artifact-producing runs)

### cross_correlation

| archive | files | analysis_200 | runs_with_artifacts |
| --- | ---: | ---: | ---: |
| mcs2024.zip | 206 | 206 | 192 |
| mcs2025.zip | 98 | 98 | 94 |
| mcs2026.zip | 16 | 15 | 8 |

### decomposition

| archive | files | analysis_200 | runs_with_artifacts |
| --- | ---: | ---: | ---: |
| mcs2024.zip | 206 | 206 | 0 |
| mcs2025.zip | 98 | 98 | 0 |
| mcs2026.zip | 16 | 15 | 0 |

### structural_break

| archive | files | analysis_200 | runs_with_artifacts |
| --- | ---: | ---: | ---: |
| mcs2024.zip | 206 | 206 | 6 |
| mcs2025.zip | 98 | 98 | 2 |
| mcs2026.zip | 16 | 15 | 3 |

## By bucket (analysis_200 and artifact-producing runs)

### cross_correlation

| bucket | files | analysis_200 | runs_with_artifacts |
| --- | ---: | ---: | ---: |
| other | 3 | 2 | 0 |
| salient | 178 | 178 | 178 |
| trends_figures | 59 | 59 | 37 |
| world | 80 | 80 | 78 |

### decomposition

| bucket | files | analysis_200 | runs_with_artifacts |
| --- | ---: | ---: | ---: |
| other | 3 | 2 | 0 |
| salient | 178 | 178 | 0 |
| trends_figures | 59 | 59 | 0 |
| world | 80 | 80 | 0 |

### structural_break

| bucket | files | analysis_200 | runs_with_artifacts |
| --- | ---: | ---: | ---: |
| other | 3 | 2 | 0 |
| salient | 178 | 178 | 5 |
| trends_figures | 59 | 59 | 6 |
| world | 80 | 80 | 0 |

## Notes

- Each method encountered one upload failure (`400`) out of 320 files; all successfully uploaded files completed analysis with `200`.
- Profiling emitted frequent KPSS interpolation warnings; runs still completed for successful uploads.
- Decomposition and structural-break methods remain constrained by observation-length and regularity prerequisites, so many runs are caveat-only.
- Consistent upload failure across all three runs:
  - `mcs2026.zip -> commodities/unknown/MCS2026_Commodities_Data.csv`
  - parse error: `utf-8` decode failure (`byte 0x97`), indicating a non-UTF-8 CSV encoding.

