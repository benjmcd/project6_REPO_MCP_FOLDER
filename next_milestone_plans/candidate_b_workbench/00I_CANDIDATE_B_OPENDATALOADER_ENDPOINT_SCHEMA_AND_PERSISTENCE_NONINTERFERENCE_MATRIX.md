
# 00I — Candidate B OpenDataLoader Endpoint, Schema, and Persistence Non-Interference Matrix

## Purpose

Make the outward non-interference rule operational.

The live root README already names a broad NRC APS connector/API surface.
Candidate B v1 must not interfere with it.

---

## A. Endpoints explicitly frozen in v1

These surfaces are named by the live root README and are all read-only / non-interference surfaces for Candidate B v1:
- `POST /api/v1/connectors/nrc-adams-aps/runs`
- `POST /api/v1/connectors/nrc-adams-aps/content-search`
- evidence bundle endpoints
- citation pack endpoints
- evidence report endpoints
- evidence report export endpoints
- evidence report export package endpoints
- context packet endpoints
- context dossier endpoints
- deterministic insight artifact endpoints
- deterministic challenge artifact endpoints
- generic connector run/target/event/report/content-unit endpoints

Candidate B v1 must not add, remove, rename, widen, or change semantics for any of those.

---

## B. Run-detail refs explicitly frozen in v1

The root README also states that additive NRC APS run-detail refs already exist for:
- evidence citation packs
- evidence reports
- evidence report exports
- evidence report export packages
- context packets
- context dossiers
- deterministic insight artifacts
- deterministic challenge artifacts
- the corresponding failure refs

Candidate B v1 must not add any new run-detail ref family.

---

## C. Persistence / schema / migration posture

Candidate B v1 must not change:
- DB models
- schemas
- migrations
- persistence-layer write paths
- runtime artifact row shapes
- connector run payloads
- review/runtime query shapes

Candidate B v1 is strictly a tests/report workbench lane.

---

## D. Output location rule

Candidate B v1 may persist only:
- tests-side report JSON
- tests-side raw OpenDataLoader outputs
- optional tests-side sidecar labels/manifest files
- non-authoritative planning docs

It may not persist new rows or refs into the live runtime artifact namespaces.

---

## E. Stop rule

If implementing Candidate B requires changing any endpoint, run-detail ref, schema, or persistence contract,
then Candidate B v1 has exceeded its allowed scope and must stop.


---
