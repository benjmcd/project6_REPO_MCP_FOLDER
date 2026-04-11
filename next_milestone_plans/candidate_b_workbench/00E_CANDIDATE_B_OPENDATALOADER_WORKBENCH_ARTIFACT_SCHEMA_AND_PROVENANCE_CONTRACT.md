# 00E — Candidate B OpenDataLoader Workbench Artifact Schema and Provenance Contract

## Purpose

Ensure Candidate B artifacts carry enough provenance that later reviewers do not have to reconstruct execution conditions by guesswork.

v6 strengthens provenance by requiring package-hash and execution-envelope capture.

---

## A. Required primary artifacts

Candidate B v1 must produce at least:
- `tests/reports/nrc_aps_candidate_b_opendataloader_proof_report.json`
- `tests/reports/nrc_aps_candidate_b_opendataloader_compare_report.json`
- `tests/reports/nrc_aps_candidate_b_opendataloader_retention_manifest.json`
- raw ODL outputs under `tests/reports/nrc_aps_candidate_b_opendataloader_raw/<run_id>/...`

---

## B. Recommended support artifacts

Recommended but optional in v1:
- a run-scoped inventory of generated raw files
- a per-batch summary if the corpus had to be split
- a short reviewer note or markdown summary for human triage

---

## C. Path and hash rules

Every durable Candidate B artifact set must record:
- authoritative SHA256 inventory for each durable report in the retention manifest
- the raw-output root path used for the run
- the corpus manifest SHA256
- the labels/sidecar SHA256 when present

The retention manifest must also record a file inventory with hashes for:
- each raw JSON output
- each raw Markdown output
- each extracted image file

Execution finding from the first actual Candidate B run:
- inline JSON self-hashing is self-referential and was not used as the authority pattern
- the retention manifest is now the authoritative durable-report hash surface
- if batch-shared external image output reuses the same relative image path across multiple documents, that collision must be recorded explicitly as a provenance weakness rather than silently treated as per-document image evidence

---

## D. Required top-level metadata fields

Every durable Candidate B report must include at least:
- `run_id`
- `generated_at_utc`
- `repo_root`
- `git_revision` if locally available
- `python_version`
- `python_executable`
- `java_version`
- `java_vendor` if available
- `odl_package_name`
- `odl_package_version`
- `odl_package_sha256_expected`
- `odl_package_sha256_verified` or explicit `null` with reason
- `odl_config_snapshot`
- `batch_plan`
- `corpus_manifest_ref`
- `corpus_manifest_sha256`
- `labels_ref`
- `labels_sha256`
- `raw_output_root`

---

## E. Required workbench-report fields

The proof report must include at least:
- `documents_attempted`
- `documents_succeeded`
- `documents_failed`
- `failed_documents`
- `struct_tree_present_count`
- `struct_tree_absent_count`
- `element_counts_by_type`
- `hidden_text_document_count`
- `regime_counts`
- `limitation_counts`
- `safety_filter_state`
- `batch_count`
- `execution_seconds`
- `interference_check_status`

---

## F. Required corpus-comparison fields

The compare report must include at least:
- `baseline_reference`
- `candidate_a_reference` when present
- `page_count_matches`
- `page_count_mismatches`
- `text_presence_deltas`
- `structural_gain_signals`
- `control_limitations`
- `non_equivalent_repo_fields`
- `vector_control_pages`
- `scanned_ocr_control_pages`
- `decision_recommendation`

---

## G. Divergence taxonomy

Allowed divergence tags include:
- `expected_structural_gain`
- `expected_hidden_text_signal`
- `expected_multi_column_signal`
- `expected_table_signal`
- `vector_non_equivalence`
- `ocr_owner_path_non_equivalence`
- `raw_output_generation_failure`
- `package_or_env_drift`
- `touch_policy_violation`

---

## H. Struct-tree taxonomy

Use one of:
- `struct_tree_present`
- `struct_tree_absent`
- `struct_tree_unknown`

---

## I. Limitation taxonomy

Use one or more of:
- `vector_limitation_control`
- `scanned_ocr_control`
- `password_control`
- `non_equivalent_owner_field`
- `batch_split_required`
- `output_redaction_required`

---

## J. Provenance interpretation rule

If a report does not capture the execution envelope,
package version,
package hash posture,
and output-root inventory,
it is not strong enough to support any merge-oriented decision.
