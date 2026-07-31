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
