# data_actual Notes

This folder contains local input archives for evaluating the Project6 ingestion and analysis flow.

## Contents

- `mcs2024.zip`
- `mcs2025.zip`
- `mcs2026.zip`
- `MCS_FILESDATA_RETRIEVAL&ORGANIZATION.txt` (reference only)

## Reference file intent

The retrieval code in `MCS_FILESDATA_RETRIEVAL&ORGANIZATION.txt` is reference material only and is not integrated into backend/runtime code.

## Quick inventory snapshot

- `mcs2024.zip`: 399 entries, 206 CSV, 93 XML
- `mcs2025.zip`: 283 entries, 98 CSV, 86 XML
- `mcs2026.zip`: 26 entries, 16 CSV, 2 XML

## Run evaluator against this folder

From repo root (with Python env active):

```powershell
py -3.12 tools\run_attached_dataset_eval.py --method-name cross_correlation --data-root data_actual --max-files 30 --seed 7 --output-prefix mcs_smoke_cc
```

Outputs are written to `data_actual/` by default (`.json`, `.csv`, `.md`) unless `--output-dir` is provided.


## Latest baseline runs (2026-03-09)

Executed from repo root:

```powershell
py -3.12 tools\run_attached_dataset_eval.py --method-name cross_correlation --data-root data_actual --max-files 30 --seed 7 --output-prefix data_actual_sample30_cc
py -3.12 tools\run_attached_dataset_eval.py --method-name decomposition --data-root data_actual --max-files 30 --seed 7 --output-prefix data_actual_sample30_decomp
py -3.12 tools\run_attached_dataset_eval.py --method-name structural_break --data-root data_actual --max-files 30 --seed 7 --output-prefix data_actual_sample30_break
```

Summary from generated CSV outputs:

- `cross_correlation`: 30/30 upload and analysis success, 27 runs with artifacts, 3 runs without artifacts.
- `decomposition`: 30/30 upload and analysis success, 0 runs with artifacts, 30 caveat-only runs on this sample.
- `structural_break`: 30/30 upload and analysis success, 2 runs with artifacts, 28 caveat-only runs.

Output files written to this folder:

- `data_actual_sample30_cc.json`, `.csv`, `.md`
- `data_actual_sample30_decomp.json`, `.csv`, `.md`
- `data_actual_sample30_break.json`, `.csv`, `.md`


## Full corpus runs (2026-03-09)

Executed:

```powershell
py -3.12 tools\run_attached_dataset_eval.py --method-name cross_correlation --data-root data_actual --max-files 0 --output-prefix data_actual_full_cc
py -3.12 tools\run_attached_dataset_eval.py --method-name decomposition --data-root data_actual --max-files 0 --output-prefix data_actual_full_decomp
py -3.12 tools\run_attached_dataset_eval.py --method-name structural_break --data-root data_actual --max-files 0 --output-prefix data_actual_full_break
```

Consolidated report:

- `data_actual_full_comparison.md`

Top-level outcomes:

- 320 CSV targets discovered.
- 319 uploaded successfully per method.
- 1 recurring upload failure (same file in all methods):
  - `mcs2026.zip -> commodities/unknown/MCS2026_Commodities_Data.csv`
  - error: UTF-8 decode failure (`byte 0x97`), likely non-UTF-8 encoding.

Artifact yield:

- `cross_correlation`: 294 runs with artifacts (588 artifacts total).
- `decomposition`: 0 runs with artifacts (caveat-only on this corpus).
- `structural_break`: 11 runs with artifacts (62 artifacts total).


## Post-encoding-fix full corpus rerun (2026-03-09)

After adding CSV encoding fallback (`utf-8`, `utf-8-sig`, `cp1252`, `latin1`) in ingestion, full-corpus runs were re-executed:

```powershell
py -3.12 tools\run_attached_dataset_eval.py --method-name cross_correlation --data-root data_actual --max-files 0 --output-prefix data_actual_full_cc_post_encoding_fix
py -3.12 tools\run_attached_dataset_eval.py --method-name decomposition --data-root data_actual --max-files 0 --output-prefix data_actual_full_decomp_post_encoding_fix
py -3.12 tools\run_attached_dataset_eval.py --method-name structural_break --data-root data_actual --max-files 0 --output-prefix data_actual_full_break_post_encoding_fix
```

Updated consolidated report:

- `data_actual_full_comparison_post_encoding_fix.md`

Updated outcomes (supersedes prior 319/320 upload note):

- 320 CSV targets discovered.
- 320 uploaded successfully per method.
- Previously failing file now ingests successfully:
  - `mcs2026.zip -> commodities/unknown/MCS2026_Commodities_Data.csv`

Artifact yield (post-fix full rerun):

- `cross_correlation`: 294 runs with artifacts (588 artifacts total).
- `decomposition`: 0 runs with artifacts (caveat-only on this corpus).
- `structural_break`: 12 runs with artifacts (64 artifacts total).

