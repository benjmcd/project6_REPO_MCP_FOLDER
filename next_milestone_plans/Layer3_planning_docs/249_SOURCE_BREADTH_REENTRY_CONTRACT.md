# Source Breadth Reentry Contract

Status: planning/control contract for `source_breadth_reentry_contract`.

This contract follows `248_POST_PROVIDER_PRIVATE_ROADMAP_SELECTION_FREEZE.md`. It defines the evidence packet required before source breadth can become implementation-admissible. It does not implement a source runtime, source adapter registry, local upload, local-directory ingestion, web connector retrieval, RAG/vector retrieval, route behavior, DTO behavior, model or migration behavior, production service behavior, executable test behavior, rendered UI controls, connector/destination dispatch, package mutation, broad qualitative/hybrid/RAG runtime, full mockup activation, auth/security behavior, hidden LLM planning, or frontend-only durable authority.

## Contract Decision

```yaml
selected_planning_mode: source_breadth_reentry_contract
entry_decision: authority_packet_required_before_runtime
selected_next_lane: source_breadth_reentry_authority_packet
runtime_status: not_implemented
source_family_selected: false
adapter_input_mode_selected: false
operator_storage_security_model_selected: false
provenance_contract_selected: false
rendered_source_control_selected: false
implementation_entry_allowed_next: false
```

This contract is complete only when it can support an evidence-based yes/no decision for a later `source_breadth_implementation_entry_freeze`.

## Required Authority Packet

The next source-breadth pass must answer these gates from repo-confirmed evidence or explicitly mark them blocked:

- `named_source_use_case`: the concrete operator/product need that current supported sources cannot satisfy;
- `selected_source_family`: exactly one candidate source family, or `none_selected_runtime_blocked`;
- `adapter_input_mode`: server-owned adapter, uploaded artifact, local directory, web connector, read-only inventory, or another single named mode;
- `source_of_truth`: the canonical authority for source identity, bytes, metadata, and freshness;
- `storage_security_model`: where bytes/metadata live, who can read them, and what local/nonlocal exposure is allowed;
- `network_retrieval_policy`: whether network retrieval is forbidden, fake-provider-only, local-only, or explicitly admitted;
- `provenance_contract`: source ids, content hashes, operator decisions, receipt/audit fields, and stale-authority behavior;
- `downstream_semantics`: how the source reaches material preview, Gate B/Gate C, execution, package, handoff/export, and qualitative/RAG lanes;
- `rendered_control_plan`: whether `/review/layer3` changes are required and how headed/headless/theme proof will be run;
- `auth_security_posture`: whether current local/proxy guardrails are sufficient or runtime auth/security must be selected first.

## Admissibility Rules

A later implementation-entry freeze may be written only if:

- one named source use case is selected;
- one source family or one no-runtime outcome is selected;
- current admitted classes are proven insufficient for that use case;
- storage/security and provenance are source-of-truth complete;
- unsupported fields remain fail-closed;
- tests can prove both admission and negative invariants;
- rendered controls, if any, have a stable headed/headless theme proof plan;
- auth/security and leakage posture is not inferred.

## Default Ordering

If the authority packet proves runtime admissibility, the next implementation should be the smallest safe source tranche:

- one selected source family;
- one owner service boundary;
- one route/API family only if required;
- one storage/provenance contract;
- no rendered controls unless the source use case cannot be operated without them;
- no connector/destination, package mutation, broad RAG, full mockup, or auth/security expansion bundled into the source pass.

If the authority packet does not prove admissibility, the correct outcome is a no-runtime closeout, not partial implementation.

## Negative Invariants

- no broad source expansion by default;
- no source adapter registry by default;
- no local upload by default;
- no local-directory ingestion by default;
- no arbitrary local path input;
- no web connector retrieval by default;
- no RAG/vector retrieval by default;
- no vector index creation;
- no unbounded runtime DB source read;
- no browser-local source authority;
- no package mutation or reconstruction;
- no provider/public URL runtime;
- no connector/destination dispatch;
- no broad qualitative/hybrid/RAG execution;
- no hidden LLM planning;
- no full mockup activation;
- no auth/security behavior change;
- no route/API/DTO/model/migration/service behavior change from this contract alone.

## Validation Standard

The reentry packet must update the progress manifest, proof manifest, progress board, README, and progress checker before any source runtime code is written. The checker must fail if the packet claims source runtime readiness without a named source use case, selected source family, storage/security posture, provenance contract, and explicit negative invariants.

## Stop Condition

Stop before implementation if any gate remains inferred, product priority is ambiguous between source breadth and connector/destination delivery, the proposed source family requires auth/security that is not selected, or the source path depends on local paths, browser storage, mockups, prompt/model state, or copied operator values as durable authority.
