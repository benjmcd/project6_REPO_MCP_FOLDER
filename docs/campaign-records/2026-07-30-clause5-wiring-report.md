# Clause-5 wiring report — Codex 019faabd (COMPLETE/PASS)

Date: 2026-07-30. Commit b75bc7d8 (parent b8625b25). The amended NRC acquisition-success clause 5 is
now wired as the evaluation-time blob rehash: requires exactly one NRC target, validates
downloaded_sha256 + raw_storage_ref binding, derives the canonical blob path from the digest (not an
arbitrary stored path), rehashes the current blob through the bounded handle-safe reader, requires
byte-count + hash equality across {fresh rehash, target content-address, rederived ledger body_sha256,
counter decoded-body sha256}, returns NrcAcquisitionSuccessEvidence.blob_rehash_raw_sha256. Fail-closed
on missing/unsafe/ambiguous/path-mismatch/size-mismatch/hash-mismatch before any marker/DB/event
mutation; target query selects only downloaded_sha256 + raw_storage_ref, never source_reference_json;
receipt/linkage/provenance stay Phase-B (fail-if-called in fixture). 2 files (service +110/-6, tests
+174/-36). Control suite 197 passed (193 baseline + 4 clause-5). Failure legs proven: blob-vs-ledger,
blob-vs-counter, same-length one-byte tamper, missing blob — each with full before/after row snapshots
showing no ScienceBase marker. Independent 5.6-sol reviews (arch/code/test/security) PASS/APPROVE.
No push, no B1a touch, no plan/campaign edit. Session-internal reviews — see adversarial Fable pass.

## Adversarial verification (Fable, 2026-07-30) — CLAUSE5-CORRECT-AND-FAILCLOSED
Pinned to commit b75bc7d8. Every attack target run to ground, no critical/major:
- Fail-closed completeness PASS: _rehash_nrc_artifact_blob (svc 744-815) — every path raises before
  marker creation (1092) and any DB write (1177); zero-mutation-on-failure proven at ROW-CONTENT level
  (_db_state_snapshot equality) in all four failure params, not just counts. One success return, after rehash.
- Fresh rehash PASS (reproduced): byte-stream SHA-256 (hash_locked_raw_file/_hash_fd), no DB read inside;
  stored downloaded_sha256 used only to derive the canonical path + as one comparand, never as the result.
  Same-length one-byte tamper param raises nrc_acquisition_success_blob_mismatch — mechanically discriminates
  the stored-column tautology (which would DID-NOT-RAISE).
- No receipt dependency PASS: zero grep hits for derive_connector_origin_receipt/assert continuity/
  source_reference_json/origin_receipt in the arming service; fixture plants a poisoned source_reference_json
  provably never selected (SQL capture: one target SELECT naming only downloaded_sha256 + raw_storage_ref).
- Leg independence PASS: four distinct sources (fresh bytes at digest-derived path; stored column; ledger
  body_sha256 from eligibility-gated events; counter decoded-body from manifest-bound http.jsonl). Impl is
  strictly TIGHTER than spec (adds ==stored-column + size equality, fail-closed direction).
- TOCTOU covered: resolve_current_egress_authority (svc 1449-1454) re-runs the full predicate incl. fresh
  rehash on every ScienceBase authority rederivation (connectors_sciencebase.py:480) — post-arming tamper
  caught at consume time; hash_locked_raw_file before/after snapshot-equality closes the mid-read window.
- Scope PASS: exactly 2 files, no plan/campaign/B1a/inbox/bc47335c touch, no push.

CORRECTION (minor): control-suite count is 198 passed on Windows (194 baseline + 4 clause-5), OR 197
passed + 1 platform-skip on non-NT (the +1 is an NTFS-ADS Windows-only test at test_egress_auth.py:833,
unrelated to clause 5). The report's "197 passed" recorded a non-NT run's passed count and omitted the
skip; favorable direction (my Windows run passes a strict superset). Focused clause-5 slice reproduces
exactly: 11 passed.
DEFERRED to Task 8: one end-to-end case running evaluate_nrc_acquisition_success through the REAL
derive_terminal_request_ledger (clause-5 tests currently inject a fabricated ledger, pinned to a canonical
projection hash so it cannot drift from the production interface — adequate now, hardened at Task 8).
