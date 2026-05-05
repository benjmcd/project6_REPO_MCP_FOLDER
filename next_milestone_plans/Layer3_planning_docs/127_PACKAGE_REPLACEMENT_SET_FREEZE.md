# Layer 3 Replacement Package Set Authority Freeze

Status: implementation-entry freeze plus bounded runtime contract for `replacement_package_set_authority`.

This artifact resolves the prerequisite discovered after `126_PACKAGE_COMMIT_FREEZE.md`: a package supersession commit cannot be implemented until the repo has an authority model for a replacement immutable package set. The exact runtime admitted by this contract is `POST /api/v1/layer3/package/replacement-set/record`, backed by `backend/app/services/layer3_replacement_package_set_authority.py` and `L3ReplacementPackageSetAuthority`. It records replacement package-set ids, refs, hashes, and authority basis only. It does not create or update `L3OutputPackage` rows, write package payload files, implement package supersession commit, render UI controls, dispatch connectors, widen sources, run qualitative/hybrid/RAG work, create provider/public URLs, activate mockups, or perform authentication/security work.

## Authority Snapshot

- authority_worktree: `C:\Users\benny\Downloads\worktree_for_audits`
- baseline_ref: `project6-origin/main`
- implementation_branch: `codex/l3-replacement-package-set-freeze`
- predecessor preview runtime: `122_PACKAGE_MUTATION_FREEZE.md`
- predecessor commit-entry freeze: `126_PACKAGE_COMMIT_FREEZE.md`
- current package row authority: `backend/app/models/models.py` `L3OutputPackage`
- current uniqueness blocker: `uq_l3_output_package_session_kind` keeps one output package per `(session_id, package_kind)`
- selected runtime route: `/api/v1/layer3/package/replacement-set/record`
- owner service: `backend/app/services/layer3_replacement_package_set_authority.py`
- authority model: `L3ReplacementPackageSetAuthority`
- migration: `0018_layer3_replacement_package_set_authority.py`
- current admitted package lifecycle runtimes: `package_supersession_preview_only` and `replacement_package_set_authority`
- current deferred capability: `package_mutation_reconstruction` remains deferred
- evidence boundary: live source, tests, and `tools/l3-progress-check.py` outrank this document

## Decision

The next package lifecycle prerequisite is narrowed to exactly this authority mode:

- selected_package_lifecycle_mode: `replacement_package_set_authority`

This is a bounded runtime admission, not broad package mutation/reconstruction. It exists because `package_supersession_commit_entry` requires replacement package-set ids, refs, and hashes, but the current live package model has no replacement package-row namespace and no safe way to create a second `L3OutputPackage` set for the same session and package kinds.

The selected runtime authority must not reuse existing `L3OutputPackage` rows as replacement rows. It must not mutate existing package rows or payload files. It must not treat a no-op lineage record as package reconstruction. It must fail closed when source ids/refs/hashes are stale, replacement refs/hashes are missing, replacement refs reuse source payload refs, replacement hash is stale, or the authority basis hash is stale.

## Selected Authority Shape

This slice selects option A from the freeze:

- option A: a dedicated replacement package set table that references immutable package payload refs/hashes without using `L3OutputPackage` for replacement rows;
- option B: a package-set namespace model that lets replacement package rows coexist without weakening existing `uq_l3_output_package_session_kind` authority;
- option C: a separately frozen package construction variant lane that creates replacement package artifacts in a new immutable namespace before any commit can reference them.

Option B and option C remain deferred. The selected runtime preserves existing package construction, package review submit, handoff/export, APS handoff, external export/download, signed-reference, internal connector record, and package supersession preview behavior.

## Required Future Fields

A future replacement package set authority record must preserve at least:

- `client_request_id`
- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `reconciliation_record_id`
- `source_package_set_hash`
- `source_output_package_ids`
- `source_package_kinds`
- `source_payload_refs`
- `source_payload_hashes`
- `replacement_package_set_id`
- `replacement_package_set_hash`
- `replacement_package_kinds`
- `replacement_payload_refs`
- `replacement_payload_hashes`
- `authority_basis_hash`
- `operator_decision`

`operator_decision` must be exactly `record_replacement_package_set_authority` for the future authority-recording lane.

## Required Runtime Negative Proof

This runtime is acceptable only when tests prove:

