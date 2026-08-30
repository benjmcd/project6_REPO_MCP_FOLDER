# ScienceBase instrument-class acquisitions

Provenance-safe live acquisitions of the public germanium CSV (asserted CC0-1.0; license_source=asserted, not independently confirmed this run) (DOI 10.5066/P9WCYUI6, ScienceBase item 63d1a3c6d34e06fef15006be, mcs2023-germa_salient.csv) via scripts/sciencebase-instrument-acquisition.ps1.

- artifact/ : the acquired CSV (510 B, sha256 c8eacb7b...930c, 13-column MCS-2023 germanium contract).
- <run-id>/acquisition-record.json : durable provenance per run (3 stages, all HTTP 200 / no redirect, per-stage shas, no credential, verbatim owner token, reviewer, source commit).

Runs: 20260830T163609868Z (initial acquisition), 20260830T170556947Z (M8 repeatability).

No one-use-signature / AppContainer / spent-marker ceremony (right-sized for this public, no-credential target). Raw stage bodies/headers retained out-of-repo under the run roots as provenance evidence.

## Status: TERMINAL (2026-08-30)

This lane is declared TERMINAL by owner ruling. The artifact + provenance records here are the terminal work product of the ScienceBase public-target acquisition: connector-origin bytes with provenance intact, in git custody. The full signed-GO harness (Attempt-5 packet, sitting runbook, etc.) is preserved and earmarked for the credentialed NRC acquisition-#2; the one-use owner signature was never used (a public CC0 no-credential fetch needed none). M7 (Layer-3 handoff) was assessed NOT-READY/ill-defined and not started.

