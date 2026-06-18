Root generated-log + scratch retirement note (2026-06-18, Lane 8 repo hygiene).

These artifacts were tracked at the repository root but are generated/scratch output,
not operator entry-surface files. Per `docs/root-surface-policy.md` they are classified
and relocated here (not deleted); their original root paths are now gitignored so
regenerated copies stay untracked.

Classification and rationale per family:

- `.project6_api_stdout.log`, `.project6_api_stderr.log` — generated report / local-only
  scratch. Stdout/stderr captured by `project6.ps1` when launching the local API harness;
  regenerated on each run. Retained here as a historical snapshot.
- `corpus_closure.log`, `corpus_verify.log`, `corpus_diagnostics_final.log`,
  `corpus_diagnostics_patch.log`, `corpus_diagnostics_patch2.log`,
  `corpus_diagnostics_v2.log` — generated report. Corpus diagnostic run output produced by
  the corpus diagnostics tooling; retained as historical evidence.
- `setup_logs/phase7a_py311_setup_20260313_235122.log`,
  `setup_logs/phase7a_py311_setup_20260314_010000.log` — generated report. Python 3.11
  environment-setup logs from the phase7a setup runs (March 2026); historical evidence.
- `temp_session.json` — local-only scratch. A transient session capture; retained as
  historical evidence rather than deleted.

Active behavior is unaffected: nothing in source or tests reads these committed paths as
inputs (`tests/test_inspect_harness_logs.py` writes its own fixtures to a temp dir).
