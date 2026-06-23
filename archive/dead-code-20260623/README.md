# Dead-code archive, 2026-06-23

Files preserved here were removed from the live root/test surface during L5 of
M-PROJECT6-DERISK. Each was verified as uncalled by tracked executable surfaces
before archival.

- `e2e-example.spec.js`: stock Playwright scaffold against `playwright.dev`;
  previously ignored by `playwright.config.js`.
- `postreview_eval.py`: one-off Linux `/mnt/data` post-review evaluator with no
  tracked executable caller.
- `corpus_diagnostics.py`: one-off NRC APS diagnostics script depending on the
  absent root `data_demo/nrc_adams_documents_for_testing` corpus.
- `run_full_export.py`: one-off full export generator depending on the absent
  demo corpus and deleting/recreating `nrc_adams_full_export` when run.
- `run_context_packet_single_export.py`: standalone in-memory seed/export helper
  with no package, harness, or test caller.
