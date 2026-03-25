# data_actual Full Evaluation Comparison (Post Encoding Fix)

Generated: 2026-03-09 12:47:50 -07:00
Input archives: mcs2024.zip, mcs2025.zip, mcs2026.zip
Run scope: full corpus (`--max-files 0`) after CSV encoding fallback patch

## Overall summary

| method | files | upload_200 | profile_200 | recommend_200 | transform_ok_(200_or_204) | analysis_200 | runs_with_artifacts | total_artifacts | avg_caveats | avg_assumptions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_correlation | 320 | 320 | 320 | 320 | 320 | 320 | 294 | 588 | 1.08 | 2 |
| decomposition | 320 | 320 | 320 | 320 | 320 | 320 | 0 | 0 | 7.16 | 18.49 |
| structural_break | 320 | 320 | 320 | 320 | 320 | 320 | 12 | 64 | 8.01 | 12.32 |

## Artifact yield by method

- **cross_correlation**: 294 / 320 runs produced artifacts (91.88%).
  Artifact type distribution:
  - cross_correlation_plot,cross_correlation_result: 294
  - <none>: 26
- **decomposition**: 0 / 320 runs produced artifacts (0%).
  Artifact type distribution:
  - <none>: 320
- **structural_break**: 12 / 320 runs produced artifacts (3.75%).
  Artifact type distribution:
  - <none>: 308
  - structural_break_plot,structural_break_result: 12

## By archive (analysis_200 and artifact-producing runs)

### cross_correlation

| archive | files | analysis_200 | runs_with_artifacts |
| --- | ---: | ---: | ---: |
| mcs2024.zip | 206 | 206 | 192 |
| mcs2025.zip | 98 | 98 | 94 |
| mcs2026.zip | 16 | 16 | 8 |

### decomposition

| archive | files | analysis_200 | runs_with_artifacts |
| --- | ---: | ---: | ---: |
| mcs2024.zip | 206 | 206 | 0 |
| mcs2025.zip | 98 | 98 | 0 |
| mcs2026.zip | 16 | 16 | 0 |

### structural_break

| archive | files | analysis_200 | runs_with_artifacts |
| --- | ---: | ---: | ---: |
| mcs2024.zip | 206 | 206 | 6 |
| mcs2025.zip | 98 | 98 | 2 |
| mcs2026.zip | 16 | 16 | 4 |

## Notes

- CSV encoding fallback eliminated the prior `mcs2026` upload decode failure; uploads are now 320/320 on all three method runs.
- Profiling still emits frequent KPSS interpolation warnings; runs completed successfully.
- Decomposition and structural-break methods remain constrained by observation-length and regularity prerequisites, so many runs are caveat-only.
