# 966 - Candidate B Default-Promotion Readiness Freeze

## Purpose

Freeze the smallest governed Candidate B default-promotion readiness audit that may be implemented after this decision is merged to current main.

This is a read-only readiness gate. It does not promote Candidate B to default, does not change the `baseline` default, and does not reinterpret Candidate B as a `visual_lane_mode`.

## Current-main authority check

As of current main `ea00174eff33bd253585664dccba5d7029fe0dd2`, Candidate B has two governed Layer 3 material authority bridges:

- `candidate_b_bundle_curated_json_md_to_layer3_material_authority_v1`
- `candidate_b_runtime_source_to_layer3_material_authority_v1`

Current main also has current-main test proof that both the bundle-backed curated markdown path and runtime-source curated markdown path can flow through Layer 3 source-directory scan, material preview, Gate B, hybrid qualitative analysis, package commit/review, handoff/export, same-origin delivery, provider-private redacted lifecycle, internal webhook dispatch/status, and session status projection.

Current main still does not admit a Candidate B default selector switch.

This document admits exactly one future implementation slice after merge:

- `candidate_b_default_promotion_readiness_audit_v1`

## Preserved posture

- `baseline` remains the default corpus-processing posture.
- Candidate A remains the admitted `candidate_a_page_evidence_v1` visual-lane variant.
- Candidate B remains either bundle-backed workbench evidence or the opt-in `document_processing_engine="candidate_b_opendataloader_pdf"` processing-engine path.
- Candidate B remains not a `visual_lane_mode`.
- Candidate B default promotion remains blocked unless a later separate promotion implementation is explicitly selected after this readiness audit passes.

## Admitted readiness audit

The audit may produce a server-authoritative, read-only readiness result over one exact Candidate B default-promotion candidate:

- candidate family: `candidate_b_opendataloader_pdf`
- eligible processing scope: PDF/corpus processing already admitted to the Candidate B runtime-source bridge
- Layer 3 bridge families: bundle-backed curated JSON/MD and runtime-source curated JSON/MD

The audit must record:

- readiness audit id;
- readiness mode `candidate_b_default_promotion_readiness_audit_v1`;
- baseline current-default evidence;
- Candidate A admitted-variant evidence;
- Candidate B non-visual-lane evidence;
- selected baseline run id;
- selected Candidate A run id;
- selected Candidate B bundle id;
- selected Candidate B runtime run id;
- bundle validation result;
- runtime validation result;
- strict compare target set for bundle and runtime sources;
- bundle bridge authority hashes;
- runtime bridge authority hashes;
- bundle downstream proof coverage;
- runtime downstream proof coverage;
- operator-visible provenance/status evidence;
- rollback-to-baseline readiness;
- fail-closed stale/missing artifact behavior;
- regression disposition against baseline and Candidate A;
- exact eligible corpus scope;
- blocked or ready state;
- blocked reasons when any required evidence is absent, stale, too broad, or contradictory.

## Required evidence

The audit must fail closed unless all of the following are proven by current-main evidence or selected live receipts:

- baseline remains current default;
- Candidate A remains `candidate_a_page_evidence_v1` and its semantics are not weakened;
- Candidate B is not requested or represented as a `visual_lane_mode`;
- baseline, Candidate A, and Candidate B comparison evidence exists for the selected bundle source;
- baseline, Candidate A, and Candidate B comparison evidence exists for the selected runtime source;
- bundle-source `tools/validate_wb_prep.py` validation passes for the selected bundle;
- runtime-source `tools/validate_wb_prep.py` validation passes for the selected runtime run;
- the selected bundle bridge receipt is present and matches its manifest/authority hashes;
- the selected runtime bridge receipt is present and matches its manifest/authority hashes;
- Candidate B bundle-derived material reaches Layer 3 downstream E2E through delivery, provider-private redacted use/revoke, internal webhook, and status projection;
- Candidate B runtime-derived material reaches Layer 3 downstream E2E through delivery, provider-private redacted use/revoke, internal webhook, and status projection;
- no unacceptable regression against baseline or Candidate A is recorded for the selected compare target set;
- rollback to `baseline` is explicitly available and does not depend on Candidate B artifacts;
- missing, stale, or mismatched bundle/runtime/bridge/downstream evidence blocks readiness;
- operator-visible status and provenance can explain the selected Candidate B source, bridge receipts, downstream proof, and blocked/ready state.

## Output states

The readiness audit may return only these states:

- `candidate_b_default_promotion_readiness_blocked`
- `candidate_b_default_promotion_ready_for_separate_selection`

The ready state is not an implementation approval for default promotion. It only authorizes selecting a later, separately frozen default-selector implementation slice.

## Excluded behavior

The readiness audit must not:

- change the default selector;
- enable Candidate B as default;
- treat Candidate B as a `visual_lane_mode`;
- change baseline default behavior;
- weaken Candidate A semantics;
- ingest PDFs, images, Office files, or arbitrary source families into Layer 3;
- ingest broad Candidate B runtime DB or storage rows;
- write provider objects;
- dispatch arbitrary connectors;
- add RAG/vector/model runtime;
- expose credentials, raw provider URLs, raw local paths, or provider-private tokens;
- add browser-storage authority;
- add frontend-only durable authority;
- activate the full mockup;
- bypass validate-only workbench prep checks;
- accept historical reports without live artifact roots or selected receipts when the audit requires live proof.

## Stop conditions

Implementation must stop if:

- current main does not still preserve `baseline` as default;
- Candidate A admission cannot be verified without changing its semantics;
- Candidate B is only available as a `visual_lane_mode`;
- selected bundle or runtime compare targets are empty;
- bundle or runtime validation fails;
- selected bridge receipts are missing, stale, or hash-mismatched;
- bundle or runtime downstream proof is absent or only indirectly inferred;
- regression disposition is missing or records unacceptable regression;
- rollback-to-baseline behavior is undefined;
- any requested audit input would require broad source expansion, runtime DB expansion, provider writes, connector dispatch, model/RAG runtime, frontend-only authority, auth/security changes, or full mockup activation.

