# Layer 3 SEC XBRL operator authority resolver gate

## Scope

This pass adds a validate-only gate for the server-owned authority resolver used
by the operator-review workflow open route.

The current runtime implementation is a default-empty server-owned registry.
Trusted runtime code can register offline evidence mappings behind opaque public
handles, but the API route cannot register or submit evidence. Empty registry,
unknown handle, raw handle, and proof-source-hash mismatch cases fail closed.

The gate is distinct from the multi-filing evidence authority gate:

- multi-filing authority proves redacted evidence handles exist for enough
  filings and for the named S1 proof scope;
- resolver readiness proves the API can resolve only those governed handles and
  fails closed for everything else.

The default S1 proof scope is:

- `fizz-10k-proof`;
- `fizz-10q-proof`;
- `ccj-10k-proof`.

The resolver must declare and bind every handle in that scope. Three other
ready-looking handles are not sufficient.

## Gate inputs

The gate accepts hash/count/state evidence from:

- the operator API contract gate;
- the multi-filing evidence authority gate;
- a resolver specification containing only public handle names and boolean
  readiness flags.

It does not accept raw filings, raw CompanyFacts payloads, local paths, SEC URLs,
accessions, raw values, storage roots, or resolved-fact identifiers.

## Required resolver evidence

The resolver must prove:

- a server-owned resolver is declared;
- the resolver registry is default-empty;
- it uses the multi-filing authority inventory;
- it binds every named S1 proof handle from the multi-filing evidence authority
  gate;
- it returns an offline evidence mapping for the atomic open workflow path;
- it rejects unknown handles;
- it rejects proof-source-hash mismatches;
- it rejects raw paths, URLs, and accessions;
- it preserves authority hashes;
- it fails closed;
- it performs no network, source acquisition, or Arelle invocation.

The resolver must also prove the negative invariants:

- caller-supplied evidence is not admitted;
- raw CompanyFacts requests are not admitted;
- local-path, SEC-URL, and accession resolution are not admitted;
- source acquisition is not performed;
- Arelle is not invoked;
- network is not performed;
- value reveal is not performed;
- production database state is not touched;
- production readiness is not claimed.

## Admission relationship

The production-admission gate now requires this gate as
`operator_authority_resolver`. This prevents the project from treating a safe
API contract and a ready evidence matrix as sufficient when no governed runtime
handle-resolution path has been proven.

The runbook and targeted-validation gates also track this dependency:

- runbooks must cover `operator_authority_resolver_failure`;
- targeted validation must include `operator_authority_resolver_gate_tests`;
- targeted validation must include `operator_review_open_api_route_tests`;
- targeted validation must include `production_admission_gate_chain_tests`.

The gate can report ready only as review evidence. It keeps:

- `operator_authority_resolver_enabled=false`;
- `runtime_default_enabled=false`;
- `value_reveal_performed=false`;
- `production_database_touched=false`;
- `production_readiness_claimed=false`.
