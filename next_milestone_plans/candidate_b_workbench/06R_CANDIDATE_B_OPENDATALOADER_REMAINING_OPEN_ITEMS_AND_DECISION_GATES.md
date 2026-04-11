# 06R - Candidate B OpenDataLoader Remaining Open Items and Decision Gates

## Purpose

Record the exact remaining nonblocking caveats after the adopted Candidate B second-iteration workbench baseline and freeze the current stop-and-hold posture.

This file is now a closure/handoff note.
It is not an implementation-entry gate list anymore.

---

## Current shared-main baseline

Resolved posture:
- the adopted Candidate B second-iteration workbench baseline is now the active shared-main Candidate B state
- Candidate B remains workbench-only, non-admitted, non-runtime, and non-selector-active
- baseline comparison remains the only mandatory comparison posture for the frozen objective
- secondary Candidate A comparison remains `NO`
- no third iteration starts by implication from the current shared-main state

---

## Remaining nonblocking caveat 1 - footer-node emission on `ml17123a319`

### What remains true
The adopted second-iteration proof report still records footer-node emission for `ml17123a319` even with `include_header_footer=False`.

### Hard rule
Treat this as an explicit package-behavior limitation/control-noise finding.
Do not describe Candidate B as footer-clean or runtime-ready.

---

## Remaining nonblocking caveat 2 - installed-package wheel-hash reproving

### What remains true
The adopted second-iteration proof report still records:
- `odl_package_sha256_expected = 18093fa87a3089abdba14043c187f85c6a4af48c4597710de32d90e95666313e`
- `odl_package_sha256_verified = null`
- `odl_package_sha256_verification_reason = installed_package_directory_not_reconstructable_to_pinned_wheel_hash`

### Hard rule
Treat the pinned wheel hash as the planning/install anchor only.
Do not overclaim installed-package reproving from the shared-main baseline.

---

## Stop-and-hold rule

Current operator posture:
- keep the adopted second-iteration Candidate B state as the current workbench-only comparator baseline
- do not start a third iteration by default
- do not admit, integrate, or selector-activate Candidate B by implication
- any future Candidate B work must begin from a new explicitly frozen objective

---

## Explicit non-next-steps

This record does not authorize:
- a third Candidate B iteration
- runtime integration
- selector admission
- hidden-consumer widening
- review/report/export schema widening
- backend dependency normalization
- helper-script or generic framework work