- replacement package authority cannot be recorded with stale source package ids, refs, or hashes;
- replacement package authority cannot be recorded with missing replacement refs or hashes;
- duplicate `client_request_id` behavior is deterministic;
- concurrent duplicate replacement authority requests cannot create duplicate replacement authority records;
- existing `L3OutputPackage` rows are unchanged;
- existing package payload files are unchanged;
- existing `L3ReconciliationRecord.summary_json` package construction state is unchanged unless a separate lineage model is created;
- package supersession commit remains blocked until replacement package-set authority exists;
- no provider/public URL, connector/destination dispatch, source expansion, qualitative/hybrid/RAG execution, full mockup activation, or auth/security behavior is admitted.

Current proof surfaces:

- `backend/tests/test_layer3_api.py::test_layer3_api_replacement_package_set_authority_records_without_package_row_or_payload_mutation`
- `backend/tests/test_layer3_api.py::test_layer3_api_replacement_package_set_authority_prechecks_fail_closed`
- `backend/tests/test_layer3_replacement_package_set_authority.py::test_replacement_package_set_authority_concurrent_duplicate_request_records_one_authority`
- `backend/tests/test_layer3_replacement_package_set_authority.py::test_replacement_package_set_authority_migration_defines_durable_unique_authority`

## Positive Invariants

The current bounded runtime slice is acceptable only when:

- `127_PACKAGE_REPLACEMENT_SET_FREEZE.md` exists and selects only `replacement_package_set_authority`;
- `/api/v1/layer3/package/replacement-set/record` is the only replacement package-set authority runtime route;
- `backend/app/services/layer3_replacement_package_set_authority.py` owns the runtime;
- `L3ReplacementPackageSetAuthority` records replacement package-set metadata without using replacement `L3OutputPackage` rows;
- `0018_layer3_replacement_package_set_authority.py` preserves unique `client_request_id` and `authority_basis_hash`;
- `package_supersession_preview_only` and `replacement_package_set_authority` are the only admitted package lifecycle runtimes;
- `package_mutation_reconstruction` remains deferred in `backend/app/services/layer3_state_action_contract.py`;
- `L3OutputPackage` still has `uq_l3_output_package_session_kind`, so the replacement-set blocker remains explicit;
- `126_PACKAGE_COMMIT_FREEZE.md` states package supersession commit remains blocked until a dedicated supersession lineage model/migration is implemented and proven;
- no UI control, replacement `L3OutputPackage` row creation, package row mutation, package payload write, package supersession commit behavior, connector dispatch, source widening, qualitative/hybrid/RAG execution, provider/public URL behavior, full mockup activation, or auth/security behavior is added by this slice;
- `105_deferred-gates.md`, `118_L3_GOAL_AUDIT.md`, and `120_L3_CLOSEOUT.md` label this as a bounded metadata-authority runtime only;
- `tools/l3-progress-check.py` fails closed if this boundary drifts.

## Negative Invariants

This slice must not accidentally admit or implement:

- replacement package row creation;
- replacement package payload creation;
- package row update or deletion;
- package payload rewrite, overwrite, deletion, or reconstruction;
- package supersession commit runtime;
- package variant editing;
- package-review submit/decision changes;
- handoff/export changes;
- APS handoff changes;
- external export/download changes;
- connector/destination dispatch changes;
- provider/public URL support;
- source/upload/local-directory/RAG/vector expansion;
- qualitative/hybrid/RAG execution;
- `L3PassRun` creation;
- `AnalysisRun` creation;
- `AnalysisArtifact` creation;
- `L3OutputPackage` creation, update, or deletion;
- `L3ReconciliationRecord` creation, update, or deletion;
- frontend-only durable state;
- hidden LLM planning;
- rendered package mutation controls;
- full mockup activation;
- authentication/security hardening.

## Future Runtime Stop Conditions

Stop before implementation if the intended change requires:

- weakening `uq_l3_output_package_session_kind` without a separate package-set namespace design;
- using the source package ids as replacement package ids;
- accepting replacement package bytes or edited package content from the browser;
- writing replacement payload files without a separately frozen artifact-generation owner;
- committing package supersession without a replacement package-set authority record;
- dispatching to connectors or destinations;
- creating provider/public URLs;
- widening source/upload/local-directory/RAG/vector inputs;
- broad qualitative, hybrid, or RAG execution;
- full mockup activation;
- authentication/security work while that lane remains deferred.
