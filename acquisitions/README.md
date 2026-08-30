# ScienceBase instrument-class acquisitions

Provenance-safe live acquisitions of the public CC0 germanium CSV (DOI 10.5066/P9WCYUI6, ScienceBase item 63d1a3c6d34e06fef15006be, mcs2023-germa_salient.csv) via scripts/sciencebase-instrument-acquisition.ps1.

- artifact/ : the acquired CSV (510 B, sha256 c8eacb7b...930c, 13-column MCS-2023 germanium contract).
- <run-id>/acquisition-record.json : durable provenance per run (3 stages, all HTTP 200 / no redirect, per-stage shas, no credential, verbatim owner token, reviewer, source commit).

Runs: 20260830T163609868Z (initial acquisition), 20260830T170556947Z (M8 repeatability).

No one-use-signature / AppContainer / spent-marker ceremony (right-sized for this public, no-credential target). Raw stage bodies/headers retained out-of-repo under the run roots as provenance evidence.
