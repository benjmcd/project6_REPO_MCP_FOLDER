# 700 - Package Rebuild Corrected Artifact Source Authority Selection Freeze

## Status

Status: corrected-artifact source authority selection freeze for `rebuild_package_from_corrected_artifacts`.

Doc: `700_PACKAGE_REBUILD_CORRECTED_ARTIFACT_SOURCE_AUTHORITY_SELECTION_FREEZE.md`.

Predecessor current-main sync doc: `699_PACKAGE_REBUILD_FROM_CORRECTED_ARTIFACTS_IMPLEMENTATION_ENTRY_AUTHORITY_AUDIT_CURRENT_MAIN_SYNC.md`.

Current-main preflight commit: `389ca519549ae86e7addfc1b1375d9c37315cd7d`.

Selected surface: `package_mutation_reconstruction`.

Selected package lifecycle action: `rebuild_package_from_corrected_artifacts`.

Selected corrected-artifact authority source: `operator_review_corrections_server_owned_corrected_package_artifact_set`.

Selected source class: `server_owned_corrected_package_artifact_authority`.

Selected implementation-entry posture: `freeze_operator_review_corrections_corrected_package_artifact_set_implementation_entry_after_source_authority_sync`.

Entry decision: `source_authority_selection_freeze_only`.

Runtime status in this pass: `not_implemented_in_this_pass`.

## Selection Basis

Current main has execution result review notes and reviewed output item state, plus replacement package artifact materialization, manifest, namespace, activation, downstream active-package-authority adoption, and external local export. Current main does not have a governed corrected-artifact source route, model, migration, manifest, hash, or rebuild basis.

This freeze selects `operator_review_corrections_server_owned_corrected_package_artifact_set` as the corrected-artifact authority source because it is the narrowest path that can turn operator-reviewed corrections into a server-owned artifact basis without admitting browser-supplied package bytes, arbitrary local paths, URLs, source expansion, RAG/vector behavior, connector/destination dispatch, or provider-public delivery/use.

The selected source must be server-owned and derived from existing Layer 3 package/review authority. It must not treat free-form review notes alone as corrected artifact authority. A future implementation-entry freeze must define how operator correction intent maps to corrected package artifact refs/hashes and how those corrected artifacts are generated or recorded without accepting arbitrary package payloads from the browser.

## Required Future Source Contract

A later implementation-entry freeze for this source must define:

- exact owner route and owner service;
- exact durable model and migration if new durable state is required;
- exact allowed request fields;
- required existing authority refs: session, plan, pass, reconciliation, source package set, execution result review, package review, package supersession preview, and replacement package lifecycle refs where applicable;
- corrected artifact set id, corrected artifact refs, corrected artifact hashes, corrected artifact byte sizes, artifact namespace, manifest hash, and corrected-artifact basis hash;
- idempotency contract for same-key replay, same-key conflict, same-basis replay, and conflicting corrected artifacts;
- failure lifecycle for stale source package, stale review, stale correction, wrong session/pass/reconciliation, wrong package kind, missing artifact, tampered hash, partial write, and unsupported correction state;
- all-or-nothing server-owned artifact write behavior if artifact files are produced;
- response redaction contract that exposes stable refs/hashes/sizes/status/history without raw local paths;
- read-only status/history shape and whether rendered status is required before package rebuild runtime.

## Non-Admission Boundary

This freeze admits no runtime implementation. It does not add a backend route, DTO, response model, model, migration, service behavior, executable backend test behavior, rendered UI control, package rebuild runtime, package payload rewrite, source `L3OutputPackage` row mutation, corrected package artifact bytes, browser-supplied package bytes, browser-supplied replacement bytes, browser-generated diffs, arbitrary artifact refs, arbitrary hashes, local paths, URLs, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, raw local path exposure, or hidden LLM planning.

## Required Validation

This freeze branch must pass:

```powershell
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
git diff --check
```

No backend runtime test or headed/headless E2E run is required because this freeze changes planning/control metadata only.

## Next Posture

After this freeze is merged, the next exact posture is `current_main_sync_operator_review_corrections_corrected_package_artifact_source_authority_selection_freeze`.

After current-main sync, the next exact posture is `freeze_operator_review_corrections_corrected_package_artifact_set_implementation_entry_after_source_authority_sync`. Runtime remains blocked until that separate implementation-entry freeze exists and admits exactly one bounded corrected-artifact source authority slice.
